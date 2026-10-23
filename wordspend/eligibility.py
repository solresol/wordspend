"""Explicit corpus selection shared by CSV and PostgreSQL analysis."""

from __future__ import annotations

import pandas as pd

RIGHTS = {'public_domain_us', 'public_domain_worldwide', 'open_license'}


def select_analysis_segments(frame: pd.DataFrame, mode: str = 'paper') -> pd.DataFrame:
    """Fail closed on missing provenance; diagnostics require explicit bootstrap mode."""
    required = {'is_machine_generated', 'translation_source_type'}
    if mode == 'paper':
        required |= {'paper_facing_eligible', 'review_status', 'analysis_status',
                     'alignment_level', 'source_editorial_status',
                     'source_rights_status', 'translation_rights_status'}
    elif mode != 'bootstrap':
        raise ValueError(f'Unknown analysis mode: {mode}')
    missing = required - set(frame.columns)
    if missing:
        raise ValueError('Missing analysis eligibility columns: ' + ', '.join(sorted(missing)))
    def values(column):
        return frame[column].fillna('').astype(str).str.strip().str.lower()
    machine = values('is_machine_generated')
    kind = values('translation_source_type')
    if mode == 'bootstrap':
        mask = machine.isin({'true', 'yes', '1'}) & kind.eq('machine_bootstrap')
    else:
        mask = (
            machine.isin({'false', 'no', '0'})
            & kind.eq('existing_human_translation')
            & values('paper_facing_eligible').isin({'true', 'yes', '1'})
            & values('review_status').eq('adjudicated')
            & values('analysis_status').eq('eligible')
            & values('alignment_level').eq('reviewed_source_line_range_to_translation_paragraph')
            & values('source_editorial_status').eq('human_edited_published')
            & values('source_rights_status').isin(RIGHTS)
            & values('translation_rights_status').isin(RIGHTS)
        )
    return frame.loc[mask].copy().reset_index(drop=True)
