"""Run only against an explicitly named disposable wordspend_test_* database."""
import copy
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from wordspend.adjudication import adjudicate_book, reviewed_book
from wordspend.corpus import digest, load_snapshot, sync_snapshot
from wordspend.db import connect, fetch_segments, get_work_id, upsert_source_version, upsert_translation, upsert_aligned_segments
from wordspend.fine_alignment import import_completed_review_rows

ROOT = Path(__file__).resolve().parents[1]
DSN = os.environ.get('WORDSPEND_TEST_DATABASE_URL')


@unittest.skipUnless(DSN, 'Set WORDSPEND_TEST_DATABASE_URL to a disposable wordspend_test_* database')
class DatabaseIntegrationTests(unittest.TestCase):
    def test_full_corpus_review_analysis_and_pipeline(self):
        with connect(DSN) as conn:
            self.assertTrue(conn.info.dbname.startswith('wordspend_test_'), 'Refusing to test a non-test database')
            self.assertIsNone(conn.execute("SELECT to_regclass('public.works') AS t").fetchone()['t'], 'Test database must be empty')
        env = {**os.environ, 'WORDSPEND_DATABASE_URL': DSN, 'WORDSPEND_SKIP_PULL': '1',
               'WORDSPEND_ANALYSIS_MODE': 'bootstrap'}
        def script(name, *args, success=True):
            executable = 'sh' if name.endswith('.sh') else sys.executable
            result = subprocess.run([executable, str(ROOT/'scripts'/name), *map(str, args)],
                                    cwd=ROOT, env=env, capture_output=True, text=True)
            if success:
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            else:
                self.assertNotEqual(result.returncode, 0)
            return result
        script('init_db.py')
        script('init_db.py')
        script('load_work_catalog.py')
        snapshot = load_snapshot(ROOT)
        with connect(DSN) as conn:
            self.assertFalse(sync_snapshot(conn, snapshot, 'test')['unchanged'])
        with connect(DSN) as conn:
            self.assertTrue(sync_snapshot(conn, snapshot, 'test')['unchanged'])
            inventory = conn.execute("SELECT * FROM corpus_preparation_inventory WHERE slug='homer-iliad'").fetchone()
            self.assertEqual([inventory[k] for k in ['source_lines', 'translation_books', 'book_pairs', 'candidates', 'entered_reviews']], [15687, 48, 48, 477, 0])
            self.assertTrue(fetch_segments(conn).empty)
            work = get_work_id(conn, 'pausanias-description-of-greece')
            source = upsert_source_version(conn, work_id=work, version_label='synthetic-test-only')
            translation = upsert_translation(conn, work_id=work, translation_label='synthetic-test-only',
                is_machine_generated=True, translation_source_type='machine_bootstrap')
            upsert_aligned_segments(conn, work_id=work, source_version_id=source, translation_id=translation,
                source_language='grc', rows=[{'segment_ref': str(i), 'segment_order': i,
                'source_text': 'alpha beta ' * i, 'target_text': 'one two three ' * (i+1)} for i in range(1,7)])
            self.assertEqual(len(fetch_segments(conn, mode='bootstrap')), 6)
            self.assertTrue(fetch_segments(conn).empty)
        script('run_analysis.py', '--input', ROOT/'data/example_segments.csv', success=False)
        script('run_analysis.py', '--input', ROOT/'data/example_segments.csv', '--save-db', success=False)
        with tempfile.TemporaryDirectory() as output:
            for i in range(2):
                script('run_analysis.py', '--from-db', '--mode', 'bootstrap', '--corpus-label', 'bootstrap',
                       '--save-db', '--output-dir', Path(output)/str(i))
            with connect(DSN) as conn:
                self.assertEqual(conn.execute('SELECT count(*) AS n FROM analysis_runs').fetchone()['n'], 1)
            env['WORDSPEND_DEPLOY_TARGET'] = output + '/site/'
            Path(env['WORDSPEND_DEPLOY_TARGET']).mkdir()
            script('run_daily_pipeline.sh')
            script('run_daily_pipeline.sh')
            self.assertIn('machine-generated English', (Path(output)/'site/index.html').read_text())
            self.assertIn('Preparation and review progress', (Path(output)/'site/corpus.html').read_text())
            with connect(DSN) as conn:
                self.assertEqual(conn.execute('SELECT count(*) AS n FROM analysis_runs').fetchone()['n'], 1)
                self.assertEqual(conn.execute("SELECT count(*) AS n FROM site_builds WHERE status='deployed'").fetchone()['n'], 2)
            blocker = Path(output)/'not-a-directory'
            blocker.write_text('test')
            env['WORDSPEND_DEPLOY_TARGET'] = str(blocker) + '/site/'
            script('run_daily_pipeline.sh', success=False)
            with connect(DSN) as conn:
                self.assertEqual(conn.execute("SELECT count(*) AS n FROM site_builds WHERE status='failed'").fetchone()['n'], 1)
        # Synthetic human decisions are confined to this guarded disposable DB.
        partial = copy.deepcopy(snapshot)
        first_review = next(a for a in partial['artifacts'] if a['kind']=='review')
        first_review['payload']['reviewer'] = 'Synthetic Test Fixture'
        first_review['sha256'] = digest(first_review['payload'])
        with connect(DSN) as conn:
            sync_snapshot(conn, partial, 'test')
        staged = copy.deepcopy(snapshot)
        candidates = [a['payload'] for a in staged['artifacts'] if a['kind']=='candidate' and a['book']==1]
        reviews = [a['payload'] for a in staged['artifacts'] if a['kind']=='review' and a['book']==1]
        source_lines = [a['payload'] for a in staged['artifacts'] if a['kind']=='source_line' and a['book']==1]
        for row in reviews:
            row.update(review_decision='accept_proposed_range', reviewer='Synthetic Test Fixture', reviewed_at='2026-10-24T00:00:00+00:00')
        candidate_sha = reviews[0]['candidate_file_sha256']
        normalized = import_completed_review_rows(reviews, candidates, source_lines, candidate_sha)
        for a in staged['artifacts']:
            a['sha256'] = digest(a['payload'])
        template = next(a for a in staged['artifacts'] if a['kind']=='candidate' and a['book']==1)
        for row in normalized:
            staged['artifacts'].append({**template, 'kind':'reviewed_alignment', 'key':row['alignment_id'],
                                       'payload':row, 'sha256':digest(row), 'status':'pending_adjudication'})
        with connect(DSN) as conn:
            sync_snapshot(conn, staged, 'test')
        with connect(DSN) as conn:
            with self.assertRaisesRegex(ValueError, 'Stored human review differs'):
                sync_snapshot(conn, snapshot, 'test')
            conn.rollback()
        with connect(DSN) as conn:
            rows = reviewed_book(conn, 'homer-iliad-en-butler-pg2199', 1)
            decisions = [dict(candidate_id=r['registry_id'], reviewed_sha256=r['sha256'], decision='approve',
                              adjudicator='Synthetic Adjudicator', adjudicated_at='2026-10-24T01:00:00+00:00', notes='Test only') for r in rows]
            with self.assertRaisesRegex(ValueError, 'exactly'):
                adjudicate_book(conn, 'homer-iliad-en-butler-pg2199', 1, decisions[:-1])
            self.assertTrue(fetch_segments(conn).empty)
            result = adjudicate_book(conn, 'homer-iliad-en-butler-pg2199', 1, decisions)
            self.assertEqual(result['segments'], 54)
        with connect(DSN) as conn:
            self.assertEqual(len(fetch_segments(conn)), 54)
            # A stale reviewed artifact or changed provenance withdraws evidence immediately.
            conn.execute("UPDATE corpus_artifacts SET is_current=false WHERE kind='reviewed_alignment'")
            self.assertTrue(fetch_segments(conn).empty)
            conn.rollback()
        with connect(DSN) as conn:
            conn.execute("UPDATE translations SET is_machine_generated=true WHERE registry_id='homer-iliad-en-butler-pg2199'")
            self.assertTrue(fetch_segments(conn).empty)
            conn.rollback()
        with connect(DSN) as conn:
            decisions[0]['decision'] = 'reject'
            for d in decisions:
                d['adjudicated_at'] = '2026-10-24T02:00:00+00:00'
            self.assertFalse(adjudicate_book(conn, 'homer-iliad-en-butler-pg2199', 1, decisions)['approved'])
            self.assertTrue(fetch_segments(conn).empty)
        with connect(DSN) as conn:
            decisions[0]['decision'] = 'approve'
            for d in decisions:
                d['adjudicated_at'] = '2026-10-24T01:00:00+00:00'
            with self.assertRaisesRegex(ValueError, 'older adjudication'):
                adjudicate_book(conn, 'homer-iliad-en-butler-pg2199', 1, decisions)


if __name__ == '__main__':
    unittest.main()
