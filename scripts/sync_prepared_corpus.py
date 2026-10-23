#!/usr/bin/env python3
"""Validate and import prepared corpus/provenance into PostgreSQL staging."""
import subprocess
from pathlib import Path

from validate_prepared_translation_texts import validate_manifest
from wordspend.corpus import load_snapshot, sync_snapshot
from wordspend.db import connect
from wordspend.source_editions import validate_source_edition_registry


def main():
    root = Path(__file__).resolve().parents[1]
    _, _, errors = validate_manifest(root/'data/prepared/translation_texts.csv', root/'data/translation_sources.csv', root)
    _, _, source_errors = validate_source_edition_registry(root/'data/source_editions.csv')
    if errors or source_errors:
        raise SystemExit('\n'.join(errors + source_errors))
    snapshot = load_snapshot(root)
    revision = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip()
    with connect() as conn:
        print(sync_snapshot(conn, snapshot, revision))


if __name__ == '__main__':
    main()
