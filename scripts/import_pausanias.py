#!/usr/bin/env python3
"""Import Pausanias aligned passages from the existing Pausanias database."""

from __future__ import annotations

import argparse
import os
from typing import Any

import psycopg
from psycopg.rows import dict_row

from wordspend.db import (
    connect,
    get_work_id,
    stable_hash,
    upsert_aligned_segments,
    upsert_source_version,
    upsert_translation,
)


def passage_sort_key(passage_id: str) -> tuple[int, ...]:
    return tuple(int(part) for part in str(passage_id).split(".") if part.isdigit())


def fetch_pausanias_rows(limit: int = 0) -> list[dict[str, Any]]:
    source_dsn = os.environ.get("PAUSANIAS_DATABASE_URL", "dbname=pausanias")
    query = """
        SELECT
            p.id AS segment_ref,
            p.passage AS source_text,
            t.english_translation AS target_text
        FROM passages p
        JOIN translations t ON t.passage_id = p.id
        WHERE t.english_translation IS NOT NULL
          AND btrim(t.english_translation) <> ''
          AND p.passage IS NOT NULL
          AND btrim(p.passage) <> ''
    """
    with psycopg.connect(source_dsn, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            rows = cur.fetchall()
    rows = sorted(rows, key=lambda row: passage_sort_key(row["segment_ref"]))
    if limit and limit > 0:
        rows = rows[:limit]
    imported = []
    for index, row in enumerate(rows, start=1):
        imported.append(
            {
                "segment_ref": row["segment_ref"],
                "segment_order": index,
                "source_text": row["source_text"],
                "target_text": row["target_text"],
                "metadata": {"source_database": "pausanias"},
            }
        )
    return imported


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0, help="Maximum rows to import; 0 means no limit.")
    args = parser.parse_args()

    rows = fetch_pausanias_rows(limit=args.limit)
    with connect() as conn:
        work_id = get_work_id(conn, "pausanias-description-of-greece")
        source_version_id = upsert_source_version(
            conn,
            work_id=work_id,
            version_label="pausanias-db-current",
            source_type="PostgreSQL import",
            source_citation="Existing /Users/gregb/Documents/devel/pausanias pipeline on raksasa",
            text_hash=stable_hash(*(row["source_text"] for row in rows[:50])),
            notes="Bootstrap import from the live Pausanias project database.",
        )
        translation_id = upsert_translation(
            conn,
            work_id=work_id,
            translation_label="pausanias-db-english-current",
            translator="Pausanias project pipeline",
            target_language="English",
            publication_date="unpublished bootstrap",
            provenance="Existing Pausanias translations table on raksasa",
            license_status="project-internal",
            rights_statement="Not paper evidence; project-internal machine-generated bootstrap translation.",
            translation_source_type="machine_bootstrap",
            is_machine_generated=True,
            text_hash=stable_hash(*(row["target_text"] for row in rows[:50])),
            notes="Used only as bootstrap diagnostics until translation provenance is paper-ready.",
        )
        count = upsert_aligned_segments(
            conn,
            work_id=work_id,
            source_version_id=source_version_id,
            translation_id=translation_id,
            rows=rows,
            source_language="Ancient Greek",
            target_language="English",
            alignment_level="passage",
        )
    print(f"Imported {count} Pausanias aligned passages")


if __name__ == "__main__":
    main()
