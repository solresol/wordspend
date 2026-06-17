#!/usr/bin/env python3
"""Prepare downloaded translation bodies while preserving raw source files."""

from __future__ import annotations

import argparse
import csv
import hashlib
import sys
from pathlib import Path

from validate_translation_sources import PAPER_RIGHTS_ALLOWED, is_yes, validate_registry


MANIFEST_COLUMNS = [
    "source_id",
    "work_id",
    "target_language_code",
    "translator",
    "translation_title",
    "edition",
    "publication_date",
    "raw_path",
    "raw_sha256",
    "prepared_path",
    "prepared_bytes",
    "prepared_sha256",
    "prepared_line_count",
    "body_start_line",
    "body_end_line",
    "removed_prefix_lines",
    "removed_suffix_lines",
    "body_start_marker",
    "body_start_marker_occurrence",
    "body_end_marker",
    "text_stage",
    "front_back_matter_status",
    "rights_status",
    "machine_human_status",
    "paper_facing_eligible",
]

RULE_COLUMNS = [
    "source_id",
    "body_start_marker",
    "body_start_marker_occurrence",
    "body_end_marker",
    "trim_trailing_blank_lines",
]


class PreparationError(ValueError):
    """Raised when a raw text cannot be prepared from its declared rule."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--registry",
        default="data/translation_sources.csv",
        help="CSV registry containing translation provenance",
    )
    parser.add_argument(
        "--raw-manifest",
        default="data/raw/translation_downloads.csv",
        help="CSV manifest written by fetch_translation_sources.py",
    )
    parser.add_argument(
        "--rules",
        default="data/text_preparation_rules.csv",
        help="CSV file declaring source-specific body-boundary markers",
    )
    parser.add_argument(
        "--output-dir",
        default="data/prepared/translations",
        help="directory for stripped translation body text files",
    )
    parser.add_argument(
        "--manifest",
        default="data/prepared/translation_texts.csv",
        help="CSV manifest to write with prepared-text checksum provenance",
    )
    parser.add_argument(
        "--source-id",
        action="append",
        default=[],
        help="prepare only this source_id; may be supplied more than once",
    )
    parser.add_argument(
        "--include-non-paper-facing",
        action="store_true",
        help="also prepare rows that are not paper-facing eligible",
    )
    return parser.parse_args()


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def resolve_repo_path(value: str, root: Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return root / path


def relative_to_root(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def keyed_rows(path: Path, key: str) -> dict[str, dict[str, str]]:
    rows = {}
    for row in read_rows(path):
        row_key = (row.get(key) or "").strip()
        if row_key in rows:
            raise PreparationError(f"{path}: duplicate {key} {row_key!r}")
        rows[row_key] = row
    return rows


def validate_rules(path: Path) -> list[str]:
    errors: list[str] = []
    if not path.exists():
        return [f"{path}: file does not exist"]

    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        missing_columns = [name for name in RULE_COLUMNS if name not in (reader.fieldnames or [])]
        if missing_columns:
            return [f"{path}: missing required columns: {', '.join(missing_columns)}"]

        seen_source_ids: set[str] = set()
        for row_number, row in enumerate(reader, start=2):
            source_id = (row.get("source_id") or "").strip()
            label = source_id or f"row {row_number}"
            if not source_id:
                errors.append(f"{label}: source_id is required")
            if source_id in seen_source_ids:
                errors.append(f"{label}: duplicate source_id")
            seen_source_ids.add(source_id)

            for column in RULE_COLUMNS:
                if not (row.get(column) or "").strip():
                    errors.append(f"{label}: {column} is required")

            occurrence = (row.get("body_start_marker_occurrence") or "").strip()
            if occurrence:
                try:
                    if int(occurrence) < 1:
                        errors.append(f"{label}: body_start_marker_occurrence must be positive")
                except ValueError:
                    errors.append(f"{label}: body_start_marker_occurrence must be an integer")

            trim_value = (row.get("trim_trailing_blank_lines") or "").strip().lower()
            if trim_value and trim_value not in {"yes", "no"}:
                errors.append(f"{label}: trim_trailing_blank_lines must be yes or no")

    return errors


def marker_text(line: bytes) -> str:
    return line.decode("utf-8").strip()


def find_marker_line(lines: list[bytes], marker: str, occurrence: int) -> int:
    seen = 0
    for index, line in enumerate(lines):
        if marker_text(line) == marker:
            seen += 1
            if seen == occurrence:
                return index
    raise PreparationError(f"could not find occurrence {occurrence} of marker {marker!r}")


def find_first_marker_line(lines: list[bytes], marker: str, start_index: int) -> int:
    for index in range(start_index, len(lines)):
        if marker_text(lines[index]) == marker:
            return index
    raise PreparationError(f"could not find end marker {marker!r}")


def strip_body(raw_bytes: bytes, rule: dict[str, str]) -> tuple[bytes, int, int, int, int]:
    lines = raw_bytes.splitlines(keepends=True)
    start_marker = (rule.get("body_start_marker") or "").strip()
    end_marker = (rule.get("body_end_marker") or "").strip()
    occurrence = int((rule.get("body_start_marker_occurrence") or "1").strip())

    start_index = find_marker_line(lines, start_marker, occurrence)
    end_marker_index = find_first_marker_line(lines, end_marker, start_index + 1)
    body_lines = lines[start_index:end_marker_index]

    if is_yes(rule.get("trim_trailing_blank_lines") or ""):
        while body_lines and not body_lines[-1].strip():
            body_lines.pop()

    if not body_lines:
        raise PreparationError("declared body markers produced an empty text")

    body_start_line = start_index + 1
    body_end_line = start_index + len(body_lines)
    removed_prefix_lines = start_index
    removed_suffix_lines = len(lines) - body_end_line
    return (
        b"".join(body_lines),
        body_start_line,
        body_end_line,
        removed_prefix_lines,
        removed_suffix_lines,
    )


def eligible_for_default_prepare(row: dict[str, str]) -> bool:
    return (
        is_yes(row.get("paper_facing_eligible") or "")
        and (row.get("machine_human_status") or "").strip() == "human_published"
        and (row.get("rights_status") or "").strip() in PAPER_RIGHTS_ALLOWED
    )


def main() -> int:
    args = parse_args()
    root = repo_root()
    registry = resolve_repo_path(args.registry, root)
    raw_manifest = resolve_repo_path(args.raw_manifest, root)
    rules_path = resolve_repo_path(args.rules, root)
    output_dir = resolve_repo_path(args.output_dir, root)
    manifest = resolve_repo_path(args.manifest, root)

    row_count, paper_facing_count, validation_errors = validate_registry(registry)
    rule_errors = validate_rules(rules_path)
    errors = validation_errors + rule_errors
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    registry_rows = keyed_rows(registry, "source_id")
    raw_rows = read_rows(raw_manifest)
    rules = keyed_rows(rules_path, "source_id")
    wanted_source_ids = set(args.source_id)

    selected_rows = []
    for raw_row in raw_rows:
        source_id = (raw_row.get("source_id") or "").strip()
        if wanted_source_ids and source_id not in wanted_source_ids:
            continue
        registry_row = registry_rows.get(source_id)
        if not registry_row:
            print(f"{source_id}: no registry row", file=sys.stderr)
            return 1
        if not args.include_non_paper_facing and not eligible_for_default_prepare(registry_row):
            continue
        if (raw_row.get("text_stage") or "").strip() != "raw_provider_text":
            print(f"{source_id}: skipping non-raw text stage", file=sys.stderr)
            continue
        if source_id not in rules:
            print(f"{source_id}: no text preparation rule", file=sys.stderr)
            return 1
        selected_rows.append((raw_row, registry_row, rules[source_id]))

    if wanted_source_ids:
        selected_ids = {raw_row["source_id"] for raw_row, _, _ in selected_rows}
        missing_ids = sorted(wanted_source_ids - selected_ids)
        if missing_ids:
            print(f"no preparable raw row(s): {', '.join(missing_ids)}", file=sys.stderr)
            return 1

    output_dir.mkdir(parents=True, exist_ok=True)
    manifest.parent.mkdir(parents=True, exist_ok=True)

    manifest_rows = []
    for raw_row, registry_row, rule in selected_rows:
        source_id = raw_row["source_id"]
        raw_path = resolve_repo_path(raw_row["raw_path"], root)
        raw_bytes = raw_path.read_bytes()
        raw_digest = hashlib.sha256(raw_bytes).hexdigest()
        expected_digest = (raw_row.get("sha256") or "").strip()
        if raw_digest != expected_digest:
            print(
                f"{source_id}: raw checksum mismatch: expected {expected_digest}, got {raw_digest}",
                file=sys.stderr,
            )
            return 1

        (
            prepared_bytes,
            body_start_line,
            body_end_line,
            removed_prefix_lines,
            removed_suffix_lines,
        ) = strip_body(raw_bytes, rule)
        prepared_path = output_dir / f"{source_id}.txt"
        prepared_path.write_bytes(prepared_bytes)
        prepared_digest = hashlib.sha256(prepared_bytes).hexdigest()
        prepared_line_count = len(prepared_bytes.splitlines())

        manifest_rows.append(
            {
                "source_id": source_id,
                "work_id": registry_row["work_id"],
                "target_language_code": registry_row["target_language_code"],
                "translator": registry_row["translator"],
                "translation_title": registry_row["translation_title"],
                "edition": registry_row["edition"],
                "publication_date": registry_row["publication_date"],
                "raw_path": relative_to_root(raw_path, root),
                "raw_sha256": raw_digest,
                "prepared_path": relative_to_root(prepared_path, root),
                "prepared_bytes": str(len(prepared_bytes)),
                "prepared_sha256": prepared_digest,
                "prepared_line_count": str(prepared_line_count),
                "body_start_line": str(body_start_line),
                "body_end_line": str(body_end_line),
                "removed_prefix_lines": str(removed_prefix_lines),
                "removed_suffix_lines": str(removed_suffix_lines),
                "body_start_marker": rule["body_start_marker"],
                "body_start_marker_occurrence": rule["body_start_marker_occurrence"],
                "body_end_marker": rule["body_end_marker"],
                "text_stage": "prepared_translation_body",
                "front_back_matter_status": "stripped",
                "rights_status": registry_row["rights_status"],
                "machine_human_status": registry_row["machine_human_status"],
                "paper_facing_eligible": registry_row["paper_facing_eligible"],
            }
        )

    with manifest.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=MANIFEST_COLUMNS)
        writer.writeheader()
        writer.writerows(manifest_rows)

    print(f"Validated {row_count} translation source row(s).")
    print(f"Paper-facing eligible source row(s): {paper_facing_count}.")
    print(f"Prepared {len(manifest_rows)} translation text(s).")
    print(f"Wrote manifest: {relative_to_root(manifest, root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
