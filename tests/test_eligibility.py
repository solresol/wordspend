import unittest

import pandas as pd

from wordspend.eligibility import select_analysis_segments


class EligibilityTests(unittest.TestCase):
    def row(self, **changes):
        return dict(is_machine_generated=False, translation_source_type='existing_human_translation',
                    paper_facing_eligible=True, review_status='adjudicated', analysis_status='eligible',
                    alignment_level='reviewed_source_line_range_to_translation_paragraph',
                    source_editorial_status='human_edited_published', source_rights_status='open_license',
                    translation_rights_status='public_domain_us', **changes)

    def test_missing_csv_provenance_fails_closed(self):
        with self.assertRaisesRegex(ValueError, 'eligibility columns'):
            select_analysis_segments(pd.DataFrame([{'source_text': 'a', 'target_text': 'b'}]))

    def test_paper_excludes_each_ineligible_condition(self):
        valid = self.row()
        self.assertEqual(len(select_analysis_segments(pd.DataFrame([valid]))), 1)
        for field, value in [('is_machine_generated', True), ('is_machine_generated', ''),
            ('translation_source_type', 'machine_bootstrap'), ('paper_facing_eligible', False),
            ('review_status', 'pending_human_review'), ('review_status', 'pending_adjudication'),
            ('analysis_status', 'excluded'), ('alignment_level', 'book'),
            ('source_editorial_status', 'unknown'), ('source_rights_status', 'unknown'),
            ('translation_rights_status', 'unclear')]:
            with self.subTest(field=field, value=value):
                row = {**valid, field: value}
                self.assertTrue(select_analysis_segments(pd.DataFrame([row])).empty)

    def test_bootstrap_cannot_mix_in_human_proposals(self):
        machine = {**self.row(), 'is_machine_generated': True, 'translation_source_type': 'machine_bootstrap'}
        selected = select_analysis_segments(pd.DataFrame([self.row(), machine]), 'bootstrap')
        self.assertEqual(len(selected), 1)
        self.assertTrue(bool(selected.iloc[0]['is_machine_generated']))
