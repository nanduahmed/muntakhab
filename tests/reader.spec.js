import { expect, test } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

import { readFileSync } from 'node:fs';

const iman = '/#/read/kalimah-tayyibah/iman';
const wudu = '/#/read/salah/virtues-of-wudu';
const promises = '/#/read/ikhlas/promises-and-rewards';
const controls = (page, name) => page.getByRole('group', { name });

async function ready(page) { await expect(page.getByText('Loading reviewed text…')).toHaveCount(0); }


// Synthetic fixture, intercepted in these tests only; never shipped as reader text.
async function mockReviewedSnapshot(page) {
  const { sources } = JSON.parse(readFileSync(new URL('../data/book-index.json', import.meta.url), 'utf8'));
  const fixture = (id, printed_start, printed_end, more = {}) => ({
    id, printed_start, printed_end, status: 'reviewed',
    arabic: 'نص للاختبار فقط', english: 'Synthetic English fixture for this test.', ...more,
  });
  await page.route('**/data/readings.json', route => route.fulfill({ json: {
    schema_version: 1, pdf_sha256: sources.edition_pdf_sha256, locators: {},
    records: [
      fixture('ayah:kalimah-tayyibah.iman:1', 1, 1),
      fixture('ayah:kalimah-tayyibah.iman:6', 3, 3, { excerpt: true }),
      fixture('hadith:kalimah:1', 3, 3, { notes: 'Synthetic note for this test.' }),
      fixture('hadith:salah:243', 225, 226),
    ],
  } }));
}

test('table of contents is a keyboard disclosure with all seven groups', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Chapters', exact: true })).toBeVisible();
  await expect(page.locator('.chapter-toggle')).toHaveCount(7);
  const salah = page.getByRole('button', { name: /^Salah/ });
  const ablution = page.getByRole('link', { name: /Virtues of Wudu/ });
  await expect(salah).toHaveAttribute('aria-expanded', 'false');
  await expect(ablution).not.toBeVisible();
  await salah.focus();
  await page.keyboard.press('Enter');
  await expect(salah).toHaveAttribute('aria-expanded', 'true');
  await expect(ablution).toBeVisible();
  await ablution.click();
  await expect(page).toHaveURL(new RegExp(wudu + '$'));
  await expect(page.getByRole('heading', { level: 1, name: 'Virtues of Wudu (Ablution)' })).toBeVisible();
  await page.getByRole('navigation', { name: 'Breadcrumb' }).getByRole('link', { name: 'Salah' }).click();
  await expect(salah).toBeFocused();
  await expect(ablution).toBeVisible();
});

test('filter finds matching topics and recovers from no matches', async ({ page }) => {
  await page.goto('/');
  const input = page.getByRole('searchbox', { name: 'Find a chapter or topic' });
  await input.fill('salah WUDU');
  await expect(page.getByText('1 matching topic', { exact: true })).toBeVisible();
  await expect(page.getByRole('link', { name: /Virtues of Wudu/ })).toBeVisible();
  await input.fill('not in this edition');
  await expect(page.getByRole('heading', { name: 'No matching topics' })).toBeVisible();
  await page.getByRole('button', { name: 'Clear search', exact: true }).first().click();
  await expect(input).toHaveValue('');
  await expect(input).toBeFocused();
});

test('Ayat and Ahadith and language controls are independent', async ({ page }) => {
  await mockReviewedSnapshot(page);
  await page.goto(iman); await ready(page);
  const ayah = page.getByRole('article', { name: 'Qur’an 21:25' });
  await expect(ayah.locator('[lang=ar]')).toHaveAttribute('dir', 'rtl');
  await expect(ayah.getByText(/Synthetic English fixture/)).toBeVisible();
  await expect(ayah.getByRole('link', { name: /Scan · p\. 1/ })).toHaveAttribute('href', /#20-21$/);
  await expect(page.getByText('Qur’an excerpt', { exact: true })).toBeVisible();
  await controls(page,'Reading language').getByRole('button', { name: 'Arabic' }).click();
  await expect(ayah.locator('.translation')).toHaveCount(0);
  await controls(page,'Reading type').getByRole('button', { name: /Ahadith/ }).click();
  const hadith = page.getByRole('article', { name: 'Hadith 1', exact: true });
  await expect(hadith.locator('.arabic')).toBeVisible();
  await expect(hadith.locator('.translation')).toHaveCount(0);
  await controls(page,'Reading language').getByRole('button', { name: 'English' }).click();
  await expect(hadith.getByText(/Synthetic English fixture/)).toBeVisible();
  await expect(hadith.locator('.arabic')).toHaveCount(0);
  await hadith.getByText('Edition note', { exact: true }).click();
  await expect(hadith.getByText(/Synthetic note/)).toBeVisible();
  await page.reload(); await ready(page);
  await expect(controls(page,'Reading language').getByRole('button', { name: 'English' })).toHaveAttribute('aria-pressed', 'true');
});

test('zero opening passages get a distinct empty state and default to Ahadith', async ({ page }) => {
  await page.goto(promises); await ready(page);
  await expect(page.getByRole('article', { name: 'Hadith 25' })).toBeVisible();
  await controls(page,'Reading type').getByRole('button', { name: /Ayat/ }).click();
  await expect(page.getByRole('heading', { name: 'No standalone Ayat in this topic' })).toBeVisible();
  await page.getByRole('button', { name: 'Read the Ahadith' }).click();
  await expect(page.getByRole('article', { name: 'Hadith 25' })).toBeVisible();
});

test('long sequences page progressively or resolve an exact entry URL', async ({ page }) => {
  await page.goto(`${iman}?view=hadith`); await ready(page);
  await expect(page.getByRole('article')).toHaveCount(12);
  await page.getByRole('button', { name: 'Show more Ahadith' }).click();
  await expect(page.getByRole('article')).toHaveCount(24);
  await expect(page.getByRole('article', { name: 'Hadith 13', exact: true })).toBeFocused();
  await page.goto(`${iman}?entry=hadith%3Akalimah%3A69`); await ready(page);
  await expect(page.getByRole('article', { name: 'Hadith 69' })).toBeFocused();
  await expect(page.getByRole('article', { name: 'Hadith 69' }).getByText('Reference only')).toBeVisible();
});

test('source failure and invalid route do not strand the reader', async ({ page }) => {
  await page.route('**/data/readings.json', (route) => route.abort());
  await page.goto(iman);
  await expect(page.getByRole('status').filter({ hasText: 'Text could not be loaded' })).toBeVisible();
  await expect(page.getByRole('article', { name: 'Qur’an 21:25' }).getByRole('link', { name: /Open topic scan/ })).toBeVisible();
  await page.goto('/#/read/missing/missing');
  await expect(page.getByRole('heading', { name: 'Topic not found' })).toBeVisible();
  await page.getByRole('link', { name: 'Back to contents' }).click();
  await expect(page.getByRole('heading', { name: 'Chapters', exact: true })).toBeVisible();
});

test('mobile reader stays inside the viewport at 320 and 390 CSS pixels', async ({ page }) => {
  await mockReviewedSnapshot(page);
  for (const width of [320,390]) {
    await page.setViewportSize({ width, height: 844 });
    await page.goto('/');
    await expect(page.locator('.chapter-toggle')).toHaveCount(7);
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(width);
    await page.goto(`${wudu}?view=hadith`); await ready(page);
    await expect(page.getByRole('article', { name: 'Hadith 243', exact: true }).getByRole('link', { name: /225–226/ })).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(width);
  }
});

test('contents and reviewed topic pass automated axe A/AA checks', async ({ page }) => {
  await mockReviewedSnapshot(page);
  for (const path of ['/', iman]) {
    await page.goto(path); await ready(page);
    const result = await new AxeBuilder({ page }).withTags(['wcag2a','wcag2aa','wcag21a','wcag21aa']).analyze();
    expect(result.violations, path).toEqual([]);
  }
});


test('public snapshot starts in reference-only mode without a load error', async ({ page }) => {
  await page.goto(iman); await ready(page);
  const entry = page.getByRole('article', { name: 'Qur’an 21:25' });
  await expect(entry.getByText('Reference only')).toBeVisible();
  await expect(entry.getByRole('link', { name: /Open topic scan/ })).toBeVisible();
  await expect(page.getByText(/Text could not be loaded/)).toHaveCount(0);
});
