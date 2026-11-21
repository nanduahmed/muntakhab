from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import sys
import unittest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))
from book_model import Book, load_json
from booktool import tally
from ocr_engine import Line, parse_tsv
from segment import extract_hadith, extract_verses, hadith_candidates, make_record
import store

BOOK = Book(load_json(ROOT / 'data/book-index.json'))
IMAN = 'kalimah-tayyibah.iman'
WUDU = 'salah.virtues-of-wudu'


def line(page, y, text, conf=93, x0=.08, x1=.92):
    return Line(page, text, x0, y, x1, y+.015, conf)


def bundle(topic_id=IMAN):
    start, end, _ = BOOK.page_range(BOOK.topics[topic_id][1])
    entries = BOOK.by_topic[topic_id]
    data = [make_record(e,BOOK,(start,end),status='unresolved') for e in entries]
    data[0] = make_record(entries[0],BOOK,(start,start),[line(start,.31,'An OCR suggestion')],
                          [line(start,.33,'النص المقترح')])
    return {'schema_version':1,'manifest_sha256':BOOK.manifest_sha,'pdf_sha256':BOOK.pdf_sha,
            'topic_ids':[topic_id],'records':data,'report':tally(data)}


class IndexAndSegmentationTests(unittest.TestCase):
    def test_complete_expected_inventory(self):
        self.assertEqual(len(BOOK.entries),1721)
        self.assertEqual(len(BOOK.topics),29)
        self.assertNotEqual(BOOK.entries['hadith:ilm:1'].topic_id, BOOK.entries['hadith:dhikr:1'].topic_id)
        self.assertEqual(BOOK.value['totals']['counts'],{'ayat':398,'ayah_passages':214,'ahadith':1507})
        self.assertFalse(BOOK.topics['ikhlas.promises-and-rewards'][1]['quran_references'])

    def test_odd_even_spread_map(self):
        self.assertEqual(BOOK.locator(1)['side'],'left')
        self.assertEqual(BOOK.locator(2)['side'],'right')
        self.assertEqual(BOOK.locator(1)['flipbook_url'].split('#')[1],'20-21')
        self.assertEqual(BOOK.locator(3)['pdf_page'],12)
        self.assertEqual(BOOK.locator(671)['pdf_page'],346)

    def test_tsv_running_head_filter_and_coordinates(self):
        header = 'level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n'
        data = '5\t1\t1\t1\t1\t1\t5\t10\t15\t9\t90\tHeading\n5\t1\t2\t1\t1\t1\t100\t220\t80\t20\t94\tIn\n5\t1\t2\t1\t1\t2\t192\t219\t156\t23\t88\torder\n'
        rows = parse_tsv(header+data, 3, 500, 600)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0].text,'In order')
        self.assertAlmostEqual(rows[0].x0,.2)
        self.assertAlmostEqual(rows[0].confidence,91)

    def test_verse_joined_reference_continues_on_next_page(self):
        e = BOOK.entries['ayah:ikram-ul-muslim.rights-of-muslims:2']
        intro = [line(424,.85,'Allāh says:'),line(424,.91,'O you who believe!'),line(425,.08,'Do not mock others.'),
                 line(425,.11,'Al-Hujurat 49:'),line(425,.135,'11–13')]
        verses,_=extract_verses(BOOK,[e],424,426,[],[line(424,.9,'يَا أَيُّهَا الَّذِينَ آمَنُوا')],intro,.7)
        result=verses[0]
        self.assertEqual(result['status'],'draft')
        self.assertIn('Do not mock',result['english'])
        self.assertEqual(result['source']['start']['printed_page'],424)
        self.assertEqual(result['source']['end']['printed_page'],425)

    def test_ref_ocr_colon_normalization_and_leading_zero(self):
        e=BOOK.entries['ayah:ikram-ul-muslim.warning-against-harm:2']
        lines=[line(488,.571,'Allah says:'),line(488,.615,'Woe to those who give less in measure.'),line(488,.9,'Al-Mutaffifin 83: 01:6')]
        q,_=extract_verses(BOOK,[e],488,489,lines,[],lines,.3)
        self.assertEqual(q[0]['status'],'draft')
        self.assertIn('ocr_reference_separator_normalized',q[0]['flags'])

    def test_embedded_ayah_does_not_become_opening_passage(self):
        e=BOOK.entries['ayah:ikram-ul-muslim.warning-against-harm:2']
        lines=[line(489,.3,'AHADITH'),line(489,.7,'And he recited 83:1–6')]
        result,_=extract_verses(BOOK,[e],488,489,lines,[],lines,.3)
        self.assertEqual(result[0]['status'],'unresolved')
        self.assertIsNone(result[0]['english'])

    def test_hadith_with_continuation_and_numbered_notes(self):
        entries=BOOK.by_topic[WUDU][2:4]
        en=[line(225,.66,'AHADITH'),line(225,.87,'243. Abu Malik narrates that he said'),
            line(225,.96,'This narrative'),line(226,.09,'continues on the next printed page.'),
            line(226,.115,'Note: 1. Editorial notes here'),line(226,.135,'2. This is not the next narration.'),
            line(226,.65,'244. Abu Hurairah narrates that he said'),line(226,.68,'This is the next narration.')]
        ar=[line(225,.77,'عن أبي مالك الأشعري'),line(226,.57,'عن أبي هريرة رضي الله عنه')]
        rows=extract_hadith(BOOK,entries,225,226,en,ar,None,en[0])
        self.assertEqual([r['id'] for r in rows],['hadith:salah:243','hadith:salah:244'])
        self.assertIn('continues',rows[0]['english'])
        self.assertNotIn('Editorial notes',rows[0]['english'])
        self.assertIn('Editorial notes',rows[0]['notes'])
        self.assertEqual(rows[0]['source']['end']['printed_page'],226)
        self.assertIn('الأشعري',rows[0]['arabic'])
        self.assertIn('هريرة',rows[1]['arabic'])

    def test_ocr_number_with_leading_punctuation(self):
        ids=[BOOK.entries['hadith:dhikr:212']]
        a=list(hadith_candidates([line(363,.836,'-212. Buraidah Radiyallahu ‘anhu narrates')],ids,363))
        self.assertEqual(a[0].order,0)


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'staging.sqlite'
        self.data = bundle()

    def test_dry_run_does_not_create_a_file(self):
        with store.session(self.path,BOOK,dry_run=True) as db:
            self.assertEqual(store.apply_bundle(db,self.data,BOOK)['inserted'],76)
        self.assertFalse(self.path.exists())

    def test_dry_run_existing_db_does_not_change_bytes(self):
        with store.session(self.path,BOOK): pass
        before=self.path.read_bytes()
        with store.session(self.path,BOOK,dry_run=True) as db:
            self.assertEqual(store.apply_bundle(db,self.data,BOOK)['inserted'],76)
        self.assertEqual(self.path.read_bytes(),before)

    def test_import_idempotent_and_incomplete_invalid(self):
        with store.session(self.path,BOOK) as db:
            self.assertEqual(store.apply_bundle(db,self.data,BOOK)['inserted'],76)
            again=store.apply_bundle(db,self.data,BOOK)
            self.assertTrue(again['already_imported'])
            bad=deepcopy(self.data); bad['records'].pop()
            with self.assertRaisesRegex(ValueError,'incomplete'):
                store.apply_bundle(db,bad,BOOK)
            self.assertEqual(db.execute('SELECT count(*) FROM import_runs').fetchone()[0],1)
        with store.session(self.path,BOOK,require_existing=True) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM entries').fetchone()[0],1721)

    def test_altered_edition_and_locator_refused(self):
        changed=deepcopy(self.data);changed['pdf_sha256']='a'*64
        with self.assertRaises(ValueError): store.validate_bundle(changed,BOOK)
        changed=deepcopy(self.data);changed['records'][0]['source']['start']['pdf_page']=1
        with self.assertRaisesRegex(ValueError,'locator'): store.validate_bundle(changed,BOOK)

    def test_weaker_ocr_never_removes_a_language(self):
        with store.session(self.path,BOOK) as db:
            store.apply_bundle(db,self.data,BOOK)
            changed=deepcopy(self.data);changed['records'][0]['arabic']=None
            self.assertEqual(store.apply_bundle(db,changed,BOOK)['kept_better_draft'],1)
            self.assertIsNotNone(store.draft_records(db)[self.data['records'][0]['id']][0]['arabic'])
            self.assertEqual(db.execute('SELECT count(*) FROM draft_history').fetchone()[0],77)

    def review(self):
        identifier=self.data['records'][0]['id']
        return {'schema_version':1,'manifest_sha256':BOOK.manifest_sha,'pdf_sha256':BOOK.pdf_sha,
                'reviewer':'Test reader','reviews':[{'id':identifier,'base_revision':0,'decision':'accept',
                   'printed_start':1,'printed_end':1,'english':'Checked against scan'}]}

    def test_changed_ocr_leaves_current_review_alone(self):
        with store.session(self.path,BOOK) as db:
            store.apply_bundle(db,self.data,BOOK)
            raw=store.export_reader(db,BOOK)
            self.assertEqual(raw['records'],[])
            self.assertNotIn('An OCR suggestion',json.dumps(raw))
            self.assertEqual(store.apply_reviews(db,self.review(),BOOK)['accepted'],1)
            changed=deepcopy(self.data);changed['records'][0]['english']='Different OCR suggestion'
            self.assertEqual(store.apply_bundle(db,changed,BOOK)['updated'],1)
            published=store.export_reader(db,BOOK)
            self.assertEqual(published['records'][0]['english'],'Checked against scan')
            self.assertNotIn('Different OCR suggestion',json.dumps(published))
            self.assertNotIn(self.data['records'][0]['id'],published['locators'])

    def test_stale_review_refused_and_revision_saved(self):
        with store.session(self.path,BOOK) as db:
            store.apply_reviews(db,self.review(),BOOK)
            revised=self.review(); revised['reviews'][0]['english']='Rechecked text'
            with self.assertRaisesRegex(ValueError,'stale'):
                store.apply_reviews(db,revised,BOOK)
            revised['reviews'][0]['base_revision']=1
            self.assertEqual(store.apply_reviews(db,revised,BOOK)['accepted'],1)
            self.assertEqual(db.execute('SELECT count(*) FROM review_history').fetchone()[0],2)
            self.assertEqual(store.apply_reviews(db,revised,BOOK)['unchanged'],1)

    def test_partial_review_sheet_is_atomic(self):
        valid=self.review(); invalid=deepcopy(valid['reviews'][0]); invalid['id']='ayah:kalimah-tayyibah.iman:2'; invalid['printed_start']=999
        valid['reviews'].append(invalid)
        with self.assertRaisesRegex(ValueError,'page bounds'):
            with store.session(self.path,BOOK) as db: store.apply_reviews(db,valid,BOOK)
        with store.session(self.path,BOOK) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM reviews').fetchone()[0],0)

    def test_review_sheet_does_not_prefill_unverified_text(self):
        with store.session(self.path,BOOK) as db:
            store.apply_bundle(db,self.data,BOOK)
            sheet=store.review_sheet(db,BOOK,[IMAN]); first=sheet['reviews'][0]
            self.assertIsNone(first['decision'])
            self.assertIsNone(first['english'])
            self.assertEqual(first['suggested']['english'],'An OCR suggestion')


if __name__ == '__main__':
    unittest.main()
