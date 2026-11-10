"""Synthetic receipt fixtures, never corpus or human review input."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from scripts.validate_bibliography_receipts import validate_receipt


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
                        historical_publication_citation='Synthetic fixture')

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
