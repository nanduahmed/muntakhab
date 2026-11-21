# Muntakhab Reading Room

A React reading prototype and an edition-aware PDF-to-SQLite tool for the Arabic/English scan of *Muntakhab Ahadith* hosted by The Islamic Bulletin. The structured edition index is in `data/book-index.json`. The reader has all **29 topics** in book order. This source checkout starts in reference-only mode. An export from a local reviewed SQLite database enables Arabic, English, and Urdu text. The interface itself can be switched between **English and Urdu** (right-to-left) with the language toggle in the header, and the reading-language control offers **All / Arabic / English / Urdu**.

- [Project instructions for agents](AGENTS.md)
- [UX findings and reading flow](docs/UX-findings.md)
- [Extraction run and coverage](docs/extraction-results.md)
- [Corpus database and translations](docs/corpus.md)
- [Source scan (PDF)](https://islamicbulletin.org/en/ebooks/resources/muntakhab_ahadith_complete.pdf)

## Run the React prototype

Use Node.js 20.19+ (or 22.12+) and npm. In this directory:

```sh
npm ci
npm run dev
```

Open the URL printed by Vite. Try **Kalimah Tayyibah → Iman (Faith)**, **Salah → Virtues of Wudu**, and **Ikhlas → Belief in Allah’s Promises and Hope of Reward**. These cover the main reading paths, including a topic with no standalone Ayat. `npm run build` creates the static site in `dist/`; serve it over HTTP. Hash routes work without server-side route rewrites. No database server is needed by the browser. The header carries the **interface language** toggle (English ↔ اردو, right-to-left), and the reader’s language control switches the reading between **All / Arabic / English / Urdu**; the choice is kept for the browser session.

## Extract the book

The PDF is an image scan, with two printed pages per PDF page. Use Python 3.11+, Tesseract 5 with `eng` and `ara` language packs (e.g. Debian/Ubuntu `tesseract-ocr tesseract-ocr-eng tesseract-ocr-ara`), and PyMuPDF. Commands are local; only retrieving the source and installing dependencies require network access.

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r tools/requirements.txt
tesseract --list-langs
mkdir -p local
curl --fail --location 'https://islamicbulletin.org/en/ebooks/resources/muntakhab_ahadith_complete.pdf' -o local/book.pdf

# Quick bilingual test. Omit --topic to scan all 671 printed body pages.
python tools/booktool.py extract --pdf local/book.pdf \
  --topic kalimah-tayyibah.iman --out local/iman-ocr.json
python tools/booktool.py extract --pdf local/book.pdf --out local/full-ocr.json
python tools/booktool.py audit --bundle local/full-ocr.json --tsv local/review-audit.tsv
```

The CLI checks the PDF’s SHA-256 and physical page count. It crops each spread, uses Tesseract’s line coordinates, looks for expected opening Qur’an citations and printed hadith numbers, and aligns them against the edition’s topic ranges. It retains full-page OCR for hadith and separate column OCR for the opening passages. Two scan-checked number hints recover a dropped digit or number. Localized retries, including two checked crop hints, recover Arabic blocks missed by the full-page pass. These are scan locators, **not** approved text. The index, page geometry and hints are specific to this edition; a different edition needs its own validated map.

OCR is slow on the first full run; a PDF-hash/engine/DPI-keyed cache supports resumption. `--topic` can be repeated; `--english-only` skips Arabic; `--dpi`, `--workers`, `--tesseract` and `--cache` are configurable. Use a new cache directory if you change Tesseract language models. `audit --unresolved-only` filters the TSV to missing anchors. If recognition fails there is still an inventory row and a scan window, with no invented text. This is not a perfect transcription: raw Arabic, diacritics, boundaries, embedded notes, variants, and page-spanning translations all require review. An OCR confidence score is **not** a measure of textual fidelity.

## Populate and maintain SQLite

This is a **dedicated local staging database**, not a connection to any existing database. To keep the scan and transcriptions out of the public repository, generate the data in your own working directory:

```sh
python tools/booktool.py init --db local/reader.sqlite
python tools/booktool.py import --db local/reader.sqlite --bundle local/full-ocr.json --dry-run
python tools/booktool.py import --db local/reader.sqlite --bundle local/full-ocr.json
python tools/booktool.py report --db local/reader.sqlite
```

Import validates the edition, scope, stable IDs, locators and counts before staging. Imports are transactional. Reimporting the same run is a no-op; newer OCR can update draft rows without deleting records, removing an already captured language, or touching approved text. Stable keys use `ayah:<topic-id>:<position>` and `hadith:<sequence-id>:<printed-number>`. This keeps *‘Ilm* #1 separate from *Dhikr* #1 and repeated Qur’an references separate by position.

### Review, correct, and publish

```sh
python tools/booktool.py review-sheet --db local/reader.sqlite \
  --topic salah.virtues-of-wudu --out local/wudu-review.json
python tools/booktool.py source-page --pdf local/book.pdf --printed 225 --out local/p225.png
# Edit local/wudu-review.json after checking the source. Then:
python tools/booktool.py apply-reviews --db local/reader.sqlite --file local/wudu-review.json --dry-run
python tools/booktool.py apply-reviews --db local/reader.sqlite --file local/wudu-review.json
python tools/booktool.py export --db local/reader.sqlite --out public/data/readings.json
```

In the review sheet, set `reviewer`, fill corrected text and exact `printed_start` / `printed_end`, and set `decision` to `"accept"` **only for checked rows**. Use `null` for a language not yet checked. Keep the supplied `base_revision`; a stale change is rejected rather than overwriting a newer review. To restore earlier wording, take the prior value from `review_history` and apply it as a new review at the current revision. Each review and distinct OCR version is preserved. Keep review sheets local; an approved edit is not the same as permission to publish a translation.

The export contains **reviewed words only**, plus compact estimated scan locators for other entries. Do not commit a locally populated `public/data/readings.json`. Keep the PDF, SQLite database, and extraction bundle out of the repository. Confirm reproduction permissions and proofread the text before public release.

## The corpus database and translations

`data/corpus.yaml` is the committed, complete inventory of the book: **214 standalone Qur’an passages (398 ayat) and 1,507 numbered Ahadith — 1,721 entries** with stable IDs, chapter/topic placement, Qur’an references or hadith numbers, and empty `arabic` / `english` / `urdu` fields. It is generated from `data/book-index.json` and checked against it:

```sh
python tools/booktool.py build-corpus --check        # verify the committed inventory matches the edition index
python tools/booktool.py build-corpus                # refuse to overwrite an existing corpus
python tools/booktool.py build-corpus --merge        # rebuild the skeleton, keeping any text you entered
python tools/booktool.py build-corpus --force        # discard and rebuild (destroys entered text)
```

No text appears in the corpus automatically — Qur’anic meanings and Ahadith are **never machine-translated by this tool**. When the editor-supplied translations are entered (by editing the YAML directly, or by handing them over for entry), they are staged into the same review history as scan-checked text:

```sh
python tools/booktool.py init --db local/reader.sqlite
python tools/booktool.py import-corpus --db local/reader.sqlite --file data/corpus.yaml --reviewer "Reviewer name" --dry-run
python tools/booktool.py import-corpus --db local/reader.sqlite --file data/corpus.yaml --reviewer "Reviewer name"
python tools/booktool.py export --db local/reader.sqlite --out public/data/readings.json
```

`import-corpus` validates every row (IDs, positions, references, page bounds), skips rows with no text, requires `--reviewer`, and records the text as a versioned review with no fabricated page spans — entries without a checked printed page fall back to the topic scan link in the reader. See [docs/corpus.md](docs/corpus.md) for the field-by-field contract.

### Files and data contract

| Path | Use |
| --- | --- |
| `src/` and `public/` | React UI (English/Urdu interface, RTL), styles, illustration, and exported reader data. |
| `data/book-index.json` | Machine-readable edition inventory derived from `muntakhab-ahadith-index.yaml`; text is not in this index. |
| `data/corpus.yaml` | Committed complete corpus inventory: every Ayah passage and hadith with empty `arabic` / `english` / `urdu` fields until the editor supplies checked text. |
| `data/scan-anchor-hints.json` | Coordinate/keyword hints tied to the exact PDF SHA-256. |
| `tools/booktool.py` | CLI; `-h` lists commands, and `<command> -h` explains flags. |
| `tools/corpus.py` | YAML corpus build, merge, drift check, validation, and review-sheet adaptation. |
| `local/full-ocr.json` | Versioned OCR bundle; locator and evidence per expected entry. Status is `draft` or `unresolved`. |
| `local/review-audit.tsv` | Filterable coverage and excerpts; OCR evidence, not reader text. |
| `local/reader.sqlite` | Entries, runs, draft history, and review history; independent of the web app. |

The extraction bundle pins both the index fingerprint and the PDF hash. Each record has a stable ID, an OCR anchor, printed/PDF/flipbook coordinates, normalized word bounds per page, available language candidates, and quality flags. `source.type = "window"` marks entries not securely located. The `entries`, `drafts` and `reviews` tables share entry IDs; historical payloads live in the corresponding history tables. Arabic, English, and Urdu are stored as UTF-8. Use `python -m unittest discover -s tests -p 'test_*.py'` for the tool tests and `npx playwright install chromium` followed by `npm run test:ui` for browser tests.
