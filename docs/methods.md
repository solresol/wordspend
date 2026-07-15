# Method Notes

## Baseline

The first model is a log-linear source-to-target length relation:

```text
log(T + 1) = alpha + beta log(S + 1) + error
```

This is a discourse-quantity control. Long source passages usually have long
translations. The interesting signal is the residual after this broad relation
has been removed.

Paper-facing analyses should use existing translations. Machine-generated
translations may be used for bootstrapping software, but they should be
excluded from evidential claims.

## Residual Interpretation

Positive residual:

- the target translation is longer than expected;
- the source may be lexically or grammatically compact;
- the translator may be explicating;
- the alignment may contain extra target material.

Negative residual:

- the target translation is shorter than expected;
- the target may have a compact lexicalisation;
- the translator may be compressing, omitting, or generalising;
- the source may contain formulaic or redundant material.

## Predictor Model

After calculating residuals, the current code fits separate regularised lexical
models for source terms and target terms. The predictors are surface unigrams
and bigrams. Coefficients are not final inferential statistics; they are ranked
leads for validation and close reading.

## Tokenization

Paper-facing prepared texts are tokenized before alignment with the versioned
`unicode-alphabetic-apostrophe-v1` profile. It extracts Unicode alphabetic
sequences, retains internal straight or curly apostrophes, requires NFC input,
and records case-folded forms, character offsets, and line locations. The
tokenizer preserves the decoded file's CRLF characters when calculating
offsets, while the source and generated token files are tied to their byte-level
SHA-256 checksums.

The profile is limited to configured alphabetic, space-delimited languages.
Classical and Modern Chinese must use an explicit, versioned segmenter; the
pipeline rejects those language codes rather than applying this profile.

## Required Robustness Checks

- Repeat at sentence and paragraph level.
- Repeat with token, character, syllable, lemma, and language-specific metrics.
- Hold out works.
- Hold out translators.
- Hold out target languages.
- Model translation publication date or publication period.
- Compare single-work and pooled models.
- Remove or separately model named entities.
- Compare source-side predictors with ordinary keyword/keyness results.
- Inspect extreme residual examples manually.

## Language-Specific Notes

Greek:

- Lemmas and morphology matter.
- Participles, case endings, particles, articles, and prepositions may explain
  much of the expansion.
- Tragedy and epic need genre-specific handling.

Old English:

- Do not confuse cultural salience with ordinary sound change.
- Love/hate/lordship examples need matched phonological and frequency controls.
- Syllable or phoneme counts are more meaningful than letters.

Classical Chinese:

- Character count and segmented-word count are both necessary.
- Classical-to-Modern Chinese and Classical-to-English answer different
  questions.
- Tokenizer versions must be recorded.
