#!/usr/bin/env python3
"""Prepare translation book bodies and structural source-target alignments."""

from __future__ import annotations

import argparse
import csv
import hashlib
import sys
from collections import defaultdict
from io import StringIO
from pathlib import Path

from validate_prepared_translation_texts import repo_root, resolve_repo_path, validate_manifest
from wordspend.book_alignment import extract_translation_books
from wordspend.source_editions import PAPER_RIGHTS_ALLOWED
from wordspend.tokenization import tokenizer_id_for_language


RULE_COLUMNS = [
    "rule_id",
    "source_id",
    "work_id",
    "source_edition_id",
    "segmentation_method",
    "expected_book_count",
    "leading_paragraphs_to_skip",
    "alignment_level",
    "paper_facing_eligible",
]

BOOK_COLUMNS = [
    "source_id",
    "work_id",
    "book",
    "segment_ref",
    "target_language_code",
    "translator",
    "publication_date",
    "prepared_translation_sha256",
    "prepared_start_char",
    "prepared_end_char",
    "prepared_start_line",
    "prepared_end_line",
    "book_text_sha256",
    "tokenizer_id",
    "token_count",
    "text",
]

SUMMARY_COLUMNS = [
    "source_id",
    "work_id",
    "rule_id",
    "segmentation_method",
    "prepared_translation_path",
    "prepared_translation_sha256",
    "book_path",
    "book_bytes",
    "book_sha256",
    "book_count",
    "token_count",
    "text_stage",
    "alignment_level",
    "rights_status",
    "machine_human_status",
    "paper_facing_eligible",
]

ALIGNMENT_COLUMNS = [
    "alignment_id",
    "work_id",
    "source_edition_id",
    "translation_source_id",
    "segment_ref",
    "alignment_level",
    "source_start_ref",
    "source_end_ref",
    "source_line_count",
    "source_editorially_deleted_line_count",
    "source_prepared_sha256",
    "target_book_path",
    "target_book_text_sha256",
    "target_token_count",
    "translation_prepared_sha256",
    "source_rights_status",
    "translation_rights_status",
    "source_editorial_status",
    "translation_machine_human_status",
    "alignment_status",
    "paper_facing_eligible",
    "analysis_status",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rules", default="data/translation_book_rules.csv")
    parser.add_argument("--translation-manifest", default="data/prepared/translation_texts.csv")
    parser.add_argument("--translation-registry", default="data/translation_sources.csv")
    parser.add_argument("--source-manifest", default="data/prepared/source_editions.csv")
    parser.add_argument("--book-dir", default="data/prepared/translation_books")
    parser.add_argument("--book-manifest", default="data/prepared/translation_books.csv")
    parser.add_argument("--alignment-manifest", default="data/prepared/book_alignments.csv")
    return parser.parse_args()


def display_path(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def indexed_rows(path: Path, key: str) -> dict[str, dict[str, str]]:
    rows = read_rows(path)
    indexed = {row[key]: row for row in rows}
    if len(indexed) != len(rows):
        raise ValueError(f"{path}: duplicate {key}")
    return indexed


def csv_payload(columns: list[str], rows: list[dict[str, object]]) -> bytes:
    handle = StringIO(newline="")
    writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return handle.getvalue().encode("utf-8")


def validate_rule(rule: dict[str, str], label: str) -> list[str]:
    errors = []
    for column in RULE_COLUMNS:
        if not (rule.get(column) or "").strip():
            errors.append(f"{label}: {column} is required")
    if (rule.get("segmentation_method") or "").strip() != "gutenberg_book_heading_v1":
        errors.append(f"{label}: unsupported segmentation_method")
    if (rule.get("alignment_level") or "").strip() != "book":
        errors.append(f"{label}: alignment_level must be book")
    if (rule.get("paper_facing_eligible") or "").strip().lower() != "yes":
        errors.append(f"{label}: only paper-facing eligible rules may be prepared")
    for column in ("expected_book_count", "leading_paragraphs_to_skip"):
        try:
            value = int((rule.get(column) or "").strip())
            if value < (1 if column == "expected_book_count" else 0):
                raise ValueError
        except ValueError:
            errors.append(f"{label}: {column} must be a valid integer")
    return errors


def main() -> int:
    args = parse_args()
    root = repo_root()
    rules_path = resolve_repo_path(args.rules, root)
    translation_manifest_path = resolve_repo_path(args.translation_manifest, root)
    translation_registry_path = resolve_repo_path(args.translation_registry, root)
    source_manifest_path = resolve_repo_path(args.source_manifest, root)
    book_dir = resolve_repo_path(args.book_dir, root)
    book_manifest_path = resolve_repo_path(args.book_manifest, root)
    alignment_manifest_path = resolve_repo_path(args.alignment_manifest, root)

    _, _, manifest_errors = validate_manifest(
        translation_manifest_path, translation_registry_path, root
    )
    if manifest_errors:
        for error in manifest_errors:
            print(error, file=sys.stderr)
        return 1

    try:
        translations = indexed_rows(translation_manifest_path, "source_id")
        source_editions = indexed_rows(source_manifest_path, "source_edition_id")
        rules = read_rows(rules_path)
    except (OSError, ValueError) as error:
        print(error, file=sys.stderr)
        return 1

    errors = []
    seen_rule_sources: set[str] = set()
    for row_number, rule in enumerate(rules, start=2):
        label = (rule.get("rule_id") or "").strip() or f"row {row_number}"
        errors.extend(validate_rule(rule, label))
        source_id = (rule.get("source_id") or "").strip()
        if source_id in seen_rule_sources:
            errors.append(f"{label}: duplicate source_id")
        seen_rule_sources.add(source_id)
        if source_id not in translations:
            errors.append(f"{label}: source_id is absent from prepared translation manifest")
        edition_id = (rule.get("source_edition_id") or "").strip()
        if edition_id not in source_editions:
            errors.append(f"{label}: source_edition_id is absent from prepared source manifest")
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    book_dir.mkdir(parents=True, exist_ok=True)
    summaries: list[dict[str, object]] = []
    alignments: list[dict[str, object]] = []

    for rule in rules:
        source_id = rule["source_id"]
        translation = translations[source_id]
        source_edition = source_editions[rule["source_edition_id"]]
        if (
            translation["work_id"] != rule["work_id"]
            or source_edition["work_id"] != rule["work_id"]
        ):
            print(f"{rule['rule_id']}: work_id does not match prepared inputs", file=sys.stderr)
            return 1
        if translation["paper_facing_eligible"] != "yes":
            print(f"{rule['rule_id']}: translation is not paper-facing eligible", file=sys.stderr)
            return 1
        if translation["machine_human_status"] != "human_published":
            print(f"{rule['rule_id']}: translation is not human_published", file=sys.stderr)
            return 1
        if source_edition["paper_facing_eligible"] != "yes":
            print(f"{rule['rule_id']}: source edition is not paper-facing eligible", file=sys.stderr)
            return 1
        if source_edition["editorial_status"] != "human_edited_published":
            print(f"{rule['rule_id']}: source edition is not human_edited_published", file=sys.stderr)
            return 1
        if source_edition["rights_status"] not in PAPER_RIGHTS_ALLOWED:
            print(f"{rule['rule_id']}: source edition rights are not paper-facing", file=sys.stderr)
            return 1

        translation_path = resolve_repo_path(translation["prepared_path"], root)
        with translation_path.open("r", encoding="utf-8", newline="") as handle:
            translation_text = handle.read()
        try:
            books = extract_translation_books(
                translation_text,
                translation["target_language_code"],
                expected_book_count=int(rule["expected_book_count"]),
                leading_paragraphs_to_skip=int(rule["leading_paragraphs_to_skip"]),
            )
        except ValueError as error:
            print(f"{rule['rule_id']}: {error}", file=sys.stderr)
            return 1

        book_rows = [
            {
                "source_id": source_id,
                "work_id": rule["work_id"],
                "book": book.book,
                "segment_ref": str(book.book),
                "target_language_code": translation["target_language_code"],
                "translator": translation["translator"],
                "publication_date": translation["publication_date"],
                "prepared_translation_sha256": translation["prepared_sha256"],
                "prepared_start_char": book.start_char,
                "prepared_end_char": book.end_char,
                "prepared_start_line": book.start_line,
                "prepared_end_line": book.end_line,
                "book_text_sha256": book.text_sha256,
                "tokenizer_id": tokenizer_id_for_language(translation["target_language_code"]),
                "token_count": book.token_count,
                "text": book.text,
            }
            for book in books
        ]
        book_payload = csv_payload(BOOK_COLUMNS, book_rows)
        book_path = book_dir / f"{source_id}.books.csv"
        book_path.write_bytes(book_payload)
        book_sha256 = hashlib.sha256(book_payload).hexdigest()

        source_path = resolve_repo_path(source_edition["prepared_path"], root)
        source_payload = source_path.read_bytes()
        if hashlib.sha256(source_payload).hexdigest() != source_edition["prepared_sha256"]:
            print(
                f"{rule['rule_id']}: prepared source checksum does not match source manifest",
                file=sys.stderr,
            )
            return 1
        source_lines_by_book: dict[int, list[dict[str, str]]] = defaultdict(list)
        for line in read_rows(source_path):
            source_lines_by_book[int(line["book"])].append(line)
        if sum(len(lines) for lines in source_lines_by_book.values()) != int(
            source_edition["line_count"]
        ):
            print(
                f"{rule['rule_id']}: prepared source line count does not match source manifest",
                file=sys.stderr,
            )
            return 1
        expected_books = list(range(1, int(rule["expected_book_count"]) + 1))
        if sorted(source_lines_by_book) != expected_books:
            print(
                f"{rule['rule_id']}: prepared source books do not match 1..{len(expected_books)}",
                file=sys.stderr,
            )
            return 1

        for book, book_row in zip(books, book_rows, strict=True):
            source_lines = source_lines_by_book[book.book]
            alignments.append(
                {
                    "alignment_id": (
                        f"{source_edition['source_edition_id']}--{source_id}--book-{book.book:02d}"
                    ),
                    "work_id": rule["work_id"],
                    "source_edition_id": source_edition["source_edition_id"],
                    "translation_source_id": source_id,
                    "segment_ref": str(book.book),
                    "alignment_level": rule["alignment_level"],
                    "source_start_ref": source_lines[0]["reference"],
                    "source_end_ref": source_lines[-1]["reference"],
                    "source_line_count": len(source_lines),
                    "source_editorially_deleted_line_count": sum(
                        line["line_status"] == "editorially_deleted" for line in source_lines
                    ),
                    "source_prepared_sha256": source_edition["prepared_sha256"],
                    "target_book_path": display_path(book_path, root),
                    "target_book_text_sha256": book.text_sha256,
                    "target_token_count": book.token_count,
                    "translation_prepared_sha256": translation["prepared_sha256"],
                    "source_rights_status": source_edition["rights_status"],
                    "translation_rights_status": translation["rights_status"],
                    "source_editorial_status": source_edition["editorial_status"],
                    "translation_machine_human_status": translation["machine_human_status"],
                    "alignment_status": "structurally_aligned",
                    "paper_facing_eligible": "yes",
                    "analysis_status": "book_length_only_finer_alignment_required_for_lexical_claims",
                }
            )

        summaries.append(
            {
                "source_id": source_id,
                "work_id": rule["work_id"],
                "rule_id": rule["rule_id"],
                "segmentation_method": rule["segmentation_method"],
                "prepared_translation_path": translation["prepared_path"],
                "prepared_translation_sha256": translation["prepared_sha256"],
                "book_path": display_path(book_path, root),
                "book_bytes": len(book_payload),
                "book_sha256": book_sha256,
                "book_count": len(books),
                "token_count": sum(book.token_count for book in books),
                "text_stage": "prepared_translation_books",
                "alignment_level": rule["alignment_level"],
                "rights_status": translation["rights_status"],
                "machine_human_status": translation["machine_human_status"],
                "paper_facing_eligible": "yes",
            }
        )

    book_manifest_path.write_bytes(csv_payload(SUMMARY_COLUMNS, summaries))
    alignment_manifest_path.write_bytes(csv_payload(ALIGNMENT_COLUMNS, alignments))
    print(f"Prepared {sum(int(row['book_count']) for row in summaries)} translation book(s).")
    print(f"Wrote {len(alignments)} structural source-target alignment row(s).")
    print(f"Wrote {display_path(book_manifest_path, root)}.")
    print(f"Wrote {display_path(alignment_manifest_path, root)}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
