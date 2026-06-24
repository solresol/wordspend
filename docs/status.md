# Status

Last updated: 2026-06-24

## Current state

The current checkout began as the initial commit with only `README.md`.
`TODO.md`, `docs/status.md`, `docs/translation-policy.md`, and `docs/works.md`
were absent, so this run added the minimal project surfaces needed to track
paper-facing translation provenance.

## 2026-06-03 progress

- Added `data/translation_sources.csv` with one prepared human-published source:
  Project Gutenberg eBook #2199, Homer, *The Iliad*, translated into English by
  Samuel Butler.
- Recorded the target language, translator, edition, publication date, catalog
  URL, plain-text download URL, rights status, rights basis, and machine/human
  status for that source.
- Added `scripts/validate_translation_sources.py` to validate registry shape and
  block machine or unclear rows from being marked paper-facing.

## 2026-06-10 progress

- Restored the minimal provenance registry surfaces into this checkout from the
  archived sparse-worktree snapshot, because `origin/main` still only contained
  `README.md`.
- Added `scripts/fetch_translation_sources.py` to fetch validated plain-text
  rows into `data/raw/translations/` and write
  `data/raw/translation_downloads.csv` with bytes, SHA-256, retrieval time,
  HTTP last-modified time, rights status, machine/human status, and raw-text
  stage.
- Downloaded the Butler *Iliad* Project Gutenberg text as raw provider text.

## 2026-06-17 progress

- Restored the June 10 provenance/fetch scaffold into this checkout from the
  archived sparse-worktree snapshot, because `origin/main` still only contained
  `README.md`.
- Added `data/text_preparation_rules.csv` to declare the source-specific body
  boundary markers for the Project Gutenberg Butler *Iliad* text.
- Added `scripts/prepare_translation_texts.py` to verify the raw checksum,
  strip Project Gutenberg title/contents/license material, and write prepared
  translation-body checksum provenance.
- Prepared `data/prepared/translations/homer-iliad-en-butler-pg2199.txt` from
  raw lines 77-14591, leaving the raw provider text unchanged.

## 2026-06-24 progress

- Added a second metadata-complete, human-published source for the same work:
  Project Gutenberg eBook #6130, Homer, *The Iliad*, translated into English by
  Alexander Pope.
- Recorded its target language, translator, edition, publication date, catalog
  URL, plain-text download URL, rights status, rights basis, and machine/human
  status in `data/translation_sources.csv`.
- Added source-specific preparation boundaries that start after the Buckley
  introduction and Pope preface and stop before the concluding note, notes, and
  Project Gutenberg license.
- Made the fetcher retry transient incomplete reads observed while retrieving
  the larger Project Gutenberg plain-text file.

## Paper-facing readiness

There are two metadata-complete, paper-facing-eligible source rows for the
same work. Their raw provider texts have been fetched and checksum-recorded,
and prepared translation-body texts with front/back matter stripped are
available. They have not yet been tokenized, aligned, compared, or analyzed, so
no word-spend claims are paper-ready.

## Blocked or pending

- A validator for prepared-text manifests is still pending.
- Comparative claims still need tokenization/alignment and paper-facing filters
  over the prepared-text manifest.
- Rights status is recorded for the United States; use outside the United States
  needs jurisdiction-specific review.
