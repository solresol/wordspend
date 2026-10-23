# Database ingestion, evidence selection, and nightly builds

## Corpus storage

Run from the repository root with the locked `uv` environment:

```sh
uv run python scripts/init_db.py
uv run python scripts/load_work_catalog.py
uv run python scripts/sync_prepared_corpus.py
```

`init_db.py` records each migration and its SHA-256 in `schema_migrations`.
Each migration and its record commit together. Changing an applied migration
is an error; add a new numbered migration instead.

The sync validates registry/prepared provenance, upstream hashes, book bodies,
candidate source coverage and target spans, and the immutable review baseline.
All validation completes before database writes. Registry identifiers are
preserved in `source_text_versions.registry_id` and `translations.registry_id`.
The former `publication_date` registry field is explicitly labelled a provider
release date. It populates `provider_release_date`, not a historical publication
year. `historical_publication_date` stays unknown until a bibliographic source
has been recorded; no translation period is inferred from Gutenberg dates.

`corpus_artifacts` stores source lines, translation books, structural book
pairs, candidates, entered reviews, and fully validated reviews as separate
artifact kinds, retaining their complete payload and checksum. They do not
automatically enter `aligned_segments`. A snapshot signature makes unchanged
imports a no-op, and artifacts absent from a newer snapshot become noncurrent.
Previously blank review fields can be filled incrementally. Entered values
cannot silently be erased or changed by a different file snapshot; such a conflict stops the sync for reconciliation.

```sql
SELECT * FROM corpus_preparation_inventory WHERE slug='homer-iliad';
SELECT kind,count(*) FROM corpus_artifacts WHERE is_current GROUP BY kind;
```

## Review and adjudication

Humans fill the existing worksheets under `data/review/fine_alignment/`.
Sync preserves partial input in staging. When a whole worksheet is complete,
it uses the existing completed-review validator to reconstruct source text,
verify reviewer/time provenance, and require ordered, gap-free source coverage.
These normalized rows remain pending adjudication. The older CSV staging
importer can still be used; database sync validates the worksheets directly.

Export a blank adjudication worksheet after a complete book review is staged:

```sh
uv run python scripts/adjudicate_alignment_book.py \
  --translation-source-id homer-iliad-en-butler-pg2199 --book 1 \
  --export /path/to/book-01-adjudication.csv
```

Export refuses to overwrite an existing file. A human enters `approve` or
`reject` for every row, with adjudicator, timezone-aware timestamp, and notes.
The worksheet includes both texts, reviewer provenance, and the exact normalized
review SHA-256. Import completed decisions with `--decisions` instead of
`--export`. Partial books, stale review hashes, missing provenance, timestamps
before review, and replays of older adjudications are rejected.

Only a wholly approved book is promoted. A rejection withdraws the whole book
from eligibility. Promoted token counts use the versioned language tokenizer.
The `paper_facing_segments` database view also checks current reviewed hashes,
source/translation identity, text, rights, human/editorial status, and provenance.
Changing or removing upstream reviewed material therefore withdraws it from
paper-facing selection until it is reviewed/adjudicated again.

## Explicit analysis scopes

```sh
# Default: only adjudicated, eligible fine alignments from published translations.
uv run python scripts/run_analysis.py --from-db --save-db --mode paper

# Explicit diagnostic mode: machine-bootstrap translations only.
uv run python scripts/run_analysis.py --from-db --save-db --mode bootstrap
```

There are currently no completed human Iliad reviews, so paper mode reports
no eligible segments. Bootstrap mode preserves the Pausanias diagnostic site.
CSV analysis applies the same eligibility fields and fails closed if they are
missing. `--save-db` requires a database input; positional CSV row numbers are
never treated as persistent segment IDs.

An analysis run key covers selected rows, parameters, mode, and Git revision.
Repeated identical builds reuse the saved analysis and residuals. Existing
legacy analysis history is retained. Every build separately records its
source revision, analysis run, output path, deployment target, completion time,
and `running`, `generated`, `deployed`, or `failed` status in `site_builds`.

## Production execution

The service runs as `wordspend` on raksasa. Its Git checkout is
`/home/wordspend/wordspend`, with HTTPS origin for unattended read access.
The nightly schedule remains 04:35 Australia/Sydney and explicitly sets
`WORDSPEND_ANALYSIS_MODE=bootstrap` until reviewed paper evidence is available.

`run_daily_pipeline.sh` holds a process lock, refuses a dirty checkout, and
requires a successful fast-forward pull **before** loading application code or
resolving dependencies. It then applies migrations, syncs provenance/staging,
optionally refreshes Pausanias, builds the selected analysis and inventory,
generates a distinct site directory, and deploys to merah. A failed step exits
nonzero; application/deployment failures are also recorded in `site_builds`.

The results page explicitly identifies machine-generated bootstrap English.
The corpus page reports prepared, reviewed, and paper-facing counts separately.
The revision is included in analysis outputs and the site.

For an isolated smoke test, point `WORDSPEND_DATABASE_URL` at a disposable
database and `WORDSPEND_DEPLOY_TARGET` at a local test directory. The explicit
`WORDSPEND_SKIP_PULL=1` option allows testing uncommitted development code.
Production does not set it.

## Verification and maintenance

Unit tests run with `uv run python -m unittest discover -s tests`. PostgreSQL
integration tests require `WORDSPEND_TEST_DATABASE_URL` naming an empty
`wordspend_test_*` database. They verify migrations, idempotent staging and
analysis, gates, review/adjudication/rejection, stale provenance, deployment
failure tracking, and the actual shell pipeline. Synthetic review decisions
are confined to the disposable database and never written into real worksheets.

On October 24, a restricted backup was made under
`/home/wordspend/backups/wordspend-before-integration-20261024.dump`, followed by
successful `REINDEX DATABASE CONCURRENTLY wordspend` and
`ALTER DATABASE wordspend REFRESH COLLATION VERSION`. The recorded and actual
versions now both read 2.43, with no invalid indexes. The rebuild precedes the
version refresh as required by the PostgreSQL
[collation maintenance documentation](https://www.postgresql.org/docs/16/sql-altercollation.html).
