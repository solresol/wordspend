#!/usr/bin/env python3
"""Download prepared translation source rows into the raw-text cache."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import sys
from pathlib import Path
from urllib.request import Request, urlopen

from validate_translation_sources import PAPER_RIGHTS_ALLOWED, is_yes, validate_registry


MANIFEST_COLUMNS = [
    "source_id",
    "work_id",
    "download_url",
    "download_format",
    "raw_path",
    "bytes",
    "sha256",
    "retrieved_at_utc",
    "http_last_modified",
    "rights_status",
    "machine_human_status",
    "paper_facing_eligible",
    "text_stage",
    "front_back_matter_status",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--registry",
        default="data/translation_sources.csv",
        help="CSV registry to fetch from",
    )
    parser.add_argument(
        "--output-dir",
        default="data/raw/translations",
        help="directory for downloaded raw text files",
    )
    parser.add_argument(
        "--manifest",
        default="data/raw/translation_downloads.csv",
        help="CSV manifest to write with checksums and retrieval provenance",
    )
    parser.add_argument(
        "--source-id",
        action="append",
        default=[],
        help="fetch only this source_id; may be supplied more than once",
    )
    parser.add_argument(
        "--include-non-paper-facing",
        action="store_true",
        help="also fetch rows that are not paper-facing eligible",
    )
    return parser.parse_args()


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def resolve_repo_path(value: str, root: Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return root / path


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def eligible_for_default_fetch(row: dict[str, str]) -> bool:
    return (
        is_yes(row.get("paper_facing_eligible") or "")
        and (row.get("machine_human_status") or "").strip() == "human_published"
        and (row.get("rights_status") or "").strip() in PAPER_RIGHTS_ALLOWED
    )


def fetch_resource(url: str) -> tuple[bytes, str]:
    request = Request(
        url,
        headers={
            "User-Agent": "wordspend-provenance-fetch/0.1 (+https://github.com/solresol/wordspend)",
        },
    )
    with urlopen(request, timeout=60) as response:
        return response.read(), response.headers.get("Last-Modified", "")


def relative_to_root(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def main() -> int:
    args = parse_args()
    root = repo_root()
    registry = resolve_repo_path(args.registry, root)
    output_dir = resolve_repo_path(args.output_dir, root)
    manifest = resolve_repo_path(args.manifest, root)

    row_count, paper_facing_count, validation_errors = validate_registry(registry)
    if validation_errors:
        for error in validation_errors:
            print(error, file=sys.stderr)
        return 1

    wanted_source_ids = set(args.source_id)
    selected_rows = []
    for row in read_rows(registry):
        source_id = (row.get("source_id") or "").strip()
        if wanted_source_ids and source_id not in wanted_source_ids:
            continue
        if not args.include_non_paper_facing and not eligible_for_default_fetch(row):
            continue
        if (row.get("download_format") or "").strip() != "plain_text":
            print(f"{source_id}: skipping non-plain-text source", file=sys.stderr)
            continue
        selected_rows.append(row)

    if wanted_source_ids:
        selected_ids = {row["source_id"] for row in selected_rows}
        missing_ids = sorted(wanted_source_ids - selected_ids)
        if missing_ids:
            print(f"no fetchable registry row(s): {', '.join(missing_ids)}", file=sys.stderr)
            return 1

    output_dir.mkdir(parents=True, exist_ok=True)
    manifest.parent.mkdir(parents=True, exist_ok=True)

    retrieved_at = dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    manifest_rows = []
    for row in selected_rows:
        source_id = row["source_id"]
        download_url = row["download_url"]
        payload, http_last_modified = fetch_resource(download_url)
        raw_path = output_dir / f"{source_id}.txt"
        raw_path.write_bytes(payload)
        digest = hashlib.sha256(payload).hexdigest()
        manifest_rows.append(
            {
                "source_id": source_id,
                "work_id": row["work_id"],
                "download_url": download_url,
                "download_format": row["download_format"],
                "raw_path": relative_to_root(raw_path, root),
                "bytes": str(len(payload)),
                "sha256": digest,
                "retrieved_at_utc": retrieved_at,
                "http_last_modified": http_last_modified,
                "rights_status": row["rights_status"],
                "machine_human_status": row["machine_human_status"],
                "paper_facing_eligible": row["paper_facing_eligible"],
                "text_stage": "raw_provider_text",
                "front_back_matter_status": "not_stripped",
            }
        )

    with manifest.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=MANIFEST_COLUMNS)
        writer.writeheader()
        writer.writerows(manifest_rows)

    print(f"Validated {row_count} translation source row(s).")
    print(f"Paper-facing eligible source row(s): {paper_facing_count}.")
    print(f"Fetched {len(manifest_rows)} source row(s).")
    print(f"Wrote manifest: {relative_to_root(manifest, root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
