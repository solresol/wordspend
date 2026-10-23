"""Promote a fully human-reviewed book only after recorded adjudication."""

from datetime import datetime

from .corpus import require
from .db import upsert_aligned_segments
from .eligibility import RIGHTS
from .tokenization import TOKENIZER_ID, tokenize_with_offsets

ADJUDICATION_FIELDS = ['candidate_id', 'reviewed_sha256', 'decision', 'adjudicator',
                       'adjudicated_at', 'notes']


def reviewed_book(conn, translation_registry_id, book):
    return conn.execute('''SELECT a.*,t.target_language,t.is_machine_generated,
        t.license_status,t.translation_source_type,t.metadata,v.rights_status,
        v.editorial_status,v.provenance FROM corpus_artifacts a
        JOIN translations t ON t.id=a.translation_id
        JOIN source_text_versions v ON v.id=a.source_version_id
        WHERE a.kind='reviewed_alignment' AND a.is_current
          AND t.registry_id=%s AND a.book=%s
        ORDER BY (a.payload->>'segment_index')::int''', (translation_registry_id, book)).fetchall()


def adjudicate_book(conn, translation_registry_id, book, decisions):
    """Validate all decisions before writing; rejection excludes the entire book."""
    conn.execute("SELECT pg_advisory_xact_lock(hashtext('wordspend-corpus'))")
    rows = reviewed_book(conn, translation_registry_id, book)
    require(bool(rows), 'No completely reviewed book is staged for adjudication')
    expected = {r['registry_id']: r for r in rows}
    entered = {r['candidate_id']: r for r in decisions}
    require(len(entered) == len(decisions) and set(entered) == set(expected), 'Decisions must cover exactly the reviewed book')
    candidate_count = conn.execute('''SELECT count(*) AS n FROM corpus_artifacts a
        JOIN translations t ON t.id=a.translation_id WHERE a.kind='candidate'
        AND a.is_current AND t.registry_id=%s AND a.book=%s''', (translation_registry_id, book)).fetchone()['n']
    require(len(rows) == candidate_count, 'Incomplete book review')
    for row in rows:
        d = entered[row['registry_id']]
        require(d['reviewed_sha256'] == row['sha256'], 'Stale or modified reviewed alignment')
        require(d['decision'] in {'approve', 'reject'}, 'Decision must be approve or reject')
        require(bool(d['adjudicator'].strip()) and bool(d['notes'].strip()), 'Adjudicator and notes are required')
        timestamp = datetime.fromisoformat(d['adjudicated_at'].replace('Z', '+00:00'))
        reviewed_at = datetime.fromisoformat(row['payload']['reviewed_at'].replace('Z', '+00:00'))
        require(timestamp.tzinfo is not None and timestamp >= reviewed_at, 'Adjudication timestamp must include timezone and follow review')
        previous = conn.execute('SELECT * FROM alignment_adjudications WHERE candidate_id=%s', (row['registry_id'],)).fetchone()
        if previous:
            require(timestamp >= previous['adjudicated_at'], 'Cannot replay an older adjudication')
            if timestamp == previous['adjudicated_at']:
                require(all(str(d[k]) == str(previous[k]) for k in ['decision', 'adjudicator', 'notes', 'reviewed_sha256']),
                        'Changed adjudication requires a newer timestamp')
        require(not row['is_machine_generated'] and row['translation_source_type'] == 'existing_human_translation'
                and row['license_status'] in RIGHTS and row['rights_status'] in RIGHTS
                and row['editorial_status'] == 'human_edited_published'
                and row['metadata']['paper_facing_eligible'] == 'yes'
                and row['provenance']['paper_facing_eligible'] == 'yes', 'Provenance is not paper-facing')
    approved = all(d['decision'] == 'approve' for d in decisions)
    for row in rows:
        payload, decision = row['payload'], entered[row['registry_id']]
        source_code = row['provenance']['source_language_code']
        target_code = row['metadata']['target_language_code']
        segment_ref = f"{book}.{int(payload['segment_index']):03d}"
        existing = conn.execute('''SELECT id FROM aligned_segments WHERE work_id=%s AND translation_id=%s
            AND segment_ref=%s AND alignment_level=%s''', (row['work_id'], row['translation_id'], segment_ref,
            payload['alignment_level'])).fetchone()
        segment_id = existing['id'] if existing else None
        if approved:
            upsert_aligned_segments(conn, work_id=row['work_id'], source_version_id=row['source_version_id'],
                translation_id=row['translation_id'], source_language=source_code, target_language=target_code,
                alignment_level=payload['alignment_level'], commit=False,
                rows=[{'segment_ref': segment_ref, 'segment_order': book * 10000 + int(payload['segment_index']),
                       'source_text': payload['source_text'], 'target_text': payload['target_text'],
                       'metadata': {'candidate_id': row['registry_id'], 'reviewed_sha256': row['sha256'],
                                    'tokenizer_id': TOKENIZER_ID, 'reviewer': payload['reviewer']}}])
            segment_id = conn.execute('''SELECT id FROM aligned_segments WHERE work_id=%s AND translation_id=%s
                AND segment_ref=%s AND alignment_level=%s''', (row['work_id'], row['translation_id'],
                segment_ref, payload['alignment_level'])).fetchone()['id']
            conn.execute('''UPDATE aligned_segments SET paper_facing_eligible=true,review_status='adjudicated',
                analysis_status='eligible',alignment_status='adjudicated',source_token_count=%s,target_token_count=%s
                WHERE id=%s''', (len(tokenize_with_offsets(payload['source_text'], source_code)),
                len(tokenize_with_offsets(payload['target_text'], target_code)), segment_id))
        elif segment_id:
            conn.execute("UPDATE aligned_segments SET paper_facing_eligible=false,analysis_status='excluded' WHERE id=%s", (segment_id,))
        conn.execute('''INSERT INTO alignment_adjudications
            (candidate_id,reviewed_sha256,decision,adjudicator,adjudicated_at,notes,aligned_segment_id)
            VALUES (%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(candidate_id) DO UPDATE SET
            reviewed_sha256=EXCLUDED.reviewed_sha256,decision=EXCLUDED.decision,
            adjudicator=EXCLUDED.adjudicator,adjudicated_at=EXCLUDED.adjudicated_at,
            notes=EXCLUDED.notes,aligned_segment_id=EXCLUDED.aligned_segment_id''',
            (row['registry_id'], row['sha256'], decision['decision'], decision['adjudicator'],
             decision['adjudicated_at'], decision['notes'], segment_id))
    return {'approved': approved, 'segments': len(rows) if approved else 0}
