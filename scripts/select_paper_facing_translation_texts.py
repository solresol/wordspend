#!/usr/bin/env python3
"""Validate and select prepared translation texts for paper-facing analysis."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from validate_prepared_translation_texts import repo_root, resolve_repo_path, validate_manifest
from wordspend.prepared_texts import load_prepared_text_manifest, select_paper_facing_prepared_texts


OUTPUT_COLUMNS = [
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
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--manifest",
        default="data/prepared/translation_texts.csv",
        help="CSV prepared-text manifest to filter",
    )
    parser.add_argument(
        "--registry",
        default="data/translation_sources.csv",
        help="CSV registry containing source provenance",
    )
    parser.add_argument(
        "--output",
        default="build/paper-facing/prepared_translation_texts.csv",
        help="CSV path to write with selected paper-facing prepared texts",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = repo_root()
    manifest = resolve_repo_path(args.manifest, root)
    registry = resolve_repo_path(args.registry, root)
    output = resolve_repo_path(args.output, root)

    row_count, validated_paper_count, errors = validate_manifest(manifest, registry, root)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    selected = select_paper_facing_prepared_texts(load_prepared_text_manifest(manifest))
    output.parent.mkdir(parents=True, exist_ok=True)
    selected.to_csv(output, columns=OUTPUT_COLUMNS, index=False)

    print(f"Validated {row_count} prepared translation text row(s).")
    print(f"Validated paper-facing prepared text row(s): {validated_paper_count}.")
    print(f"Selected paper-facing prepared text row(s): {len(selected)}.")
    print(f"Wrote {Path(args.output)}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
