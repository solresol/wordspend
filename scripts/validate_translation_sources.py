#!/usr/bin/env python3
"""Validate the translation source provenance registry."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import re
import sys
from pathlib import Path
from urllib.parse import urlparse


REQUIRED_COLUMNS = [
    "source_id",
    "work_id",
    "work_title",
    "source_language",
    "source_language_code",
    "target_language",
    "target_language_code",
    "translator",
    "translation_title",
    "edition",
    "publication_date",
    "catalog_url",
    "download_url",
    "download_format",
    "rights_status",
    "rights_basis",
    "machine_human_status",
    "paper_facing_eligible",
]

ALLOWED_HUMAN_STATUS = {
    "human_published",
    "machine_bootstrap",
    "mixed_or_unclear",
}

PAPER_RIGHTS_ALLOWED = {
    "public_domain_us",
    "public_domain_worldwide",
    "open_license",
}

LANGUAGE_CODE_RE = re.compile(r"^[a-z]{2,3}(?:-[A-Za-z0-9]+)*$")
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "registry",
        nargs="?",
        default="data/translation_sources.csv",
        help="CSV registry to validate",
    )
    return parser.parse_args()


def is_yes(value: str) -> bool:
    return value.strip().lower() == "yes"


def validate_iso_date(value: str, field: str, row_label: str, errors: list[str]) -> None:
    if not value:
        return
    try:
        dt.date.fromisoformat(value)
    except ValueError:
        errors.append(f"{row_label}: {field} must be an ISO date, got {value!r}")


def validate_url(value: str, field: str, row_label: str, errors: list[str]) -> None:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        errors.append(f"{row_label}: {field} must be an http(s) URL, got {value!r}")


def validate_registry(path: Path) -> tuple[int, int, list[str]]:
    errors: list[str] = []
    seen_source_ids: set[str] = set()
    paper_facing_count = 0

    if not path.exists():
        return 0, 0, [f"{path}: file does not exist"]

    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        missing_columns = [name for name in REQUIRED_COLUMNS if name not in fieldnames]
        if missing_columns:
            errors.append(f"{path}: missing required columns: {', '.join(missing_columns)}")
            return 0, 0, errors

        row_count = 0
        for row_number, row in enumerate(reader, start=2):
            row_count += 1
            source_id = (row.get("source_id") or "").strip()
            row_label = source_id or f"row {row_number}"

            for column in REQUIRED_COLUMNS:
                if not (row.get(column) or "").strip():
                    errors.append(f"{row_label}: {column} is required")

            if source_id in seen_source_ids:
                errors.append(f"{row_label}: duplicate source_id")
            seen_source_ids.add(source_id)

            for slug_field in ("source_id", "work_id"):
                value = (row.get(slug_field) or "").strip()
                if value and not SLUG_RE.match(value):
                    errors.append(f"{row_label}: {slug_field} must be a lowercase slug")

            for language_field in ("source_language_code", "target_language_code"):
                value = (row.get(language_field) or "").strip()
                if value and not LANGUAGE_CODE_RE.match(value):
                    errors.append(f"{row_label}: {language_field} has invalid language code {value!r}")

            validate_iso_date((row.get("publication_date") or "").strip(), "publication_date", row_label, errors)
            validate_iso_date((row.get("last_updated") or "").strip(), "last_updated", row_label, errors)
            validate_url((row.get("catalog_url") or "").strip(), "catalog_url", row_label, errors)
            validate_url((row.get("download_url") or "").strip(), "download_url", row_label, errors)

            status = (row.get("machine_human_status") or "").strip()
            if status and status not in ALLOWED_HUMAN_STATUS:
                errors.append(
                    f"{row_label}: machine_human_status must be one of "
                    f"{', '.join(sorted(ALLOWED_HUMAN_STATUS))}"
                )

            paper_eligible = (row.get("paper_facing_eligible") or "").strip().lower()
            if paper_eligible not in {"yes", "no"}:
                errors.append(f"{row_label}: paper_facing_eligible must be yes or no")

            if is_yes(row.get("paper_facing_eligible") or ""):
                paper_facing_count += 1
                rights_status = (row.get("rights_status") or "").strip()
                if status != "human_published":
                    errors.append(f"{row_label}: paper-facing rows must be human_published")
                if rights_status not in PAPER_RIGHTS_ALLOWED:
                    errors.append(
                        f"{row_label}: paper-facing rows need an allowed rights_status, got {rights_status!r}"
                    )

        return row_count, paper_facing_count, errors


def main() -> int:
    args = parse_args()
    row_count, paper_facing_count, errors = validate_registry(Path(args.registry))

    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    print(f"Validated {row_count} translation source row(s).")
    print(f"Paper-facing eligible source row(s): {paper_facing_count}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
