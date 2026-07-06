# Word Spend: Translation Residuals as Evidence for Relative Lexical Compression

## Abstract

This paper introduces a translation-residual method for studying relative
lexical compression across historical languages and their translations. For
aligned source and target segments, we fit a baseline relation between source
length and translation length, then examine the residuals: cases where the
translation spends more or fewer words than expected. We then model which
source and target lexical features predict those residuals. The method is
designed to identify candidate sites of lexical, grammatical, cultural, and
translator-driven compression for closer reading. A bootstrap Greek-to-English
case study using Pausanias demonstrates the workflow; paper-facing analyses use
existing published translations with translation date and target-language
metadata. Broader Greek, Old English, and Classical Chinese corpora are planned
to test stability across works, translators, genres, target languages, and
language families.

## 1. Introduction

Languages differ in where they spend words. A term, construction, or formula
that is compact in one language may require a phrase, explanation, or
translatorly addition in another. These differences are easy to notice in close
reading, but hard to survey systematically across a corpus.

The proposed method begins with a simple observation: translations preserve
discourse quantity well enough that source length and target length usually
have a strong relation. The deviations from that relation are therefore
interesting. When a source segment is much shorter than expected for its
translation, something in the source, the target language, the translator, or
the alignment has made the translation spend extra words. When the target is
shorter than expected, the target may have compressed the source.

The method is not a direct measure of cultural importance. It is a way to find
where relative compression is happening and then ask why.

## 2. Relation To Prior Work

The background literature includes the law of abbreviation, information-theoretic
accounts of word length, psycholexical approaches to culturally salient
vocabulary, corpus keyness, and corpus-based translation studies. The novelty
claimed here should be narrow: a translation-aware residual method for finding
where aligned translations spend unexpected words.

This section still needs verified citations and exact positioning before
submission.

## 3. Data

The first live corpus is Pausanias, imported from the existing Pausanias project
database on `raksasa`. It is a bootstrap corpus because the aligned passages and
English translations already exist, but the current English rows are
project-generated. They are useful for testing the method and site; they are not
paper evidence.

The paper-facing corpus should later include:

- multiple Greek prose and verse works;
- multiple existing translators for at least some works;
- target languages beyond English where aligned translations can be sourced;
- translation publication dates or publication periods;
- Old English to Modern English comparisons;
- Classical Chinese to English and Classical Chinese to Modern Chinese
  comparisons;
- Latin or Sanskrit controls if source and translation provenance are clean.

## 4. Method

For aligned segment `i`, define source length `S_i` and target length `T_i`.
The default model is:

```text
log(T_i + 1) = alpha + beta log(S_i + 1) + error_i
```

The residual is:

```text
R_i = log(T_i + 1) - predicted_log(T_i + 1)
```

Positive residuals indicate target expansion relative to the baseline. Negative
residuals indicate target compression relative to the baseline.

After calculating residuals, regularised lexical models are fitted separately
for source-side and target-side features. The first implementation uses surface
unigrams and bigrams. Later versions should use lemmas, POS filters, named
entity flags, Chinese characters, Chinese segmented words, and language-specific
morphological features.

## 5. Bootstrap Results

The first verified run uses the Pausanias bootstrap corpus imported from the
existing project database on `raksasa`. Because its target text is
project-generated, this run is a software and method diagnostic only.

Corpus:

- work: Pausanias, `Description of Greece`;
- aligned passage segments: 3,170;
- source tokens: 218,516;
- target tokens: 282,699.

Baseline:

- metric: token count;
- model: `log(target_tokens + 1) ~ log(source_tokens + 1)`;
- intercept: 0.4064365677810482;
- slope: 0.9632556065373404;
- R squared: 0.8623764934745082;
- residual standard deviation: 0.09961810148569929.

Residual predictor models:

- source features: 2,000;
- target features: 2,000;
- source residual-model R squared: 0.615406973082145;
- target residual-model R squared: 0.6990041716015285.

The current top source-side predictors include Greek terms and phrases such as
`Helen`, `the sanctuary`, `Peloponnesians`, `has been established`, `others`,
`a hero-shrine`, and `sanctuary`, depending on coefficient direction and
surface form. The current target-side predictors include phrases such as
`dedicated to`, `because he`, `a temple`, `rivers`, `Orchomenus`, and
`cavalry`.

These are not yet paper claims. They are triage outputs. The next step is to
import existing published translations, inspect the associated passages,
separate named-entity and cult-site effects from lexical compression, and
compare the same workflow against Herodotus, Strabo, and at least one
multi-translator and multi-target-language corpus.

## 6. Robustness

The first submission needs at least some of:

- sentence versus paragraph alignments;
- token versus character versus syllable metrics;
- leave-one-work-out checks;
- leave-one-translator-out checks;
- leave-one-target-language-out checks;
- publication-period controls;
- named-entity sensitivity;
- genre controls;
- comparison with ordinary keyness;
- manual alignment-error audit.

## 7. Interpretation

A residual predictor can mean several things:

- culturally loaded lexical compression;
- grammatical compression;
- translator explicitation;
- modern lexical compression;
- named-entity effects;
- genre formulae;
- alignment error;
- source or target editorial convention.

The paper should treat statistical predictors as ranked evidence for
philological inspection, not as automatic cultural conclusions.

## 8. Venue Fit

Most likely:

- Computational Humanities Research;
- Journal of Cultural Analytics;
- Digital Scholarship in the Humanities;
- LaTeCH-CLfL/SIGHUM or another ACL-adjacent humanities/NLP workshop.

If the corpus and tooling become the central contribution, consider Language
Resources and Evaluation or LREC-style venues.

## 9. Current Next Steps

1. Finish the Pausanias bootstrap import and public site.
2. Verify the strongest residual predictors manually.
3. Add Herodotus and Strabo as first comparison corpora.
4. Add one multiple-translation experiment using existing published
   translations with publication dates.
5. Add one non-English target-language experiment.
6. Add Classical Chinese character-level and segmented-word analyses.
7. Revisit the paper claims after the cross-corpus checks.
