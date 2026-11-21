"""Render this edition's split scans and cache coordinate-aware Tesseract output."""
from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import subprocess
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from threading import get_ident


@dataclass(frozen=True)
class Line:
    page: int
    text: str
    x0: float
    y0: float
    x1: float
    y1: float
    confidence: float

    @property
    def position(self):
        return self.page, self.y0, self.x0

    @property
    def mid_y(self):
        return (self.y0 + self.y1) / 2


def digest(path: Path) -> str:
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def parse_tsv(tsv: str, page: int, width: int, height: int, *, body_only=True) -> list[Line]:
    lines = defaultdict(list)
    for w in csv.DictReader(io.StringIO(tsv), delimiter='\t', quoting=csv.QUOTE_NONE):
        if w.get('level') != '5' or not (w.get('text') or '').strip():
            continue
        try:
            x, y, ww, hh = (int(w[k]) for k in ('left', 'top', 'width', 'height'))
            conf = float(w['conf'])
        except (ValueError, TypeError, KeyError):
            continue
        lines[(w['block_num'], w['par_num'], w['line_num'])].append((w['text'].strip(), x, y, x+ww, y+hh, conf))
    output = []
    for words in lines.values():
        line = Line(page, ' '.join(w[0] for w in words), min(w[1] for w in words)/width,
                    min(w[2] for w in words)/height, max(w[3] for w in words)/width,
                    max(w[4] for w in words)/height, sum(w[5] for w in words)/len(words))
        # Running heads and page counters occur above the body of this scan.
        if not body_only or 0.065 < line.mid_y < 0.986:
            output.append(line)
    return sorted(output, key=lambda line: line.position)


class OCR:
    def __init__(self, pdf: Path, index: dict, cache: Path, engine: str, dpi: int, arabic: bool):
        try:
            import pymupdf
        except ImportError as exc:
            raise ValueError('Install PyMuPDF first: python -m pip install -r tools/requirements.txt') from exc
        self.fitz = pymupdf
        self.pdf, self.index, self.dpi, self.engine, self.arabic = pdf, index, dpi, engine, arabic
        self.first_pdf = index['chapters'][0]['pages']['pdf_start']
        self.sha = digest(pdf)
        expected_sha = index.get('sources', {}).get('edition_pdf_sha256')
        if expected_sha and self.sha != expected_sha:
            raise ValueError('PDF checksum differs from this edition. Use its source PDF or supply the matching index.')
        with pymupdf.open(pdf) as original:
            expected_pages = index['book']['pagination']['pdf_pages']
            if len(original) != expected_pages:
                raise ValueError(f'Wrong page map: expected {expected_pages} PDF pages, got {len(original)}.')
        self.env = dict(os.environ, OMP_THREAD_LIMIT='1')
        try:
            result = subprocess.run([engine, '--version'], text=True, capture_output=True, check=True, timeout=15, env=self.env)
            self.version = result.stdout.splitlines()[0]
            installed = subprocess.run([engine, '--list-langs'], text=True, capture_output=True, check=True, timeout=15, env=self.env).stdout.splitlines()
        except (FileNotFoundError, subprocess.SubprocessError, IndexError) as exc:
            raise ValueError('Tesseract could not be started. Install it or pass --tesseract /path/to/tesseract.') from exc
        needed = {'eng', 'ara'} if arabic else {'eng'}
        if not needed <= {x.strip() for x in installed}:
            raise ValueError('Missing Tesseract language data: ' + ', '.join(sorted(needed - {x.strip() for x in installed})) + '. Install the language packs or use --english-only.')
        tag = hashlib.sha256(f'layout-v4/{self.version}/{self.dpi}/{self.first_pdf}'.encode()).hexdigest()[:12]
        self.cache = cache / self.sha / tag
        self.cache.mkdir(parents=True, exist_ok=True)

    def pdf_page(self, printed_page: int) -> int:
        return self.first_pdf+(printed_page-1)//2

    def _recognize(self, page: int, language: str, cache_tag: str,
                   *, lo: float, hi: float, top: float, bottom: float, psm: str, dpi: int) -> list[Line]:
        f = self.cache / f'p{page:03d}-{language}-{cache_tag}.json'
        if f.is_file():
            try:
                return [Line(**x) for x in json.loads(f.read_text(encoding='utf-8'))]
            except (TypeError, json.JSONDecodeError):
                pass
        with self.fitz.open(self.pdf) as source:
            scan = source[self.pdf_page(page)-1]
            r = scan.rect
            if r.width/r.height < 1.08:
                raise ValueError(f'Printed page {page} did not map to a two-page scan; check the edition.')
            mid = r.width/2
            crop = self.fitz.Rect(2, 2, mid-4, r.height-2) if page%2 else self.fitz.Rect(mid+4, 2, r.width-2, r.height-2)
            section = self.fitz.Rect(crop.x0+lo*crop.width, crop.y0+top*crop.height,
                                     crop.x0+hi*crop.width, crop.y0+bottom*crop.height)
            pix = scan.get_pixmap(clip=section, dpi=dpi, colorspace=self.fitz.csGRAY, alpha=False)
        try:
            proc = subprocess.run([self.engine, 'stdin', 'stdout', '-l', language, '--dpi', str(dpi), '--psm', psm, 'tsv'],
                                  input=pix.tobytes('png'), capture_output=True, check=True, timeout=90, env=self.env)
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError) as exc:
            raise ValueError(f'OCR failed on printed page {page} ({language}); rerun to resume from cache: {exc}') from exc
        raw = parse_tsv(proc.stdout.decode('utf-8', 'replace'), page, pix.width, pix.height,
                        body_only=(top==0. and bottom==1.))
        rows = [Line(x.page,x.text,lo+x.x0*(hi-lo),top+x.y0*(bottom-top),
                     lo+x.x1*(hi-lo),top+x.y1*(bottom-top),x.confidence) for x in raw]
        # Atomic per-thread file prevents concurrent attempts from corrupting the cache.
        t = f.with_suffix(f'.{os.getpid()}.{get_ident()}.tmp')
        t.write_text(json.dumps([asdict(x) for x in rows], ensure_ascii=False), encoding='utf-8')
        t.replace(f)
        return rows

    def recognize(self, page: int, language: str, region: str = 'page') -> list[Line]:
        profiles = {'page': (0., 1., '3'), 'verse-en': (0., .585, '6'), 'verse-ar': (.56, 1., '6')}
        lo, hi, psm = profiles[region]
        return self._recognize(page, language, region, lo=lo, hi=hi, top=0., bottom=1., psm=psm, dpi=self.dpi)

    def arabic_band(self, page: int, top: float, bottom: float) -> list[Line]:
        top, bottom = round(top,4), round(bottom,4)
        dpi = max(300,self.dpi)
        return self._recognize(page, 'ara', f'band-{dpi}-{int(top*10000):04d}-{int(bottom*10000):04d}',
                               lo=.034, hi=.975, top=top, bottom=bottom, psm='6', dpi=dpi)
    def both(self, page: int) -> tuple[list[Line],list[Line]]:
        return self.recognize(page,'eng'), self.recognize(page,'ara') if self.arabic else []
