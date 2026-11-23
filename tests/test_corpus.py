from pathlib import Path
from tempfile import TemporaryDirectory
import sys
import unittest

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))

from book_model import Book, load_json, fingerprint
import corpus
import store

BOOK = Book(load_json(ROOT / 'data/book-index.json'))
CORPUS = ROOT / 'data' / 'corpus.yaml'


def fresh_corpus(book=BOOK):
    return corpus.render_corpus(book, corpus.inventory_rows(book))


class CorpusFileTests(unittest.TestCase):
    def test_committed_corpus_matches_edition_inventory(self):
        self.assertTrue(corpus.check_corpus_file(CORPUS, BOOK))

    def test_committed_corpus_has_no_text_yet(self):
        # Nothing ships until the editor supplies translations.
        with CORPUS.open(encoding='utf-8') as handle:
            data = yaml.safe_load(handle)
        self.assertEqual(len(data['entries']), 1721)
        for row in data['entries']:
            self.assertIsNone(row['arabic'])
            self.assertIsNone(row['english'])
            self.assertIsNone(row['urdu'])
            self.assertEqual(row['status'], 'pending')


class CorpusValidationTests(unittest.TestCase):
    def setUp(self):
        self.data = yaml.safe_load(fresh_corpus())

    def test_blank_inventory_has_nothing_to_stage(self):
        filled, pending = corpus.validate_corpus(self.data, BOOK)
        self.assertEqual(filled, [])
        self.assertEqual(pending, 1721)

    def test_tampered_reference_refused(self):
        self.data['entries'][0]['reference'] = '1:1'
        with self.assertRaisesRegex(ValueError, 'reference'):
            corpus.validate_corpus(self.data, BOOK)

    def test_unknown_id_refused(self):
        self.data['entries'][0]['id'] = 'ayah:nowhere:1'
        with self.assertRaisesRegex(ValueError, 'unknown entry id'):
            corpus.validate_corpus(self.data, BOOK)

    def test_missing_entries_refused(self):
        self.data['entries'].pop()
        with self.assertRaisesRegex(ValueError, 'missing'):
            corpus.validate_corpus(self.data, BOOK)

    def test_mismatched_fingerprint_pin_refused(self):
        self.data['manifest_sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'different edition'):
            corpus.validate_corpus(self.data, BOOK)

    def test_excerpt_only_on_ayat(self):
        target = next(row for row in self.data['entries'] if row['kind'] == 'hadith')
        target['excerpt'] = True
        with self.assertRaisesRegex(ValueError, 'excerpt'):
            corpus.validate_corpus(self.data, BOOK)

    def test_scan_pages_must_be_paired_and_inside_topic(self):
        self.data['entries'][0]['printed_start'] = 1
        with self.assertRaisesRegex(ValueError, 'together'):
            corpus.validate_corpus(self.data, BOOK)
        self.data['entries'][0]['printed_end'] = 999
        with self.assertRaisesRegex(ValueError, 'topic span'):
            corpus.validate_corpus(self.data, BOOK)


class CorpusMergeTests(unittest.TestCase):
    def test_merge_preserves_hand_entered_text(self):
        with TemporaryDirectory() as temp:
            path = Path(temp) / 'corpus.yaml'
            data = yaml.safe_load(fresh_corpus())
            data['entries'][0]['urdu'] = 'متن محفوظ رہنا چاہیے'
            data['entries'][0]['english'] = 'Hand-entered text must survive.'
            data['entries'][0]['status'] = 'provided'
            data['entries'][0]['printed_start'] = 1
            data['entries'][0]['printed_end'] = 2
            path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding='utf-8')
            merged, provided = corpus.merge_corpus(BOOK, path)
            self.assertEqual(provided, 1)
            first = merged[0]
            self.assertEqual(first['urdu'], 'متن محفوظ رہنا چاہیے')
            self.assertEqual(first['english'], 'Hand-entered text must survive.')
            self.assertEqual(first['status'], 'provided')
            self.assertEqual((first['printed_start'], first['printed_end']), (1, 2))

    def test_merge_refuses_drifted_file(self):
        with TemporaryDirectory() as temp:
            path = Path(temp) / 'corpus.yaml'
            data = yaml.safe_load(fresh_corpus())
            data['entries'][0], data['entries'][1] = data['entries'][1], data['entries'][0]
            path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'Cannot merge'):
                corpus.merge_corpus(BOOK, path)


class UrdlRoundTripTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db_path = Path(self.temp.name) / 'staging.sqlite'

    def test_urdu_translation_flows_to_export(self):
        data = yaml.safe_load(fresh_corpus())
        target = data['entries'][0]
        target['urdu'] = ' مصنوعی جانچ — اصل متن نہیں'
        target['english'] = 'Synthetic probe — not a translation.'
        target['status'] = 'provided'
        with store.session(self.db_path, BOOK) as db:
            rows = corpus.review_rows(data, BOOK, {})
            self.assertEqual(len(rows), 1)
            self.assertIsNone(rows[0]['printed_start'])  # no invented page span
            sheet = {'schema_version': 1, 'manifest_sha256': BOOK.manifest_sha, 'pdf_sha256': BOOK.pdf_sha,
                     'reviewer': 'Synthetic Probe', 'reviews': rows}
            self.assertEqual(store.apply_reviews(db, sheet, BOOK)['accepted'], 1)
            out = store.export_reader(db, BOOK)
        (record,) = out['records']
        self.assertEqual(record['id'], target['id'])
        self.assertEqual(record['urdu'], target['urdu'])
        self.assertEqual(record['english'], target['english'])
        self.assertIsNone(record['printed_start'])
        self.assertEqual(out['locators'], {})

    def test_partial_scan_span_rejected_but_none_allowed(self):
        identifier = 'ayah:kalimah-tayyibah.iman:1'
        base = {'schema_version': 1, 'manifest_sha256': BOOK.manifest_sha, 'pdf_sha256': BOOK.pdf_sha,
                'reviewer': 'Synthetic Probe', 'reviews': [
                    {'id': identifier, 'base_revision': 0, 'decision': 'accept',
                     'printed_start': 1, 'printed_end': None, 'urdu': 'مصنوعی جانچ'}]}
        with store.session(self.db_path, BOOK) as db:
            with self.assertRaisesRegex(ValueError, 'page bounds'):
                store.apply_reviews(db, base, BOOK)
        with store.session(self.db_path, BOOK) as db:
            base['reviews'][0]['printed_start'] = None
            self.assertEqual(store.apply_reviews(db, base, BOOK)['accepted'], 1)
            payload = store.reviewer_records(db)[identifier][0]
            self.assertEqual(payload['urdu'], 'مصنوعی جانچ')
            self.assertIsNone(payload['printed_start'])


if __name__ == '__main__':
    unittest.main()
