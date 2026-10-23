#!/usr/bin/env python3
"""Apply the wordspend database schema and migrations."""

import hashlib
from pathlib import Path

from wordspend.db import connect


def main() -> None:
    repo = Path(__file__).resolve().parents[1]
    with connect() as conn:
        conn.execute("SELECT pg_advisory_lock(hashtext('wordspend-schema'))")
        conn.execute('''CREATE TABLE IF NOT EXISTS schema_migrations (
            filename TEXT PRIMARY KEY, sha256 TEXT NOT NULL,
            applied_at TIMESTAMPTZ NOT NULL DEFAULT now())''')
        conn.commit()
        for schema_path in sorted((repo / "schema").glob("*.sql")):
            digest = hashlib.sha256(schema_path.read_bytes()).hexdigest()
            old = conn.execute('SELECT sha256 FROM schema_migrations WHERE filename=%s',
                               (schema_path.name,)).fetchone()
            if old:
                if old['sha256'] != digest:
                    raise RuntimeError(f'Applied migration changed: {schema_path.name}')
                continue
            # Record each migration in the same transaction as its DDL.
            conn.execute(schema_path.read_text())
            conn.execute('INSERT INTO schema_migrations(filename,sha256) VALUES (%s,%s)',
                         (schema_path.name, digest))
            conn.commit()
            print(f"Applied {schema_path.relative_to(repo)}")


if __name__ == "__main__":
    main()
