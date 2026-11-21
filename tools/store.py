"""Transactional SQLite staging, audited review corrections, and reviewed-only export."""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from book_model import SCHEMA, canonical, fingerprint

TABLES = (
    'CREATE TABLE IF NOT EXISTS edition (one INTEGER PRIMARY KEY CHECK(one=1), schema_version INTEGER NOT NULL, manifest_sha TEXT NOT NULL, pdf_sha TEXT NOT NULL, manifest TEXT NOT NULL)',
    'CREATE TABLE IF NOT EXISTS chapters (id TEXT PRIMARY KEY, position INTEGER UNIQUE NOT NULL, title TEXT NOT NULL)',
    'CREATE TABLE IF NOT EXISTS topics (id TEXT PRIMARY KEY, chapter_id TEXT NOT NULL REFERENCES chapters, position INTEGER NOT NULL, title TEXT NOT NULL, printed_start INTEGER NOT NULL, printed_end INTEGER NOT NULL, UNIQUE(chapter_id, position))',
    '''CREATE TABLE IF NOT EXISTS entries (
      id TEXT PRIMARY KEY, topic_id TEXT NOT NULL REFERENCES topics, kind TEXT NOT NULL CHECK (kind IN ('ayah','hadith')),
      position INTEGER NOT NULL, quran_ref TEXT, hadith_number INTEGER, sequence_id TEXT,
      UNIQUE(topic_id, position), UNIQUE(sequence_id, hadith_number),
      CHECK ((kind='ayah' AND quran_ref IS NOT NULL AND hadith_number IS NULL AND sequence_id IS NULL)
         OR (kind='hadith' AND quran_ref IS NULL AND hadith_number IS NOT NULL AND sequence_id IS NOT NULL)))''',
    '''CREATE TABLE IF NOT EXISTS import_runs (
      run_sha TEXT PRIMARY KEY, input TEXT NOT NULL, report TEXT NOT NULL,
      imported_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')))''',
    '''CREATE TABLE IF NOT EXISTS draft_history (
      entry_id TEXT NOT NULL REFERENCES entries, sha TEXT NOT NULL, run_sha TEXT NOT NULL REFERENCES import_runs,
      payload TEXT NOT NULL CHECK(json_valid(payload)), PRIMARY KEY(entry_id,sha))''',
    '''CREATE TABLE IF NOT EXISTS drafts (
      entry_id TEXT PRIMARY KEY REFERENCES entries, sha TEXT NOT NULL,
      status TEXT NOT NULL CHECK(status IN ('draft','unresolved')),
      FOREIGN KEY(entry_id,sha) REFERENCES draft_history(entry_id,sha))''',
    '''CREATE TABLE IF NOT EXISTS review_history (
      entry_id TEXT NOT NULL REFERENCES entries, revision INTEGER NOT NULL, reviewer TEXT NOT NULL,
      payload TEXT NOT NULL CHECK(json_valid(payload)), reviewed_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
      based_on_draft TEXT,
      PRIMARY KEY(entry_id,revision))''',
    '''CREATE TABLE IF NOT EXISTS reviews (
      entry_id TEXT PRIMARY KEY REFERENCES entries, revision INTEGER NOT NULL,
      FOREIGN KEY(entry_id,revision) REFERENCES review_history(entry_id,revision))''',
)


@contextmanager
def session(path, book, *, dry_run=False, require_existing=False):
    path = Path(path)
    if require_existing and not path.is_file():
        raise ValueError(f'Database not found: {path}')
    if dry_run or require_existing:
        db = sqlite3.connect(':memory:') if dry_run else sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(path, timeout=15)
    try:
        if dry_run and path.is_file():
            existing = sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True)
            try:
                existing.backup(db)
            finally:
                existing.close()
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        db.execute('BEGIN' if require_existing else 'BEGIN IMMEDIATE')
        tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
        if (tables and 'edition' not in tables) or (require_existing and 'edition' not in tables):
            raise ValueError('Use a dedicated database created with this tool; no existing database was modified.')
        if not require_existing:
            for stmt in TABLES:
                db.execute(stmt)
        saved = db.execute('SELECT schema_version, manifest_sha, pdf_sha FROM edition WHERE one=1').fetchone()
        if saved and tuple(saved) != (SCHEMA, book.manifest_sha, book.pdf_sha):
            raise ValueError('Database and this index/edition do not match. Use the original index or a new staging database.')
        if not saved and require_existing:
            raise ValueError('Database does not have an edition inventory')
        if not saved:
            seed(db, book)
        yield db
        db.commit()
    except BaseException:
        db.rollback()
        raise
    finally:
        db.close()


def seed(db, book):
    db.execute('INSERT INTO edition VALUES(1,?,?,?,?)', (SCHEMA,book.manifest_sha,book.pdf_sha,canonical(book.value)))
    db.executemany('INSERT INTO chapters VALUES(?,?,?)', [(c['id'],c['position'],c['title']) for c in book.chapters.values()])
    db.executemany('INSERT INTO topics VALUES(?,?,?,?,?,?)', [(t['id'],c['id'],t['position'],t['title'],*book.page_range(t)[:2]) for c,t in book.topics.values()])
    db.executemany('INSERT INTO entries VALUES(?,?,?,?,?,?,?)', [(e.id,e.topic_id,e.kind,e.position,e.reference,e.number,e.sequence) for e in book.entries.values()])


def check_header(data, book, field):
    if not isinstance(data, dict) or data.get('schema_version') != SCHEMA or data.get('manifest_sha256') != book.manifest_sha or data.get('pdf_sha256') != book.pdf_sha:
        raise ValueError('Input schema or edition checksum does not match the index')
    if not isinstance(data.get(field), list):
        raise ValueError(f'Input must include a {field} array')


def check_pages(book, entry, start, end):
    low, high, _ = book.page_range(book.topics[entry.topic_id][1])
    if type(start) is not int or type(end) is not int or not (low <= start <= end <= high):
        raise ValueError(f'{entry.id}: printed page bounds must be inside topic span {low}–{high}')


def check_fields(record, fields, identifier):
    for key in fields:
        value = record.get(key)
        if value is not None and (not isinstance(value,str) or not value.strip() or len(value) > 100_000 or '\0' in value):
            raise ValueError(f'{identifier}: invalid {key} text')


def validate_bundle(bundle, book):
    check_header(bundle, book, 'records')
    ids = bundle['topic_ids']
    if not isinstance(ids, list) or not ids or any(not isinstance(t,str) for t in ids) or len(set(ids)) != len(ids):
        raise ValueError('Run must declare its topic scope without duplicates')
    needed = {e.id for t in book.scope(ids) for e in book.by_topic[t]}
    seen = set()
    for r in bundle['records']:
        entry = book.entries.get(r['id'])
        if not entry or r['id'] not in needed or r['id'] in seen or (entry.topic_id,entry.kind) != (r['topic_id'],r['kind']):
            raise ValueError(f'Unexpected, duplicate, or mismapped record: {r["id"]}')
        seen.add(entry.id)
        check_fields(r, ('english','arabic','notes'), entry.id)
        source = r['source']
        a,b = source['start'],source['end']
        check_pages(book, entry,a['printed_page'],b['printed_page'])
        if a != book.locator(a['printed_page']) or b != book.locator(b['printed_page']):
            raise ValueError(f'{entry.id}: source locator does not match the scanned edition')
        statuses = {'draft':'candidate','unresolved':'window'}
        if r.get('status') not in statuses or source.get('type') != statuses[r['status']]:
            raise ValueError(f'{entry.id}: import only accepts OCR drafts and unresolved windows')
        has_text = bool(r.get('english') or r.get('arabic'))
        if (r['status'] == 'draft') != has_text:
            raise ValueError(f'{entry.id}: draft must have text; unresolved entries must not')
        if not isinstance(r.get('flags'), list) or any(not isinstance(f,str) for f in r['flags']):
            raise ValueError(f'{entry.id}: flags must be an array of strings')
    if seen != needed:
        raise ValueError(f'Extraction file is incomplete: {len(needed - seen)} missing record(s) in declared scope; rerun extraction')


def apply_bundle(db, bundle, book):
    validate_bundle(bundle, book)
    sha = fingerprint(bundle)
    stats = dict(inserted=0, updated=0, unchanged=0, kept_better_draft=0, reviewed_untouched=0, run_sha256=sha)
    reviewed = {row[0] for row in db.execute('SELECT entry_id FROM reviews')}
    stats['reviewed_untouched'] = sum(r['id'] in reviewed for r in bundle['records'])
    if db.execute('SELECT 1 FROM import_runs WHERE run_sha=?',(sha,)).fetchone():
        stats['unchanged'] = len(bundle['records'])
        stats['already_imported'] = True
        return stats
    info = {key:value for key,value in bundle.items() if key not in ('records','report')}
    db.execute('INSERT INTO import_runs(run_sha,input,report) VALUES(?,?,?)', (sha,canonical(info),canonical(bundle.get('report',{}))))
    for r in bundle['records']:
        identifier, rhash = r['id'], fingerprint(r)
        previous = db.execute('''SELECT d.sha,h.payload FROM drafts d JOIN draft_history h
                              ON d.entry_id=h.entry_id AND d.sha=h.sha WHERE d.entry_id=?''',(identifier,)).fetchone()
        if previous and previous['sha']==rhash:
            stats['unchanged'] += 1
            continue
        db.execute('INSERT OR IGNORE INTO draft_history(entry_id,sha,run_sha,payload) VALUES(?,?,?,?)',(identifier,rhash,sha,canonical(r)))
        if previous:
            old = json.loads(previous['payload'])
            if any(old.get(lang) and not r.get(lang) for lang in ('english','arabic')):
                stats['kept_better_draft'] += 1
                continue
        db.execute('''INSERT INTO drafts(entry_id,sha,status) VALUES(?,?,?)
                   ON CONFLICT(entry_id) DO UPDATE SET sha=excluded.sha,status=excluded.status''', (identifier,rhash,r['status']))
        stats['updated' if previous else 'inserted'] += 1
    return stats


def draft_records(db):
    return {r['entry_id']:(json.loads(r['payload']),r['sha']) for r in db.execute('''
      SELECT d.entry_id,h.payload,d.sha FROM drafts d JOIN draft_history h ON h.entry_id=d.entry_id AND h.sha=d.sha''')}


def reviewer_records(db):
    return {r['entry_id']:(json.loads(r['payload']),r['revision'],r['reviewer']) for r in db.execute('''
      SELECT r.entry_id,h.payload,r.revision,h.reviewer FROM reviews r JOIN review_history h ON h.entry_id=r.entry_id AND h.revision=r.revision''')}


def review_sheet(db, book, topic_ids, unresolved_only=False):
    draft, reviewed = draft_records(db), reviewer_records(db)
    rows = []
    for tid in book.scope(topic_ids):
        for entry in book.by_topic[tid]:
            evidence, sha = draft.get(entry.id, (None,None))
            chosen, revision, _ = reviewed.get(entry.id, (None,0,None))
            if unresolved_only and (chosen or (evidence and evidence['status'] == 'draft')):
                continue
            data = chosen or {}
            pages = book.page_range(book.topics[tid][1])[:2]
            rows.append({
                'id':entry.id, 'topic_id':tid, 'reference':entry.reference, 'hadith_number':entry.number,
                'decision':None, 'base_revision':revision, 'based_on_draft':sha,
                # Candidates are side-by-side, not pre-filled into publishable text fields.
                'printed_start':data.get('printed_start'), 'printed_end':data.get('printed_end'),
                'english':data.get('english'), 'arabic':data.get('arabic'), 'notes':data.get('notes'),
                'citation':data.get('citation'), 'excerpt':data.get('excerpt',False),
                'suggested':evidence or {'status':'not_extracted','source':{'start':book.locator(pages[0]),'end':book.locator(pages[1])}},
            })
    return {'schema_version':SCHEMA,'manifest_sha256':book.manifest_sha,'pdf_sha256':book.pdf_sha,
            'reviewer':None,'reviews':rows}


def apply_reviews(db, data, book):
    check_header(data,book,'reviews')
    accepted = [row for row in data['reviews'] if row.get('decision')=='accept']
    if any(row.get('decision') not in (None,'accept','skip') for row in data['reviews']):
        raise ValueError('Review decision must be null, skip, or accept')
    reviewer = data.get('reviewer')
    if accepted and (not isinstance(reviewer,str) or not (0<len(reviewer.strip())<=120)):
        raise ValueError('Supply a reviewer name before accepting records')
    stats = dict(accepted=0, unchanged=0, skipped=len(data['reviews'])-len(accepted))
    current = reviewer_records(db)
    seen = set()
    for row in accepted:
        identifier = row['id']
        entry = book.entries.get(identifier)
        if not entry or identifier in seen:
            raise ValueError(f'Unknown or repeated approved entry: {identifier}')
        seen.add(identifier)
        check_fields(row, ('english','arabic','notes','citation'), identifier)
        if not (row.get('english') or row.get('arabic')):
            raise ValueError(f'{identifier}: at least one corrected language is required')
        check_pages(book, entry,row.get('printed_start'),row.get('printed_end'))
        excerpt = row.get('excerpt',False)
        if type(excerpt) is not bool or excerpt and entry.kind != 'ayah':
            raise ValueError(f'{identifier}: only Qur’an passages can be marked as excerpts')
        value = {key:row.get(key) for key in ('printed_start','printed_end','english','arabic','notes','citation')}
        value['excerpt'] = excerpt
        old, revision, author = current.get(identifier,(None,0,None))
        if old==value and author==reviewer.strip():
            stats['unchanged'] += 1
            continue
        if type(row.get('base_revision')) is not int or row['base_revision'] != revision:
            raise ValueError(f'{identifier}: stale review sheet (current revision {revision}); export it again')
        draft_sha = row.get('based_on_draft')
        if draft_sha is not None and not db.execute('SELECT 1 FROM draft_history WHERE entry_id=? AND sha=?',(identifier,draft_sha)).fetchone():
            raise ValueError(f'{identifier}: missing OCR evidence referenced by this review')
        db.execute('INSERT INTO review_history(entry_id,revision,reviewer,payload,based_on_draft) VALUES(?,?,?,?,?)',
                   (identifier,revision+1,reviewer.strip(),canonical(value),draft_sha))
        db.execute('INSERT INTO reviews(entry_id,revision) VALUES(?,?) ON CONFLICT(entry_id) DO UPDATE SET revision=excluded.revision',
                   (identifier,revision+1))
        stats['accepted'] += 1
    return stats


def export_reader(db, book):
    reviewed = reviewer_records(db)
    locators = {}
    for identifier, (draft, _) in draft_records(db).items():
        if identifier not in reviewed:
            source = draft['source']
            locators[identifier] = [source['start']['printed_page'], source['end']['printed_page'], source['type']]
    return {'schema_version':SCHEMA,'manifest_sha256':book.manifest_sha,'pdf_sha256':book.pdf_sha,
            'locators':locators,
            'records':[{'id':e.id,'topic_id':e.topic_id,'kind':e.kind,'status':'reviewed',**reviewed[e.id][0]}
                       for e in book.entries.values() if e.id in reviewed]}


def report(db, book):
    drafts = draft_records(db)
    reviewed = reviewer_records(db)
    result = {}
    status = lambda e: drafts.get(e.id, ({},None))[0].get('status')
    for tid, (_,topic) in book.topics.items():
        vals = book.by_topic[tid]
        result[tid] = {'title':topic['title'], **{k:{'expected':len(entries),
            'draft':sum(status(e)=='draft' for e in entries), 'unresolved':sum(status(e)=='unresolved' for e in entries),
            'not_extracted':sum(status(e) is None for e in entries), 'reviewed':sum(e.id in reviewed for e in entries)}
            for k in ('ayah','hadith') for entries in ([e for e in vals if e.kind==k],)}}
    return {'counts':{k:{key:sum(x[k][key] for x in result.values())
                        for key in ('expected','draft','unresolved','not_extracted','reviewed')} for k in ('ayah','hadith')},
            'topics':result}
