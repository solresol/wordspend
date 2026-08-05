# Works

## `homer-iliad`

- Title: *The Iliad*
- Source language: Ancient Greek (`grc`)
- Prepared sources: 2
- Prepared manifest status: validated by
  `scripts/validate_prepared_translation_texts.py`
- Paper-facing selection status: selected by
  `scripts/select_paper_facing_translation_texts.py`
- Tokenization status: both selected rows are tokenized by
  `scripts/tokenize_paper_facing_translation_texts.py`; generated token tables
  retain prepared-text and token-file checksum provenance.
- Source edition status: Monro and Allen's Ancient Greek third edition is
  prepared as 15,687 checksum-linked `book.line` records.
- Alignment status: Butler and Pope each have 24 checksum-linked translation
  book bodies and 24 structural alignments to the Greek source books. Finer
  alignment remains pending for both.

### Prepared source edition

- `homer-iliad-grc-monro-allen-perseus`: Ancient Greek (`grc`), Homer,
  *Homeri Opera*, edited by David B. Monro and Thomas W. Allen, third edition,
  volumes 1-2, Oxford: Clarendon Press, 1908-1920. The Perseus TEI edition is
  identified by `urn:cts:greekLit:tlg0012.tlg001.perseus-grc2`; its download is
  pinned to canonical-greekLit commit
  `91595f89e15b4d3000cd93efcf8990720c8be2b9`. Rights status is `open_license`
  under CC BY-SA 4.0; editorial status is `human_edited_published`; paper-facing
  metadata eligibility is `yes`. The raw XML is retained in the ignored raw
  cache, and the committed prepared line table and checksum manifest are under
  `data/prepared/source_editions/` and `data/prepared/source_editions.csv`.

### Prepared translation sources

- `homer-iliad-en-butler-pg2199`: English (`en`), translated by Samuel Butler,
  Project Gutenberg eBook #2199 plain-text edition, released 2000-06-01 and
  most recently updated 2022-08-16. Rights status is recorded as
  `public_domain_us`; machine/human status is `human_published`;
  paper-facing metadata eligibility is `yes`. The raw provider text is fetched
  to `data/raw/translations/homer-iliad-en-butler-pg2199.txt`, with checksum
  provenance in `data/raw/translation_downloads.csv`. A prepared
  translation-body text is written to
  `data/prepared/translations/homer-iliad-en-butler-pg2199.txt`, with checksum
  and line-boundary provenance in `data/prepared/translation_texts.csv`. Its
  24 book bodies exclude the declared editorial summary after each `BOOK`
  heading and contain 153,268 tokens. Their source offsets, checksums, and
  structural Greek-book alignments are recorded under `data/prepared/`.
- `homer-iliad-en-pope-pg6130`: English (`en`), translated by Alexander Pope,
  Project Gutenberg eBook #6130 plain-text edition, released 2004-07-01 and
  most recently updated 2026-02-07. Rights status is recorded as
  `public_domain_us`; machine/human status is `human_published`;
  paper-facing metadata eligibility is `yes`. The raw provider text is fetched
  to `data/raw/translations/homer-iliad-en-pope-pg6130.txt`, with checksum
  provenance in `data/raw/translation_downloads.csv`. A prepared
  translation-body text is written to
  `data/prepared/translations/homer-iliad-en-pope-pg6130.txt`, with checksum
  and line-boundary provenance in `data/prepared/translation_texts.csv`. It is
  prepared as 24 book bodies containing 146,800 tokens under a reviewed rule
  that skips each argument label, title, and synopsis and removes 71 internal
  illustration/caption paragraphs. The rule, excluded-paragraph counts,
  per-book checksums, and 24 structural Greek-book alignments are recorded
  under `data/prepared/`. These alignments are restricted to book-length use.
