"""Validate and mirror prepared corpus artifacts without promoting proposals."""

from __future__ import annotations

import csv
import hashlib
import json
from io import StringIO
from pathlib import Path

from psycopg.types.json import Jsonb

from .db import get_work_id, upsert_source_version, upsert_translation
from .eligibility import RIGHTS
from .fine_alignment import import_completed_review_rows, prepare_review_worklist_rows

REVIEW_FIELDS = {'review_decision', 'reviewed_source_start_ref', 'reviewed_source_end_ref',
                 'reviewer', 'reviewed_at', 'review_notes'}


def digest(payload) -> str:
    if not isinstance(payload, bytes):
        payload = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()
    return hashlib.sha256(payload).hexdigest()


def read_csv(path: Path) -> list[dict]:
    with path.open(newline='', encoding='utf-8') as handle:
        return list(csv.DictReader(handle))


def checked_rows(root: Path, path: str, expected: str) -> list[dict]:
    filename = (root / path).resolve()
    if not filename.is_relative_to(root.resolve()):
        raise ValueError(f'Artifact path escapes repository: {path}')
    if digest(filename.read_bytes()) != expected:
        raise ValueError(f'Checksum mismatch: {path}')
    return read_csv(filename)


def indexed(rows, key):
    result = {row[key]: row for row in rows}
    if len(result) != len(rows):
        raise ValueError(f'Duplicate {key}')
    return result


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load_snapshot(root: Path) -> dict:
    """Verify all links and review inputs before opening a database write transaction."""
    root = root.resolve()
    def read(name):
        return read_csv(root / name)
    sources = indexed(read('data/source_editions.csv'), 'source_edition_id')
    translations = indexed(read('data/translation_sources.csv'), 'source_id')
    prepared = indexed(read('data/prepared/translation_texts.csv'), 'source_id')
    source_manifests = indexed(read('data/prepared/source_editions.csv'), 'source_edition_id')
    artifacts = []
    lines, books = {}, {}
    def add(kind, key, row, source=None, translation=None, status='prepared'):
        artifacts.append({'kind': kind, 'key': key, 'work': row['work_id'],
                          'source': source, 'translation': translation,
                          'book': int(row.get('book', row.get('segment_ref', 0))),
                          'status': status, 'sha256': digest(row), 'payload': row})
    for key, manifest in source_manifests.items():
        registry = sources[key]
        require(manifest['rights_status'] == registry['rights_status']
                and manifest['editorial_status'] == registry['editorial_status'], 'Source provenance mismatch')
        table = checked_rows(root, manifest['prepared_path'], manifest['prepared_sha256'])
        require(len(table) == int(manifest['line_count']), 'Source line count mismatch')
        indexed(table, 'reference')
        for row in table:
            require(row['source_edition_id'] == key and row['work_id'] == registry['work_id'], 'Source identity mismatch')
            lines.setdefault((key, row['book']), []).append(row)
            add('source_line', key + ':' + row['reference'], row, source=key)
    for key, registry in translations.items():
        manifest = prepared[key]
        require(registry['machine_human_status'] == manifest['machine_human_status']
                and registry['rights_status'] == manifest['rights_status'], 'Translation provenance mismatch')
        require(registry['machine_human_status'] == 'human_published'
                and registry['rights_status'] in RIGHTS, 'Translation not publication-usable')
        require(digest((root / manifest['prepared_path']).read_bytes()) == manifest['prepared_sha256'],
                'Prepared translation checksum mismatch')
    for manifest in read('data/prepared/translation_books.csv'):
        key = manifest['source_id']
        require(manifest['prepared_translation_sha256'] == prepared[key]['prepared_sha256'], 'Book upstream mismatch')
        table = checked_rows(root, manifest['book_path'], manifest['book_sha256'])
        require(len(table) == int(manifest['book_count']), 'Book count mismatch')
        indexed(table, 'book')
        for row in table:
            require(digest(row['text'].encode()) == row['book_text_sha256'], 'Book text checksum mismatch')
            require(row['source_id'] == key, 'Book translation identity mismatch')
            books[key, row['book']] = row
            add('translation_book', key + ':' + row['book'], row, translation=key)
    for row in read('data/prepared/book_alignments.csv'):
        source, translation, book = row['source_edition_id'], row['translation_source_id'], row['segment_ref']
        require(row['source_prepared_sha256'] == source_manifests[source]['prepared_sha256']
                and row['target_book_text_sha256'] == books[translation, book]['book_text_sha256'], 'Book alignment upstream mismatch')
        source_rows = lines[source, book]
        require(row['source_start_ref'] == source_rows[0]['reference']
                and row['source_end_ref'] == source_rows[-1]['reference'], 'Book source coverage mismatch')
        add('book_alignment', row['alignment_id'], row, source, translation, 'book_length_only')
    worklists = {(r['translation_source_id'], r['book']): r for r in read('data/review/fine_alignment_worklists.csv')}
    for summary in read('data/prepared/fine_alignment_candidates.csv'):
        source, translation, book = summary['source_edition_id'], summary['translation_source_id'], summary['book']
        require(summary['work_id'] == sources[source]['work_id'] == translations[translation]['work_id'], 'Candidate work identity mismatch')
        candidates = checked_rows(root, summary['candidate_path'], summary['candidate_sha256'])
        require(len(candidates) == int(summary['candidate_count']), 'Candidate count mismatch')
        indexed(candidates, 'candidate_id')
        source_rows = lines[source, book]
        source_positions = {r['reference']: i for i, r in enumerate(source_rows)}
        target = books[translation, book]
        position, token_end = 0, 0
        for row in candidates:
            start, end = source_positions[row['source_start_ref']], source_positions[row['source_end_ref']]
            require(row['source_edition_id'] == source and row['translation_source_id'] == translation
                    and row['book'] == book and row['work_id'] == summary['work_id'], 'Candidate identity mismatch')
            require(row['source_prepared_sha256'] == source_manifests[source]['prepared_sha256']
                    and row['translation_prepared_sha256'] == prepared[translation]['prepared_sha256']
                    and row['target_book_text_sha256'] == target['book_text_sha256'], 'Candidate upstream mismatch')
            require(start == position and end >= start, 'Candidate source coverage mismatch')
            require(row['source_text'] == '\n'.join(r['text'] for r in source_rows[start:end+1]), 'Candidate source text mismatch')
            require(row['target_text'] == target['text'][int(row['target_start_char']):int(row['target_end_char'])], 'Candidate target span mismatch')
            require(int(row['target_start_token']) == token_end + 1, 'Candidate token gap/overlap')
            position, token_end = end + 1, int(row['target_end_token'])
            add('candidate', row['candidate_id'], row, source, translation, 'pending_human_review')
        require(position == len(source_rows) and token_end == int(target['token_count']), 'Incomplete candidate coverage')
        blank = prepare_review_worklist_rows(candidates, summary['candidate_sha256'])
        worklist = worklists[translation, book]
        require(worklist['candidate_sha256'] == summary['candidate_sha256'], 'Review upstream mismatch')
        baseline = StringIO(newline='')
        writer = csv.DictWriter(baseline, fieldnames=list(blank[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(blank)
        baseline_bytes = baseline.getvalue().encode()
        require(digest(baseline_bytes) == worklist['review_worklist_sha256']
                and len(baseline_bytes) == int(worklist['review_worklist_bytes']), 'Review baseline checksum mismatch')
        reviews = read_csv(root / worklist['review_worklist_path'])
        require(len(reviews) == len(blank), 'Review row count mismatch')
        for actual, baseline in zip(reviews, blank):
            require(all(str(actual.get(k, '')) == str(v) for k, v in baseline.items() if k not in REVIEW_FIELDS),
                    'Immutable review content changed')
            add('review', actual['candidate_id'], actual, source, translation,
                'entered' if any(actual.get(k, '').strip() for k in REVIEW_FIELDS) else 'pending_human_review')
        if reviews and all(r['review_decision'].strip() for r in reviews):
            for row in import_completed_review_rows(reviews, candidates, source_rows, summary['candidate_sha256']):
                add('reviewed_alignment', row['alignment_id'], row, source, translation, 'pending_adjudication')
    ids = [(a['kind'], a['key']) for a in artifacts]
    require(len(ids) == len(set(ids)), 'Duplicate artifact identity')
    return {'sources': sources, 'source_manifests': source_manifests,
            'translations': translations, 'prepared': prepared, 'artifacts': artifacts}


def sync_snapshot(conn, snapshot: dict, revision: str) -> dict:
    """Atomic, idempotent sync. Staging cannot implicitly enter analysis."""
    signature = digest(snapshot)
    conn.execute("SELECT pg_advisory_xact_lock(hashtext('wordspend-corpus'))")
    old = conn.execute('SELECT manifest_hash FROM corpus_sync_state WHERE singleton').fetchone()
    if old and old['manifest_hash'] == signature:
        conn.execute('UPDATE corpus_sync_state SET source_revision=%s WHERE singleton', (revision,))
        return {'unchanged': True, 'artifacts': len(snapshot['artifacts'])}
    work_ids = {}
    def work(slug):
        if slug not in work_ids:
            work_ids[slug] = get_work_id(conn, slug)
        return work_ids[slug]
    source_ids, translation_ids = {}, {}
    for key, manifest in snapshot['source_manifests'].items():
        r = snapshot['sources'][key]
        sid = upsert_source_version(conn, work_id=work(r['work_id']), version_label=key,
                                    source_type=r['editorial_status'], source_citation=r['edition_title'],
                                    source_url=r['catalog_url'], text_hash=manifest['prepared_sha256'])
        conn.execute('''UPDATE source_text_versions SET registry_id=%s, rights_status=%s,
            editorial_status=%s, provenance=%s WHERE id=%s''',
                     (key, r['rights_status'], r['editorial_status'], Jsonb(r), sid))
        source_ids[key] = sid
    for key, r in snapshot['translations'].items():
        historical = r.get('historical_publication_date') or ''
        tid = upsert_translation(conn, work_id=work(r['work_id']), translation_label=key,
            translator=r['translator'], target_language=r['target_language'],
            publication_year=int(historical[:4]) if historical else None,
            publication_date=historical, edition_citation=r['edition'],
            provenance=r['catalog_url'], source_url=r['catalog_url'], download_url=r['download_url'],
            license_status=r['rights_status'], rights_statement=r['rights_basis'],
            text_hash=snapshot['prepared'][key]['prepared_sha256'])
        conn.execute('''UPDATE translations SET registry_id=%s, provider_release_date=%s,
            historical_publication_date=%s, preparation_status='prepared_books', metadata=%s WHERE id=%s''',
                     (key, r.get('provider_release_date') or r['publication_date'], historical or None, Jsonb(r), tid))
        translation_ids[key] = tid
    # Do not silently erase human input entered after a prior sync.
    for artifact in snapshot['artifacts']:
        if artifact['kind'] == 'review':
            existing = conn.execute("SELECT payload FROM corpus_artifacts WHERE kind='review' AND registry_id=%s", (artifact['key'],)).fetchone()
            if existing and any(existing['payload'].get(k, '').strip() for k in REVIEW_FIELDS):
                require(existing['payload'] == artifact['payload'], 'Stored human review differs; reconcile explicitly before syncing')
    conn.execute('UPDATE corpus_artifacts SET is_current=false WHERE is_current')
    with conn.cursor() as cur:
        cur.executemany('''INSERT INTO corpus_artifacts
            (kind,registry_id,work_id,source_version_id,translation_id,book,status,sha256,payload)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (kind,registry_id) DO UPDATE SET work_id=EXCLUDED.work_id,
                source_version_id=EXCLUDED.source_version_id, translation_id=EXCLUDED.translation_id,
                book=EXCLUDED.book,status=EXCLUDED.status,sha256=EXCLUDED.sha256,
                payload=EXCLUDED.payload,is_current=true''',
            [(a['kind'], a['key'], work(a['work']), source_ids.get(a['source']),
              translation_ids.get(a['translation']), a['book'], a['status'], a['sha256'], Jsonb(a['payload']))
             for a in snapshot['artifacts']])
    conn.execute('''INSERT INTO corpus_sync_state(singleton,manifest_hash,source_revision)
        VALUES (true,%s,%s) ON CONFLICT(singleton) DO UPDATE SET
        manifest_hash=EXCLUDED.manifest_hash,source_revision=EXCLUDED.source_revision,synced_at=now()''', (signature, revision))
    return {'unchanged': False, 'artifacts': len(snapshot['artifacts'])}
