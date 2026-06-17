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

## Next

- [ ] Add at least one second human-published translation of the same work so
  word-spend comparisons are not single-row metadata only.
- [ ] Add a validation gate for prepared-text manifests so paper-facing
  analysis can require `front_back_matter_status=stripped`.
- [ ] Add paper-facing analysis filters that select only validated rows where
  `paper_facing_eligible=yes`, `machine_human_status=human_published`, and the
  rights status is usable for publication.
- [ ] Keep machine-generated translations, if any are added for bootstrap tests,
  explicitly labelled `machine_bootstrap` and excluded from paper-facing claims.
