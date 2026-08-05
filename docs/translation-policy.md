# Translation Policy

Paper-facing evidence must use existing published translations. New machine
translations are not evidence for claims about human translation practice.

## Required source metadata

Each prepared source row must record:

- stable source ID and work ID
- source language and target language
- translator or responsible translation body
- translation title and edition
- publication date for the edition being used
- catalog URL and direct download URL
- download format
- rights status and rights basis
- machine/human status
- paper-facing eligibility

## Machine/human status

Use these values in `data/translation_sources.csv`:

- `human_published`: an existing published human translation.
- `machine_bootstrap`: generated or synthetic data used only to test tooling.
- `mixed_or_unclear`: provenance does not clearly establish human publication.

Rows marked `machine_bootstrap` or `mixed_or_unclear` must not be marked
paper-facing eligible.

## Rights status

Rows marked paper-facing eligible must have one of these rights statuses:

- `public_domain_us`
- `public_domain_worldwide`
- `open_license`

Rows with unknown, restricted, or unverified rights may be prepared for review
but must remain `paper_facing_eligible=no`.

## Paper-facing eligibility

A source may be marked `paper_facing_eligible=yes` only when it is
`human_published`, has a usable rights status, and has all required provenance
fields filled in. The validator enforces this gate before registry rows are used
for analysis.

## Prepared text staging

Raw provider text must remain available for checksum verification. Prepared
translation-body files may be used for paper-facing analysis only when they are
derived from the raw provider file by declared source-specific boundary rules
and their manifest records the raw checksum, prepared checksum, line boundaries,
`machine_human_status`, and `front_back_matter_status=stripped`.
Run `scripts/validate_prepared_translation_texts.py` before paper-facing
analysis to verify those manifest rows against the registry and the files on
disk.

## Paper-facing prepared-text selection

Before alignment or residual analysis, run:

```bash
uv run python scripts/select_paper_facing_translation_texts.py
```

The selector first validates the prepared-text manifest, then writes only rows
that are `paper_facing_eligible=yes`, `machine_human_status=human_published`,
publication-usable by rights status, `text_stage=prepared_translation_body`,
and `front_back_matter_status=stripped`.

## Tokenization staging

Run `scripts/tokenize_paper_facing_translation_texts.py` after prepared-text
validation. The tokenization summary carries forward source, edition, rights,
machine/human, eligibility, and prepared-text checksum fields. Each generated
token table records ordered tokens, normalized tokens, character offsets, and
line locations; the summary records its versioned tokenizer ID and SHA-256
checksum.

Tokenization must fail closed when a target language does not have an explicit
profile. In particular, Classical and Modern Chinese require a separately
versioned segmentation policy rather than the alphabetic tokenizer. Tokenized
whole texts are preparation inputs only and are not paper-facing evidence until
they are aligned to a provenance-complete source edition.

## Translation book staging

When a translation contains stable book headings, declare its extraction rule
in `data/translation_book_rules.csv` and run:

```bash
uv run python scripts/prepare_book_alignments.py
```

The rule must state how much leading per-book paratext is removed and identify
any internal-paratext policy. Generated book rows retain the prepared
translation checksum, prepared-text character and line offsets, applied
internal-paratext policy, excluded-paragraph count, per-book text checksum,
tokenizer ID, and token count. The alignment manifest must also retain those
paratext audit fields, the source-edition checksum and reference range, rights
and human/editorial statuses, and any flagged source lines.

Book-level structural alignment permits review or book-length exploratory
comparison only. It is not sufficient for lexical residual claims, which
require a finer reviewed alignment. A translation with additional internal
paratext, such as arguments, illustration captions, or notes, must have an
explicit removal policy before it is prepared.
The Pope rule skips its three leading argument paragraphs per book and removes
each Gutenberg paragraph beginning `[Illustration: ]`, including continuation
lines in wrapped captions.

## Source edition staging

Paper-facing alignment must use a source-language edition recorded in
`data/source_editions.csv`. Each row records the author, editors, edition and
publication details, canonical identifier, provider, version-pinned download,
rights basis, editorial status, and paper-facing eligibility.

Source-edition editorial status uses these values:

- `human_edited_published`: an identified published edition prepared by human
  editors;
- `machine_bootstrap`: synthetic or generated source text used only for tests;
- `mixed_or_unclear`: editorial provenance is not clear enough for claims.

Only `human_edited_published` rows with publication-usable rights may be
paper-facing. Run `scripts/import_source_editions.py` to validate that gate,
retain raw-download checksum provenance, and extract deterministic,
NFC-normalized source records with stable edition-local references. Prepared
source records must preserve explicit editorial states such as TEI deletions so
they can be reviewed or excluded during alignment. Source lines are alignment
inputs, not evidence of translation spending until a reviewable source-target
alignment exists.
