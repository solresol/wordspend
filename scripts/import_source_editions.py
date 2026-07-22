#!/usr/bin/env python3
"""Fetch and prepare provenance-validated TEI source editions."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import http.client
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

from wordspend.source_editions import (
    PAPER_RIGHTS_ALLOWED,
    extract_tei_source_lines,
    is_yes,
    validate_source_edition_registry,
)


DOWNLOAD_COLUMNS = [
    "source_edition_id",
    "work_id",
    "download_url",
    "version_id",
    "download_format",
    "raw_path",
    "raw_bytes",
    "raw_sha256",
    "retrieved_at_utc",
    "http_last_modified",
    "rights_status",
    "editorial_status",
    "paper_facing_eligible",
    "text_stage",
]

PREPARED_COLUMNS = [
    "source_edition_id",
    "work_id",
    "source_language_code",
    "author",
    "editors",
    "edition_title",
    "edition_label",
    "publication_date",
    "publication_date_text",
    "canonical_id",
    "version_id",
    "raw_path",
    "raw_sha256",
    "prepared_path",
    "prepared_bytes",
    "prepared_sha256",
    "book_count",
    "line_count",
    "editorially_deleted_line_count",
    "text_stage",
    "reference_scheme",
    "rights_status",
    "editorial_status",
    "paper_facing_eligible",
]

LINE_COLUMNS = [
    "source_edition_id",
    "work_id",
    "reference",
    "book",
    "line",
    "text",
    "line_status",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry", default="data/source_editions.csv")
    parser.add_argument("--raw-dir", default="data/raw/source_editions")
    parser.add_argument("--download-manifest", default="data/raw/source_edition_downloads.csv")
    parser.add_argument("--prepared-dir", default="data/prepared/source_editions")
    parser.add_argument("--prepared-manifest", default="data/prepared/source_editions.csv")
    parser.add_argument("--source-edition-id", action="append", default=[])
    parser.add_argument("--include-non-paper-facing", action="store_true")
    return parser.parse_args()


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def resolve_repo_path(value: str, root: Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else root / path


def display_path(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def eligible_for_default_import(row: dict[str, str]) -> bool:
    return (
        is_yes(row.get("paper_facing_eligible") or "")
        and (row.get("editorial_status") or "").strip() == "human_edited_published"
        and (row.get("rights_status") or "").strip() in PAPER_RIGHTS_ALLOWED
    )


def fetch_resource(url: str, attempts: int = 3) -> tuple[bytes, str]:
    request = Request(
        url,
        headers={
            "User-Agent": "wordspend-provenance-fetch/0.1 (+https://github.com/solresol/wordspend)",
        },
    )
    last_error: BaseException | None = None
    for attempt in range(1, attempts + 1):
        try:
            with urlopen(request, timeout=120) as response:
                return response.read(), response.headers.get("Last-Modified", "")
        except (http.client.IncompleteRead, TimeoutError, URLError) as error:
            last_error = error
            if attempt < attempts:
                time.sleep(2)
    raise RuntimeError(f"failed to fetch {url} after {attempts} attempt(s): {last_error}") from last_error


def csv_payload(fieldnames: list[str], rows: list[dict[str, object]]) -> bytes:
    from io import StringIO

    handle = StringIO(newline="")
    writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return handle.getvalue().encode("utf-8")


def main() -> int:
    args = parse_args()
    root = repo_root()
    registry = resolve_repo_path(args.registry, root)
    raw_dir = resolve_repo_path(args.raw_dir, root)
    download_manifest = resolve_repo_path(args.download_manifest, root)
    prepared_dir = resolve_repo_path(args.prepared_dir, root)
    prepared_manifest = resolve_repo_path(args.prepared_manifest, root)

    row_count, paper_facing_count, errors = validate_source_edition_registry(registry)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    wanted_ids = set(args.source_edition_id)
    selected_rows: list[dict[str, str]] = []
    for row in read_rows(registry):
        edition_id = row["source_edition_id"]
        if wanted_ids and edition_id not in wanted_ids:
            continue
        if not args.include_non_paper_facing and not eligible_for_default_import(row):
            continue
        if row["download_format"] != "tei_xml":
            print(f"{edition_id}: download_format must be tei_xml", file=sys.stderr)
            return 1
        selected_rows.append(row)

    selected_ids = {row["source_edition_id"] for row in selected_rows}
    missing_ids = sorted(wanted_ids - selected_ids)
    if missing_ids:
        print(f"no importable source edition row(s): {', '.join(missing_ids)}", file=sys.stderr)
        return 1

    raw_dir.mkdir(parents=True, exist_ok=True)
    download_manifest.parent.mkdir(parents=True, exist_ok=True)
    prepared_dir.mkdir(parents=True, exist_ok=True)
    prepared_manifest.parent.mkdir(parents=True, exist_ok=True)

    retrieved_at = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    download_rows: list[dict[str, object]] = []
    prepared_rows: list[dict[str, object]] = []

    for row in selected_rows:
        edition_id = row["source_edition_id"]
        try:
            raw_payload, http_last_modified = fetch_resource(row["download_url"])
            source_lines = extract_tei_source_lines(raw_payload, row["canonical_id"])
        except (RuntimeError, ValueError) as error:
            print(f"{edition_id}: {error}", file=sys.stderr)
            return 1

        raw_path = raw_dir / f"{edition_id}.xml"
        raw_path.write_bytes(raw_payload)
        raw_sha256 = hashlib.sha256(raw_payload).hexdigest()

        line_rows = [
            {
                "source_edition_id": edition_id,
                "work_id": row["work_id"],
                "reference": source_line.reference,
                "book": source_line.book,
                "line": source_line.line,
                "text": source_line.text,
                "line_status": source_line.line_status,
            }
            for source_line in source_lines
        ]
        prepared_payload = csv_payload(LINE_COLUMNS, line_rows)
        prepared_path = prepared_dir / f"{edition_id}.lines.csv"
        prepared_path.write_bytes(prepared_payload)
        prepared_sha256 = hashlib.sha256(prepared_payload).hexdigest()
        book_count = len({source_line.book for source_line in source_lines})

        download_rows.append(
            {
                "source_edition_id": edition_id,
                "work_id": row["work_id"],
                "download_url": row["download_url"],
                "version_id": row["version_id"],
                "download_format": row["download_format"],
                "raw_path": display_path(raw_path, root),
                "raw_bytes": len(raw_payload),
                "raw_sha256": raw_sha256,
                "retrieved_at_utc": retrieved_at,
                "http_last_modified": http_last_modified,
                "rights_status": row["rights_status"],
                "editorial_status": row["editorial_status"],
                "paper_facing_eligible": row["paper_facing_eligible"],
                "text_stage": "raw_provider_tei_xml",
            }
        )
        prepared_rows.append(
            {
                "source_edition_id": edition_id,
                "work_id": row["work_id"],
                "source_language_code": row["source_language_code"],
                "author": row["author"],
                "editors": row["editors"],
                "edition_title": row["edition_title"],
                "edition_label": row["edition_label"],
                "publication_date": row["publication_date"],
                "publication_date_text": row["publication_date_text"],
                "canonical_id": row["canonical_id"],
                "version_id": row["version_id"],
                "raw_path": display_path(raw_path, root),
                "raw_sha256": raw_sha256,
                "prepared_path": display_path(prepared_path, root),
                "prepared_bytes": len(prepared_payload),
                "prepared_sha256": prepared_sha256,
                "book_count": book_count,
                "line_count": len(source_lines),
                "editorially_deleted_line_count": sum(
                    source_line.line_status == "editorially_deleted"
                    for source_line in source_lines
                ),
                "text_stage": "prepared_source_lines",
                "reference_scheme": "book.line",
                "rights_status": row["rights_status"],
                "editorial_status": row["editorial_status"],
                "paper_facing_eligible": row["paper_facing_eligible"],
            }
        )

    download_manifest.write_bytes(csv_payload(DOWNLOAD_COLUMNS, download_rows))
    prepared_manifest.write_bytes(csv_payload(PREPARED_COLUMNS, prepared_rows))

    print(f"Validated {row_count} source edition row(s).")
    print(f"Paper-facing eligible source edition row(s): {paper_facing_count}.")
    print(f"Imported {len(prepared_rows)} source edition(s).")
    print(f"Prepared {sum(int(row['line_count']) for row in prepared_rows)} source line(s).")
    print(f"Wrote manifest: {display_path(prepared_manifest, root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
