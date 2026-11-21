#!/usr/bin/env python3
"""Extract and maintain the Muntakhab Ahadith bilingual reading inventory."""
from __future__ import annotations

import argparse
import csv
import io
import sqlite3
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from book_model import BASE, SCHEMA, Book, atomic_text, load_json, write_json
from segment import apply_arabic_retry, missing_arabic_bands, segment_topic
import store


def tally(records):
    report = {}
    for kind in ('ayah','hadith'):
        found = [r for r in records if r['kind']==kind]
        report[kind] = {'expected':len(found),'draft':sum(r['status']=='draft' for r in found),
                        'unresolved':sum(r['status']=='unresolved' for r in found),
                        'english_candidates':sum(bool(r['english']) for r in found),
                        'arabic_candidates':sum(bool(r['arabic']) for r in found),
                        'bilingual_candidates':sum(bool(r['english'] and r['arabic']) for r in found)}
    return report


def extraction_plan(book, tids, with_arabic):
    tasks = {}
    for tid in tids:
        _,t = book.topics[tid]
        a,b,h = book.page_range(t)
        jobs = [(p,'eng','page') for p in range(a,b+1)]
        if t['quran_references']:
            jobs += [(p,'eng','verse-en') for p in range(a,h+1)]
            if with_arabic:
                jobs += [(p,'ara','verse-ar') for p in range(a,h+1)]
        if with_arabic:
            jobs += [(p,'ara','page') for p in range(h,b+1)]
        tasks[tid] = jobs
    return tasks


def extract(args, book):
    from ocr_engine import OCR
    if not 130 <= args.dpi <= 450 or not 1 <= args.workers <= 16:
        raise ValueError('Use 130–450 DPI and 1–16 workers')
    if args.pdf.resolve() == args.out.resolve():
        raise ValueError('Output must not overwrite the source PDF')
    hint_file = args.anchors or BASE/'data/scan-anchor-hints.json'
    anchor_file = load_json(hint_file)
    if args.anchors and anchor_file.get('pdf_sha256') != book.pdf_sha:
        raise ValueError('Scan-anchor hints must pin this PDF SHA-256')
    if anchor_file.get('pdf_sha256') != book.pdf_sha:
        anchor_file = {}
    hints = anchor_file.get('hints', {})
    special_bands = anchor_file.get('arabic_bands', {})
    for identifier, bands in special_bands.items():
        entry = book.entries[identifier]
        first,last,_ = book.page_range(book.topics[entry.topic_id][1])
        if entry.kind != 'hadith' or not bands or any(not (type(p) is int and first <= p <= last and 0 <= a < b <= 1) for p,a,b in bands):
            raise ValueError(f'Invalid Arabic band hint: {identifier}')
    tid = book.scope(args.topic)
    jobs = extraction_plan(book, tid, not args.english_only)
    engine = OCR(args.pdf,book.value,args.cache,args.tesseract,args.dpi,not args.english_only)
    output = []
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        for name, page_jobs in jobs.items():
            maps = dict(zip(page_jobs,executor.map(lambda job:engine.recognize(*job),page_jobs)))
            topic = book.topics[name][1]
            records = segment_topic(book,topic,book.by_topic[name],maps,hints)
            if not args.english_only:
                for record in records:
                    checked = special_bands.get(record['id']) if record['status']=='draft' else None
                    bands = checked or missing_arabic_bands(record,topic,maps)
                    if bands:
                        rows = [row for part in executor.map(lambda band:engine.arabic_band(*band),bands) for row in part]
                        apply_arabic_retry(record,book,rows,checked=bool(checked))
            output.extend(records)
            print(f"{name}: {sum(r['status']=='draft' for r in records)}/{len(records)} draft anchors",file=sys.stderr,flush=True)
    bundle = {'schema_version':SCHEMA,'manifest_sha256':book.manifest_sha,'pdf_sha256':engine.sha,'pdf_url':book.pdf_url,
              'topic_ids':tid,'settings':{'dpi':args.dpi,'engine':engine.version,'languages':['eng'] if args.english_only else ['eng','ara'],
                                       'segmenter':'manifest-ocr-band-retry-v1','scan_checked_anchor_ids':sorted(hints),'scan_checked_arabic_band_ids':sorted(special_bands)},
              'report':{'counts':tally(output),'topics':{t:tally([r for r in output if r['topic_id']==t]) for t in tid},
                        'flags':dict(sorted(Counter(flag for r in output for flag in r['flags']).items()))},'records':output}
    store.validate_bundle(bundle,book)
    write_json(args.out,bundle)
    print_summary(bundle['report']['counts'])
    print(f'Wrote {args.out} · all transcriptions are unreviewed')


def print_summary(counts):
    for kind, vals in counts.items():
        print(f'{kind:7} ' + '   '.join(f'{k.replace("_", " ")}: {v}' for k,v in vals.items()))


def audit(args, book):
    bundle = load_json(args.bundle)
    store.validate_bundle(bundle,book)
    print_summary(tally(bundle['records']))
    if args.tsv:
        if args.tsv.resolve() == args.bundle.resolve(): raise ValueError('TSV must not overwrite the extraction bundle')
        buf = io.StringIO(newline='')
        writer = csv.writer(buf,delimiter='\t',lineterminator='\n')
        writer.writerow(['id','topic','kind','reference_or_number','status','printed_start','printed_end','pdf_start','source_scan','flags','english_start','arabic_start'])
        def text_for_sheet(value):
            # Keep untrusted OCR from being interpreted as a spreadsheet expression.
            s = (value or '').replace('\t',' ').replace('\r',' ').replace('\n',' ')[:130].strip()
            return "'"+s if s.startswith(('=','+','-','@')) else s
        for r in bundle['records']:
            if args.unresolved_only and r['status'] != 'unresolved': continue
            e = book.entries[r['id']]; s = r['source']['start']; end = r['source']['end']
            writer.writerow([e.id,e.topic_id,e.kind,e.reference or e.number,r['status'],s['printed_page'],end['printed_page'],s['pdf_page'],
                             s['flipbook_url'],','.join(r['flags']),text_for_sheet(r['english']),text_for_sheet(r['arabic'])])
        atomic_text(args.tsv,buf.getvalue())
        print(f'Wrote {args.tsv}')


def source_crop(args, book):
    from ocr_engine import digest
    try:
        import pymupdf
    except ImportError as exc:
        raise ValueError('Install PyMuPDF first: python -m pip install -r tools/requirements.txt') from exc
    if digest(args.pdf) != book.pdf_sha:
        raise ValueError('PDF checksum does not match the edition')
    if args.out.suffix.lower() != '.png' or not 1 <= args.printed <= book.value['book']['pagination']['last_printed_page']:
        raise ValueError('Provide a printed body/back-matter page and use a .png output')
    with pymupdf.open(args.pdf) as doc:
        page = doc[book.pdf_page(args.printed)-1]; r = page.rect
        x0,x1 = (0,r.width/2) if args.printed%2 else (r.width/2,r.width)
        args.out.parent.mkdir(parents=True,exist_ok=True)
        page.get_pixmap(clip=pymupdf.Rect(x0,0,x1,r.height),dpi=200,alpha=False).save(args.out)
    print(book.locator(args.printed)['flipbook_url'])


def args_setup():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--index',type=Path,default=BASE/'data/book-index.json',help='pinned edition JSON index (override takes precedence)')
    sub = p.add_subparsers(dest='cmd',required=True)
    def cmd(name, help, *, db=False, scope=False, out=False, dry=False):
        c = sub.add_parser(name,help=help)
        if db: c.add_argument('--db',type=Path,required=True,help='dedicated local SQLite file')
        if scope: c.add_argument('--topic',action='append',help='stable topic ID; repeat to select multiple, defaults to all')
        if out: c.add_argument('--out',type=Path,required=True)
        if dry: c.add_argument('--dry-run',action='store_true',help='validate and simulate without writing the database')
        return c
    x = cmd('extract','OCR a scan into candidate records and unresolved windows',scope=True,out=True)
    x.add_argument('--pdf',type=Path,required=True)
    x.add_argument('--cache',type=Path,default=BASE/'.cache'/'ocr')
    x.add_argument('--tesseract',default='tesseract')
    x.add_argument('--anchors',type=Path,help='optional edition-pinned file of scan-checked anchor hints')
    x.add_argument('--dpi',type=int,default=190)
    x.add_argument('--workers',type=int,default=2)
    x.add_argument('--english-only',action='store_true')
    a = cmd('audit','check extraction against the edition manifest')
    a.add_argument('--bundle',type=Path,required=True)
    a.add_argument('--tsv',type=Path)
    a.add_argument('--unresolved-only',action='store_true')
    o = cmd('source-page','render one printed page from the edition',out=True)
    o.add_argument('--pdf',type=Path,required=True); o.add_argument('--printed',type=int,required=True)
    cmd('init','initialize SQLite and seed the complete inventory',db=True)
    i = cmd('import','transactionally upsert staged OCR from a run',db=True,dry=True)
    i.add_argument('--bundle',type=Path,required=True)
    r = cmd('review-sheet','make a blank correction sheet with OCR evidence',db=True,scope=True,out=True)
    r.add_argument('--unresolved-only',action='store_true')
    v = cmd('apply-reviews','add editor-approved corrections as versioned reviews',db=True,dry=True)
    v.add_argument('--file',type=Path,required=True)
    cmd('export','publish reviewed text as a reader JSON snapshot',db=True,out=True)
    stats = cmd('report','report expected, staged, unresolved, and reviewed counts',db=True)
    stats.add_argument('--out',type=Path)
    return p.parse_args()


def main():
    args = args_setup()
    try:
        book = Book(load_json(args.index))
        direct = {'extract':extract,'audit':audit,'source-page':source_crop}
        if args.cmd in direct:
            direct[args.cmd](args,book)
            return 0
        if args.cmd in ('import','apply-reviews'):
            data = load_json(args.bundle if args.cmd=='import' else args.file)
            if args.cmd=='import': store.validate_bundle(data,book)
            else: store.check_header(data,book,'reviews')
        read_only = args.cmd in ('review-sheet','export','report')
        dry_run = getattr(args,'dry_run',False)
        with store.session(args.db,book,dry_run=dry_run,require_existing=read_only) as db:
            if args.cmd=='init':
                result = f'{len(book.chapters)} chapter groups, {len(book.topics)} topics, {len(book.entries)} entries in {args.db}'
            elif args.cmd=='import':
                result = store.apply_bundle(db,data,book)
            elif args.cmd=='apply-reviews':
                result = store.apply_reviews(db,data,book)
            elif args.cmd=='review-sheet':
                result = store.review_sheet(db,book,args.topic,args.unresolved_only)
            elif args.cmd=='export':
                result = store.export_reader(db,book)
            else:
                result = store.report(db,book)
        if args.cmd in ('review-sheet','export','report') and args.out:
            if args.out.resolve() == args.db.resolve(): raise ValueError('Output must not overwrite the database')
            write_json(args.out,result)
            print(f'Wrote {args.out}')
        if args.cmd=='report': print_summary(result['counts'])
        elif args.cmd not in ('review-sheet','export'): print(('Dry run · ' if dry_run else '')+str(result))
        return 0
    except (OSError,ValueError,TypeError,KeyError,IndexError,AttributeError,sqlite3.Error) as error:
        print(f'Error: {error}',file=sys.stderr)
        return 1


if __name__=='__main__':
    raise SystemExit(main())
