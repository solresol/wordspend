"""PostgreSQL helpers for wordspend."""

from __future__ import annotations

import csv
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Iterable

import pandas as pd
import psycopg
from psycopg.rows import dict_row

from .analysis import dataframe_to_records
from .textstats import length_metrics


def database_url() -> str:
    """Return the configured database URL or local peer default."""
    return os.environ.get("WORDSPEND_DATABASE_URL", "dbname=wordspend")


def connect(dsn: str | None = None) -> psycopg.Connection:
    """Open a PostgreSQL connection."""
    return psycopg.connect(dsn or database_url(), row_factory=dict_row)


def apply_schema(conn: psycopg.Connection, schema_path: str | Path) -> None:
    """Apply an SQL schema file."""
    sql = Path(schema_path).read_text(encoding="utf-8")
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.commit()


def stable_hash(*parts: object) -> str:
    """Hash text parts for provenance and idempotent imports."""
    digest = hashlib.sha256()
    for part in parts:
        digest.update(str(part or "").encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()


def upsert_work(conn: psycopg.Connection, row: dict[str, Any]) -> int:
    """Insert or update a work and return its id."""
    fields = [
        "slug",
        "title",
        "author",
        "source_language",
        "planned_target_languages",
        "period",
        "genre",
        "priority",
        "status",
        "source_provenance",
        "translation_plan",
        "license_status",
        "notes",
    ]
    values = {field: row.get(field) or None for field in fields}
    values["priority"] = values["priority"] or "medium"
    values["status"] = values["status"] or "candidate"
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO works (
                slug, title, author, source_language, planned_target_languages,
                period, genre, priority, status, source_provenance,
                translation_plan, license_status, notes
            )
            VALUES (
                %(slug)s, %(title)s, %(author)s, %(source_language)s,
                %(planned_target_languages)s, %(period)s, %(genre)s,
                %(priority)s, %(status)s, %(source_provenance)s, %(translation_plan)s,
                %(license_status)s, %(notes)s
            )
            ON CONFLICT (slug) DO UPDATE SET
                title = EXCLUDED.title,
                author = EXCLUDED.author,
                source_language = EXCLUDED.source_language,
                planned_target_languages = EXCLUDED.planned_target_languages,
                period = EXCLUDED.period,
                genre = EXCLUDED.genre,
                priority = EXCLUDED.priority,
                status = EXCLUDED.status,
                source_provenance = EXCLUDED.source_provenance,
                translation_plan = EXCLUDED.translation_plan,
                license_status = EXCLUDED.license_status,
                notes = EXCLUDED.notes,
                updated_at = now()
            RETURNING id
            """,
            values,
        )
        work_id = int(cur.fetchone()["id"])
    return work_id


def load_work_catalog(conn: psycopg.Connection, catalog_path: str | Path) -> int:
    """Load the candidate work catalog."""
    count = 0
    with Path(catalog_path).open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            upsert_work(conn, row)
            count += 1
    conn.commit()
    return count


def get_work_id(conn: psycopg.Connection, slug: str) -> int:
    """Return a work id for a slug."""
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM works WHERE slug = %s", (slug,))
        row = cur.fetchone()
    if not row:
        raise KeyError(f"Unknown work slug: {slug}")
    return int(row["id"])


def upsert_source_version(
    conn: psycopg.Connection,
    *,
    work_id: int,
    version_label: str,
    source_type: str = "",
    source_citation: str = "",
    source_url: str = "",
    text_hash: str = "",
    notes: str = "",
) -> int:
    """Insert or update a source text version."""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO source_text_versions (
                work_id, version_label, source_type, source_citation,
                source_url, text_hash, notes
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (work_id, version_label) DO UPDATE SET
                source_type = EXCLUDED.source_type,
                source_citation = EXCLUDED.source_citation,
                source_url = EXCLUDED.source_url,
                text_hash = EXCLUDED.text_hash,
                notes = EXCLUDED.notes
            RETURNING id
            """,
            (work_id, version_label, source_type, source_citation, source_url, text_hash, notes),
        )
        return int(cur.fetchone()["id"])


def upsert_translation(
    conn: psycopg.Connection,
    *,
    work_id: int,
    translation_label: str,
    translator: str = "",
    target_language: str = "English",
    publication_year: int | None = None,
    publication_date: str = "",
    edition_citation: str = "",
    provenance: str = "",
    source_url: str = "",
    download_url: str = "",
    license_status: str = "",
    rights_statement: str = "",
    translation_source_type: str = "existing_human_translation",
    is_machine_generated: bool = False,
    text_hash: str = "",
    notes: str = "",
) -> int:
    """Insert or update a translation version."""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO translations (
                work_id, translator, translation_label, target_language,
                publication_year, publication_date, edition_citation,
                provenance, source_url, download_url, license_status,
                rights_statement, translation_source_type, is_machine_generated,
                text_hash, notes
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (work_id, translation_label) DO UPDATE SET
                translator = EXCLUDED.translator,
                target_language = EXCLUDED.target_language,
                publication_year = EXCLUDED.publication_year,
                publication_date = EXCLUDED.publication_date,
                edition_citation = EXCLUDED.edition_citation,
                provenance = EXCLUDED.provenance,
                source_url = EXCLUDED.source_url,
                download_url = EXCLUDED.download_url,
                license_status = EXCLUDED.license_status,
                rights_statement = EXCLUDED.rights_statement,
                translation_source_type = EXCLUDED.translation_source_type,
                is_machine_generated = EXCLUDED.is_machine_generated,
                text_hash = EXCLUDED.text_hash,
                notes = EXCLUDED.notes
            RETURNING id
            """,
            (
                work_id,
                translator,
                translation_label,
                target_language,
                publication_year,
                publication_date,
                edition_citation,
                provenance,
                source_url,
                download_url,
                license_status,
                rights_statement,
                translation_source_type,
                is_machine_generated,
                text_hash,
                notes,
            ),
        )
        return int(cur.fetchone()["id"])


def upsert_aligned_segments(
    conn: psycopg.Connection,
    *,
    work_id: int,
    source_version_id: int | None,
    translation_id: int | None,
    rows: Iterable[dict[str, Any]],
    source_language: str,
    target_language: str = "English",
    alignment_level: str = "passage",
) -> int:
    """Insert or update aligned segments."""
    count = 0
    with conn.cursor() as cur:
        for row in rows:
            source_text = row["source_text"]
            target_text = row["target_text"]
            metrics = length_metrics(source_text, target_text, source_language, target_language)
            metadata = row.get("metadata") or {}
            if isinstance(metadata, str):
                metadata = json.loads(metadata) if metadata.strip() else {}
            cur.execute(
                """
                INSERT INTO aligned_segments (
                    work_id, source_version_id, translation_id, segment_ref,
                    segment_order, alignment_level, alignment_status,
                    source_text, target_text, source_token_count,
                    target_token_count, source_char_count, target_char_count,
                    source_syllable_count, target_syllable_count, metadata,
                    text_hash
                )
                VALUES (
                    %(work_id)s, %(source_version_id)s, %(translation_id)s,
                    %(segment_ref)s, %(segment_order)s, %(alignment_level)s,
                    %(alignment_status)s, %(source_text)s, %(target_text)s,
                    %(source_token_count)s, %(target_token_count)s,
                    %(source_char_count)s, %(target_char_count)s,
                    %(source_syllable_count)s, %(target_syllable_count)s,
                    %(metadata)s::jsonb, %(text_hash)s
                )
                ON CONFLICT (work_id, translation_id, segment_ref, alignment_level)
                DO UPDATE SET
                    source_version_id = EXCLUDED.source_version_id,
                    source_text = EXCLUDED.source_text,
                    target_text = EXCLUDED.target_text,
                    source_token_count = EXCLUDED.source_token_count,
                    target_token_count = EXCLUDED.target_token_count,
                    source_char_count = EXCLUDED.source_char_count,
                    target_char_count = EXCLUDED.target_char_count,
                    source_syllable_count = EXCLUDED.source_syllable_count,
                    target_syllable_count = EXCLUDED.target_syllable_count,
                    metadata = EXCLUDED.metadata,
                    text_hash = EXCLUDED.text_hash,
                    imported_at = now()
                """,
                {
                    "work_id": work_id,
                    "source_version_id": source_version_id,
                    "translation_id": translation_id,
                    "segment_ref": row["segment_ref"],
                    "segment_order": int(row.get("segment_order") or count + 1),
                    "alignment_level": alignment_level,
                    "alignment_status": row.get("alignment_status") or "imported",
                    "source_text": source_text,
                    "target_text": target_text,
                    **metrics,
                    "metadata": json.dumps(metadata),
                    "text_hash": stable_hash(row["segment_ref"], source_text, target_text),
                },
            )
            count += 1
    conn.commit()
    return count


def fetch_segments(conn: psycopg.Connection, work_slugs: list[str] | None = None, limit: int | None = None) -> pd.DataFrame:
    """Fetch aligned segments for analysis."""
    params: list[Any] = []
    where = ["s.source_text <> ''", "s.target_text <> ''"]
    if work_slugs:
        where.append("w.slug = ANY(%s)")
        params.append(work_slugs)
    query = f"""
        SELECT
            s.id AS aligned_segment_id,
            w.slug AS work_slug,
            w.title AS work_title,
            w.source_language,
            coalesce(t.target_language, '') AS target_language,
            s.segment_ref,
            s.segment_order,
            s.alignment_level,
            s.source_text,
            s.target_text,
            s.source_token_count,
            s.target_token_count,
            s.source_char_count,
            s.target_char_count,
            s.source_syllable_count,
            s.target_syllable_count
        FROM aligned_segments s
        JOIN works w ON w.id = s.work_id
        LEFT JOIN translations t ON t.id = s.translation_id
        WHERE {' AND '.join(where)}
        ORDER BY w.slug, s.segment_order, s.segment_ref
    """
    if limit and limit > 0:
        query += " LIMIT %s"
        params.append(limit)
    with conn.cursor() as cur:
        cur.execute(query, params)
        rows = cur.fetchall()
    return pd.DataFrame(rows)


def fetch_work_catalog(conn: psycopg.Connection) -> pd.DataFrame:
    """Fetch work inventory for the site."""
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM corpus_inventory")
        rows = cur.fetchall()
    return pd.DataFrame(rows)


def save_analysis_result(conn: psycopg.Connection, result: dict[str, Any], notes: str = "") -> int:
    """Persist one analysis result and return the analysis run id."""
    metrics = result["metrics"]
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO analysis_runs (
                corpus_label, metric, baseline_model, feature_space,
                segment_count, source_length_column, target_length_column,
                intercept, slope, r2, rmse, residual_std,
                source_feature_count, target_feature_count,
                source_predictor_r2, target_predictor_r2, parameters, notes
            )
            VALUES (
                %(corpus_label)s, %(metric)s, %(baseline_model)s,
                %(feature_space)s, %(segment_count)s,
                %(source_length_column)s, %(target_length_column)s,
                %(intercept)s, %(slope)s, %(r2)s, %(rmse)s,
                %(residual_std)s, %(source_feature_count)s,
                %(target_feature_count)s, %(source_predictor_r2)s,
                %(target_predictor_r2)s, %(parameters)s::jsonb, %(notes)s
            )
            RETURNING id
            """,
            {
                **metrics,
                "parameters": json.dumps(
                    {
                        "min_df": metrics.get("min_df"),
                        "top_n": metrics.get("top_n"),
                        "max_features": metrics.get("max_features"),
                    }
                ),
                "notes": notes,
            },
        )
        run_id = int(cur.fetchone()["id"])

        segments = result.get("segments", pd.DataFrame())
        for record in dataframe_to_records(segments):
            aligned_segment_id = record.get("aligned_segment_id")
            if aligned_segment_id is None:
                continue
            cur.execute(
                """
                INSERT INTO segment_residuals (
                    analysis_run_id, aligned_segment_id, source_length,
                    target_length, expected_target_length, residual,
                    standardized_residual
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (analysis_run_id, aligned_segment_id) DO UPDATE SET
                    source_length = EXCLUDED.source_length,
                    target_length = EXCLUDED.target_length,
                    expected_target_length = EXCLUDED.expected_target_length,
                    residual = EXCLUDED.residual,
                    standardized_residual = EXCLUDED.standardized_residual
                """,
                (
                    run_id,
                    int(aligned_segment_id),
                    float(record["source_length"]),
                    float(record["target_length"]),
                    float(record["expected_target_length"]),
                    float(record["residual"]),
                    float(record.get("standardized_residual") or 0.0),
                ),
            )

        for side, frame_name in (("source", "source_predictors"), ("target", "target_predictors")):
            for record in dataframe_to_records(result.get(frame_name, pd.DataFrame())):
                cur.execute(
                    """
                    INSERT INTO residual_predictors (
                        analysis_run_id, side, feature, coefficient,
                        segment_count, mean_residual_with_feature,
                        mean_residual_without_feature, example_refs
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                    ON CONFLICT (analysis_run_id, side, feature) DO UPDATE SET
                        coefficient = EXCLUDED.coefficient,
                        segment_count = EXCLUDED.segment_count,
                        mean_residual_with_feature = EXCLUDED.mean_residual_with_feature,
                        mean_residual_without_feature = EXCLUDED.mean_residual_without_feature,
                        example_refs = EXCLUDED.example_refs
                    """,
                    (
                        run_id,
                        side,
                        record["feature"],
                        float(record["coefficient"]),
                        int(record["segment_count"]),
                        record.get("mean_residual_with_feature"),
                        record.get("mean_residual_without_feature"),
                        json.dumps(record.get("example_refs") or []),
                    ),
                )
    conn.commit()
    return run_id
