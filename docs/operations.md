# Operations

## Hosts

- Public host: `wordspend.symmachus.org`
- Web host: `merah`
- Web root: `/var/www/vhosts/wordspend.symmachus.org/htdocs/`
- Worker host: `raksasa`
- Worker checkout: `/home/wordspend/wordspend`
- Service account: `wordspend`
- PostgreSQL database: `wordspend`

The site should stay static until there is a specific need for a CGI review or
annotation workflow. Heavy work belongs on `raksasa`.

## Merah Vhost Stanza

Use this OpenBSD `httpd.conf` stanza for the static site:

```conf
server "wordspend.symmachus.org" {
	log style combined
	directory { auto index }
	listen on $listen_addr port 80
	root "/vhosts/wordspend.symmachus.org/htdocs"
}
```

After adding it on `merah`:

```sh
doas httpd -n
doas rcctl reload httpd
```

## Raksasa Cron

Suggested service-account cron:

```cron
35 4 * * * /home/wordspend/wordspend/scripts/run_daily_pipeline.sh >> /home/wordspend/wordspend/logs/cron.log 2>&1
```

Use `IMPORT_PAUSANIAS=1` only when the cron account can read the source
Pausanias database or when the environment explicitly grants that access.

## Manual Run

```sh
cd /home/wordspend/wordspend
export WORDSPEND_DATABASE_URL=dbname=wordspend
uv run python scripts/init_db.py
uv run python scripts/load_work_catalog.py
uv run python scripts/run_analysis.py --from-db --save-db --output-dir build/analysis
uv run python scripts/generate_site.py --analysis-dir build/analysis --output-dir site
rsync -az --delete site/ wordspend@merah:/var/www/vhosts/wordspend.symmachus.org/htdocs/
```

## Smoke Checks

```sh
psql -d wordspend -c 'select * from corpus_inventory limit 10'
test -f site/index.html
curl -fsS https://wordspend.symmachus.org/ | head
```

As of October 22, 2026, the public URL serves the generated Word Spend site;
its footer reports the October 22 04:35 Sydney-time build. The earlier note
about a fallback autoindex is no longer current.

## Failure Rules

- If the service checkout is dirty, skip `git pull` and log the reason.
- If the database has fewer than five aligned segments, do not publish new
  result claims.
- If deployment fails, keep the generated `site/` for inspection and let cron
  mail report the error.
- Do not publish private source files, raw logs, `.env`, or database dumps.

## TODO progress automation

As of 2026-10-22, `wordspend-todo-progress` is paused on udara and active in
the local Codex app each Wednesday at 10:00 (Australia/Sydney), using GPT-6
Astra with high reasoning effort. It completes one bounded TODO increment,
validates it, updates project status, and commits and pushes the result.

The registered local project is `/home/gregb/devel/wordspend/wordspend`; enter
the Git root `/home/gregb/devel/wordspend` before running scripts or reading
project documentation. Use `/home/gregb/.local/bin/uv` if needed. Run `uv sync`
to install the locked dependencies. The provenance/alignment workflow uses
CSV and text files and does not require PostgreSQL credentials from udara.
This local machine is raksasa. The automation runs as `gregb`; the nightly
service runs separately as the `wordspend` system account. Both can connect to
the local `wordspend` database over its Unix socket without a password. No
database credentials need to be copied from udara. `gregb` currently has a
PostgreSQL superuser role; scheduled production work should continue using
the existing `wordspend` service role.

The October 22 audit verified a read-only database analysis/site build from
this checkout, then exercised the complete pipeline on a disposable database
snapshot with rsync directed to a local test directory. See
`docs/database-audit-2026-10-22.md` and its companion notebook for evidence.

The service directory `/home/wordspend/wordspend` currently has no `.git`
directory and still contains May-era application files. Its nightly job is
active, but the script's conditional Git pull is skipped. Updating this
development checkout therefore does not update the service deployment.
