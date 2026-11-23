"""Conservative, manifest-guided OCR segmentation; never returns approved text."""
from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from statistics import mean

from ocr_engine import Line

# Faithful to the audited edition index: short/mistyped citations warrant review, not silent acceptance.
PRINTED_ALIASES = {'49:11': '49:11-13', '49:11-12': '49:11-13', '83:1': '83:1-6', '83:1-5': '83:1-6'}
REF_RE = re.compile(r'(?<!\d)(\d{1,3})\s*[:;]\s*(\d{1,3})(?:\s*[-–—−~:]\s*(\d{1,3}))?(?![\d:])')
NUMBER_RE = re.compile(r"^\s*[._*+~–—‘’'\[({-]?\s*([\dIlIOoSBZ|!]{1,3})([.,:;’')\]-]|\s)(?=\s*\S)\s*", re.ASCII)
NUMBER_FIX = str.maketrans({'I':'1', 'l':'1', '|':'1', '!':'1', 'O':'0', 'o':'0', 'S':'5', 'B':'8', 'Z':'2'})
NARRATOR_RE = re.compile(r"narrat\w*|reports?\b|\bradiy|\brad[il]y|\b[aā]b[uū]\b|\b(ibne?|bin)\b|ras[uūi]l|sallall|\bprophet\b|\b(he|she)\s+(said|asked|heard|replied)", re.I)
EN_BITS = re.compile(r"\b(the|of|and|in|with|you|your|we|his|him|her|for|who|was|are|have|that|they|from|will|when|allah|unto|this|those|not|has)\b", re.I)
AYAH_INTRO = re.compile(r"^[^a-z]{0,3}(?:and\s+)?(?:allah|all[aā]h|he)\b.{0,72}\b(?:say[st]?|sai[dcl]|stated)\b", re.I)
AHADITH_HEADING = re.compile(r"\b(?:[ao]h[aod]?[aod]d[i1l][ftl][hb]|had[i1l][tf][hb])", re.I)
ARABIC_LETTER = re.compile('[\u0621-\u063a\u0641-\u064a\u0671-\u06d3]')
DIGITS = str.maketrans('٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹', '01234567890123456789')


@dataclass(frozen=True)
class Anchor:
    order: int
    line: Line
    score: float
    evidence: str
    mode: str
    end: Line | None = None


def align(candidates):
    """Pick the strongest ordered chain of anchors without reusing a position or an ID."""
    nodes = sorted(candidates, key=lambda a: (a.line.page, a.line.y0, a.order))
    weights, chain = [], []
    for i, node in enumerate(nodes):
        best, predecessor = 0., None
        for k in range(i):
            prev = nodes[k]
            if (prev.order < node.order and weights[k] > best and
                    (prev.line.page < node.line.page or prev.line.y0+.009 < node.line.y0)):
                best, predecessor = weights[k], k
        weights.append(node.score+best)
        chain.append(predecessor)
    at = max(range(len(nodes)), key=weights.__getitem__) if nodes else None
    matches = {}
    while at is not None:
        matches[nodes[at].order] = nodes[at]
        at = chain[at]
    return matches


def english(row):
    text = row.text
    count = len(re.findall(r'[a-zA-Z]', text))
    return count >= 3 and (row.confidence >= 58 or (row.confidence >= 40 and (EN_BITS.search(text) or NARRATOR_RE.search(text))))


def arabic(row):
    text = row.text
    return len(ARABIC_LETTER.findall(text)) >= 4 and len(re.findall(r'[0-9١-٩]', text)) < max(6, .48*len(text))


def before(row, page, y):
    return (row.page, row.y0) < (page, y)


def at_or_after(row, page, y):
    return not before(row, page, y)


def locator_bounds(rows):
    by_page = defaultdict(list)
    for row in rows:
        by_page[row.page].append(row)
    return [{'printed_page': p, 'box': [round(x, 4) for x in (min(l.x0 for l in values), min(l.y0 for l in values),
                                                              max(l.x1 for l in values), max(l.y1 for l in values))]}
            for p, values in sorted(by_page.items())]


def confidence(rows):
    return round(mean(l.confidence for l in rows), 1) if rows else None


def join(rows):
    # Preserve recognition, but collapse line-wrap hyphens so reviewers can edit in a paragraph.
    return re.sub(r'(?<=[a-zA-Z])-\n(?=[a-z])', '', '\n'.join(row.text for row in rows)).replace('\n', ' ').strip()


def make_record(entry, book, pages, en=(), ar=(), note=None, anchor=None, flags=(), status='draft', english_text=None):
    start, end = pages
    english_text = join(en) if english_text is None else english_text
    arabic_text = join(ar)
    limitations = list(flags)
    for field, text, rows in (('english',english_text,en), ('arabic',arabic_text,ar)):
        if not text:
            limitations.append(f'{field}_not_captured')
        elif rows and confidence(rows) < (72 if field == 'english' else 65):
            limitations.append(f'{field}_low_ocr_confidence')
    return {'id': entry.id, 'topic_id': entry.topic_id, 'kind': entry.kind, 'status': status,
            'english': english_text or None, 'arabic': arabic_text or None, 'urdu': None, 'notes': note,
            'source': {'start': book.locator(start), 'end': book.locator(end), 'type': 'window' if status == 'unresolved' else 'candidate',
                       'anchor': {'printed_page': anchor.line.page, 'y': round(anchor.line.y0, 4), 'ocr': anchor.evidence,
                                  'method': anchor.mode} if anchor else None,
                       'english_boxes': locator_bounds(en), 'arabic_boxes': locator_bounds(ar),
                       'mean_confidence': {'english': confidence(en), 'arabic': confidence(ar)}},
            'flags': sorted(set(limitations))}


def gap_window(order, matches, low, high, *, next_starts_earlier=False):
    previous = max((i for i in matches if i < order), default=None)
    following = min((i for i in matches if i > order), default=None)
    lo = matches[previous].line.page if previous is not None else low
    hi = matches[following].line.page if following is not None else high
    # A hadith's Arabic may begin before the page where the English number is printed.
    return max(low, lo-1) if next_starts_earlier else lo, hi


def verse_candidates(rows, entries, mode):
    options = defaultdict(list)
    for i, entry in enumerate(entries):
        options[entry.reference].append(i)
    result = []
    for i, row in enumerate(rows):
        variants = [(row.text, row)]
        if i+1 < len(rows) and (row.x0 < .55 and (rows[i+1].page != row.page or rows[i+1].y0 - row.y0 < .065)):
            following = rows[i+1]
            if re.search(r'\d\s*[:;\-–]\s*$', row.text) or re.match(r'^\s*[0-9:;\-–]', following.text):
                variants.append((row.text + ' ' + following.text, following))
        for raw, end_row in variants:
            for m in REF_RE.finditer(raw.translate(DIGITS)):
                if end_row is not row and m.end() <= len(row.text):
                    continue
                ref = f'{int(m[1])}:{int(m[2])}' + (f'-{int(m[3])}' if m[3] else '')
                adjusted = PRINTED_ALIASES.get(ref) if ref not in options else None
                for n in options.get(adjusted or ref, []):
                    score = 8 + min(1.9, row.confidence/50) + (1.4 if mode == 'english_column' else 0)
                    if ref != entries[n].reference or ';' in m[0]:
                        score -= 2.2
                    adjusted_separator = (';' in m[0] or m[0].count(':') > 1)
                    if not english(row): score -= 2.1
                    result.append(Anchor(n, row, score, raw, ('printed_reference_variant' if adjusted else 'punctuation_normalized' if adjusted_separator else mode), end_row))
    # Both crops can identify one printed line. The alignment cannot consume it twice.
    return result


def extract_verses(book, entries, first, hadith_page, english_full, arabic_crops, english_crops, first_hadith_y):
    if not entries:
        return [], None
    columns = sorted(english_crops, key=lambda row: row.position)
    trimmed = lambda lines: [row for row in lines if before(row, hadith_page, first_hadith_y)]
    columns, broad = trimmed(columns), trimmed(english_full)
    candidates = verse_candidates(columns, entries, 'english_column') + verse_candidates(broad, entries, 'full_page_fallback')
    matches = align(candidates)
    output = []
    prev_end = None
    for i, entry in enumerate(entries):
        if i not in matches:
            output.append(make_record(entry, book, gap_window(i, matches, first, hadith_page), status='unresolved', flags=['printed_reference_not_located']))
            continue
        anchor = matches[i]
        stop = anchor.end or anchor.line
        connected = [r for r in columns if (r.page, r.y0) <= (stop.page, stop.y0 + .013) and
                     (prev_end is None or at_or_after(r, prev_end.page, prev_end.y0+.015))]
        if not connected or (connected[-1].page, connected[-1].y0) < (stop.page, stop.y0 - .035):
            connected = [r for r in broad if (r.page, r.y0) <= (stop.page, stop.y0+.004) and
                         (prev_end is None or at_or_after(r, prev_end.page, prev_end.y0+.015)) and r.x0 < .53]
        starts = [k for k, r in enumerate(connected) if AYAH_INTRO.search(r.text) or
                  re.search(r'^.{0,24}\bsays:\s*$', r.text, re.I) and k and
                  re.search(r'Allah|mentioning', ' '.join(x.text for x in connected[max(0,k-3):k]), re.I)]
        flags = []
        if anchor.mode == 'printed_reference_variant': flags.append('printed_reference_needs_range_check')
        if anchor.mode == 'punctuation_normalized': flags.append('ocr_reference_separator_normalized')
        if starts:
            marker = connected[starts[-1]]
            selected = connected[starts[-1]+1:]
            while selected and re.search(r"^(?:His Prophet\b|wasallam:\s*)", selected[0].text, re.I):
                selected = selected[1:]
            # A separate next intro suggests a skipped block, not part of this quotation.
        else:
            flags.append('verse_start_uncertain')
            selected = connected
            # On chapter openings discard the chapter/section headings above the passage.
            breaks = [k for k,r in enumerate(selected) if re.search(r'verses\s+of\s+qu', r.text, re.I)]
            if breaks: selected = selected[breaks[-1]+1:]
            marker = selected[0] if selected else anchor.line
        en = [r for r in selected if english(r) or abs(r.y0-stop.y0) < .015 and r.page == stop.page]
        if not en:
            en = [anchor.line]
            flags.append('verify_verse_text_extent')
        lo = marker.page
        ar = [r for r in arabic_crops if arabic(r) and at_or_after(r, lo, marker.y0-.025) and before(r, stop.page, stop.y1+.028)]
        output.append(make_record(entry, book, (lo, stop.page), en, ar, anchor=anchor, flags=flags))
        prev_end = stop
    return output, prev_end


def hadith_candidates(rows, entries, first_page):
    numbers = {entry.number: i for i, entry in enumerate(entries)}
    for i, row in enumerate(rows):
        m = NUMBER_RE.match(row.text)
        if not m or row.x0 > .23:
            continue
        digits = m[1].translate(NUMBER_FIX)
        if not digits.isdecimal() or int(digits) not in numbers:
            continue
        order = numbers[int(digits)]
        if order == 0 and row.page != first_page:
            continue
        next_line = rows[i+1].text if i+1 < len(rows) and rows[i+1].page == row.page else ''
        text = row.text[m.end():]
        narrator = NARRATOR_RE.search(text + ' ' + next_line[:110])
        if m[2].isspace() and not narrator:
            continue
        if not english(row) and not narrator:
            continue
        fuzzy = m[1] != digits or m[2].isspace()
        if fuzzy and (not narrator or row.confidence < 53):
            continue
        # Arabic lexical noise and translator's numbered explanatory notes can look like entries.
        # Prefer narrator/formula signals over isolated in-range digits.
        score = 5.5 + (4.5 if narrator else 0) + row.confidence/55 + (.5 if row.x0 < .16 else 0)
        score -= (3.0 if fuzzy else 0) + (4 if re.match(r'(?:the meaning|the objective|another meaning)', text, re.I) else 0)
        if score > 4:
            yield Anchor(order, row, score, row.text, 'corrected_number_candidate' if fuzzy else 'english_number')


def checked_anchors(rows, entries, hints):
    for i, entry in enumerate(entries):
        hint = (hints or {}).get(entry.id)
        if not hint:
            continue
        eligible = [row for row in rows if row.page == hint['printed_page'] and hint['y_min'] <= row.y0 <= hint['y_max']
                    and re.search(hint['pattern'], row.text, re.I)]
        if eligible:
            row = max(eligible, key=lambda line: line.confidence)
            yield Anchor(i, row, 19, row.text, 'scan_checked_number_anchor')


def arabic_before(broad_en, broad_ar, start, lower):
    # Arabic narration normally precedes its English numbered translation. Look back to
    # the last genuine English line, including at a page break, rather than treating OCR's
    # apparent Arabic characters on English paragraphs as Arabic source.
    preceding_en = [r for r in broad_en if r.page >= start.page-1 and before(r,start.page,start.y0-.012) and english(r)]
    last = preceding_en[-1] if preceding_en else None
    page, y = max(lower, (last.page, last.y1) if last else (start.page-1, 0.))
    return [r for r in broad_ar if r.page >= start.page-1 and at_or_after(r,page,y-.002)
            and before(r,start.page,start.y0-.008) and arabic(r)]


def extract_hadith(book, entries, first_page, last_page, en_full, ar_full, known_verse_end, header, hints=None):
    if not entries:
        return []
    cut = max((line.y1 for line in (header, known_verse_end) if line and line.page == first_page), default=.065)
    en_rows = [r for r in en_full if at_or_after(r, first_page, cut)]
    ar_rows = [r for r in ar_full if at_or_after(r, first_page, cut)]
    matches = align([*hadith_candidates(en_rows, entries, first_page), *checked_anchors(en_rows, entries, hints)])
    arabic_groups = {k: arabic_before(en_rows, ar_rows, a.line, (first_page, cut)) for k, a in matches.items()}
    keys = sorted(matches)
    output = []
    for i, entry in enumerate(entries):
        if i not in matches:
            output.append(make_record(entry, book, gap_window(i, matches, first_page, last_page, next_starts_earlier=True),
                                      status='unresolved', flags=['printed_number_not_located']))
            continue
        start = matches[i]
        j = next((k for k in keys if k > i), None)
        stop = matches[j].line if j is not None else None
        upper = (stop.page, stop.y0) if stop else (last_page, 1.)
        if j is not None and arabic_groups[j]:
            first_ar = arabic_groups[j][0]
            upper = min(upper, (first_ar.page, first_ar.y0-.003))
        flags = []
        if start.mode == 'scan_checked_number_anchor': flags.append('scan_checked_anchor_text_unreviewed')
        elif start.mode != 'english_number': flags.append('ocr_number_corrected_verify')
        if (j is None and i < len(entries)-1) or (j is not None and j > i+1):
            # An unrecognized number can conceal a boundary; do not consume unknown pages.
            upper = min(upper, (start.line.page, .985))
            flags.append('next_number_unresolved_text_extent_uncertain')
        if start.score < 8: flags.append('possible_numbered_note_verify')
        candidates = [r for r in en_rows if at_or_after(r,start.line.page,start.line.y0-.001) and before(r,*upper)]
        en = [r for r in candidates if english(r) or r == start.line]
        note_start = next((k for k, r in enumerate(en) if k and re.match(r'^\W*(?:Note|N.B.)\s*[:.]', r.text, re.I)), len(en))
        # If the Arabic match starts too early, retain the numbered evidence and flag the extent.
        narrative = en[:note_start] or [start.line]
        if not en:
            flags.append('verify_hadith_text_extent')
        note = join(en[note_start:]) or None
        ar = arabic_groups[i]
        lo = min(start.line.page, ar[0].page if ar else start.line.page)
        hi = max(start.line.page, max((r.page for r in en), default=start.line.page))
        translated = join(narrative)
        translated = NUMBER_RE.sub('', translated, count=1).strip() or start.line.text
        output.append(make_record(entry, book, (lo, hi), narrative, ar, note=note, anchor=start, flags=flags,
                                  english_text=translated))
    return output


def segment_topic(book, topic, entries, layout, hints=None):
    first, last, h_start = book.page_range(topic)
    full = [r for p in range(first,last+1) for r in layout[p,'eng','page']]
    opening = [r for r in full if r.page <= h_start]
    header = next((r for r in opening if r.page == h_start and r.x0 > .17 and r.x1 < .9 and
                   len(r.text) < 41 and AHADITH_HEADING.search(r.text)), None)
    a_entries = [e for e in entries if e.kind == 'ayah']
    h_entries = [e for e in entries if e.kind == 'hadith']
    if header:
        first_hadith_y = header.y0
    else:
        first_candidate = next((a for a in hadith_candidates([r for r in full if r.page == h_start],h_entries,h_start) if a.order == 0 and a.score >= 8), None)
        first_hadith_y = first_candidate.line.y0 if first_candidate else 1.
    verses, last_verse = extract_verses(book, a_entries, first, h_start, opening,
        [r for p in range(first,h_start+1) for r in layout.get((p,'ara','verse-ar'), [])],
        [r for p in range(first,h_start+1) for r in layout.get((p,'eng','verse-en'), [])], first_hadith_y)
    hadith = extract_hadith(book, h_entries, h_start, last, full,
                          [r for p in range(h_start,last+1) for r in layout.get((p,'ara','page'), [])], last_verse, header, hints)
    return verses + hadith



def missing_arabic_bands(record, topic, layout):
    """Try only the blank space between English blocks, never whole English pages."""
    if record['kind'] != 'hadith' or record.get('arabic') or record['status'] != 'draft':
        return []
    anchor = record['source']['anchor']
    page, y = anchor['printed_page'], anchor['y']
    low = topic['pages']['printed_start']
    bands = []
    for p in range(max(low,page-1),page+1):
        end = y-.005 if p == page else .986
        if p != page and y>.27:
            continue
        prev = [r for r in layout[p,'eng','page'] if r.y0 < end-.013 and english(r)]
        if p != page and any(english(r) for r in layout[page,'eng','page'] if r.y0 < y-.022):
            continue
        start = max(.068, end-.30, prev[-1].y1 + .001 if prev else 0.)
        if end - start > .024:
            bands.append((p,start,end))
    return bands


def apply_arabic_retry(record, book, rows, *, checked=False):
    useful = [r for r in rows if arabic(r) and r.confidence >= 18]
    if not useful:
        return
    record['arabic'] = join(useful)
    record['source']['arabic_boxes'] = locator_bounds(useful)
    record['source']['mean_confidence']['arabic'] = confidence(useful)
    record['source']['start'] = book.locator(min(record['source']['start']['printed_page'], min(r.page for r in useful)))
    record['source']['end'] = book.locator(max(record['source']['end']['printed_page'], max(r.page for r in useful)))
    record['flags'] = sorted((set(record['flags']) - {'arabic_not_captured'}) | {'scan_checked_arabic_band_text_unreviewed' if checked else 'arabic_band_retry_check_boundaries'} |
                             ({'arabic_low_ocr_confidence'} if confidence(useful)<65 else set()))
