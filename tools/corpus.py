"""Committed YAML corpus: complete inventory, translation staging, and import.

`data/corpus.yaml` is the versioned, human-editable store of every Ayah passage and
hadith in Muntakhab Ahadith. It carries no text until a checked translation is
entered by hand; `import-corpus` stages filled rows into SQLite as versioned
reviews, exactly as the scan-checked review-sheet flow does. Nothing here
translates or rewrites religious text: fields left empty stay empty.
"""
from __future__ import annotations

import copy
from pathlib import Path

import yaml

from book_model import SCHEMA

LANGUAGES = ('arabic', 'english', 'urdu')
TEXT_FIELDS = {'arabic', 'english', 'urdu', 'notes', 'citation'}
FINGERPRINT_FIELDS = ('id', 'chapter', 'topic', 'kind', 'position', 'reference', 'hadith_number', 'sequence_id')
HEADER = """\
# Muntakhab Ahadith · complete corpus inventory (1,721 entries)
# Generated from data/book-index.json by tools/booktool.py build-corpus.
# Keep ids, positions, references, and order exactly as generated — they are the
# stable identity of every entry. Fill in arabic / english / urdu (each a plain
# string, or leave null) from your own checked sources; this file never gains text
# automatically. Optional scan-page span: set both printed_start and printed_end
# to the printed page(s) that carry the entry. Set excerpt: true only on partial
# Qur’an quotations. Fields with no checked value stay null.
# Bring this file into SQLite with:
#   python tools/booktool.py import-corpus --db local/reader.sqlite --file data/corpus.yaml --reviewer "Name"
"""


def inventory_rows(book):
    rows = []
    for chapter in book.value['chapters']:
        for topic in chapter['subchapters']:
            entries = book.by_topic[topic['id']]
            for entry in entries:
                rows.append({
                    'id': entry.id,
                    'chapter': chapter['id'],
                    'topic': topic['id'],
                    'kind': entry.kind,
                    'position': entry.position,
                    'reference': entry.reference,
                    'hadith_number': entry.number,
                    'sequence_id': entry.sequence,
                    'excerpt': None,
                    'printed_start': None,
                    'printed_end': None,
                    'citation': None,
                    'arabic': None,
                    'english': None,
                    'urdu': None,
                    'notes': None,
                    'status': 'pending',
                })
    return rows


HAND_FIELDS = ('excerpt', 'printed_start', 'printed_end', 'citation', 'arabic', 'english', 'urdu', 'notes', 'status')


def merge_corpus(book, existing_path):
    """Rebuild the inventory skeleton for the current index, keeping hand-entered fields.

    Fails rather than guessing when the committed file no longer lines up row-for-row
    with the edition inventory (ids drifted): a human must reconcile the merge.
    """
    data = load_corpus(existing_path)
    rows = data.get('entries')
    if not isinstance(rows, list):
        raise ValueError('Corpus must include an entries list')
    fresh = inventory_rows(book)
    if len(rows) != len(fresh):
        raise ValueError(f'Cannot merge: {len(rows)} existing rows vs {len(fresh)} expected; rebuild from scratch or restore the file')
    for index, (row, old) in enumerate(zip(fresh, rows)):
        if row['id'] != old.get('id'):
            raise ValueError(f'Cannot merge: expected {row["id"]} at entries[{index}], found {old.get("id")!r}')
    merged = []
    for row, old in zip(fresh, rows):
        out = dict(row)
        for key in HAND_FIELDS:
            if old.get(key) is not None:
                out[key] = old[key]
        merged.append(out)
    provided = sum(1 for row in merged if any(row.get(lang) for lang in LANGUAGES))
    return merged, provided


def corpus_document(book, rows):
    return {
        'schema_version': SCHEMA,
        'manifest_sha256': book.manifest_sha,
        'pdf_sha256': book.pdf_sha,
        'totals': copy.deepcopy(book.value['totals']['counts']),
        'languages': list(LANGUAGES),
        'entries': rows,
    }


def render_corpus(book, rows):
    body = yaml.safe_dump(corpus_document(book, rows), allow_unicode=True, sort_keys=False, width=120)
    return HEADER + body


def strip_hand_fields(row):
    skeleton = {key: row.get(key) for key in FINGERPRINT_FIELDS}
    return skeleton


def load_corpus(path):
    text = Path(path).read_text(encoding='utf-8')
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ValueError(f'Corpus is not valid YAML: {exc}') from exc
    if not isinstance(data, dict):
        raise ValueError('Corpus must be a YAML mapping')
    return data


def validate_corpus(data, book):
    """Return (filled_rows, pending_count). Raises ValueError on any inconsistency."""
    if data.get('schema_version') != SCHEMA:
        raise ValueError('Corpus must declare schema_version: 1')
    if data.get('manifest_sha256') != book.manifest_sha:
        raise ValueError('Corpus was built for a different edition index')
    rows = data.get('entries')
    if not isinstance(rows, list):
        raise ValueError('Corpus must include an entries list')
    seen, filled, pending = set(), [], 0
    for index, row in enumerate(rows):
        where = f'entries[{index}]'
        if not isinstance(row, dict):
            raise ValueError(f'{where}: each entry must be a mapping')
        identifier = row.get('id')
        if not isinstance(identifier, str) or identifier not in book.entries:
            raise ValueError(f'{where}: unknown entry id {identifier!r}')
        if identifier in seen:
            raise ValueError(f'{where}: duplicate entry {identifier}')
        seen.add(identifier)
        entry = book.entries[identifier]
        if row.get('topic') != entry.topic_id or row.get('chapter') != book.topics[entry.topic_id][0]['id']:
            raise ValueError(f'{identifier}: chapter/topic do not match the edition index')
        if row.get('kind') != entry.kind or row.get('position') != entry.position:
            raise ValueError(f'{identifier}: kind or position do not match the edition index')
        if entry.kind == 'ayah':
            if row.get('reference') != entry.reference:
                raise ValueError(f'{identifier}: Qur’an reference does not match the edition index')
            if row.get('hadith_number') is not None or row.get('sequence_id') is not None:
                raise ValueError(f'{identifier}: hadith fields set on an Ayah entry')
        else:
            if row.get('hadith_number') != entry.number or row.get('sequence_id') != entry.sequence:
                raise ValueError(f'{identifier}: hadith number or sequence does not match the edition index')
            if row.get('reference') is not None:
                raise ValueError(f'{identifier}: Qur’an reference set on a hadith entry')
        for key, value in row.items():
            if key in TEXT_FIELDS:
                if value is not None and (not isinstance(value, str) or not value.strip() or len(value) > 100_000 or '\0' in value):
                    raise ValueError(f'{identifier}: invalid {key} text')
        excerpt = row.get('excerpt')
        if excerpt is not None and (type(excerpt) is not bool or excerpt and entry.kind != 'ayah'):
            raise ValueError(f'{identifier}: only Qur’an passages can carry excerpt: true')
        start, end = row.get('printed_start'), row.get('printed_end')
        if (start is None) != (end is None):
            raise ValueError(f'{identifier}: printed_start and printed_end must be set together')
        if start is not None:
            low, high, _ = book.page_range(book.topics[entry.topic_id][1])
            if type(start) is not int or type(end) is not int or not (low <= start <= end <= high):
                raise ValueError(f'{identifier}: printed pages must be inside topic span {low}–{high}')
        if not any(row.get(lang) for lang in LANGUAGES):
            pending += 1
            continue
        filled.append(row)
    if seen != set(book.entries):
        missing = len(set(book.entries) - seen)
        raise ValueError(f'Corpus is missing {missing} entr{"y" if missing == 1 else "ies"}; rebuild it with build-corpus')
    return filled, pending


def review_rows(data, book, revisions):
    filled, _ = validate_corpus(data, book)
    rows = []
    for row in filled:
        entry_id = row['id']
        rows.append({
            'id': entry_id,
            'topic_id': book.entries[entry_id].topic_id,
            'decision': 'accept',
            'base_revision': revisions.get(entry_id, 0),
            'printed_start': row.get('printed_start'),
            'printed_end': row.get('printed_end'),
            'english': row.get('english'),
            'arabic': row.get('arabic'),
            'urdu': row.get('urdu'),
            'notes': row.get('notes'),
            'citation': row.get('citation'),
            'excerpt': bool(row.get('excerpt')),
        })
    return rows


def skeleton(book):
    return [strip_hand_fields(row) for row in inventory_rows(book)]


def check_corpus_file(path, book):
    data = load_corpus(path)
    rows = data.get('entries')
    if not isinstance(rows, list):
        raise ValueError('Corpus must include an entries list')
    current = [strip_hand_fields(row) for row in rows if isinstance(row, dict)]
    expected = skeleton(book)
    if len(current) != len(expected):
        raise ValueError(f'Corpus inventory drift: {len(current)} rows vs {len(expected)} expected (ids or rows changed)')
    for index, (want, got) in enumerate(zip(expected, current)):
        if got != want:
            raise ValueError(f'Corpus inventory drift at entries[{index}]: {got.get("id")!r} differs from the edition index')
    validate_corpus(data, book)  # also enforces reference/position cross-checks and field hygiene
    return True
