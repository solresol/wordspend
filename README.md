# wordspend
How many words a language or translation “spends” to express something

The first project surface is a provenance registry for published translation
sources. Paper-facing evidence should come only from human-published
translations with target language, translator, edition, publication date,
download provenance, rights status, and machine/human status recorded.

- `data/translation_sources.csv` records prepared translation sources.
- `scripts/validate_translation_sources.py` validates the registry before a
  source can be used in paper-facing analysis.
- `scripts/fetch_translation_sources.py` downloads validated source rows into a
  raw-text cache and records checksum provenance.
- `scripts/prepare_translation_texts.py` strips source-specific front/back
  matter into prepared body text while preserving raw-text checksums.
- `docs/translation-policy.md` defines paper-facing eligibility.
