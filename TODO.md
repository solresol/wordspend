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

## Next

- [ ] Tokenize and align the selected paper-facing prepared-text rows against
  source text before residual analysis.
- [ ] Keep machine-generated translations, if any are added for bootstrap tests,
  explicitly labelled `machine_bootstrap` and excluded from paper-facing claims.
