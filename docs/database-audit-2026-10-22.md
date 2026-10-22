# Database and automation audit — 2026-10-22

## Conclusion

Database access works from this checkout. The current machine is **raksasa**:
`gregb` and the `wordspend` service account both connect to the local database
without passwords. The migration from udara did not need database credentials.

There is a substantial integration gap. The preparation pipeline has built
useful, checksum-linked Iliad files, but none of that corpus is in PostgreSQL.
The automation has been extending blank review queues while database ingestion,
adjudication, and analysis eligibility enforcement remain unimplemented.

## Verified state

Snapshot: October 22, 2026, approximately 11:39 Australia/Sydney. Repository
revision tested: `6ca98a7`. The companion
[`audits/database-audit-2026-10-22.ipynb`](audits/database-audit-2026-10-22.ipynb)
contains the read-only SQL, file reconciliation code, and captured results.

| Material | Repository files | Live PostgreSQL |
| --- | ---: | ---: |
| Candidate work catalog | 44 works | 44 works |
| Published Iliad translations | 2: Butler and Pope | 0 |
| Monro–Allen Iliad source edition | 1 edition; 15,687 Greek lines | 0 |
| Prepared translation books | 48; 300,068 target tokens | 0 |
| Structural source/translation book pairs | 48 | 0 |
| Fine-alignment candidates | 477 across Butler Books 1–10 | 0 |
| Entered human review decisions | 0 of 477 | No Iliad reviewed corpus |
| Pausanias machine-bootstrap passages | Existing production corpus | 3,170 |

The database has one source version and one translation, both for Pausanias.
The translation is correctly labelled `machine_bootstrap` and
`is_machine_generated=true`. Passage import timestamps remain May 23.
No missing or mismatched source/translation foreign-key relationships were found.

All 23 checked source/book/candidate/worklist file hashes matched their
manifests. All ten candidate queues cover their source books exactly in order,
preserve source and target text spans, and have continuous target token ranges.
All 477 review rows remain paper-facing ineligible. Thirty unit tests and both
translation provenance validators passed. These checks validate preparation
integrity, not the semantic accuracy of the proportional alignment proposals.

## Build verification

1. Connected to the live database from the development checkout using the
   default `dbname=wordspend` connection. Also verified service-account access.
2. Ran `run_analysis.py --from-db` with PostgreSQL transactions forced read-only,
   then generated the static site into `build/database-audit/`. It reproduced
   the existing 3,170-segment baseline (R squared approximately 0.86238).
3. Created a disposable database from a dump of the live schema and corpus,
   excluding historical analysis/output rows. Ran the **unchanged**
   `run_daily_pipeline.sh` from a clean Git archive, directing rsync to a local
   test directory. Schema setup, catalog loading, analysis, persistence of one
   run / 3,170 residuals / 80 predictors, HTML generation, and rsync all passed.
   Removed the disposable database afterward.

The test did not change the live corpus or deploy to the public host. Optional
Pausanias reimport (`IMPORT_PAUSANIAS=1`) was not exercised. The public URL was
read separately and serves the generated site with an October 22 04:35 Sydney
build timestamp; the old autoindex warning in the documentation was stale.
Local logs and trial outputs are under the ignored `build/database-audit/`.

## Findings and priorities

### High: the prepared corpus has no database ingestion path

`import_source_editions.py` and `import_completed_fine_alignment_reviews.py`
write prepared CSV files. Their names do not imply PostgreSQL import.
Only the work catalog and Pausanias importer currently load corpus data into
the database. The nightly pipeline does not consume the published translation
registry, source-edition registry, prepared book pairs, or review worklists.

The two translation records and Greek edition should be registered in the
database with stable IDs, provenance, checksums, and preparation status. Source
lines, book text, structural pairs, and candidate/review state can then be
stored in separate staging tables where they support inventory and review.
The versioned files can remain the reproducible source artifacts; duplicating
every raw file in PostgreSQL is not a prerequisite for useful integration.

### High: database analysis does not enforce evidence eligibility

`wordspend.db.fetch_segments()` selects all nonempty source/target pairs. It
does not filter machine translations, review status, adjudication, rights,
alignment level, or paper-facing eligibility. `run_analysis.py` has no explicit
paper-facing mode; the CSV input path also accepts rows without an eligibility
gate. The current default build therefore analyzes the Pausanias bootstrap.

Simply inserting the 477 unreviewed proposals into `aligned_segments` would
make them available to the current analysis. They must remain excluded.
Similarly, 48 whole-book pairs can support labelled book-length exploration,
but cannot be treated as reviewed fine alignments for lexical claims. Build
and test explicit evidence selection before connecting staging to analysis.

The public footer calls results bootstrap diagnostics, but does not explicitly
identify the translation as machine-generated. Corpus provenance and eligibility
should be visible in generated outputs, alongside the explicit bootstrap mode.

### High: the nightly service is disconnected from repository development

`/home/wordspend/wordspend` is a copied tree without `.git`. Its application
files retain May 23 timestamps, and it lacks the newer preparation scripts.
Consequently the conditional Git pull in `run_daily_pipeline.sh` never runs.
The latest successful nightly analysis is October 22 at 04:35, but it uses the
same corpus and baseline as every prior run.

Deploy a known repository revision to the service and record that revision.
Wire ingestion into the nightly pipeline only after eligibility gates are
verified. Changing the development checkout alone does not deploy it.

### Medium: preparation has progressed without reviewed evidence

All 477 review decisions are blank; no reviewed-alignment manifest exists.
The completed-review importer deliberately stops at pending adjudication, and
there is no final adjudication-to-database promotion path. Producing another
blank book each week does not resolve these bottlenecks. Prioritize the gates,
ingestion, and review/promotion workflow. Remaining deterministic book queues
can be generated in a bounded batch when useful to reviewers.

### Medium: maintenance and provenance gaps

- There are 152 analysis runs with one distinct baseline parameter triple,
  481,840 residual rows, and 12,160 predictor rows. Repeated nightly output is
  being stored even though the corpus is unchanged. Define a run identity from
  corpus checksums, parameters, and code version, with an explicit rerun policy.
- `site_builds` has zero rows; the build script never records build/deployment
  status there. A successful analysis row alone does not prove deployment.
- PostgreSQL reports a collation version mismatch: recorded libc 2.39 versus
  runtime 2.43. Plan the indicated index/collation maintenance; it was not
  performed as part of this audit. Successful queries do not clear this warning.
- The translation registry's publication dates are the Gutenberg release dates
  (2000 and 2004). Distinguish these from historical translation/edition dates
  before using translation publication period as a statistical control.

## Scope of the resulting changes

This audit adds the evidence notebook, corrects operations/status documentation,
and prioritizes database integration in TODO and the automation prompt. It does not import the Iliad into
the live database, promote candidates, alter the nightly schedule, replace the
service deployment, or perform database maintenance. Those implementation steps
remain explicitly tracked work, with eligibility enforcement first.
