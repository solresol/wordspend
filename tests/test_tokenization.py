import unittest

from wordspend.tokenization import TOKENIZER_ID, tokenize_with_offsets, tokenizer_id_for_language


class TokenizationTests(unittest.TestCase):
    def test_preserves_unicode_apostrophes_and_offsets(self):
        text = "Sing, goddess\r\nAchilles' wrath and o’erflow."

        tokens = tokenize_with_offsets(text, "en")

        self.assertEqual(
            [token.token for token in tokens],
            ["Sing", "goddess", "Achilles", "wrath", "and", "o’erflow"],
        )
        self.assertEqual([token.line_number for token in tokens], [1, 1, 2, 2, 2, 2])
        self.assertEqual(text[tokens[2].start_char : tokens[2].end_char], "Achilles")
        self.assertEqual(tokens[-1].normalized_token, "o’erflow")

    def test_rejects_decomposed_unicode_to_keep_offsets_source_stable(self):
        with self.assertRaisesRegex(ValueError, "NFC-normalized"):
            tokenize_with_offsets("A\N{COMBINING ACUTE ACCENT}te", "grc")

    def test_accepts_bcp47_region_for_supported_base_language(self):
        self.assertEqual(tokenizer_id_for_language("en-GB"), TOKENIZER_ID)

    def test_keeps_unicode_combining_marks_inside_tokens(self):
        tokens = tokenize_with_offsets("कर्म योग", "sa")

        self.assertEqual([token.token for token in tokens], ["कर्म", "योग"])

    def test_rejects_languages_needing_a_different_segmentation_policy(self):
        with self.assertRaisesRegex(ValueError, "language-specific tokenizer"):
            tokenize_with_offsets("天下", "lzh")


if __name__ == "__main__":
    unittest.main()
