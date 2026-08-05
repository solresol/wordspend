# Status

Last updated: 2026-08-05

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

## 2026-07-01 progress

- Added `scripts/validate_prepared_translation_texts.py` as a reusable
  prepared-text manifest gate for paper-facing analysis.
- The validator checks that prepared manifest rows match the source registry,
  raw and prepared checksum provenance matches the files on disk, and
  paper-facing prepared rows have `text_stage=prepared_translation_body`,
  `front_back_matter_status=stripped`, `machine_human_status=human_published`,
  and a publication-usable rights status.

## 2026-07-08 progress

- Added `wordspend/prepared_texts.py` as the reusable prepared-text manifest
  filter for paper-facing work.
- Added `scripts/select_paper_facing_translation_texts.py`, which runs the
  prepared-text validator first and then writes the selected paper-facing rows
  to `build/paper-facing/prepared_translation_texts.csv`.
- Verified the selector against the current corpus: it validated 2 prepared
  translation rows and selected the 2 human-published, publication-usable,
  stripped *Iliad* prepared texts by Samuel Butler and Alexander Pope.

## 2026-07-15 progress

- Added an explicit tokenization stage for the validated paper-facing prepared
  texts. It records the tokenizer ID, source prepared-text checksum, token-table
  checksum, token count, character offsets, and line locations.
- The tokenizer accepts only configured alphabetic, space-delimited language
  profiles; languages such as Classical Chinese fail closed until a suitable
  segmenter and version are configured.
- Tokenization remains a corpus-preparation output. It does not create aligned
  source-target segments or paper-facing residual claims.

## 2026-07-22 progress

- Added `data/source_editions.csv` with a provenance-complete Ancient Greek
  *Iliad*: Monro and Allen's *Homeri Opera*, third edition, volumes 1-2,
  published 1908-1920 and supplied as TEI XML by the Perseus Project.
- Recorded the CTS edition URN, editors, publication details, catalog URL,
  commit-pinned download URL, CC BY-SA 4.0 rights basis, and
  `human_edited_published` / paper-facing status.
- Added `scripts/import_source_editions.py` and reusable validation/extraction
  code in `wordspend/source_editions.py`. The importer preserves the raw XML
  checksum and writes deterministic, NFC-normalized `book.line` records.
- Prepared all 24 books as 15,687 unique line records, with raw and prepared
  SHA-256 provenance in `data/prepared/source_editions.csv`; four TEI
  editorial-deletion lines are retained but explicitly flagged.

## 2026-07-29 progress

- Added `data/translation_book_rules.csv` with an explicit Butler rule: identify
  the 24 canonical `BOOK` headings and skip the single Project Gutenberg
  editorial summary paragraph after each heading.
- Added `wordspend/book_alignment.py` and
  `scripts/prepare_book_alignments.py` to validate upstream prepared-text
  provenance, extract deterministic book bodies, and retain prepared-text
  character and line offsets plus per-book SHA-256 checksums.
- Prepared 24 Butler translation-book rows containing 153,268 translation
  tokens, with a checksum-linked summary in
  `data/prepared/translation_books.csv`.
- Recorded 24 structural Greek-to-English book alignments in
  `data/prepared/book_alignments.csv`. Each carries the Greek edition and
  translation checksums, source reference range, source editorial-deletion
  count, target checksum and token count, rights and human/editorial statuses,
  and an explicit restriction to book-length analysis.

## 2026-08-05 progress

- Extended translation-book rules with an explicit internal-paratext policy
  and carried that policy plus excluded-paragraph counts into the generated
  book and alignment manifests.
- Added Pope's reviewed rule: skip the argument label, argument title, and
  prose synopsis at the start of each book, then remove internal Gutenberg
  illustration paragraphs together with wrapped caption lines.
- Prepared all 24 Pope book bodies with 146,800 translation tokens, removing
  71 illustration/caption paragraphs, and recorded 24 checksum-linked
  structural alignments to the Monro and Allen Greek source books.
- Verified that the generated Pope bodies contain no argument headings or
  Gutenberg illustration markers. The alignments remain explicitly limited to
  book-length use and do not support lexical residual claims.

## Paper-facing readiness

There are two metadata-complete, paper-facing-eligible translation rows for the
same work. Their raw provider texts have been fetched and checksum-recorded,
and prepared translation-body texts with front/back matter stripped are
available behind local validation and selection gates. A provenance-complete,
open-licensed, human-edited Ancient Greek source edition is prepared as a
checksum-linked line table. Both translations are now structurally aligned to
that edition at book level under explicit paratext rules. No
source-line-to-translation alignment or lexical residual analysis is
paper-ready.

## Blocked or pending

- Lexical comparative claims still need an explicit, reviewable finer alignment
  between the prepared Greek `book.line` rows and Butler translation tokens.
- Pope likewise needs a finer reviewed Greek-line-to-translation-token
  alignment before lexical comparative claims.
- The English translation rights status is recorded for the United States; use
  outside the United States needs jurisdiction-specific review. The Perseus
  source edition is recorded under CC BY-SA 4.0 and must retain attribution and
  share-alike terms when redistributed.
