"""Stable IDs and locators shared by extraction, SQLite, and the reader."""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
SCHEMA = 1


def load_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def fingerprint(value):
    return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()


def atomic_text(path, text):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=p.parent, delete=False, mode='w', encoding='utf-8', newline='') as f:
        temp = Path(f.name)
        try:
            f.write(text)
            f.close()
            os.replace(temp, p)
        finally:
            temp.unlink(missing_ok=True)


def write_json(path, data):
    atomic_text(path, json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + '\n')


@dataclass(frozen=True)
class Entry:
    id: str
    topic_id: str
    kind: str
    position: int
    reference: str | None = None
    number: int | None = None
    sequence: str | None = None


class Book:
    def __init__(self, value):
        self.value = value
        self.manifest_sha = fingerprint(value)
        self.pdf_sha = value['sources']['edition_pdf_sha256']
        self.pdf_url = value['sources']['edition_pdf']
        self.flipbook = value['sources']['flipbook'].split('#')[0]
        if not re.fullmatch('[0-9a-f]{64}', self.pdf_sha):
            raise ValueError('Index must pin the exact PDF SHA-256')
        self.chapters = {c['id']: c for c in value['chapters']}
        self.topics = {}
        self.entries = {}
        self.by_topic = {}
        self.first_pdf = value['chapters'][0]['pages']['pdf_start']
        expected_first = 1
        for chapter in value['chapters']:
            for topic in chapter['subchapters']:
                tid = topic['id']
                if tid in self.topics or not tid.startswith(chapter['id'] + '.'):
                    raise ValueError(f'Invalid/duplicate topic {tid}')
                self.topics[tid] = (chapter, topic)
                first, last, h_start = self.page_range(topic)
                if not first == expected_first <= h_start <= last:
                    raise ValueError(f'Invalid or discontinuous page map: {tid}')
                if (self.pdf_page(first), self.pdf_page(last)) != (topic['pages']['pdf_start'], topic['pages']['pdf_end']):
                    raise ValueError(f'Inconsistent PDF page map: {tid}')
                expected_first = last + 1
                h = topic['hadith_numbers']
                refs = topic['quran_references']
                if (topic['counts']['ayah_passages'], topic['counts']['ahadith']) != (len(refs), h['last'] - h['first'] + 1):
                    raise ValueError(f'Counts do not match entries: {tid}')
                entries = [Entry(f'ayah:{tid}:{i}', tid, 'ayah', i, reference=ref) for i, ref in enumerate(refs, 1)]
                entries += [Entry(f"hadith:{h['sequence_id']}:{n}", tid, 'hadith', len(refs) + i, number=n, sequence=h['sequence_id'])
                            for i, n in enumerate(range(h['first'], h['last'] + 1), 1)]
                for e in entries:
                    if e.id in self.entries:
                        raise ValueError(f'Duplicate entry {e.id}')
                    self.entries[e.id] = e
                self.by_topic[tid] = entries
        if expected_first - 1 != value['book']['pagination']['last_numbered_body_page']:
            raise ValueError('Topic page map does not cover the numbered body')
        for kind, key in [('ayah', 'ayah_passages'), ('hadith', 'ahadith')]:
            if sum(e.kind == kind for e in self.entries.values()) != value['totals']['counts'][key]:
                raise ValueError(f'Book {key} count differs from the manifest')

    @staticmethod
    def page_range(topic):
        return topic['pages']['printed_start'], topic['pages']['printed_end'], topic['hadith_numbers']['first_entry_printed_page']

    def pdf_page(self, page):
        return self.first_pdf + (page-1)//2

    def locator(self, page):
        n = self.pdf_page(page)
        return {'printed_page': page, 'pdf_page': n, 'side': 'left' if page%2 else 'right',
                'flipbook_url': f'{self.flipbook}#{n*2-2}-{n*2-1}'}

    def scope(self, topic_ids=None):
        selection = set(topic_ids or self.topics)
        if not selection <= self.topics.keys():
            raise ValueError('Unknown topic: ' + ', '.join(sorted(selection - self.topics.keys())))
        return [t for t in self.topics if t in selection]
