#!/usr/bin/env python3
"""Load data/work_catalog.csv into PostgreSQL."""

import argparse
from pathlib import Path

from wordspend.db import connect, load_work_catalog


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", default="data/work_catalog.csv")
    args = parser.parse_args()

    repo = Path(__file__).resolve().parents[1]
    catalog = (repo / args.catalog).resolve() if not Path(args.catalog).is_absolute() else Path(args.catalog)
    with connect() as conn:
        count = load_work_catalog(conn, catalog)
    print(f"Loaded {count} catalog rows from {catalog}")


if __name__ == "__main__":
    main()
