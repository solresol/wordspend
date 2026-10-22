# TODO

## Completed

- [x] Seed a published-translation provenance registry with Project Gutenberg
  eBook #2199, Homer, *The Iliad*, translated into English by Samuel Butler.
  The row records target language, translator, edition, publication date,
  catalog and download URLs, rights status, and machine/human status.
- [x] Add a raw-text fetcher for prepared translation rows and record download
  checksum provenance for the Butler *Iliad* Project Gutenberg text.
- [x] Strip Project Gutenberg front/back matter from the downloaded Butler
  *Iliad* raw text into a prepared translation-body file, with raw and prepared
  checksums recorded.
- [x] Add a second human-published translation of the same work: Project
  Gutenberg eBook #6130, Homer, *The Iliad*, translated into English by
  Alexander Pope. The row records target language, translator, edition,
  publication date, catalog and download URLs, rights status, and
  machine/human status; its raw and prepared checksum provenance is recorded.
- [x] Add a validation gate for prepared-text manifests so paper-facing
  analysis can require `front_back_matter_status=stripped`.
- [x] Add paper-facing prepared-text filters that validate the prepared-text
  manifest, then select only rows where `paper_facing_eligible=yes`,
  `machine_human_status=human_published`, rights are publication-usable,
  `text_stage=prepared_translation_body`, and front/back matter is stripped.
- [x] Tokenize the selected paper-facing prepared texts with an explicit,
  versioned language profile and record deterministic token-file checksums,
  character offsets, and line locations for downstream alignment.
- [x] Import a provenance-complete Ancient Greek *Iliad* source edition: Monro
  and Allen's 1908-1920 third edition from Perseus. Record its edition,
  publication, canonical ID, commit-pinned download, CC BY-SA 4.0 rights, and
  human-edited status, then prepare 15,687 checksum-linked `book.line` rows
  with TEI editorial deletions explicitly flagged.
- [x] Prepare the Samuel Butler translation as 24 checksum-linked book bodies,
  removing the declared Project Gutenberg editorial summary after each book
  heading, and record 24 structural alignments to the corresponding Monro and
  Allen source-book ranges. These rows support book-length review only, not
  lexical residual claims.
- [x] Define and apply a separate paratext-removal policy for Pope's
  translation: skip each book's argument label, title, and synopsis, remove 71
  illustration/caption paragraphs, and record 24 checksum-linked book bodies
  and structural alignments. These rows remain restricted to book-length use.
- [x] Prepare a deterministic Butler Book 1 fine-alignment review queue: 54
  translation paragraphs with token spans provisionally paired to all 611
  Greek lines. Mark every proportional proposal `machine_proposed_unreviewed`,
  `paper_facing_eligible=no`, and excluded from analysis pending human review.
- [x] Prepare a checksum-linked Butler Book 1 human-review worklist with the 54
  proposals and both source and target text visible. Leave every decision,
  reviewed range, reviewer, date, and note field blank, and keep all rows
  paper-facing ineligible and excluded from analysis.
- [x] Add a fail-closed import gate for completed Butler Book 1 review
  decisions. Validate immutable candidate fields, reviewer and timestamp
  provenance, allowed accept/adjust decisions, checksum-linked source text, and
  complete gap-free source coverage; keep imported rows excluded pending
  adjudication.
- [x] Extend the Butler review queue to Book 2: prepare 83 checksum-linked
  machine-proposed segments covering all 877 Greek lines and 7,945 published
  translation tokens, plus a blank human-review worklist. Keep every row
  paper-facing ineligible and excluded from analysis pending review.
- [x] Extend the Butler review queue to Book 3: prepare 41 checksum-linked
  machine-proposed segments covering all 461 Greek lines and 4,040 published
  translation tokens, plus a blank human-review worklist. Keep every row
  paper-facing ineligible and excluded from analysis pending review.
- [x] Extend the Butler review queue to Book 4: prepare 39 checksum-linked
  machine-proposed segments covering all 544 Greek lines and 5,048 published
  translation tokens, plus a blank human-review worklist. Keep every row
  paper-facing ineligible and excluded from analysis pending review.
- [x] Extend the Butler review queue to Book 5: prepare 67 checksum-linked
  machine-proposed segments covering all 909 Greek lines and 8,590 published
  translation tokens, plus a blank human-review worklist. Keep every row
  paper-facing ineligible and excluded from analysis pending review.
- [x] Extend the Butler review queue to Book 6: prepare 35 checksum-linked
  machine-proposed segments covering all 529 Greek lines and 4,984 published
  translation tokens, plus a blank human-review worklist. Keep every row
  paper-facing ineligible and excluded from analysis pending review.

- [x] Extend the Butler review queue to Book 7: prepare 35 checksum-linked
  machine-proposed segments covering all 482 Greek lines and 4,400 published
  translation tokens, plus a blank human-review worklist. Keep every row
  paper-facing ineligible and excluded from analysis pending review.

- [x] Extend the Butler review queue to Book 8: prepare 41 checksum-linked
  machine-proposed segments covering all 565 Greek lines and 5,289 published
  translation tokens, plus a blank human-review worklist. Keep every row
  paper-facing ineligible and excluded from analysis pending review.

- [x] Extend the Butler review queue to Book 9: prepare 34 checksum-linked
  machine-proposed segments covering all 709 Greek lines and 6,895 published
  translation tokens, plus a blank human-review worklist. Keep every row
  paper-facing ineligible and excluded from analysis pending review.

- [x] Extend the Butler review queue to Book 10: prepare 48 checksum-linked
  machine-proposed segments covering all 579 Greek lines and 5,518 published
  translation tokens, plus a blank human-review worklist. Keep every row
  paper-facing ineligible and excluded from analysis pending review.

## Next

Prioritize the database integration and analysis gates below before extending
the blank alignment queue. See `docs/database-audit-2026-10-22.md` for the live
database reconciliation and verified build checks.

- [ ] Add explicit analysis eligibility and corpus selection to the database
  path. Paper-facing lexical runs must reject machine bootstrap, unreviewed,
  pending-adjudication, and book-only rows; keep an explicitly labelled
  bootstrap mode for the existing Pausanias diagnostics. Test both CSV and
  PostgreSQL inputs so importing preparation data cannot bypass the gates.
- [ ] Add an idempotent PostgreSQL import for the two published translation
  records and Greek source edition, preserving stable registry IDs, provenance,
  checksums, rights, and preparation/review status. Add separate staging for
  source lines, translation books, book-level pairs, and review candidates as
  needed; do not insert unreviewed candidates into the analysis corpus.
- [ ] Connect completed human review, adjudication, and database promotion.
  The existing completed-review importer writes CSV staging only; all 477
  current review decisions are blank. Make reviewed progress visible in the
  corpus inventory without treating preparation as reviewed evidence.
- [ ] Make the nightly service deployment track a known repository revision.
  `/home/wordspend/wordspend` is a May-era copy without `.git`, so the current
  pull step never runs there. Connect the new ingestion stages after their
  exclusion gates are tested, and record source revision and build status.
- [ ] Separate historical translation/edition publication dates from digital
  provider release dates before using publication period as an analysis control.
- [ ] Plan PostgreSQL collation/index maintenance for the observed 2.39 versus
  2.43 mismatch, and avoid accumulating identical nightly analysis runs without
  a changed corpus, parameters, or code revision.

- [ ] Produce a finer, reviewable alignment between the prepared Ancient Greek
  source lines and Butler translation tokens before lexical residual analysis.
  Books 1–10 candidate queues and human-review worklists are prepared;
  completed-decision validation/import tooling is prepared, while human review,
  adjudication, and Books 11-24 remain pending.
- [ ] Produce a finer, reviewable alignment between the prepared Ancient Greek
  source lines and Pope translation tokens before lexical residual analysis.
- [ ] Keep machine-generated translations, if any are added for bootstrap tests,
  explicitly labelled `machine_bootstrap` and excluded from paper-facing claims.
