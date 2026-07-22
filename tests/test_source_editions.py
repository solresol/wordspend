import csv
import tempfile
import unittest
from pathlib import Path

from wordspend.source_editions import extract_tei_source_lines, validate_source_edition_registry


TEI = """<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0">
  <text><body><div type="edition" n="urn:cts:greekLit:test.work.edition">
    <div type="textpart" subtype="Book" n="1">
      <l n="1"><milestone unit="para"/>mūnin aeide</l>
      <l n="2"><del>thea</del></l>
    </div>
    <div type="textpart" subtype="Book" n="2"><l n="1">andra</l></div>
  </div></body></text>
</TEI>
""".encode("utf-8")


def valid_registry_row(**overrides):
    row = {
        "source_edition_id": "test-source-edition",
        "work_id": "test-work",
        "work_title": "Test Work",
        "source_language": "Ancient Greek",
        "source_language_code": "grc",
        "author": "Author",
        "editors": "Editor",
        "edition_title": "Edition",
        "edition_label": "First edition",
        "publication_date": "1920",
        "publication_date_text": "1920",
        "publisher": "Publisher",
        "publication_place": "Place",
        "digital_provider": "Provider",
        "canonical_id": "urn:cts:greekLit:test.work.edition",
        "version_id": "abc123",
        "catalog_url": "https://example.org/catalog",
        "download_url": "https://example.org/source.xml",
        "download_format": "tei_xml",
        "rights_status": "open_license",
        "rights_basis": "CC BY-SA 4.0",
        "rights_url": "https://example.org/license",
        "editorial_status": "human_edited_published",
        "paper_facing_eligible": "yes",
        "notes": "",
    }
    row.update(overrides)
    return row


class SourceEditionTests(unittest.TestCase):
    def test_extracts_nfc_line_text_and_stable_references(self):
        lines = extract_tei_source_lines(TEI, "urn:cts:greekLit:test.work.edition")

        self.assertEqual([line.reference for line in lines], ["1.1", "1.2", "2.1"])
        self.assertEqual(lines[0].text, "mūnin aeide")
        self.assertEqual(
            [line.line_status for line in lines],
            ["edition_text", "editorially_deleted", "edition_text"],
        )

    def test_rejects_out_of_order_line_references(self):
        payload = TEI.replace(b'<l n="2"><del>thea</del></l>', b'<l n="1"><del>thea</del></l>')
        with self.assertRaisesRegex(ValueError, "strictly increasing"):
            extract_tei_source_lines(payload, "urn:cts:greekLit:test.work.edition")

    def test_paper_facing_registry_rejects_machine_bootstrap(self):
        row = valid_registry_row(editorial_status="machine_bootstrap")
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "source_editions.csv"
            with path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(row))
                writer.writeheader()
                writer.writerow(row)

            row_count, paper_count, errors = validate_source_edition_registry(path)

        self.assertEqual((row_count, paper_count), (1, 1))
        self.assertTrue(any("human_edited_published" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
