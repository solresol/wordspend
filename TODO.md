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
- [x] Prepare a deterministic Butler Book 1 fine-alignment review queue: 54
  translation paragraphs with token spans provisionally paired to all 611
  Greek lines. Mark every proportional proposal `machine_proposed_unreviewed`,
  `paper_facing_eligible=no`, and excluded from analysis pending human review.
- [x] Prepare a checksum-linked Butler Book 1 human-review worklist with the 54
  proposals and both source and target text visible. Leave every decision,
  reviewed range, reviewer, date, and note field blank, and keep all rows
  paper-facing ineligible and excluded from analysis.
- [x] Add a fail-closed import gate for completed Butler Book 1 review
  decisions. Validate immutable candidate fields, reviewer and timestamp
  provenance, allowed accept/adjust decisions, checksum-linked source text, and
  complete gap-free source coverage; keep imported rows excluded pending
  adjudication.

## Next

- [ ] Produce a finer, reviewable alignment between the prepared Ancient Greek
  source lines and Butler translation tokens before lexical residual analysis.
  The Book 1 candidate queue and human-review worklist are prepared;
  completed-decision validation/import tooling is prepared, while human review,
  adjudication, and Books 2-24 remain pending.
- [ ] Produce a finer, reviewable alignment between the prepared Ancient Greek
  source lines and Pope translation tokens before lexical residual analysis.
- [ ] Keep machine-generated translations, if any are added for bootstrap tests,
  explicitly labelled `machine_bootstrap` and excluded from paper-facing claims.
