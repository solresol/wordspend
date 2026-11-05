# Production database configuration

Wordspend uses PostgreSQL 18 on Raksasa. The independent Pausanias read-only
source also uses PG18. Migration evidence and rollback conditions are recorded
in `docs/postgresql18-migration.md`.

| Connection | Database / role | Host / port / major | Configuration |
| --- | --- | --- | --- |
| Wordspend production | `wordspend` / `wordspend` | `/var/run/postgresql` / 5433 / 18 | `wordspend/db.py`: `WORDSPEND_DATABASE_URL`, default `host=/var/run/postgresql port=5433 dbname=wordspend` |
| Installed Pausanias reader | `pausanias` / `wordspend` | `/var/run/postgresql` / 5433 / 18 | `scripts/import_pausanias.py`: dedicated `PAUSANIAS_DATABASE_URL` override |

The installed checkout is `/home/wordspend/wordspend`. Its service-account cron
runs `/home/wordspend/wordspend/scripts/run_daily_pipeline.sh` at
`35 4 * * *` Australia/Sydney. That wrapper holds `logs/pipeline.lock`, refuses a
dirty checkout, fast-forwards before loading Python, and runs `scripts/run_pipeline.py`.
The Pausanias importer runs only when `IMPORT_PAUSANIAS=1`; that flag was not enabled
in the inspected cron. This migration does not enable it or run an import.

Both routes use existing local peer authentication. `/home/wordspend/.pgpass` and
`.pg_service.conf` were absent at inspection. This reader patch changes no credentials,
roles, listeners or schedules. There is no separate production `.env` or `config.py`
override in the inspected checkout. `WORDSPEND_DATABASE_URL` is the dedicated
Wordspend override; do not use global `PGPORT` for either application connection.
The separately approved Pausanias CONNECT replay is described below.

Wordspend resolves explicit socket, port and database defaults before connecting,
preserving an explicit DSN's fields and the existing OS-role/`PGUSER` default.
It checks the actual database, role, host, port and PostgreSQL major before returning
the connection to application SQL. A name-only override cannot inherit port 5432.
Explicit isolated test databases are supported, but PG16 is rejected before
application queries. Administrative `psql` commands must specify `-h /var/run/postgresql
-p 5433 -U wordspend -d wordspend`; they do not call the Python guard.

The installed reader supplies explicit socket, port, database and role defaults,
then applies fields explicitly supplied in `PAUSANIAS_DATABASE_URL`. This preserves
an isolated test-source override without inheriting an unrelated `PGPORT=5432`.
Before any source query it verifies the actual endpoint fields and PostgreSQL 18,
closes a mismatched connection, and uses a read-only transaction. The subsequent
Wordspend write connection still uses only `WORDSPEND_DATABASE_URL`.

Pausanias's existing named `wordspend CONNECT` right was explicitly approved and
reproduced on the fresh PG18 copy, without grant option or new table/schema rights.
The actual reader probe verified schema USAGE, both SELECTs and read-only routing
on canonical Pausanias OID 728836519/5433/PG18 during its November 3 handoff, when
Wordspend still used PG16. The Wordspend migration does not run or enable that importer.
Pausanias's retained PG16 source is closed to connections; do not route readers or
writers back there. Preserve receipts and reconcile new PG18 writes before rollback.
