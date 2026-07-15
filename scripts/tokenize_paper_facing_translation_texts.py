#!/usr/bin/env python3
"""Tokenize validated, paper-facing prepared translation texts."""

from __future__ import annotations

import argparse
import csv
import hashlib
import sys
from pathlib import Path

from validate_prepared_translation_texts import repo_root, resolve_repo_path, validate_manifest
from wordspend.prepared_texts import load_prepared_text_manifest, select_paper_facing_prepared_texts
from wordspend.tokenization import TokenSpan, tokenize_with_offsets, tokenizer_id_for_language


TOKEN_COLUMNS = [
    "token_index",
    "token",
    "normalized_token",
    "start_char",
    "end_char",
    "line_number",
]

SUMMARY_COLUMNS = [
    "source_id",
    "work_id",
    "target_language_code",
    "translator",
    "translation_title",
    "edition",
    "publication_date",
    "prepared_path",
    "prepared_sha256",
    "rights_status",
    "machine_human_status",
    "paper_facing_eligible",
    "tokenizer_id",
    "token_file_format",
    "token_path",
    "token_count",
    "token_bytes",
    "token_sha256",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--manifest",
        default="data/prepared/translation_texts.csv",
        help="CSV prepared-text manifest to validate and filter",
    )
    parser.add_argument(
        "--registry",
        default="data/translation_sources.csv",
        help="CSV registry containing source provenance",
    )
    parser.add_argument(
        "--output-dir",
        default="build/paper-facing/tokens",
        help="Directory for deterministic token CSV files",
    )
    parser.add_argument(
        "--summary",
        default="build/paper-facing/tokenized_translation_texts.csv",
        help="CSV tokenization summary with source and output checksums",
    )
    return parser.parse_args()


def display_path(path: Path, root: Path) -> str:
    """Use a repository-relative path where possible."""
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


def read_text_preserving_newlines(path: Path) -> str:
    """Decode UTF-8 without translating CRLF, keeping offsets reproducible."""
    with path.open("r", encoding="utf-8", newline="") as handle:
        return handle.read()


def write_token_file(path: Path, tokens: list[TokenSpan]) -> tuple[int, int, str]:
    """Write a deterministic token table and return count, bytes, and SHA-256."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=TOKEN_COLUMNS, lineterminator="\n")
        writer.writeheader()
        for token in tokens:
            writer.writerow(
                {
                    "token_index": token.token_index,
                    "token": token.token,
                    "normalized_token": token.normalized_token,
                    "start_char": token.start_char,
                    "end_char": token.end_char,
                    "line_number": token.line_number,
                }
            )

    payload = path.read_bytes()
    return len(tokens), len(payload), hashlib.sha256(payload).hexdigest()


def main() -> int:
    args = parse_args()
    root = repo_root()
    manifest = resolve_repo_path(args.manifest, root)
    registry = resolve_repo_path(args.registry, root)
    output_dir = resolve_repo_path(args.output_dir, root)
    summary_path = resolve_repo_path(args.summary, root)

    row_count, validated_paper_count, errors = validate_manifest(manifest, registry, root)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    selected = select_paper_facing_prepared_texts(load_prepared_text_manifest(manifest))

    profile_errors = []
    for row in selected.to_dict(orient="records"):
        try:
            tokenizer_id_for_language(row["target_language_code"])
        except ValueError as error:
            profile_errors.append(f"{row['source_id']}: {error}")
    if profile_errors:
        for error in profile_errors:
            print(error, file=sys.stderr)
        return 1

    summaries = []
    total_tokens = 0
    for row in selected.to_dict(orient="records"):
        prepared_path = resolve_repo_path(row["prepared_path"], root)
        tokenizer_id = tokenizer_id_for_language(row["target_language_code"])
        tokens = tokenize_with_offsets(
            read_text_preserving_newlines(prepared_path),
            row["target_language_code"],
        )
        token_path = output_dir / f"{row['source_id']}.tokens.csv"
        token_count, token_bytes, token_sha256 = write_token_file(token_path, tokens)
        total_tokens += token_count

        summary = {column: row[column] for column in SUMMARY_COLUMNS if column in row}
        summary.update(
            {
                "tokenizer_id": tokenizer_id,
                "token_file_format": "csv-utf8",
                "token_path": display_path(token_path, root),
                "token_count": token_count,
                "token_bytes": token_bytes,
                "token_sha256": token_sha256,
            }
        )
        summaries.append(summary)

    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with summary_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=SUMMARY_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(summaries)

    print(f"Validated {row_count} prepared translation text row(s).")
    print(f"Validated paper-facing prepared text row(s): {validated_paper_count}.")
    print(f"Tokenized paper-facing prepared text row(s): {len(summaries)}.")
    print(f"Wrote {total_tokens} token(s) using explicit language profiles.")
    print(f"Wrote {display_path(summary_path, root)}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
