# Production database configuration

Verified on Raksasa at 22:38 UTC on 3 November 2026. The Pausanias read-only source
handoff is installed and probed on PG18. Wordspend's own database is unchanged.

| Connection | Database / role | Host / port / major | Configuration |
| --- | --- | --- | --- |
| Wordspend production | `wordspend` / `wordspend` | Unix socket / 5432 / 16 | `wordspend/db.py`: `WORDSPEND_DATABASE_URL`, default `dbname=wordspend` |
| Installed Pausanias reader | `pausanias` / `wordspend` | `/var/run/postgresql` / 5433 / 18 | `scripts/import_pausanias.py`: dedicated `PAUSANIAS_DATABASE_URL` override |

The installed checkout is `/home/wordspend/wordspend`. Its service-account cron
runs `/home/wordspend/wordspend/scripts/run_daily_pipeline.sh` at
`35 4 * * *` Australia/Sydney. That wrapper holds `logs/pipeline.lock`, refuses a
dirty checkout, fast-forwards before loading Python, and runs `scripts/run_pipeline.py`.
The Pausanias importer runs only when `IMPORT_PAUSANIAS=1`; that flag was not enabled
in the inspected cron. This migration does not enable it or run an import.

Both routes use existing local peer authentication. `/home/wordspend/.pgpass` and
`.pg_service.conf` were absent at inspection. This reader patch changes no credentials,
roles, listeners, schedules or Wordspend database. The separately approved Pausanias
CONNECT replay is described below. Never set a global `PGPORT` to
move the Pausanias reader: that would also affect Wordspend's own default route.

The installed reader supplies explicit socket, port, database and role defaults,
then applies fields explicitly supplied in `PAUSANIAS_DATABASE_URL`. This preserves
an isolated test-source override without inheriting an unrelated `PGPORT=5432`.
Before any source query it verifies the actual endpoint fields and PostgreSQL 18,
closes a mismatched connection, and uses a read-only transaction. The subsequent
Wordspend write connection still uses only `WORDSPEND_DATABASE_URL`.

Pausanias's existing named `wordspend CONNECT` right was explicitly approved and
reproduced on the fresh PG18 copy, without grant option or new table/schema rights.
The actual reader probe verified schema USAGE, both SELECTs and read-only routing
on canonical Pausanias OID 728836519/5433/PG18; its own Wordspend connection still
resolved to 5432/PG16. No importer or paid pipeline was run for this smoke test.
Pausanias's retained PG16 source is closed to connections; do not route readers or
writers back there. Preserve receipts and reconcile new PG18 writes before rollback.
