import unittest

from wordspend.fine_alignment import extract_target_paragraphs, propose_source_ranges


class FineAlignmentTests(unittest.TestCase):
    def test_extracts_paragraphs_with_whole_book_token_spans(self):
        paragraphs = extract_target_paragraphs(
            "Sing, goddess.\nWrapped line.\n\nThe anger ended.", "en"
        )

        self.assertEqual(len(paragraphs), 2)
        self.assertEqual((paragraphs[0].start_token, paragraphs[0].end_token), (1, 4))
        self.assertEqual((paragraphs[1].start_token, paragraphs[1].end_token), (5, 7))
        self.assertEqual(paragraphs[0].text, "Sing, goddess.\nWrapped line.")

    def test_proposal_covers_each_source_line_once_in_order(self):
        paragraphs = extract_target_paragraphs(
            "One two three four.\n\nFive six.\n\nSeven eight nine ten.", "en"
        )
        source_lines = list(range(1, 11))
        candidates = propose_source_ranges(source_lines, paragraphs)

        self.assertEqual(candidates[0].source_start_index, 0)
        self.assertEqual(candidates[-1].source_end_index, len(source_lines))
        self.assertTrue(
            all(
                previous.source_end_index == current.source_start_index
                for previous, current in zip(candidates, candidates[1:])
            )
        )
        self.assertTrue(
            all(
                candidate.source_end_index > candidate.source_start_index
                for candidate in candidates
            )
        )

    def test_rejects_more_paragraphs_than_source_lines(self):
        paragraphs = extract_target_paragraphs("One.\n\nTwo.\n\nThree.", "en")
        with self.assertRaisesRegex(ValueError, "fewer lines"):
            propose_source_ranges([1, 2], paragraphs)


if __name__ == "__main__":
    unittest.main()
