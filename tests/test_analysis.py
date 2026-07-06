import unittest

import pandas as pd

from wordspend.analysis import analyze_translation_spend
from wordspend.textstats import count_characters, count_tokens, estimate_english_syllables


class TextStatsTests(unittest.TestCase):
    def test_counts_word_like_tokens(self):
        self.assertEqual(count_tokens("alpha beta, gamma."), 3)
        self.assertEqual(count_tokens("Athenians and Thebans"), 3)

    def test_counts_characters_inside_tokens(self):
        self.assertEqual(count_characters("ab cd!"), 4)

    def test_estimates_english_syllables(self):
        self.assertGreaterEqual(estimate_english_syllables("translation residual"), 5)


class AnalysisTests(unittest.TestCase):
    def test_models_residual_predictors(self):
        frame = pd.DataFrame(
            [
                {
                    "work_slug": "fixture",
                    "segment_ref": "1",
                    "source_text": "compact alpha beta gamma",
                    "target_text": "one two three four five six seven eight nine",
                },
                {
                    "work_slug": "fixture",
                    "segment_ref": "2",
                    "source_text": "compact delta epsilon zeta",
                    "target_text": "one two three four five six seven eight",
                },
                {
                    "work_slug": "fixture",
                    "segment_ref": "3",
                    "source_text": "compact eta theta iota",
                    "target_text": "one two three four five six seven eight ten",
                },
                {
                    "work_slug": "fixture",
                    "segment_ref": "4",
                    "source_text": "sprawl alpha beta gamma kappa lambda",
                    "target_text": "one two three",
                },
                {
                    "work_slug": "fixture",
                    "segment_ref": "5",
                    "source_text": "sprawl delta epsilon zeta kappa lambda",
                    "target_text": "one two three four",
                },
                {
                    "work_slug": "fixture",
                    "segment_ref": "6",
                    "source_text": "sprawl eta theta iota kappa lambda",
                    "target_text": "one two three",
                },
            ]
        )

        result = analyze_translation_spend(frame, min_df=1, top_n=100)

        self.assertTrue(result["available"])
        self.assertEqual(result["metrics"]["segment_count"], 6)
        features = set(result["source_predictors"]["feature"])
        self.assertTrue(any(feature.startswith("compact") for feature in features))
        self.assertTrue(any(feature.startswith("sprawl") for feature in features))
        self.assertEqual(len(result["segments"]), 6)
        compact = result["source_predictors"][
            result["source_predictors"]["feature"].str.startswith("compact")
        ]["coefficient"].max()
        sprawl = result["source_predictors"][
            result["source_predictors"]["feature"].str.startswith("sprawl")
        ]["coefficient"].min()
        self.assertGreater(compact, 0)
        self.assertLess(sprawl, 0)


if __name__ == "__main__":
    unittest.main()
