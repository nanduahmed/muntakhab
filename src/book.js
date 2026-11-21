import book from '../data/book-index.json';

export { book };
export const fmt = (number) => number.toLocaleString('en');
export const qty = (number, one, many = `${one}s`) => `${fmt(number)} ${number === 1 ? one : many}`;
export const printed = ({ printed_start: from, printed_end: to }) => from === to ? `p. ${from}` : `pp. ${from}–${to}`;
export const pageNumber = (n) => String(n).padStart(2, '0');
export const topics = book.chapters.flatMap((chapter) => chapter.subchapters.map((topic) => ({ chapter, topic })));
export const topicSlug = (topic) => topic.id.split('.')[1];
export const readingPath = (chapter, topic) => `/read/${chapter.id}/${topicSlug(topic)}`;
export function spreadUrl(printedPage) {
  const scan = book.chapters[0].pages.pdf_start + Math.floor((printedPage - 1) / 2);
  return `${book.sources.flipbook.split('#')[0]}#${2 * scan - 2}-${2 * scan - 1}`;
}

export function inventory(topic, kind) {
  if (kind === 'ayah') return topic.quran_references.map((reference, k) => ({ id: `ayah:${topic.id}:${k + 1}`, title: `Qur’an ${reference.replace('-', '–')}`, kind }));
  const { first, last, sequence_id: sequence } = topic.hadith_numbers;
  return Array.from({ length: last - first + 1 }, (_, k) => ({ id: `hadith:${sequence}:${first + k}`, title: `Hadith ${first + k}`, kind }));
}

export function searchable(value) {
  return value.normalize('NFD').toLowerCase().replace(/\p{M}/gu, '').replace(/[‘’'ʿʻ]/g, '').replace(/[^a-z0-9\p{Script=Arabic}]+/gu, ' ').trim();
}
