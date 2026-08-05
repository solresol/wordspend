# wordspend

How many words does a language or translation spend to express something?

`wordspend` is a quantitative humanities project about relative lexical
compression. It starts from aligned source texts and existing translations, fits a
baseline relation between source length and target length, then asks which
source and target words predict unusually large residuals.

The motivating example is ancient Greek to a modern target language: if a Greek
passage is much shorter than its translation after controlling for passage
length, the Greek may be using compact lexical, grammatical, cultural, or
genre-specific resources that the translator has to spell out. If the target is
unexpectedly shorter, the reverse may be true, or the translator may be
omitting, generalising, or using a modern compressed term.

The project deliberately treats this as an evidence-generating method, not as a
direct proof that a concept was "important" to one culture. Residuals are
signals for closer philological work.

## Public Site

The intended public site is:

- `https://wordspend.symmachus.org`
- `merah` web root: `/var/www/vhosts/wordspend.symmachus.org/htdocs/`

The site is generated statically from the PostgreSQL-backed corpus and analysis
outputs on `raksasa`. `merah` should serve generated HTML, CSS, JavaScript, and
downloadable result files only. There is no CGI surface planned for the first
version.

## Core Question

For aligned segment `i`, let `S_i` be a source length and `T_i` be a target
translation length. The default model is:

```text
log(T_i + 1) = alpha + beta log(S_i + 1) + error_i
```

The residual is:

```text
R_i = log(T_i + 1) - predicted_log(T_i + 1)
```

Positive residuals mean the translation spends more words than expected.
Negative residuals mean it spends fewer words than expected.

After fitting this baseline, the project fits regularised lexical models over
source and target terms to find words, lemmas, phrases, or characters associated
with large positive or negative residuals.

## Why This Is Not Just Zipf

The classic law of abbreviation says frequent words tend to be shorter. That is
important background, but it is not the project novelty.

This project asks a translation-aware question:

- Where does a translator need to spend unexpected extra verbal material?
- Which source terms repeatedly trigger that spending?
- Which target terms repeatedly compress the translation?
- Are those patterns stable across works, translators, genres, and languages?
- Which residuals are lexical/cultural and which are grammatical, editorial, or
  translator-style effects?

The method is closest to a translation-aware keyness measure combined with a
source-target length model.

## Current First Slice

The first operational slice is intentionally small but real:

1. store a broad work catalog in PostgreSQL;
2. import existing Pausanias Greek to English aligned passages from the
   `pausanias` database on `raksasa` as a machine-generated bootstrap only;
3. fit the source-to-target length baseline;
4. calculate residuals and source/target lexical predictors;
5. generate a static research site with corpus inventory, methods, plots,
   top predictors, and downloadable CSV/JSON outputs;
6. publish that site to `wordspend.symmachus.org`.

Pausanias is a bootstrap corpus, not the final evidence base. The current
Pausanias English rows are project-generated and are useful for testing the
pipeline, but they are not paper evidence. The paper-facing corpus should use
downloaded or otherwise ingested existing published translations, with
translator, edition, target language, and publication date recorded. The paper
only becomes persuasive when the same method is run across multiple authors,
genres, translators, target languages, and language families.

## Repository Map

- `schema/`: PostgreSQL schema for works, source versions, translations,
  aligned segments, analysis runs, residuals, and predictors.
- `data/work_catalog.csv`: candidate works and corpus priorities.
- `wordspend/`: Python package for text metrics, regression analysis, database
  I/O, and static site generation.
- `scripts/`: command-line entrypoints for schema setup, catalog loading,
  Pausanias import, analysis, site generation, and cron execution.
- `tests/`: focused tests for text counts and residual modelling.
- `docs/`: project method, operations notes, work list, and paper plan.
- `paper/`: live paper draft.
- `site/`: generated static output, ignored by git.
- `build/`: generated analysis outputs, ignored by git.
- `logs/`: cron and local run logs, ignored by git.

## Data Model

The durable unit is an aligned segment:

- a work;
- a source text version with provenance and hash;
- a translation or target text version with translator/provenance;
- target language and translation publication date;
- a reference such as book.chapter.section, line range, chapter/verse, or
  paragraph id;
- source text;
- target text;
- alignment level;
- precomputed length metrics;
- metadata.

Analysis runs are stored separately so the same corpus can be analysed with
different:

- length metrics: tokens, characters, syllables, morphemes, or language-specific
  units;
- baselines: raw linear or log-linear;
- feature spaces: surface tokens, lemmas, POS-filtered tokens, n-grams, Chinese
  characters, Chinese segmented words, Old English lemmas, and so on;
- inclusion rules: by work, translator, genre, period, language, or alignment
  level.

## First Work List

The first comparison set should be balanced rather than merely large.

High priority Greek:

- Pausanias, `Description of Greece`: already available as the bootstrap corpus.
- Herodotus, `Histories`: narrative prose with ethnography, place, war, and
  local customs.
- Thucydides, `History of the Peloponnesian War`: compressed political and
  military prose.
- Homer, `Iliad` and `Odyssey`: formulaic epic with multiple public-domain
  translations.
- Hesiod, `Theogony` and `Works and Days`: mythic genealogy, labour, and moral
  vocabulary.
- Plato, `Apology`, `Phaedo`, and selections from `Republic`: philosophical
  terms and argument structure.
- Sophocles, Euripides, and Aeschylus: dramatic verse, kinship, ritual, civic
  and status vocabulary.
- Strabo, `Geography`: a useful comparison with Pausanias for geographic
  description.
- Plutarch, selected `Lives`: biography, exemplarity, virtue, civic status.

High priority non-Greek:

- Old English `Beowulf`: lordship, kinship, feud, fate, gift, hall, and warrior
  vocabulary.
- `The Wanderer`, `The Seafarer`, and selected Exeter Book poems: exile,
  affect, lordship, and Christian reinterpretation.
- Anglo-Saxon Chronicle selections: compact administrative and event prose.
- `Sermo Lupi ad Anglos`: moral, social, legal, and ecclesiastical language.
- Classical Chinese `Analects`, `Mencius`, `Zhuangzi`, `Daodejing`, `Shiji`,
  `Hanshu`, and `Zuozhuan`: compact classical prose with Modern Chinese and
  English translation comparators.
- Sanskrit `Bhagavad Gita`, selected `Mahabharata`, `Ramayana`, and Kalidasa:
  useful for verse/prose and cultural vocabulary controls.
- Latin Caesar, Cicero, Virgil, Ovid, Tacitus, and Augustine: strong control
  cases with many translations and well-studied genre differences.

The full candidate catalog is in `data/work_catalog.csv`; the more discursive
version is in `docs/works.md`.

## Translation Policy

The paper-facing plan is to download, parse, or otherwise ingest existing
translations. It is not to generate fresh translations and analyse them as
evidence. Machine-generated rows are allowed only as bootstrap or UI fixtures
and must be marked that way.

Each translation should record:

- target language;
- translator;
- translation label or edition;
- publication year and publication-date text;
- edition citation;
- source URL and download URL;
- license or rights statement;
- whether it is a published human translation, modernisation, classroom text,
  or machine bootstrap.

English is one useful target language, not the project boundary. The first
broader target plan is Greek/Latin to English, French, German, and Italian;
Classical Chinese to Modern Chinese and English; Old English to Modern English
with later German/French comparators; and Sanskrit to English, Hindi, and German
where clean public translations are available.

See `docs/translation-policy.md`.

### Translation source pipeline

The paper-facing evidence base is a provenance registry of published
translation sources: only human-published translations are used, each recorded
with target language, translator, edition, publication date, download
provenance, rights status, and machine/human status. The ingestion pipeline
that builds and validates that registry:

- `data/translation_sources.csv` records prepared translation sources.
- `scripts/validate_translation_sources.py` validates the registry before a
  source can be used in paper-facing analysis.
- `scripts/fetch_translation_sources.py` downloads validated source rows into a
  raw-text cache and records checksum provenance.
- `scripts/prepare_translation_texts.py` strips source-specific front/back
  matter into prepared body text while preserving raw-text checksums.
- `scripts/validate_prepared_translation_texts.py` validates prepared-text
  manifests, checksum links, and paper-facing prepared-body requirements.
- `scripts/select_paper_facing_translation_texts.py` validates the prepared-text
  manifest and writes the subset eligible for paper-facing alignment and
  analysis.
- `scripts/tokenize_paper_facing_translation_texts.py` tokenizes that validated
  subset with an explicit language profile and records token-file checksums and
  offsets for downstream alignment.
- `scripts/prepare_book_alignments.py` applies explicit translation-structure
  rules, removes declared leading and internal paratext, and records
  checksum-linked source-target book alignments. The current rules prepare the
  Butler and Pope *Iliad* translations; book alignment is not fine enough for
  lexical residual claims.

### Source edition pipeline

Paper-facing alignment also requires a provenance-complete edition of the
source-language text. `data/source_editions.csv` records edition, editor,
publication, canonical identifier, version-pinned download, rights, and
human/machine editorial status. Run:

```bash
uv run python scripts/import_source_editions.py
```

The importer validates paper-facing eligibility, preserves the raw provider TEI
XML in the ignored raw cache, and writes a checksum-linked, line-addressable
source table plus manifest under `data/prepared/source_editions/`.

Run `uv run python scripts/prepare_book_alignments.py` to prepare configured
translation book bodies and pair them with the corresponding source-edition
book ranges. Rules are declared in `data/translation_book_rules.csv`; generated
book bodies and structural alignment manifests are committed under
`data/prepared/` for review and reproducibility.

## Methodological Cautions

Residuals are not self-interpreting. A source word predicting English expansion
may reflect:

- lexical compression;
- culturally loaded institutions or practices;
- inflectional morphology;
- particles, discourse markers, or formulae;
- named entities and titles;
- genre conventions;
- translator explicitation;
- inconsistent alignment;
- editorial punctuation;
- typography and script conventions;
- ordinary sound change or orthographic change.

This is why the paper needs both statistical stability checks and close-reading
examples.

## Length Metrics

The project should run multiple metrics and keep them separate:

- tokens: the primary translation-spend measure;
- characters: useful but script-sensitive;
- syllables or phonemes: closer to spoken lexical economy, but language-specific;
- lemmas: useful for source-side Greek, Latin, Old English, and Sanskrit
  interpretation;
- Chinese characters: essential for Classical Chinese;
- Chinese segmented words: essential for modern Chinese comparisons, but
  tokenizer-dependent;
- morphemes: useful where morphology is doing much of the compression.

The current code supports token, character, and approximate syllable metrics.
Approximate syllables are diagnostic only until language-specific syllabifiers
are added.

## Statistical Plan

The minimum paper-facing analysis should include:

1. baseline source-to-target length regressions by corpus;
2. residual predictor models for source and target terms;
3. held-out checks by work and translator where data permits;
4. repeated analyses at sentence and paragraph level;
5. alternate length metrics;
6. controls for source language, target language, target publication date,
   genre, translator, and period;
7. named-entity and POS sensitivity checks;
8. qualitative close readings of the strongest residual examples;
9. comparison with ordinary keyword/keyness results;
10. error analysis for bad alignments and translator intrusions.

## Local Setup

Install dependencies with `uv`:

```bash
uv sync
```

Run tests:

```bash
uv run python -m unittest discover -s tests
```

Run analysis from a CSV file:

```bash
uv run python scripts/run_analysis.py \
  --input data/example_segments.csv \
  --output-dir build/analysis
```

Generate the static site from existing analysis outputs:

```bash
uv run python scripts/generate_site.py \
  --analysis-dir build/analysis \
  --catalog data/work_catalog.csv \
  --output-dir site
```

Run against PostgreSQL:

```bash
export WORDSPEND_DATABASE_URL=dbname=wordspend
uv run python scripts/init_db.py
uv run python scripts/load_work_catalog.py
uv run python scripts/import_pausanias.py --limit 0
uv run python scripts/run_analysis.py --from-db --save-db --output-dir build/analysis
uv run python scripts/generate_site.py --analysis-dir build/analysis --output-dir site
```

`--limit 0` means no limit.

## Operations

The intended live checkout is:

- `raksasa:/home/wordspend/wordspend`

The intended service account and database are:

- system account: `wordspend`
- PostgreSQL role: `wordspend`
- PostgreSQL database: `wordspend`

The intended nightly cron shape is:

```cron
35 4 * * * /home/wordspend/wordspend/scripts/run_daily_pipeline.sh >> /home/wordspend/wordspend/logs/cron.log 2>&1
```

The pipeline:

1. enters the repo;
2. pulls from git only when the checkout is clean;
3. applies schema;
4. loads the work catalog;
5. optionally refreshes imported corpora;
6. runs analysis from PostgreSQL;
7. generates the static site;
8. deploys to `merah:/var/www/vhosts/wordspend.symmachus.org/htdocs/`;
9. leaves logs and generated analysis files in `logs/` and `build/`.

## Publication Plan

The paper should be framed as a method paper plus a careful first empirical
study:

- title: `Word Spend: Translation Residuals as Evidence for Relative Lexical
  Compression`;
- venue candidates: Computational Humanities Research, Journal of Cultural
  Analytics, Digital Scholarship in the Humanities, LaTeCH-CLfL/SIGHUM, LREC or
  Language Resources and Evaluation if the corpus/tooling becomes the main
  contribution;
- contribution: a reproducible method and corpus for identifying where
  translation spends unexpected extra words;
- claim strength: relative lexical, grammatical, and translational compression,
  not direct measurement of cultural importance.

The current draft is in `paper/wordspend.md`.

## Current Status

As of May 23, 2026, the first vertical slice is running on `raksasa`:

- `wordspend` system account created on `raksasa`;
- PostgreSQL database `wordspend` created and owned by role `wordspend`;
- 44 work-catalog rows loaded;
- 3,170 Pausanias aligned passages imported;
- token/log baseline run and saved to PostgreSQL;
- nightly cron installed for `35 4 * * *`;
- static site generated and rsynced to
  `/var/www/vhosts/wordspend.symmachus.org/htdocs/` on `merah`.

Bootstrap Pausanias metrics:

- segments: 3,170;
- source tokens: 218,516;
- target tokens: 282,699;
- baseline: `log(target_tokens + 1) ~ log(source_tokens + 1)`;
- R squared: 0.862;
- slope: 0.963;
- residual standard deviation: 0.0996;
- source features modelled: 2,000;
- target features modelled: 2,000.

The generated files are deployed on `merah`, but the public URL still needs the
`httpd.conf` server stanza in `docs/operations.md` to be added and `httpd`
reloaded before `https://wordspend.symmachus.org/` serves the new site instead
of the fallback autoindex.

The first results should be treated as bootstrap diagnostics until multiple
corpora and translator controls are imported.
