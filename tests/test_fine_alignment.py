import unittest

from wordspend.fine_alignment import (
    extract_target_paragraphs,
    import_completed_review_rows,
    prepare_review_worklist_rows,
    propose_source_ranges,
    review_worklist_has_human_input,
)


class FineAlignmentTests(unittest.TestCase):
    def completed_review_fixture(self):
        source_lines = [
            {
                "reference": f"1.{line}",
                "text": f"source {line}",
                "line_status": "edition_text",
            }
            for line in range(1, 5)
        ]
        candidates = []
        for segment, (start, end) in enumerate(((1, 2), (3, 4)), start=1):
            candidates.append(
                {
                    "candidate_id": f"candidate-{segment}",
                    "work_id": "work",
                    "source_edition_id": "source",
                    "translation_source_id": "translation",
                    "book": "1",
                    "segment_index": str(segment),
                    "alignment_level": "source_line_range_to_translation_paragraph",
                    "proposal_method": "proportional_translation_paragraph_tokens_v1",
                    "source_start_ref": f"1.{start}",
                    "source_end_ref": f"1.{end}",
                    "source_line_count": "2",
                    "source_editorially_deleted_line_count": "0",
                    "target_paragraph": str(segment),
                    "target_start_token": str(segment * 2 - 1),
                    "target_end_token": str(segment * 2),
                    "target_token_count": "2",
                    "target_start_char": str((segment - 1) * 10),
                    "target_end_char": str(segment * 10),
                    "source_text": f"source {start}\nsource {end}",
                    "target_text": f"target {segment}",
                    "source_prepared_sha256": "b" * 64,
                    "target_book_text_sha256": "c" * 64,
                    "translation_prepared_sha256": "d" * 64,
                    "proposal_status": "machine_proposed_unreviewed",
                    "review_status": "pending_human_review",
                    "paper_facing_eligible": "no",
                    "analysis_status": "excluded_until_human_review",
                }
            )
        worklist = prepare_review_worklist_rows(candidates, "a" * 64)
        for row in worklist:
            row["review_decision"] = "accept_proposed_range"
            row["reviewer"] = "Reviewer Name"
            row["reviewed_at"] = "2026-08-26T09:00:00+10:00"
        return worklist, candidates, source_lines

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

    def test_imports_completed_review_but_keeps_it_pending_adjudication(self):
        worklist, candidates, source_lines = self.completed_review_fixture()

        rows = import_completed_review_rows(
            worklist, candidates, source_lines, "a" * 64
        )

        self.assertEqual(len(rows), 2)
        self.assertEqual(sum(row["source_line_count"] for row in rows), 4)
        self.assertEqual(
            rows[0]["review_status"],
            "completed_human_review_pending_adjudication",
        )
        self.assertEqual(rows[0]["paper_facing_eligible"], "no")
        self.assertEqual(rows[0]["analysis_status"], "excluded_until_adjudication")

    def test_import_reconstructs_adjusted_ranges_from_source_edition(self):
        worklist, candidates, source_lines = self.completed_review_fixture()
        worklist[0].update(
            {
                "review_decision": "adjust_source_range",
                "reviewed_source_start_ref": "1.1",
                "reviewed_source_end_ref": "1.1",
                "review_notes": "Move the boundary after line 1.",
            }
        )
        worklist[1].update(
            {
                "review_decision": "adjust_source_range",
                "reviewed_source_start_ref": "1.2",
                "reviewed_source_end_ref": "1.4",
                "review_notes": "Move the boundary before line 2.",
            }
        )

        rows = import_completed_review_rows(
            worklist, candidates, source_lines, "a" * 64
        )

        self.assertEqual(rows[0]["source_text"], "source 1")
        self.assertEqual(rows[1]["source_text"], "source 2\nsource 3\nsource 4")

    def test_import_rejects_incomplete_review(self):
        worklist, candidates, source_lines = self.completed_review_fixture()
        worklist[0]["review_decision"] = ""

        with self.assertRaisesRegex(ValueError, "review_decision"):
            import_completed_review_rows(
                worklist, candidates, source_lines, "a" * 64
            )

    def test_import_rejects_gap_or_overlap(self):
        worklist, candidates, source_lines = self.completed_review_fixture()
        worklist[0].update(
            {
                "review_decision": "adjust_source_range",
                "reviewed_source_start_ref": "1.1",
                "reviewed_source_end_ref": "1.1",
                "review_notes": "Test boundary.",
            }
        )

        with self.assertRaisesRegex(ValueError, "no gaps or overlaps"):
            import_completed_review_rows(
                worklist, candidates, source_lines, "a" * 64
            )

    def test_import_rejects_changed_immutable_worklist_data(self):
        worklist, candidates, source_lines = self.completed_review_fixture()
        worklist[0]["target_text"] = "changed"

        with self.assertRaisesRegex(ValueError, "target_text changed"):
            import_completed_review_rows(
                worklist, candidates, source_lines, "a" * 64
            )


if __name__ == "__main__":
    unittest.main()
