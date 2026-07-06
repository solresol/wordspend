#!/usr/bin/env python3
"""Apply the wordspend database schema and migrations."""

from pathlib import Path

from wordspend.db import apply_schema, connect


def main() -> None:
    repo = Path(__file__).resolve().parents[1]
    with connect() as conn:
        for schema_path in sorted((repo / "schema").glob("*.sql")):
            apply_schema(conn, schema_path)
            print(f"Applied {schema_path.relative_to(repo)}")


if __name__ == "__main__":
    main()
