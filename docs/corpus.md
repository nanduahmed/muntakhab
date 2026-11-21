# The corpus database and translations

*Muntakhab Ahadith* is a scanned edition hosted by The Islamic Bulletin. This project maintains a complete, machine-checked inventory of everything the book contains, plus a place for the editor-supplied translations. **No text is ever machine-translated here.** Qur’anic meanings and Ahadith enter the app only after a human supplies and signs them off.

## What exists today

| Layer | Contents | Text? |
| --- | --- | --- |
| `data/book-index.json` | Edition manifest: chapters, topics, page map, Qur’an references, hadith numbering, SHA-256 pins. | No |
| `data/corpus.yaml` | **The complete corpus database** — all 214 standalone Qur’an passages (398 ayat) and 1,507 numbered Ahadith (1,721 entries), with chapter/topic placement, Qur’an references or hadith numbers, and empty `arabic` / `english` / `urdu` fields. | Empty (`null`) |
| `local/reader.sqlite` | Dedicated local staging database (untracked): entries, drafts, reviews, full history. | Built from the same manifest via `init` |
| `public/data/readings.json` | Browser snapshot, generated from SQLite by `export`. **Reference-only** until reviewed text exists and publication is approved. | Reference-only |
| `data/scan-anchor-hints.json` | PDF-pinned OCR locator hints (evidence, not text). | No |

`data/corpus.yaml` is the store of record for translations. It is safe to commit: it carries structure only until the editor supplies text.

## Entry identity

IDs are stable and shared by every layer:

- Ayah passages: `ayah:<topic-id>:<1-based-position>` — e.g. `ayah:salah.virtues-of-wudu:1` for Qur’an 5:6.
- Ahadith: `hadith:<sequence-id>:<printed-number>` — e.g. `hadith:salah:243`. `ʿIlm` and `Dhikr` each have a Hadith #1; the sequence keeps them distinct.

Never renumber or hand-edit an ID. The `chapter` / `topic` / `kind` / `position` / `reference` / `hadith_number` / `sequence_id` fields in `corpus.yaml` are cross-checked against the edition index on every `import-corpus` and `--check` run; drift fails loudly instead of importing bad data.

## Field legend (`data/corpus.yaml`)

| Field | Meaning |
| --- | --- |
| `id`, `chapter`, `topic`, `kind`, `position` | Identity and placement. `kind` is `ayah` or `hadith`. |
| `reference` | Qur’an citation `surah:verse` or `surah:first-last` (ayah rows only). |
| `hadith_number`, `sequence_id` | Printed number and numbering sequence (hadith rows only). |
| `arabic` | Arabic source passage, exactly as the edition prints it. |
| `english` | English translation of the Ayah/hadith. |
| `urdu` | Urdu translation of the Ayah/hadith. |
| `citation` | Optional extra citation, e.g. hadith collection/number. Free-form, editor-supplied. |
| `notes` | Optional editorial note shown under the entry ("Edition note"). |
| `printed_start`, `printed_end` | Optional printed page span carrying the entry. Both or neither; must lie inside the topic’s page range. Leave `null` when not known — the reader then links to the topic scan rather than claiming fake pages. |
| `excerpt` | `true` only when a Qur’an citation quotes a partial verse. Ayat rows only. |
| `status` | Informational: `pending` (empty) or anything the editor sets once filled (`provided`, …). Staging is driven by text presence, not this flag. |

## Entering translations

1. Open `data/corpus.yaml`. Find the entry by `id`.
2. Fill `arabic`, `english`, and/or `urdu` with your checked text. YAML quoting handles Arabic/Urdu; multi-line text can use a block scalar (`arabic: >-`).
3. Optionally set `printed_start` / `printed_end`, `citation`, `notes`, or `excerpt`.
4. Do not rename IDs, reorder rows, or drop entries — `import-corpus` rejects a tampered or truncated file.

The same check runs in CI/tests via `python tools/booktool.py build-corpus --check`.

## Staging translations into SQLite

```sh
python tools/booktool.py init --db local/reader.sqlite
python tools/booktool.py import-corpus --db local/reader.sqlite --file data/corpus.yaml --reviewer "Your name" --dry-run
python tools/booktool.py import-corpus --db local/reader.sqlite --file data/corpus.yaml --reviewer "Your name"
python tools/booktool.py report --db local/reader.sqlite
python tools/booktool.py export --db local/reader.sqlite --out public/data/readings.json
```

- Rows without text are skipped and counted as `pending_rows`.
- Translations are staged as **reviews** (the same versioned audit trail as scan-checked OCR corrections). `--reviewer` is recorded against every staged entry.
- Re-running with unchanged text is a no-op (`unchanged`); edits create a new revision, keeping history.
- Validation is all-or-nothing per run and transactional: a bad row aborts the import without partial writes.
- No printed-page span is invented. Rows without `printed_start`/`printed_end` export without pages; the reader links to the topic scan instead.

`export` writes `public/data/readings.json` with **reviewed text only**. Publishing it (vs. keeping it local) needs the editor’s explicit approval, per the project’s proofread-before-release rule.

## Rebuilding or migrating the corpus

```sh
python tools/booktool.py build-corpus --check   # verify committed file still matches the edition index
python tools/booktool.py build-corpus --merge   # edition index changed: rebuild skeleton, keep entered text
python tools/booktool.py build-corpus           # refuses to overwrite an existing corpus
python tools/booktool.py build-corpus --force   # rebuild from scratch, discarding entered text
```

`--merge` fails rather than guessing when rows no longer align; a human then reconciles the file.

## The reader and Urdu

The app interface is available in **English and Urdu** (header toggle; the document switches to `lang="ur"`, `dir="rtl"`, and Noto Nastaliq Urdu). The reading-language control offers **All / Arabic / English / Urdu** independently of the interface language. Urdu transcriptions render right-to-left in Nastaliq; Arabic renders in Naskh; English in the reading serif. Language preference is kept per browser session.

## What this tooling deliberately does not do

- Translate anything, in any language.
- Fetch Qur’an/hadith text from the network.
- Publish text without an editor’s checked entry and an explicit `export`.
- Deduce per-entry printed pages the scan does not state.
