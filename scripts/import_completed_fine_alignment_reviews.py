#!/usr/bin/env python3
"""Validate completed fine-alignment reviews and stage them for adjudication."""

from __future__ import annotations

import argparse
import hashlib
import sys

from prepare_book_alignments import indexed_rows, read_rows
from prepare_fine_alignment_candidates import csv_payload, display_path
from prepare_fine_alignment_review_worklist import (
    WORKLIST_COLUMNS,
    indexed_candidate_summary,
)
from validate_prepared_translation_texts import repo_root, resolve_repo_path
from wordspend.fine_alignment import (
    import_completed_review_rows,
    prepare_review_worklist_rows,
)


REVIEWED_COLUMNS = [
    "alignment_id",
    "work_id",
    "source_edition_id",
    "translation_source_id",
    "book",
    "segment_index",
    "alignment_level",
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
    "candidate_file_sha256",
    "review_decision",
    "reviewer",
    "reviewed_at",
    "review_notes",
    "review_status",
    "paper_facing_eligible",
    "analysis_status",
]

SUMMARY_COLUMNS = [
    "work_id",
    "source_edition_id",
    "translation_source_id",
    "book",
    "review_worklist_path",
    "review_worklist_sha256",
    "reviewed_alignment_path",
    "reviewed_alignment_bytes",
    "reviewed_alignment_sha256",
    "alignment_count",
    "source_line_count",
    "target_token_count",
    "reviewer_count",
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
    parser.add_argument(
        "--worklist-summary", default="data/review/fine_alignment_worklists.csv"
    )
    parser.add_argument("--source-manifest", default="data/prepared/source_editions.csv")
    parser.add_argument("--output-dir", default="data/prepared/reviewed_fine_alignments")
    parser.add_argument("--summary", default="data/prepared/reviewed_fine_alignments.csv")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = repo_root()
    if args.book < 1:
        print("--book must be positive", file=sys.stderr)
        return 1

    try:
        candidate_summary = indexed_candidate_summary(
            resolve_repo_path(args.candidate_summary, root),
            args.translation_source_id,
            args.book,
        )
        worklist_summary = indexed_candidate_summary(
            resolve_repo_path(args.worklist_summary, root),
            args.translation_source_id,
            args.book,
        )
        candidate_path = resolve_repo_path(candidate_summary["candidate_path"], root)
        candidate_payload = candidate_path.read_bytes()
        candidate_sha256 = hashlib.sha256(candidate_payload).hexdigest()
        if candidate_sha256 != candidate_summary["candidate_sha256"]:
            raise ValueError("Candidate file checksum does not match its summary")
        if candidate_sha256 != worklist_summary["candidate_sha256"]:
            raise ValueError("Worklist and candidate summaries disagree on checksum")
        if (
            candidate_summary["review_status"] != "pending_human_review"
            or candidate_summary["paper_facing_eligible"] != "no"
            or candidate_summary["analysis_status"] != "excluded_until_human_review"
        ):
            raise ValueError("Candidate summary is not pending and analysis-excluded")
        if (
            worklist_summary["review_status"] != "pending_human_review"
            or worklist_summary["paper_facing_eligible"] != "no"
            or worklist_summary["analysis_status"]
            != "excluded_until_completed_review"
            or int(worklist_summary["completed_review_count"]) != 0
        ):
            raise ValueError("Worklist summary is not the pending-review baseline")

        worklist_path = resolve_repo_path(worklist_summary["review_worklist_path"], root)
        worklist_payload = worklist_path.read_bytes()
        candidate_rows = read_rows(candidate_path)
        if len(candidate_rows) != int(candidate_summary["candidate_count"]):
            raise ValueError("Candidate row count does not match its summary")
        blank_worklist_payload = csv_payload(
            WORKLIST_COLUMNS,
            prepare_review_worklist_rows(candidate_rows, candidate_sha256),
        )
        if (
            len(blank_worklist_payload) != int(worklist_summary["review_worklist_bytes"])
            or hashlib.sha256(blank_worklist_payload).hexdigest()
            != worklist_summary["review_worklist_sha256"]
        ):
            raise ValueError("Pending worklist baseline does not match its summary")
        worklist_rows = read_rows(worklist_path)
        if len(worklist_rows) != int(worklist_summary["review_row_count"]):
            raise ValueError("Worklist row count does not match its summary")

        source_manifests = indexed_rows(
            resolve_repo_path(args.source_manifest, root), "source_edition_id"
        )
        source_manifest = source_manifests[candidate_summary["source_edition_id"]]
        source_path = resolve_repo_path(source_manifest["prepared_path"], root)
        source_payload = source_path.read_bytes()
        if hashlib.sha256(source_payload).hexdigest() != source_manifest["prepared_sha256"]:
            raise ValueError("Source line file checksum does not match its manifest")
        source_lines = [
            row for row in read_rows(source_path) if int(row["book"]) == args.book
        ]
        reviewed_rows = import_completed_review_rows(
            worklist_rows, candidate_rows, source_lines, candidate_sha256
        )
    except (KeyError, OSError, ValueError) as error:
        print(error, file=sys.stderr)
        return 1

    output_dir = resolve_repo_path(args.output_dir, root)
    output_dir.mkdir(parents=True, exist_ok=True)
    reviewed_path = output_dir / (
        f"{args.translation_source_id}.book-{args.book:02d}.reviewed.csv"
    )
    reviewed_payload = csv_payload(REVIEWED_COLUMNS, reviewed_rows)
    reviewed_path.write_bytes(reviewed_payload)

    summary_row = {
        "work_id": candidate_summary["work_id"],
        "source_edition_id": candidate_summary["source_edition_id"],
        "translation_source_id": args.translation_source_id,
        "book": args.book,
        "review_worklist_path": display_path(worklist_path, root),
        "review_worklist_sha256": hashlib.sha256(worklist_payload).hexdigest(),
        "reviewed_alignment_path": display_path(reviewed_path, root),
        "reviewed_alignment_bytes": len(reviewed_payload),
        "reviewed_alignment_sha256": hashlib.sha256(reviewed_payload).hexdigest(),
        "alignment_count": len(reviewed_rows),
        "source_line_count": sum(int(row["source_line_count"]) for row in reviewed_rows),
        "target_token_count": sum(int(row["target_token_count"]) for row in reviewed_rows),
        "reviewer_count": len({str(row["reviewer"]) for row in reviewed_rows}),
        "review_status": "completed_human_review_pending_adjudication",
        "paper_facing_eligible": "no",
        "analysis_status": "excluded_until_adjudication",
    }
    summary_path = resolve_repo_path(args.summary, root)
    prior_rows = read_rows(summary_path) if summary_path.exists() else []
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
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_bytes(csv_payload(SUMMARY_COLUMNS, summary_rows))

    print(
        f"Imported {len(reviewed_rows)} completed human-review row(s) for "
        f"{args.translation_source_id} book {args.book}."
    )
    print("Rows remain excluded from paper-facing analysis pending adjudication.")
    print(f"Wrote {display_path(reviewed_path, root)}.")
    print(f"Wrote {display_path(summary_path, root)}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
