#!/usr/bin/env python3
"""Create a checksum-linked worklist for human review of alignment candidates."""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

from prepare_book_alignments import read_rows
from prepare_fine_alignment_candidates import csv_payload, display_path
from validate_prepared_translation_texts import repo_root, resolve_repo_path
from wordspend.fine_alignment import (
    prepare_review_worklist_rows,
    review_worklist_has_human_input,
)


WORKLIST_COLUMNS = [
    "candidate_id",
    "candidate_file_sha256",
    "work_id",
    "source_edition_id",
    "translation_source_id",
    "book",
    "segment_index",
    "target_paragraph",
    "proposed_source_start_ref",
    "proposed_source_end_ref",
    "proposed_source_line_count",
    "review_decision",
    "reviewed_source_start_ref",
    "reviewed_source_end_ref",
    "reviewer",
    "reviewed_at",
    "review_notes",
    "source_text",
    "target_text",
    "review_status",
    "paper_facing_eligible",
    "analysis_status",
]

SUMMARY_COLUMNS = [
    "work_id",
    "source_edition_id",
    "translation_source_id",
    "book",
    "candidate_path",
    "candidate_sha256",
    "review_worklist_path",
    "review_worklist_bytes",
    "review_worklist_sha256",
    "review_row_count",
    "completed_review_count",
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
        "--candidate-summary", default="data/prepared/fine_alignment_candidates.csv"
    )
    parser.add_argument("--output-dir", default="data/review/fine_alignment")
    parser.add_argument("--summary", default="data/review/fine_alignment_worklists.csv")
    return parser.parse_args()


def indexed_candidate_summary(path: Path, source_id: str, book: int) -> dict[str, str]:
    matches = [
        row
        for row in read_rows(path)
        if row["translation_source_id"] == source_id and int(row["book"]) == book
    ]
    if len(matches) != 1:
        raise ValueError("Expected exactly one candidate summary row")
    return matches[0]


def main() -> int:
    args = parse_args()
    root = repo_root()
    if args.book < 1:
        print("--book must be positive", file=sys.stderr)
        return 1

    try:
        summary_path = resolve_repo_path(args.candidate_summary, root)
        candidate_summary = indexed_candidate_summary(
            summary_path, args.translation_source_id, args.book
        )
        candidate_path = resolve_repo_path(candidate_summary["candidate_path"], root)
        candidate_payload = candidate_path.read_bytes()
        candidate_sha256 = hashlib.sha256(candidate_payload).hexdigest()
        if candidate_sha256 != candidate_summary["candidate_sha256"]:
            raise ValueError("Candidate file checksum does not match its summary")
        if (
            candidate_summary["review_status"] != "pending_human_review"
            or candidate_summary["paper_facing_eligible"] != "no"
            or candidate_summary["analysis_status"] != "excluded_until_human_review"
        ):
            raise ValueError("Candidate summary is not pending and analysis-excluded")

        candidate_rows = read_rows(candidate_path)
        if len(candidate_rows) != int(candidate_summary["candidate_count"]):
            raise ValueError("Candidate row count does not match its summary")
        worklist_rows = prepare_review_worklist_rows(candidate_rows, candidate_sha256)
    except (KeyError, OSError, ValueError) as error:
        print(error, file=sys.stderr)
        return 1

    output_dir = resolve_repo_path(args.output_dir, root)
    output_dir.mkdir(parents=True, exist_ok=True)
    worklist_path = output_dir / (
        f"{args.translation_source_id}.book-{args.book:02d}.review.csv"
    )
    if worklist_path.exists() and review_worklist_has_human_input(read_rows(worklist_path)):
        print(
            f"Refusing to overwrite human review input in {display_path(worklist_path, root)}.",
            file=sys.stderr,
        )
        return 1
    worklist_payload = csv_payload(WORKLIST_COLUMNS, worklist_rows)
    worklist_path.write_bytes(worklist_payload)

    summary_row = {
        "work_id": candidate_summary["work_id"],
        "source_edition_id": candidate_summary["source_edition_id"],
        "translation_source_id": args.translation_source_id,
        "book": args.book,
        "candidate_path": display_path(candidate_path, root),
        "candidate_sha256": candidate_sha256,
        "review_worklist_path": display_path(worklist_path, root),
        "review_worklist_bytes": len(worklist_payload),
        "review_worklist_sha256": hashlib.sha256(worklist_payload).hexdigest(),
        "review_row_count": len(worklist_rows),
        "completed_review_count": 0,
        "review_status": "pending_human_review",
        "paper_facing_eligible": "no",
        "analysis_status": "excluded_until_completed_review",
    }
    output_summary_path = resolve_repo_path(args.summary, root)
    prior_rows = read_rows(output_summary_path) if output_summary_path.exists() else []
    summary_rows = [
        row
        for row in prior_rows
        if not (
            row["translation_source_id"] == args.translation_source_id
            and int(row["book"]) == args.book
        )
    ]
    summary_rows.append(summary_row)
    summary_rows.sort(key=lambda row: (str(row["translation_source_id"]), int(row["book"])))
    output_summary_path.parent.mkdir(parents=True, exist_ok=True)
    output_summary_path.write_bytes(csv_payload(SUMMARY_COLUMNS, summary_rows))

    print(
        f"Prepared {len(worklist_rows)} pending human-review row(s) for "
        f"{args.translation_source_id} book {args.book}."
    )
    print("No row is paper-facing eligible; all review fields are blank.")
    print(f"Wrote {display_path(worklist_path, root)}.")
    print(f"Wrote {display_path(output_summary_path, root)}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
