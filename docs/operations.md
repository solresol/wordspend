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

As of May 23, 2026, the files are deployed but the public URL still hits the
fallback autoindex. The `httpd.conf` stanza above still needs to be installed
and `httpd` reloaded.

## Failure Rules

- If the service checkout is dirty, skip `git pull` and log the reason.
- If the database has fewer than five aligned segments, do not publish new
  result claims.
- If deployment fails, keep the generated `site/` for inspection and let cron
  mail report the error.
- Do not publish private source files, raw logs, `.env`, or database dumps.
