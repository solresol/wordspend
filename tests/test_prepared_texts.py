import unittest

import pandas as pd

from wordspend.prepared_texts import select_paper_facing_prepared_texts


def row(source_id, **overrides):
    data = {
        "source_id": source_id,
        "work_id": "fixture-work",
        "target_language_code": "en",
        "translator": "Translator",
        "translation_title": "Translation",
        "edition": "Edition",
        "publication_date": "1900-01-01",
        "prepared_path": f"data/prepared/translations/{source_id}.txt",
        "prepared_sha256": "abc123",
        "text_stage": "prepared_translation_body",
        "front_back_matter_status": "stripped",
        "rights_status": "public_domain_us",
        "machine_human_status": "human_published",
        "paper_facing_eligible": "yes",
    }
    data.update(overrides)
    return data


class PreparedTextFilterTests(unittest.TestCase):
    def test_selects_only_validated_human_published_usable_body_rows(self):
        frame = pd.DataFrame(
            [
                row("valid"),
                row("machine", machine_human_status="machine_bootstrap"),
                row("restricted", rights_status="restricted"),
                row("raw", text_stage="raw_provider_text"),
                row("front-matter", front_back_matter_status="not_stripped"),
                row("not-eligible", paper_facing_eligible="no"),
            ]
        )

        selected = select_paper_facing_prepared_texts(frame)

        self.assertEqual(list(selected["source_id"]), ["valid"])

    def test_requires_filter_columns(self):
        with self.assertRaisesRegex(ValueError, "paper_facing_eligible"):
            select_paper_facing_prepared_texts(pd.DataFrame([{"source_id": "missing"}]))


if __name__ == "__main__":
    unittest.main()
