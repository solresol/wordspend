import csv
import tempfile
import unittest
from pathlib import Path

from scripts.validate_translation_sources import validate_registry


ROOT = Path(__file__).resolve().parents[1]


class TranslationDateTests(unittest.TestCase):
    def setUp(self):
        with (ROOT / 'data/translation_sources.csv').open(newline='') as handle:
            self.row = next(r for r in csv.DictReader(handle)
                            if r['source_id'] == 'homer-iliad-en-pope-pg6130')

    def errors(self, **changes):
        row = {**self.row, **changes}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'registry.csv'
            with path.open('w', newline='') as handle:
                writer = csv.DictWriter(handle, fieldnames=list(row))
                writer.writeheader()
                writer.writerow(row)
            return validate_registry(path)[2]

    def test_year_and_full_date_preserve_provider_date(self):
        self.assertEqual(self.row['historical_publication_date'], '1899')
        self.assertEqual(self.row['provider_release_date'], '2004-07-01')
        for value in ('1899', '1899-06-15', ''):
            with self.subTest(value=value):
                self.assertEqual(self.errors(historical_publication_date=value), [])

    def test_rejects_malformed_or_impossible_historical_dates(self):
        for value in ('0000', '1899-02-29', '1899-13-01', '1899?', '1899-1900'):
            with self.subTest(value=value):
                self.assertTrue(self.errors(historical_publication_date=value))

    def test_requires_citation_url_and_edition_scope(self):
        for changes in (
            {'historical_publication_source_url': ''},
            {'historical_publication_source_url': 'not-a-url'},
            {'historical_publication_citation': '  '},
            {'historical_publication_date_kind': ''},
            {'historical_publication_date_kind': 'translation_first_publication'},
            {'publication_date': '1899-01-01'},
        ):
            with self.subTest(changes=changes):
                self.assertTrue(self.errors(**changes))
