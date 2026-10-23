#!/usr/bin/env python3
"""Export blank adjudication decisions or import completed human decisions."""
import argparse
import csv
from pathlib import Path

from wordspend.adjudication import ADJUDICATION_FIELDS, adjudicate_book, reviewed_book
from wordspend.corpus import read_csv
from wordspend.db import connect


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--translation-source-id', required=True)
    parser.add_argument('--book', type=int, required=True)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--export', type=Path)
    action.add_argument('--decisions', type=Path)
    args = parser.parse_args()
    with connect() as conn:
        if args.export:
            rows = reviewed_book(conn, args.translation_source_id, args.book)
            if not rows:
                raise SystemExit('No completely reviewed book is available.')
            # Exclusive creation preserves any previously entered decisions.
            with args.export.open('x', newline='', encoding='utf-8') as handle:
                fields = ADJUDICATION_FIELDS + ['source_text', 'target_text', 'reviewer', 'reviewed_at']
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                for row in rows:
                    writer.writerow({'candidate_id': row['registry_id'], 'reviewed_sha256': row['sha256'],
                                     **{k: row['payload'][k] for k in fields[len(ADJUDICATION_FIELDS):]}})
        else:
            print(adjudicate_book(conn, args.translation_source_id, args.book, read_csv(args.decisions)))


if __name__ == '__main__':
    main()
