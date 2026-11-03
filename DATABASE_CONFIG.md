# Production database configuration

Verified on Raksasa on 3 November 2026. This branch prepares the Pausanias reader
handoff; that handoff is not yet installed. Wordspend's own database is unchanged.

| Connection | Database / role | Host / port / major | Configuration |
| --- | --- | --- | --- |
| Wordspend production | `wordspend` / `wordspend` | Unix socket / 5432 / 16 | `wordspend/db.py`: `WORDSPEND_DATABASE_URL`, default `dbname=wordspend` |
| Prepared Pausanias reader | `pausanias` / `wordspend` | `/var/run/postgresql` / 5433 / 18 | `scripts/import_pausanias.py`: dedicated `PAUSANIAS_DATABASE_URL` override |

The installed checkout is `/home/wordspend/wordspend`. Its service-account cron
runs `/home/wordspend/wordspend/scripts/run_daily_pipeline.sh` at
`35 4 * * *` Australia/Sydney. That wrapper holds `logs/pipeline.lock`, refuses a
dirty checkout, fast-forwards before loading Python, and runs `scripts/run_pipeline.py`.
The Pausanias importer runs only when `IMPORT_PAUSANIAS=1`; that flag was not enabled
in the inspected cron. This migration does not enable it or run an import.

Both routes use existing local peer authentication. `/home/wordspend/.pgpass` and
`.pg_service.conf` were absent at inspection. No credential, role, grant, listener,
schedule or Wordspend database change is required. Never set a global `PGPORT` to
move the Pausanias reader: that would also affect Wordspend's own default route.

The prepared reader supplies explicit socket, port, database and role defaults,
then applies fields explicitly supplied in `PAUSANIAS_DATABASE_URL`. This preserves
an isolated test-source override without inheriting an unrelated `PGPORT=5432`.
Before any source query it verifies the actual endpoint fields and PostgreSQL18,
closes a mismatched connection, and uses a read-only transaction. The subsequent
Wordspend write connection still uses only `WORDSPEND_DATABASE_URL`.

Pausanias retains its explicit source database-level Wordspend CONNECT grant on
PG16; a restored PG18 database's default PUBLIC CONNECT gives current effective
access, while schema USAGE and the two table SELECT grants are restored. The
omitted named database grant changes future PUBLIC-revoke semantics. No grant is
silently added by this reader patch. Preserve that caveat in the Pausanias cutover
record, and verify actual peer access after promotion before calling handoff complete.
