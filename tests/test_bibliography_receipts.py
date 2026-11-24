"""Synthetic receipt fixtures, never corpus or human review input."""
import csv
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from scripts.validate_bibliography_receipts import validate_receipt, validate_receipts


class BibliographyReceiptTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.raw = b'Header\r\nExample Press 1898 edition\r\nFooter\r\n'
        (self.root / 'raw.txt').write_bytes(self.raw)
        self.receipt = dict(source_id='synthetic-test', evidence_kind='provider_archived_production_credit',
                            source_url='https://example.org/credit', resolved_url='https://example.org/credit',
                            retrieved_at='2026-11-11T00:00:00+00:00', raw_path='raw.txt',
                            raw_bytes=len(self.raw), raw_sha256=hashlib.sha256(self.raw).hexdigest(),
                            credited_edition_year='1898', credited_publisher='Example Press',
                            credit_line_start=2, credit_line_end=2,
                            credit_text='Example Press 1898 edition', limitations='Synthetic test only')
        self.row = dict(source_id='synthetic-test', historical_publication_date='1898',
                        historical_publication_date_kind='edition',
                        historical_publication_source_url='https://example.org/credit',
                        historical_publication_citation='Synthetic fixture',
                        historical_publication_receipt_path='receipt.json')

    def errors(self, **changes):
        path = self.root / 'receipt.json'
        path.write_text(json.dumps({**self.receipt, **changes}))
        return validate_receipt(path, [self.row], self.root)

    def test_valid_receipt_with_crlf_source(self):
        self.assertEqual(self.errors(), [])

    def test_missing_or_changed_cache(self):
        (self.root / 'raw.txt').write_bytes(self.raw.replace(b'1898', b'1899'))
        self.assertIn('raw_sha256 mismatch', self.errors()[0])
        (self.root / 'raw.txt').unlink()
        self.assertTrue(self.errors())

    def test_rejects_receipt_drift(self):
        for changes in (
            {'raw_bytes': 0}, {'raw_sha256': 'bad'}, {'credit_line_start': 0},
            {'credit_line_end': 100}, {'credit_line_start': True},
            {'credit_line_start': 3, 'credit_line_end': 2},
            {'credit_text': 'invented credit'}, {'credited_publisher': 'Other Press'},
            {'source_id': 'unknown'}, {'credited_edition_year': '1899'},
            {'source_url': 'https://example.org/other'}, {'raw_path': '../outside.txt'},
            {'retrieved_at': '2026-11-11T00:00:00'}, {'limitations': ''},
            {'resolved_url': 'file:///tmp/source'}, {'evidence_kind': 'physical_scan'},
        ):
            with self.subTest(changes=changes):
                self.assertTrue(self.errors(**changes))

    def test_rejects_registry_drift(self):
        for field in ('historical_publication_date', 'historical_publication_date_kind',
                      'historical_publication_source_url', 'historical_publication_citation'):
            original = self.row[field]
            self.row[field] = ''
            with self.subTest(field=field):
                self.assertTrue(self.errors())
            self.row[field] = original

    def test_malformed_receipt_fails_closed(self):
        path = self.root / 'receipt.json'
        for value in ('{', '[]', '{}'):
            path.write_text(value)
            self.assertTrue(validate_receipt(path, [self.row], self.root))

    def title_page_fixture(self):
        self.raw = b'Title\r\nTranslated by Example Translator\r\n1898\r\n'
        (self.root / 'raw.txt').write_bytes(self.raw)
        self.receipt.update(evidence_kind='provider_transcribed_title_page',
                            credited_publisher='', credited_translator='Example Translator',
                            download_url='https://example.org/text',
                            raw_bytes=len(self.raw), raw_sha256=hashlib.sha256(self.raw).hexdigest(),
                            credit_line_start=2, credit_line_end=3,
                            credit_text='Translated by Example Translator\n1898')
        del self.receipt['resolved_url']  # Legacy fetcher did not record redirect URLs.
        self.row.update(translator='Example Translator', download_url='https://example.org/text')
        directory = self.root / 'data/raw'
        directory.mkdir(parents=True)
        download = dict(source_id=self.receipt['source_id'], download_url=self.receipt['download_url'],
                        raw_path='raw.txt', sha256=self.receipt['raw_sha256'],
                        retrieved_at_utc=self.receipt['retrieved_at'])
        with (directory / 'translation_downloads.csv').open('w', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=download.keys())
            writer.writeheader()
            writer.writerow(download)

    def test_title_page_allows_unknown_publisher(self):
        self.title_page_fixture()
        self.assertEqual(self.errors(), [])

    def test_title_page_rejects_provenance_drift(self):
        self.title_page_fixture()
        for changes in (
            {'credited_translator': 'Other Translator'}, {'credited_publisher': 'Invented Press'},
            {'download_url': 'https://example.org/other'}, {'credit_line_end': 2},
            {'retrieved_at': '2026-11-12T00:00:00+00:00'}, {'raw_sha256': 'bad'},
            {'credited_publisher': None}, {'credited_translator': ''},
        ):
            with self.subTest(changes=changes):
                self.assertTrue(self.errors(**changes))
        self.row['translator'] = 'Other Translator'
        self.assertTrue(self.errors(credited_translator='Other Translator'))

    def test_title_page_requires_download_manifest(self):
        self.title_page_fixture()
        (self.root / 'data/raw/translation_downloads.csv').unlink()
        self.assertTrue(self.errors())


class BibliographyCoverageTests(unittest.TestCase):
    def setUp(self):
        BibliographyReceiptTests.setUp(self)
        directory = self.root / 'data/bibliography'
        directory.mkdir(parents=True)
        self.row['historical_publication_receipt_path'] = 'data/bibliography/edition.json'
        self.path = directory / 'edition.json'
        self.path.write_text(json.dumps(self.receipt))

    def test_missing_linked_receipt_does_not_silently_disappear(self):
        second = {**self.row, 'source_id': 'second',
                  'historical_publication_receipt_path': 'data/bibliography/second.json'}
        other = self.root / second['historical_publication_receipt_path']
        other.write_text(json.dumps({**self.receipt, 'source_id': 'second'}))
        self.assertEqual(validate_receipts(self.root, [self.row, second]), (2, []))
        self.path.unlink()
        count, errors = validate_receipts(self.root, [self.row, second])
        self.assertEqual(count, 2)
        self.assertTrue(any('edition.json' in error for error in errors))

    def test_historical_date_requires_explicit_link(self):
        del self.row['historical_publication_receipt_path']
        self.assertTrue(validate_receipts(self.root, [self.row])[1])

    def test_wrong_source_link_is_rejected(self):
        second = {**self.row, 'source_id': 'second'}
        self.assertTrue(validate_receipts(self.root, [self.row, second])[1])

    def test_unsafe_links_are_rejected(self):
        for link in ('../outside.json', '/tmp/outside.json', 'data/bibliography/file.txt'):
            with self.subTest(link=link):
                self.row['historical_publication_receipt_path'] = link
                self.assertTrue(validate_receipts(self.root, [self.row])[1])

    def test_discovered_unlinked_receipt_is_rejected(self):
        extra = self.path.with_name('extra.json')
        extra.write_text(json.dumps(self.receipt))
        self.assertTrue(validate_receipts(self.root, [self.row])[1])
