# PostgreSQL 18 migration and recovery

The production endpoint is the local Unix socket `/var/run/postgresql`, port
5433, database and role `wordspend`. Python connections verify the resolved
endpoint and PostgreSQL 18 before application SQL. The optional Pausanias source
has its own independent, read-only connection; this migration does not enable it.

The November 4–5 migration retains the original PG16 database, all analysis and
site-build history, and the historical PG18 candidate. Private operational evidence
is on Raksasa under
`/var/backups/postgresql/wordspend-cutover-20261104T234000Z/`.
No passwords, row contents or private logs are stored in Git.

Before handover, the fresh source archive was restored independently onto PG18
and PG16. All 12 tables, all 8 sequences, schema, ownership and ACLs matched.
The stale PG18 candidate also has its own independently restored archive.
The full isolated application suite passed 52 tests and 25 subtests, including
idempotent imports, stored review protection, analysis, local publication and a
failed-publication receipt. Fictional fixtures were confined to a disposable
`wordspend_test_*` database and temporary local publication directories.

The cutover uses the existing `logs/pipeline.lock`, a final source read-only
handover, and a fresh exact table/sequence/schema comparison before preserving
the stale PG18 candidate and promoting the verified fresh copy. It changes no
cron schedule, authentication, role, privilege or Pausanias source setting.
The retained PG16 database remains available for reads/backups, with
`default_transaction_read_only=on` after handover. This is an operational guard,
not an authentication boundary; no permanent connection closure is part of this
migration.

The source archive's PG16 restore proves original-engine recovery. Before any
new PG18 writes, a failed handover can restore the previous code and routing
after verifying unchanged data. Once PG18 has accepted writes, do not simply
point the application at the stale PG16 copy: pause writers, preserve a new PG18
backup and reconcile or reverse-copy those writes, testing restoration first.
Never remove historical copies to simplify rollback.

Acceptance requires an actual production pipeline receipt on PG18, unchanged
PG16 source data, successful static publication, public/local file hashes and a
fresh independently restored PG18 backup. A prepared restore alone is not
evidence that production routing or publication completed. The original daily
cron remains `35 4 * * *` Australia/Sydney in the `wordspend` crontab.
