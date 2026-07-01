#!/usr/bin/env python3
"""Validate prepared translation text manifests and checksums."""

from __future__ import annotations

import argparse
import csv
import hashlib
import sys
from pathlib import Path

from prepare_translation_texts import MANIFEST_COLUMNS
from validate_translation_sources import PAPER_RIGHTS_ALLOWED, is_yes, validate_registry


INTEGER_COLUMNS = [
    "prepared_bytes",
    "prepared_line_count",
    "body_start_line",
    "body_end_line",
    "removed_prefix_lines",
    "removed_suffix_lines",
    "body_start_marker_occurrence",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "manifest",
        nargs="?",
        default="data/prepared/translation_texts.csv",
        help="CSV prepared-text manifest to validate",
    )
    parser.add_argument(
        "--registry",
        default="data/translation_sources.csv",
        help="CSV registry containing source provenance",
    )
    return parser.parse_args()


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def resolve_repo_path(value: str, root: Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return root / path


def read_rows(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    if not path.exists():
        return [], [f"{path}: file does not exist"]

    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        missing_columns = [name for name in MANIFEST_COLUMNS if name not in fieldnames]
        if missing_columns:
            return [], [f"{path}: missing required columns: {', '.join(missing_columns)}"]
        return list(reader), []


def validate_integer(value: str, column: str, row_label: str, errors: list[str]) -> None:
    try:
        parsed = int(value)
    except ValueError:
        errors.append(f"{row_label}: {column} must be an integer")
        return
    if parsed < 0:
        errors.append(f"{row_label}: {column} must be non-negative")


def digest_file(path: Path) -> tuple[int, str, int]:
    payload = path.read_bytes()
    return len(payload), hashlib.sha256(payload).hexdigest(), len(payload.splitlines())


def validate_manifest(manifest: Path, registry: Path, root: Path) -> tuple[int, int, list[str]]:
    _, _, registry_errors = validate_registry(registry)
    if registry_errors:
        return 0, 0, registry_errors

    rows, manifest_errors = read_rows(manifest)
    if manifest_errors:
        return 0, 0, manifest_errors

    with registry.open(newline="", encoding="utf-8") as handle:
        registry_rows = {
            row["source_id"]: row
            for row in csv.DictReader(handle)
            if (row.get("source_id") or "").strip()
        }

    errors: list[str] = []
    seen_source_ids: set[str] = set()
    paper_facing_count = 0

    for row_number, row in enumerate(rows, start=2):
        source_id = (row.get("source_id") or "").strip()
        row_label = source_id or f"row {row_number}"
        if not source_id:
            errors.append(f"{row_label}: source_id is required")

        if source_id in seen_source_ids:
            errors.append(f"{row_label}: duplicate source_id")
        seen_source_ids.add(source_id)

        for column in MANIFEST_COLUMNS:
            if not (row.get(column) or "").strip():
                errors.append(f"{row_label}: {column} is required")

        for column in INTEGER_COLUMNS:
            value = (row.get(column) or "").strip()
            if value:
                validate_integer(value, column, row_label, errors)

        registry_row = registry_rows.get(source_id)
        if not registry_row:
            errors.append(f"{row_label}: no source registry row")
            continue

        for column in [
            "work_id",
            "target_language_code",
            "translator",
            "translation_title",
            "edition",
            "publication_date",
            "rights_status",
            "machine_human_status",
            "paper_facing_eligible",
        ]:
            if (row.get(column) or "").strip() != (registry_row.get(column) or "").strip():
                errors.append(f"{row_label}: {column} does not match source registry")

        paper_eligible = (row.get("paper_facing_eligible") or "").strip().lower()
        if paper_eligible not in {"yes", "no"}:
            errors.append(f"{row_label}: paper_facing_eligible must be yes or no")

        if is_yes(row.get("paper_facing_eligible") or ""):
            paper_facing_count += 1
            if (row.get("machine_human_status") or "").strip() != "human_published":
                errors.append(f"{row_label}: paper-facing prepared texts must be human_published")
            rights_status = (row.get("rights_status") or "").strip()
            if rights_status not in PAPER_RIGHTS_ALLOWED:
                errors.append(
                    f"{row_label}: paper-facing prepared texts need an allowed rights_status, got {rights_status!r}"
                )
            if (row.get("text_stage") or "").strip() != "prepared_translation_body":
                errors.append(f"{row_label}: paper-facing prepared texts must have text_stage=prepared_translation_body")
            if (row.get("front_back_matter_status") or "").strip() != "stripped":
                errors.append(f"{row_label}: paper-facing prepared texts must have front_back_matter_status=stripped")

        raw_path_value = (row.get("raw_path") or "").strip()
        if raw_path_value:
            raw_path = resolve_repo_path(raw_path_value, root)
            if not raw_path.exists():
                errors.append(f"{row_label}: raw_path does not exist: {raw_path_value}")
            else:
                _, raw_digest, _ = digest_file(raw_path)
                if raw_digest != (row.get("raw_sha256") or "").strip():
                    errors.append(f"{row_label}: raw_sha256 does not match raw_path")

        prepared_path_value = (row.get("prepared_path") or "").strip()
        if prepared_path_value:
            prepared_path = resolve_repo_path(prepared_path_value, root)
            if not prepared_path.exists():
                errors.append(f"{row_label}: prepared_path does not exist: {prepared_path_value}")
            else:
                prepared_bytes, prepared_digest, prepared_line_count = digest_file(prepared_path)
                if str(prepared_bytes) != (row.get("prepared_bytes") or "").strip():
                    errors.append(f"{row_label}: prepared_bytes does not match prepared_path")
                if prepared_digest != (row.get("prepared_sha256") or "").strip():
                    errors.append(f"{row_label}: prepared_sha256 does not match prepared_path")
                if str(prepared_line_count) != (row.get("prepared_line_count") or "").strip():
                    errors.append(f"{row_label}: prepared_line_count does not match prepared_path")

        start_value = (row.get("body_start_line") or "").strip()
        end_value = (row.get("body_end_line") or "").strip()
        if start_value and end_value:
            try:
                if int(start_value) < 1:
                    errors.append(f"{row_label}: body_start_line must be at least 1")
                if int(end_value) < int(start_value):
                    errors.append(f"{row_label}: body_end_line must be greater than or equal to body_start_line")
            except ValueError:
                pass

    return len(rows), paper_facing_count, errors


def main() -> int:
    args = parse_args()
    root = repo_root()
    manifest = resolve_repo_path(args.manifest, root)
    registry = resolve_repo_path(args.registry, root)
    row_count, paper_facing_count, errors = validate_manifest(manifest, registry, root)

    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    print(f"Validated {row_count} prepared translation text row(s).")
    print(f"Paper-facing prepared text row(s): {paper_facing_count}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
