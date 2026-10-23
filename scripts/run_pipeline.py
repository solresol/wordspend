#!/usr/bin/env python3
"""Build a recorded, revision-controlled corpus/site release."""
import fcntl
import json
import os
import subprocess
import sys
from pathlib import Path

import pandas as pd

from wordspend.db import connect, fetch_work_catalog

ROOT = Path(__file__).resolve().parents[1]


def main():
    os.chdir(ROOT)
    (ROOT/'logs').mkdir(exist_ok=True)
    inherited = os.environ.get('WORDSPEND_PIPELINE_LOCK_FD')
    if not inherited and os.environ.get('WORDSPEND_SKIP_PULL') != '1':
        raise SystemExit('Use scripts/run_daily_pipeline.sh to update the checkout before loading Python')
    lockfile = os.fdopen(int(inherited), 'w') if inherited else (ROOT/'logs/pipeline.lock').open('w')
    with lockfile as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit('Another pipeline is running')
        run()


def run():
    def git(*args):
        return subprocess.check_output(['git', *args], text=True).strip()
    revision = git('rev-parse', 'HEAD')
    def script(name, *args):
        subprocess.run([sys.executable, 'scripts/'+name, *args], check=True)
    script('init_db.py')
    target = os.environ.get('WORDSPEND_DEPLOY_TARGET', 'wordspend@merah:/var/www/vhosts/wordspend.symmachus.org/htdocs/')
    with connect() as conn:
        build_id = conn.execute('''INSERT INTO site_builds(status,source_revision,deployed_to)
            VALUES ('running',%s,%s) RETURNING id''', (revision, target)).fetchone()['id']
    try:
        script('load_work_catalog.py')
        script('sync_prepared_corpus.py')
        if os.environ.get('IMPORT_PAUSANIAS', '0') == '1':
            script('import_pausanias.py', '--limit', '0')
        analysis = ROOT/'build/analysis'
        mode = os.environ.get('WORDSPEND_ANALYSIS_MODE', 'paper')
        script('run_analysis.py', '--from-db', '--save-db', '--mode', mode,
               '--corpus-label', mode, '--output-dir', str(analysis))
        metrics = json.loads((analysis/'metrics.json').read_text())
        with connect() as conn:
            catalog = fetch_work_catalog(conn)
            preparation = conn.execute('SELECT * FROM corpus_preparation_inventory').fetchall()
            catalog = catalog.merge(pd.DataFrame(preparation), on='slug', how='left')
            catalog.to_csv(ROOT/'build/corpus_inventory.csv', index=False)
        # A failed build leaves the previous successful local site available.
        site = ROOT/'build/sites'/str(build_id)
        script('generate_site.py', '--analysis-dir', str(analysis),
               '--catalog', str(ROOT/'build/corpus_inventory.csv'), '--output-dir', str(site))
        with connect() as conn:
            conn.execute('''UPDATE site_builds SET status='generated',analysis_run_id=%s,
                output_path=%s WHERE id=%s''', (metrics['analysis_run_id'], str(site), build_id))
        subprocess.run(['rsync', '-az', '--delete', str(site)+'/', target], check=True)
        with connect() as conn:
            conn.execute("UPDATE site_builds SET status='deployed',finished_at=now() WHERE id=%s", (build_id,))
        print(f'Deployed build {build_id}, revision {revision}, analysis {metrics["analysis_run_id"]}', flush=True)
    except BaseException as error:
        with connect() as conn:
            conn.execute("UPDATE site_builds SET status='failed',message=%s,finished_at=now() WHERE id=%s", (str(error), build_id))
        raise


if __name__ == '__main__':
    main()
