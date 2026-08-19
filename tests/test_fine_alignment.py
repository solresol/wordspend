import unittest

from wordspend.fine_alignment import (
    extract_target_paragraphs,
    prepare_review_worklist_rows,
    propose_source_ranges,
    review_worklist_has_human_input,
)


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

    def test_review_worklist_preserves_proposal_but_starts_excluded(self):
        candidate = {
            "candidate_id": "candidate-1",
            "work_id": "work",
            "source_edition_id": "source",
            "translation_source_id": "translation",
            "book": "1",
            "segment_index": "1",
            "source_start_ref": "1.1",
            "source_end_ref": "1.2",
            "source_line_count": "2",
            "target_paragraph": "1",
            "source_text": "source text",
            "target_text": "target text",
            "proposal_status": "machine_proposed_unreviewed",
            "review_status": "pending_human_review",
            "paper_facing_eligible": "no",
            "analysis_status": "excluded_until_human_review",
        }

        rows = prepare_review_worklist_rows([candidate], "a" * 64)

        self.assertEqual(rows[0]["proposed_source_start_ref"], "1.1")
        self.assertEqual(rows[0]["review_decision"], "")
        self.assertEqual(rows[0]["reviewer"], "")
        self.assertEqual(rows[0]["paper_facing_eligible"], "no")
        self.assertEqual(rows[0]["analysis_status"], "excluded_until_completed_review")

    def test_review_worklist_rejects_promoted_candidate_rows(self):
        candidate = {
            "candidate_id": "candidate-1",
            "work_id": "work",
            "source_edition_id": "source",
            "translation_source_id": "translation",
            "book": "1",
            "segment_index": "1",
            "source_start_ref": "1.1",
            "source_end_ref": "1.2",
            "source_line_count": "2",
            "target_paragraph": "1",
            "source_text": "source text",
            "target_text": "target text",
            "proposal_status": "machine_proposed_unreviewed",
            "review_status": "approved",
            "paper_facing_eligible": "yes",
            "analysis_status": "included",
        }

        with self.assertRaisesRegex(ValueError, "unreviewed and analysis-excluded"):
            prepare_review_worklist_rows([candidate], "a" * 64)

    def test_detects_human_input_before_worklist_regeneration(self):
        self.assertFalse(review_worklist_has_human_input([{"review_decision": ""}]))
        self.assertTrue(
            review_worklist_has_human_input(
                [{"review_decision": "accept_proposed_range"}]
            )
        )


if __name__ == "__main__":
    unittest.main()
