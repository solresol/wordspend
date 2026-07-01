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
