# AGENTS.md — Muntakhab Reading Room

These instructions apply to the whole `muntakhab-reader/` project. Run the commands below from this directory. Read the [README](README.md) for setup, the [UX findings](docs/UX-findings.md) for product decisions, and the [extraction results](docs/extraction-results.md) for the measured baseline.

## Which skill to consult

Open the relevant installed `SKILL.md` before making UI or UX changes. Skill paths below are relative to the project root in the shared workspace.

| Change | Read first |
| --- | --- |
| Chapter hierarchy, topic labels, search/filtering, URLs, or breadcrumbs | [`information-architecture`](../.claude/skills/information-architecture/SKILL.md) |
| Reading journeys, navigation between screens, or loading, empty, and error states | [`ux-flow-planner`](../.claude/skills/ux-flow-planner/SKILL.md) |
| Layout, typography, Arabic/English presentation, components, responsive design, or accessibility | [`ui-ux-pro-max`](../.claude/skills/ui-ux-pro-max/SKILL.md) |
| Shared tokens or component styling conventions | [`design-system`](../.claude/skills/design-system/SKILL.md), optionally [`ui-styling`](../.claude/skills/ui-styling/SKILL.md). Keep the existing React and CSS setup; do not adopt a new framework just because a skill suggests it. |
| OCR, record identity, database, or export | Use the pinned scan, manifest, CLI help, and pipeline tests. UX skills are not transcription or source authorities. |

This source checkout does not bundle the workspace skills. If they are unavailable, use the recorded decisions in `docs/UX-findings.md`. Document substantive flow or navigation changes there.

## Code and data organization

| Path | Responsibility |
| --- | --- |
| `src/main.jsx` | React routes and reader screens: chapter disclosure, topic pages, type/language switches, and fallback states. |
| `src/book.js` | Frontend helpers for topic URLs, indexed entries, and scan links. |
| `src/styles.css`, `src/HeroArt.jsx`, `public/mark.svg` | Shared CSS tokens, responsive reading layout, and decorative artwork. |
| `data/book-index.json` | Runtime edition manifest: chapter order, topic IDs, citations, numbering sequences, and page map. Derived from `../muntakhab-ahadith-index.yaml`; the runtime manifest is self-contained in this checkout. |
| `data/scan-anchor-hints.json` | PDF-pinned OCR locator hints, not reviewed text. |
| `tools/booktool.py`, `tools/book_model.py` | CLI entry point and manifest validation, stable IDs, and page mapping. |
| `tools/ocr_engine.py`, `tools/segment.py` | Split-scan rendering, OCR cache and coordinates, and segmentation into candidate readings. |
| `tools/store.py` | SQLite import, draft and review history, validation, and the reader export. |
| `public/data/readings.json` | Generated browser snapshot. Use `booktool.py export` for local reads; keep the checked-in snapshot reference-only unless publication is approved. Never put a raw OCR bundle here. |
| `artifacts/`, `local/` | Keep the PDF, extraction bundles, review sheets, and working databases untracked. No run artifacts are included in the source checkout. |
| `tests/`, `docs/` | Python and browser regression tests; UX decisions and verified run findings. |

## Read and verify PDF inputs

1. **Use the pinned edition.** The [Islamic Bulletin PDF](https://islamicbulletin.org/en/ebooks/resources/muntakhab_ahadith_complete.pdf) has 349 physical PDF pages. Its SHA-256 is `1baf1cabf4e504979fce346fb37f823a442b59ac4db503fa7a241143c8c106db`. The CLI rejects a different checksum. If the scan changes, stop and validate a new edition manifest and page map; do not bypass the check or reuse this edition’s hints.
2. **Use printed page numbers for review.** This is an image scan, not a reliable text-layer PDF. For a numbered printed page `p`, its one-based PDF page is `11 + floor((p − 1) / 2)`. Odd pages are on the left, even pages on the right. For a body PDF page `n`, the viewer spread is `#(2n−2)-(2n−1)`. Use `source-page` to render the correct half; inspect adjacent pages if text or a note continues.
3. **Start small.** Use Python 3.11+, PyMuPDF (`tools/requirements.txt`), and Tesseract 5 with `eng` and `ara`. Download the source once to `local/book.pdf`. Use the opening Qur’an citations and hadith ranges in the manifest to guide OCR segmentation, not to fill missing words. Check the proposed boundaries, text, and citations against the scan; an OCR confidence score or a matching count does not prove accuracy.

```sh
python tools/booktool.py source-page --pdf local/book.pdf --printed 225 --out local/p225.png
python tools/booktool.py extract --pdf local/book.pdf \
  --topic salah.virtues-of-wudu --out local/wudu-ocr.json
python tools/booktool.py audit --bundle local/wudu-ocr.json --tsv local/wudu-audit.tsv
```

Repeat `--topic` to check more than one topic. Omit it only when a full run is needed (printed body pp. 1–671). Reuse `.cache/ocr/` when the OCR settings and language models have not changed. If a boundary cannot be located, retain the unresolved record and its scan window; do not guess a translation or borrow one from another edition.

## Protect content and data

- **Preserve identity and counts.** Use `ayah:<topic-id>:<1-based-passage-position>` and `hadith:<sequence-id>:<printed-number>`. ‘Ilm and Dhikr each have a Hadith #1. Preserve repeated Qur’an references, excerpts, verse ranges, and variants under the same printed hadith number. The baseline is 29 topics, 214 standalone Qur’an passages covering 398 ayat, and 1,507 numbered Ahadith. Embedded quotes, notes, and front/back matter are not additional readings. Do not renumber existing IDs or edit the manifest and database fingerprint to force an import; treat legitimate ID or edition changes as a migration.
- **Separate OCR from approval.** Import into a dedicated local SQLite file or a copy, first with `import --dry-run`. Keep reimports transactional and idempotent. On corrections, use `review-sheet`, verify wording and exact printed pages, and apply an explicit `accept` with a reviewer and the current `base_revision`. Leave an unchecked language blank (`null`). Preserve history and never promote bulk OCR or overwrite reviewed text during extraction.
- **Publish checked text only.** Export to `public/data/readings.json` from SQLite. Reference-only entries may have estimated scan links, never draft text. Keep raw bundles, SQLite files, and downloaded scans out of `public/`. Do not modify a production database or publish a new corpus without explicit approval.
- **Preserve reading behavior.** Keep chapter disclosures keyboard-operable, topic URLs stable, Ayat/Ahadith and language controls separate, and Arabic marked with `lang="ar"` and `dir="rtl"`. A topic with no standalone Ayat should open to Ahadith. A failed snapshot request must still leave references and scan links available.

## Verify before handing off

```sh
# Pipeline: no OCR engine needed for these unit tests.
python -m unittest discover -s tests -p 'test_*.py'

# Frontend, after installing dependencies and Playwright Chromium.
npm ci
npx playwright install chromium
npm run test:ui
npm run build
```

For extraction changes, verify a real sample on the pinned scan as well as the unit tests. Useful regression cases: Wudu Hadith #243 spans pp. 225–226; Qur’an 49:11–13 spans pp. 424–425; the Ikhlas promises topic has no standalone Ayat. For import changes, check an exact reimport and a changed draft against a database that already contains a review. Report expected entries, draft coverage by language, and reviewed counts separately. Update the appropriate `docs/` file when the flow, run results, or workflow changes.
