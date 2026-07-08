"""Prepared translation-text manifest loading and paper-facing filters."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


PAPER_FACING_RIGHTS_STATUSES = frozenset(
    {
        "public_domain_us",
        "public_domain_worldwide",
        "open_license",
    }
)

PAPER_FACING_PREPARED_TEXT_COLUMNS = (
    "source_id",
    "work_id",
    "target_language_code",
    "translator",
    "translation_title",
    "edition",
    "publication_date",
    "prepared_path",
    "prepared_sha256",
    "text_stage",
    "front_back_matter_status",
    "rights_status",
    "machine_human_status",
    "paper_facing_eligible",
)


def is_yes(value: object) -> bool:
    """Return true for the manifest's normalized yes flag."""
    return str(value or "").strip().lower() == "yes"


def load_prepared_text_manifest(path: str | Path) -> pd.DataFrame:
    """Load a prepared-text manifest as strings, preserving blank values."""
    return pd.read_csv(path, dtype=str).fillna("")


def paper_facing_prepared_text_mask(frame: pd.DataFrame) -> pd.Series:
    """Return a mask for prepared texts eligible for paper-facing analysis."""
    missing = [column for column in PAPER_FACING_PREPARED_TEXT_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(f"Missing required prepared-text columns: {', '.join(missing)}")

    return (
        frame["paper_facing_eligible"].map(is_yes)
        & frame["machine_human_status"].astype(str).str.strip().eq("human_published")
        & frame["rights_status"].astype(str).str.strip().isin(PAPER_FACING_RIGHTS_STATUSES)
        & frame["text_stage"].astype(str).str.strip().eq("prepared_translation_body")
        & frame["front_back_matter_status"].astype(str).str.strip().eq("stripped")
    )


def select_paper_facing_prepared_texts(frame: pd.DataFrame) -> pd.DataFrame:
    """Select manifest rows that may feed paper-facing alignment and analysis."""
    return frame.loc[paper_facing_prepared_text_mask(frame)].copy().reset_index(drop=True)
