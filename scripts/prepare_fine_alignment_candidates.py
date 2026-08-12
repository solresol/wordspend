#!/usr/bin/env python3
"""Prepare an explicitly unreviewed fine-alignment queue for one book."""

from __future__ import annotations

import argparse
import csv
import hashlib
import sys
from io import StringIO
from pathlib import Path

from prepare_book_alignments import indexed_rows, read_rows
from validate_prepared_translation_texts import repo_root, resolve_repo_path
from wordspend.fine_alignment import (
    PROPOSAL_METHOD,
    extract_target_paragraphs,
    propose_source_ranges,
)


CANDIDATE_COLUMNS = [
    "candidate_id",
    "work_id",
    "source_edition_id",
    "translation_source_id",
    "book",
    "segment_index",
    "alignment_level",
    "proposal_method",
    "source_start_ref",
    "source_end_ref",
    "source_line_count",
    "source_editorially_deleted_line_count",
    "target_paragraph",
    "target_start_token",
    "target_end_token",
    "target_token_count",
    "target_start_char",
    "target_end_char",
    "source_text",
    "target_text",
    "source_prepared_sha256",
    "target_book_text_sha256",
    "translation_prepared_sha256",
    "proposal_status",
    "review_status",
    "paper_facing_eligible",
    "analysis_status",
]

SUMMARY_COLUMNS = [
    "work_id",
    "source_edition_id",
    "translation_source_id",
    "book",
    "proposal_method",
    "candidate_path",
    "candidate_bytes",
    "candidate_sha256",
    "candidate_count",
    "source_line_count",
    "target_paragraph_count",
    "target_token_count",
    "proposal_status",
    "review_status",
    "paper_facing_eligible",
    "analysis_status",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--translation-source-id", default="homer-iliad-en-butler-pg2199"
    )
    parser.add_argument("--book", type=int, default=1)
    parser.add_argument(
        "--translation-book-manifest", default="data/prepared/translation_books.csv"
    )
    parser.add_argument("--source-manifest", default="data/prepared/source_editions.csv")
    parser.add_argument("--book-alignment-manifest", default="data/prepared/book_alignments.csv")
    parser.add_argument("--output-dir", default="data/prepared/fine_alignment_candidates")
    parser.add_argument("--summary", default="data/prepared/fine_alignment_candidates.csv")
    return parser.parse_args()


def csv_payload(columns: list[str], rows: list[dict[str, object]]) -> bytes:
    handle = StringIO(newline="")
    writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return handle.getvalue().encode("utf-8")


def display_path(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def file_matches(path: Path, expected_sha256: str) -> bool:
    return hashlib.sha256(path.read_bytes()).hexdigest() == expected_sha256


def main() -> int:
    args = parse_args()
    root = repo_root()
    if args.book < 1:
        print("--book must be positive", file=sys.stderr)
        return 1

    try:
        book_summaries = indexed_rows(
            resolve_repo_path(args.translation_book_manifest, root), "source_id"
        )
        source_manifests = indexed_rows(
            resolve_repo_path(args.source_manifest, root), "source_edition_id"
        )
        book_alignments = read_rows(
            resolve_repo_path(args.book_alignment_manifest, root)
        )
        summary = book_summaries[args.translation_source_id]
    except (KeyError, OSError, ValueError) as error:
        print(error, file=sys.stderr)
        return 1

    matches = [
        row
        for row in book_alignments
        if row["translation_source_id"] == args.translation_source_id
        and int(row["segment_ref"]) == args.book
    ]
    if len(matches) != 1:
        print("Expected exactly one upstream book alignment", file=sys.stderr)
        return 1
    upstream = matches[0]
    source_manifest = source_manifests[upstream["source_edition_id"]]

    if upstream["paper_facing_eligible"] != "yes":
        print("Upstream book alignment is not paper-facing eligible", file=sys.stderr)
        return 1
    if summary["machine_human_status"] != "human_published":
        print("Translation is not human_published", file=sys.stderr)
        return 1

    book_path = resolve_repo_path(summary["book_path"], root)
    source_path = resolve_repo_path(source_manifest["prepared_path"], root)
    if not file_matches(book_path, summary["book_sha256"]):
        print("Translation book file checksum does not match its manifest", file=sys.stderr)
        return 1
    if not file_matches(source_path, source_manifest["prepared_sha256"]):
        print("Source line file checksum does not match its manifest", file=sys.stderr)
        return 1

    book_rows = read_rows(book_path)
    selected_books = [row for row in book_rows if int(row["book"]) == args.book]
    if len(selected_books) != 1:
        print("Expected exactly one translation book row", file=sys.stderr)
        return 1
    book_row = selected_books[0]
    if book_row["book_text_sha256"] != upstream["target_book_text_sha256"]:
        print("Translation book checksum does not match upstream alignment", file=sys.stderr)
        return 1

    source_lines = [
        row for row in read_rows(source_path) if int(row["book"]) == args.book
    ]
    if not source_lines:
        print("Source edition has no lines for requested book", file=sys.stderr)
        return 1

    try:
        paragraphs = extract_target_paragraphs(
            book_row["text"], book_row["target_language_code"]
        )
        candidates = propose_source_ranges(source_lines, paragraphs)
    except ValueError as error:
        print(error, file=sys.stderr)
        return 1

    rows: list[dict[str, object]] = []
    for candidate in candidates:
        lines = source_lines[candidate.source_start_index : candidate.source_end_index]
        rows.append(
            {
                "candidate_id": (
                    f"{upstream['source_edition_id']}--{args.translation_source_id}"
                    f"--book-{args.book:02d}--segment-{candidate.segment:03d}"
                ),
                "work_id": upstream["work_id"],
                "source_edition_id": upstream["source_edition_id"],
                "translation_source_id": args.translation_source_id,
                "book": args.book,
                "segment_index": candidate.segment,
                "alignment_level": "source_line_range_to_translation_paragraph",
                "proposal_method": PROPOSAL_METHOD,
                "source_start_ref": lines[0]["reference"],
                "source_end_ref": lines[-1]["reference"],
                "source_line_count": len(lines),
                "source_editorially_deleted_line_count": sum(
                    line["line_status"] == "editorially_deleted" for line in lines
                ),
                "target_paragraph": candidate.target.paragraph,
                "target_start_token": candidate.target.start_token,
                "target_end_token": candidate.target.end_token,
                "target_token_count": candidate.target.token_count,
                "target_start_char": candidate.target.start_char,
                "target_end_char": candidate.target.end_char,
                "source_text": "\n".join(line["text"] for line in lines),
                "target_text": candidate.target.text,
                "source_prepared_sha256": source_manifest["prepared_sha256"],
                "target_book_text_sha256": book_row["book_text_sha256"],
                "translation_prepared_sha256": book_row["prepared_translation_sha256"],
                "proposal_status": "machine_proposed_unreviewed",
                "review_status": "pending_human_review",
                "paper_facing_eligible": "no",
                "analysis_status": "excluded_until_human_review",
            }
        )

    output_dir = resolve_repo_path(args.output_dir, root)
    output_dir.mkdir(parents=True, exist_ok=True)
    candidate_path = output_dir / f"{args.translation_source_id}.book-{args.book:02d}.csv"
    payload = csv_payload(CANDIDATE_COLUMNS, rows)
    candidate_path.write_bytes(payload)

    summary_row = {
        "work_id": upstream["work_id"],
        "source_edition_id": upstream["source_edition_id"],
        "translation_source_id": args.translation_source_id,
        "book": args.book,
        "proposal_method": PROPOSAL_METHOD,
        "candidate_path": display_path(candidate_path, root),
        "candidate_bytes": len(payload),
        "candidate_sha256": hashlib.sha256(payload).hexdigest(),
        "candidate_count": len(rows),
        "source_line_count": sum(int(row["source_line_count"]) for row in rows),
        "target_paragraph_count": len(paragraphs),
        "target_token_count": sum(int(row["target_token_count"]) for row in rows),
        "proposal_status": "machine_proposed_unreviewed",
        "review_status": "pending_human_review",
        "paper_facing_eligible": "no",
        "analysis_status": "excluded_until_human_review",
    }
    summary_path = resolve_repo_path(args.summary, root)
    prior_summaries = read_rows(summary_path) if summary_path.exists() else []
    summaries = [
        row
        for row in prior_summaries
        if not (
            row["translation_source_id"] == args.translation_source_id
            and int(row["book"]) == args.book
        )
    ]
    summaries.append(summary_row)
    summaries.sort(key=lambda row: (str(row["translation_source_id"]), int(row["book"])))
    summary_path.write_bytes(csv_payload(SUMMARY_COLUMNS, summaries))

    print(
        f"Prepared {len(rows)} unreviewed candidate segment(s) for "
        f"{args.translation_source_id} book {args.book}."
    )
    print(
        f"Allocated {len(source_lines)} source line(s) and "
        f"{summary_row['target_token_count']} target token(s)."
    )
    print("All candidate rows are excluded from paper-facing analysis until human review.")
    print(f"Wrote {display_path(candidate_path, root)}.")
    print(f"Wrote {display_path(summary_path, root)}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
