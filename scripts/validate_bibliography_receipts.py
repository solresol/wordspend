#!/usr/bin/env python3
"""Check cached edition-credit receipts; this does not authenticate a printing."""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
from pathlib import Path
import sys
from urllib.parse import urlparse


def validate_receipt(path: Path, registry: list[dict[str, str]], root: Path) -> list[str]:
    """Fail closed on missing evidence, drift, or mismatched registry links."""
    try:
        receipt = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(receipt, dict):
            raise ValueError('receipt must be a JSON object')
        for field in ('source_id', 'evidence_kind', 'source_url', 'resolved_url',
                      'retrieved_at', 'raw_path', 'raw_sha256', 'credited_edition_year',
                      'credited_publisher', 'credit_text', 'limitations'):
            if not isinstance(receipt.get(field), str) or not receipt[field].strip():
                raise ValueError(f'{field} must be a nonblank string')
        if receipt['evidence_kind'] != 'provider_archived_production_credit':
            raise ValueError('unsupported evidence_kind')
        timestamp = dt.datetime.fromisoformat(receipt['retrieved_at'])
        if timestamp.utcoffset() is None:
            raise ValueError('retrieved_at requires a timezone')
        for field in ('source_url', 'resolved_url'):
            url = urlparse(receipt[field])
            if url.scheme not in {'http', 'https'} or not url.netloc:
                raise ValueError(f'{field} must be an HTTP(S) URL')
        matches = [r for r in registry if r.get('source_id') == receipt['source_id']]
        if len(matches) != 1:
            raise ValueError('source_id must identify exactly one registry row')
        row = matches[0]
        if (row.get('historical_publication_date') != receipt['credited_edition_year']
                or row.get('historical_publication_date_kind') != 'edition'
                or row.get('historical_publication_source_url') != receipt['source_url']
                or not row.get('historical_publication_citation', '').strip()):
            raise ValueError('historical edition date/citation/URL does not match registry')
        raw_path = (root / receipt['raw_path']).resolve()
        if not raw_path.is_relative_to(root.resolve()) or Path(receipt['raw_path']).is_absolute():
            raise ValueError('raw_path must stay within repository')
        raw = raw_path.read_bytes()
        if type(receipt.get('raw_bytes')) is not int or receipt['raw_bytes'] != len(raw):
            raise ValueError('raw_bytes mismatch')
        if hashlib.sha256(raw).hexdigest() != receipt['raw_sha256']:
            raise ValueError('raw_sha256 mismatch')
        lines = raw.decode('utf-8').splitlines()
        start, end = receipt.get('credit_line_start'), receipt.get('credit_line_end')
        if (type(start) is not int or type(end) is not int
                or not 1 <= start <= end <= len(lines)):
            raise ValueError('invalid credit line range')
        credit = '\n'.join(lines[start - 1:end])
        if credit != receipt['credit_text']:
            raise ValueError('credit_text does not match cached line range')
        if receipt['credited_edition_year'] not in credit or receipt['credited_publisher'] not in credit:
            raise ValueError('credited year/publisher absent from credit_text')
    except (OSError, ValueError, TypeError) as exc:
        return [f'{path}: {exc}']
    return []


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.root
    try:
        with (root / 'data/translation_sources.csv').open(encoding='utf-8', newline='') as handle:
            registry = list(csv.DictReader(handle))
        paths = sorted((root / 'data/bibliography').glob('*.json'))
        errors = [] if paths else ['No bibliography receipts found']
        for path in paths:
            errors.extend(validate_receipt(path, registry, root))
    except OSError as exc:
        errors = [str(exc)]
    if errors:
        print('\n'.join(errors), file=sys.stderr)
        return 1
    print(f'Validated {len(paths)} cached edition-credit receipt(s); physical printing fidelity remains unverified.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
