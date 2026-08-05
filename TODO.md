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

## Next

- [ ] Produce a finer, reviewable alignment between the prepared Ancient Greek
  source lines and Butler translation tokens before lexical residual analysis.
- [ ] Produce a finer, reviewable alignment between the prepared Ancient Greek
  source lines and Pope translation tokens before lexical residual analysis.
- [ ] Keep machine-generated translations, if any are added for bootstrap tests,
  explicitly labelled `machine_bootstrap` and excluded from paper-facing claims.
