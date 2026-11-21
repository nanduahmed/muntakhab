# Full-edition extraction run

This records the local prototype run. The public source checkout excludes the scan, OCR bundles, database, and checked samples. It opens with references and scan links only.

**Source:** the 349-scan [Islamic Bulletin PDF](https://islamicbulletin.org/en/ebooks/resources/muntakhab_ahadith_complete.pdf), SHA-256 `1baf1cabf4e504979fce346fb37f823a442b59ac4db503fa7a241143c8c106db`. The run processed all 671 numbered body pages; front and back matter are not staged as readings. OCR used Tesseract 5.5.0 with English and Arabic at 190 DPI, with localized Arabic retries at 300 DPI.

| Unit | Expected inventory | English OCR candidate | Arabic OCR candidate | Checked for the wireframe |
| --- | ---: | ---: | ---: | ---: |
| Opening Qur’an passages (398 ayat) | 214 | 214 | 214 | 9 |
| Numbered Ahadith | 1,507 | 1,507 | 1,507 | 5 |
| **Total** | **1,721** | **1,721** | **1,721** | **14** |

**Candidate does not mean verified.** The counts above measure detected entry anchors and the presence of text in each language. They do not certify correct wording, complete passage boundaries, or reliable diacritics. In this run, 1,574 records were flagged for low Arabic OCR confidence. Only 14 scan-checked sample readings appear as text in the wireframe; the other 1,707 entries have reference cards and estimated scan links. An independent proofread remains necessary before publishing the corpus.

## Edition cases checked

- `ʿIlm` and `Dhikr` each have a Hadith #1; sequence-qualified IDs preserve both.
- Qur’an 49:11–13 spans pp. 424–425. Qur’an 83:1–6 on p. 488 has a punctuation variant. Both retain the normalized index reference and scan evidence.
- The output includes the easily missed Kalimah #190 and Da‘wat #149 in the primary scan, not from a secondary transcription.
- A regular pass left 25 hadith records without Arabic OCR. A tightly cropped retry found 23; scan-checked crop bounds covered Ikram #228 across pp. 471–472 and Ikram #301 on p. 497. Separate number-anchor hints cover Dhikr #11 and Ikram #72. These hints do not approve the extracted wording.
- Iman shows bilingual passages and hadith; Wudu includes the two-page Hadith #243; the Ikhlas promises topic demonstrates a section with no standalone Ayat.

## Database and browser checks

- The first import inserted 1,721 draft rows. A byte-identical rerun from the OCR cache and reimport changed no rows and protected all 14 reviews. On a separate database seeded from the earlier OCR pass, importing the final run updated 25 draft rows and preserved every checked reading.
- The staged database passes SQLite integrity and foreign-key checks. Every source locator reconciles to the pinned edition and every installed topic opens by URL. The build, 17 pipeline tests, and 8 Chromium reader tests passed, including width checks at 320 and 390 CSS pixels and automated axe checks on contents and a reviewed topic. Automated checks are not a full accessibility audit.

## Files from the local run (not committed)

- `artifacts/muntakhab.sqlite` — local staging database with the edition, indexed entries, draft history, and checked samples.
- `artifacts/extraction.json` — raw OCR candidates and scan evidence, independently importable.
- `artifacts/review-audit.tsv` — one row per expected entry, with initial excerpts, flags, and starting scan links.
- `artifacts/db-report.json` — actual staged and checked counts per topic.
- `public/data/readings.json` — safe read-only export for the prototype: checked words plus approximate scan locators, no unreviewed OCR text.

See the [project README](../README.md) for re-extracting, reviewing, applying updates, and exporting the reader snapshot.
