import React, { createContext, useContext, useLayoutEffect, useMemo, useState } from 'react';
import { storage } from './storage';

export const UI_LANGUAGES = [
  { code: 'en', label: 'English', dir: 'ltr' },
  { code: 'ur', label: 'اردو', dir: 'rtl' },
];

// Every user-facing string in the app, in both interface languages.
// Book content (chapter titles, Qur’an references, transcriptions) is never translated here.
const dictionary = {
  en: {
    'brand.home': 'Muntakhab Reading Room home',
    'brand.tagline': 'READING ROOM',
    'nav.contents': 'Contents',
    'nav.edition': 'About the edition',
    'nav.primary': 'Primary',
    'nav.breadcrumb': 'Breadcrumb',
    'action.originalScan': 'Original scan',
    'action.scanShort': 'Scan',
    'action.opensNewTab': 'opens in a new tab',
    'skip.toContent': 'Skip to content',
    'header.uiLanguage': 'Interface language',
    'footer.about': 'About the edition',
    'footer.mark': 'The Muntakhab Reading Room',

    'hero.kicker': 'THE READING ROOM',
    'hero.description': 'A selection of Qur’an passages and Ahadith relating to the six qualities of Da‘wat and Tabligh.',
    'hero.browse': 'Browse chapters',

    'contents.kicker': 'TABLE OF CONTENTS',
    'contents.heading': 'Chapters',
    'contents.searchPlaceholder': 'Find a topic…',
    'contents.searchLabel': 'Find a chapter or topic',
    'contents.clearSearch': 'Clear search',
    'contents.helpDefault': 'Expand a chapter to explore its topics.',
    'contents.conclusionLabel': 'Concluding section',
    'contents.emptyTitle': 'No matching topics',
    'contents.emptyHelp': 'Try a chapter name, “prayer”, or “Wudu”.',

    'overview.kicker': 'AT A GLANCE',
    'overview.chapters': 'Chapters',
    'overview.topics': 'Topics',
    'overview.ayat': 'Ayat',
    'overview.ahadith': 'Ahadith',
    'overview.note': 'Six main chapters and a concluding section, in the order of the printed book.',
    'teaser.title': 'Arabic · English · Urdu',
    'teaser.body': 'Read the original Arabic with English or Urdu, or open the source scan.',
    'teaser.link': 'About this edition',

    'topic.chapter': 'CHAPTER',
    'topic.conclusion': 'CONCLUDING SECTION',
    'topic.topic': 'TOPIC',
    'topic.ayat': 'Ayat',
    'topic.ahadith': 'Ahadith',

    'reader.readingType': 'Reading type',
    'reader.readingLanguage': 'Reading language',
    'reader.all': 'All',
    'reader.arabic': 'Arabic',
    'reader.english': 'English',
    'reader.urdu': 'Urdu',
    'reader.loading': 'Loading reviewed text…',
    'reader.loadFailed': 'Text could not be loaded. References and scan links are still available.',
    'reader.noAyatTitle': 'No standalone Ayat in this topic',
    'reader.noAyatBody': 'The printed topic begins with Ahadith.',
    'reader.readAhadith': 'Read the Ahadith',
    'reader.showMorePassages': 'Show more passages',
    'reader.showMoreAhadith': 'Show more Ahadith',
    'reader.showingOf': 'Showing {shown} of {total}',
    'reader.guideKicker': 'IN THIS TOPIC',
    'reader.sourceEdition': 'SOURCE EDITION',
    'reader.originalScan': 'Original scan',
    'reader.previewKicker': 'READING PREVIEW',
    'reader.previewSome': '{count} in this topic. Other entries link to the scan.',
    'reader.previewNone': 'This topic currently shows references with links to the scan.',
    'reader.previous': 'PREVIOUS TOPIC',
    'reader.next': 'NEXT TOPIC',
    'reader.adjacentTopics': 'Adjacent topics',

    'entry.quran': 'Qur’an',
    'entry.hadith': 'Hadith',
    'entry.excerpt': 'Qur’an excerpt',
    'entry.passage': 'Qur’an passage',
    'entry.narration': 'Narration',
    'entry.referenceOnly': 'Reference only',
    'entry.noTranscript': 'No {language} transcription available for this entry.',
    'entry.notAvailableIn': 'Not available in: {languages}.',
    'entry.editionNote': 'Edition note',
    'entry.scanWithPages': 'Scan · {pages}',
    'entry.scanNear': 'Find in scan · near p. {page}',
    'entry.openTopicScan': 'Open topic scan',

    'edition.kicker': 'THE SOURCE TEXT',
    'edition.title': 'About the edition',
    'edition.printedBook': 'The printed book',
    'edition.printedBookBody': 'This reading room follows the Arabic and English scan hosted by The Islamic Bulletin. The numbered pages in this reader refer to the book, not the PDF viewer’s page counter.',
    'edition.compiledBy': 'Compiled by',
    'edition.organizedBy': 'Organized and presented by',
    'edition.imprint': 'Imprint',
    'edition.preview': 'What the preview includes',
    'edition.previewBody1': 'Browse every topic. Where a transcription was checked for the prototype, the reader shows it; otherwise it shows the reference and a link to the scan. The counts are for the whole printed book, not the transcribed preview.',
    'edition.previewBody2': 'An opening Qur’an passage can contain more than one ayat. Ayat quoted inside numbered Ahadith are not counted separately.',
    'edition.sourcesKicker': 'SOURCE LINKS',
    'edition.flipbook': 'Open the original flipbook',
    'edition.pdf': 'Open the PDF scan',
    'edition.contents': 'Printed table of contents',

    'notfound.title': 'Topic not found',
    'notfound.body': 'Check the link or choose a topic from the table of contents.',
    'notfound.back': 'Back to contents',
  },
  ur: {
    'brand.home': 'منتخب مطالعہ گاہ — صفحۂ اول',
    'brand.tagline': 'مطالعہ گاہ',
    'nav.contents': 'فہرست',
    'nav.edition': 'ایڈیشن کے بارے میں',
    'nav.primary': 'بنیادی راہ نمائی',
    'nav.breadcrumb': 'مسیرِ راہ',
    'action.originalScan': 'اصل اسکین',
    'action.scanShort': 'اسکین',
    'action.opensNewTab': 'نئے ٹیب میں کھلتا ہے',
    'skip.toContent': 'مرکزی مواد پر جائیں',
    'header.uiLanguage': 'انٹرفیس کی زبان',
    'footer.about': 'ایڈیشن کے بارے میں',
    'footer.mark': 'منتخب مطالعہ گاہ',

    'hero.kicker': 'مطالعہ گاہ',
    'hero.description': 'دعوت و تبلیغ کی چھ صفات سے متعلق قرآنِ کریم کی عبارتوں اور احادیث کا انتخاب۔',
    'hero.browse': 'ابواب دیکھیں',

    'contents.kicker': 'فہرستِ مضامین',
    'contents.heading': 'ابواب',
    'contents.searchPlaceholder': 'موضوع تلاش کریں…',
    'contents.searchLabel': 'باب یا موضوع تلاش کریں',
    'contents.clearSearch': 'تلاش صاف کریں',
    'contents.helpDefault': 'موضوعات دیکھنے کے لیے کوئی باب کھولیں۔',
    'contents.conclusionLabel': 'اختتامی حصہ',
    'contents.emptyTitle': 'کوئی موضوع نہیں ملا',
    'contents.emptyHelp': 'باب کا نام مثلاً “نماز” یا “وضو” آزما کر دیکھیں۔',

    'overview.kicker': 'ایک نظر میں',
    'overview.chapters': 'ابواب',
    'overview.topics': 'موضوعات',
    'overview.ayat': 'آیات',
    'overview.ahadith': 'احادیث',
    'overview.note': 'کتاب کی ترتیب میں چھ مرکزی ابواب اور ایک اختتامی حصہ۔',
    'teaser.title': 'عربی · انگریزی · اردو',
    'teaser.body': 'اصل عربی متن اردو یا انگریزی ترجمے کے ساتھ پڑھیں، یا منتخب اسکین کھولیں۔',
    'teaser.link': 'اس ایڈیشن کے بارے میں',

    'topic.chapter': 'باب',
    'topic.conclusion': 'اختتامی حصہ',
    'topic.topic': 'موضوع',
    'topic.ayat': 'آیات',
    'topic.ahadith': 'احادیث',

    'reader.readingType': 'مطالعے کی قسم',
    'reader.readingLanguage': 'مطالعے کی زبان',
    'reader.all': 'سب',
    'reader.arabic': 'عربی',
    'reader.english': 'انگریزی',
    'reader.urdu': 'اردو',
    'reader.loading': 'جائزہ شدہ متن لوڈ ہو رہا ہے…',
    'reader.loadFailed': 'متن لوڈ نہیں ہو سکا۔ حوالے اور اسکین کے لنکس دستیاب ہیں۔',
    'reader.noAyatTitle': 'اس موضوع میں آیات کا کوئی مستقل حصہ نہیں',
    'reader.noAyatBody': 'طباعت شدہ موضوع براہِ راست احادیث سے شروع ہوتا ہے۔',
    'reader.readAhadith': 'احادیث پڑھیں',
    'reader.showMorePassages': 'مزید اقتباسات دکھائیں',
    'reader.showMoreAhadith': 'مزید احادیث دکھائیں',
    'reader.showingOf': '{total} میں سے {shown} دکھائے جا رہے ہیں',
    'reader.guideKicker': 'اس موضوع میں',
    'reader.sourceEdition': 'ماخذ ایڈیشن',
    'reader.originalScan': 'اصل اسکین',
    'reader.previewKicker': 'مطالعے کا پیش نظارہ',
    'reader.previewSome': 'اس موضوع میں {count}۔ باقی اندراجات اسکین کی طرف لے جاتے ہیں۔',
    'reader.previewNone': 'فی الحال اس موضوع میں حوالے اور اسکین کے لنکس دکھائے جا رہے ہیں۔',
    'reader.previous': 'پچھلا موضوع',
    'reader.next': 'اگلا موضوع',
    'reader.adjacentTopics': 'ملحقہ موضوعات',

    'entry.quran': 'قرآن',
    'entry.hadith': 'حدیث',
    'entry.excerpt': 'قرآنی اقتباس',
    'entry.passage': 'قرآنی عبارت',
    'entry.narration': 'روایت',
    'entry.referenceOnly': 'صرف حوالہ',
    'entry.noTranscript': 'اس اندراج کے لیے {language} متن دستیاب نہیں۔',
    'entry.notAvailableIn': 'دستیاب نہیں: {languages}۔',
    'entry.editionNote': 'ایڈیشن نوٹ',
    'entry.scanWithPages': 'اسکین · {pages}',
    'entry.scanNear': 'اسکین میں دیکھیں · ص {page} کے قریب',
    'entry.openTopicScan': 'موضوع کا اسکین کھولیں',

    'edition.kicker': 'ماخذی متن',
    'edition.title': 'ایڈیشن کے بارے میں',
    'edition.printedBook': 'طباعت شدہ کتاب',
    'edition.printedBookBody': 'یہ مطالعہ گاہ دی اسلامک بلیٹن کی میزبان عربی و انگریزی سکانی کاپی کی پیروی کرتی ہے۔ اس میں صفحے کے نمبر کتاب کے ہیں، پی ڈی ایف ویوور کے نہیں۔',
    'edition.compiledBy': 'مرتب',
    'edition.organizedBy': 'ترتیب و پیشکش',
    'edition.imprint': 'ناشر',
    'edition.preview': 'پیش نظارہ میں کیا شامل ہے',
    'edition.previewBody1': 'ہر موضوع دیکھیں۔ جہاں پیش نما کے نمونے کے لیے نقل شدہ متن کی جانچ ہو چکی ہے وہاں وہ دکھایا جاتا ہے؛ ورنہ حوالہ اور اسکین کا لنک دکھایا جاتا ہے۔ گنتی پورے طباعت شدہ کتاب کی ہے، صرف نقل شدہ حصے کی نہیں۔',
    'edition.previewBody2': 'ابتدائی قرآنی عبارت میں ایک سے زیادہ آیات ہو سکتی ہیں۔ نمبر شدہ احادیث کے اندر نقل شدہ آیات الگ سے نہیں گنی جاتیں۔',
    'edition.sourcesKicker': 'ماخذ لنکس',
    'edition.flipbook': 'اصل فلیپ بک کھولیں',
    'edition.pdf': 'پی ڈی ایف سکانی کھولیں',
    'edition.contents': 'طباعت شدہ فہرستِ مضامین',

    'notfound.title': 'موضوع نہیں ملا',
    'notfound.body': 'لنک چیک کریں یا فہرستِ مضامین سے کوئی موضوع منتخب کریں۔',
    'notfound.back': 'فہرست کی طرف واپس',
  },
};

// count() needs number words/noun forms per language: [singular, plural]
const units = {
  en: {
    topic: ['topic', 'topics'],
    ayat: ['ayat', 'ayat'],
    ahadith: ['hadith', 'ahadith'],
    passage: ['passage', 'passages'],
    entry: ['entry', 'entries'],
    transcribed: ['transcribed entry', 'transcribed entries'],
    'matching-topic': ['matching topic', 'matching topics'],
  },
  ur: {
    topic: ['موضوع', 'موضوعات'],
    ayat: ['آیت', 'آیات'],
    ahadith: ['حدیث', 'احادیث'],
    passage: ['اقتباس', 'اقتباسات'],
    entry: ['اندراج', 'اندراجات'],
    transcribed: ['نقل شدہ اندراج', 'نقل شدہ اندراجات'],
    'matching-topic': ['ملتا جلتا موضوع', 'ملتے جلتے موضوعات'],
  },
};

const fmtNumber = (n) => Number(n).toLocaleString('en');

export function interpolate(template, values) {
  return Object.entries(values).reduce((text, [key, value]) => text.replaceAll(`{${key}}`, String(value)), template);
}

export function formatPages(lang, { printed_start: from, printed_end: to }) {
  const same = from === to;
  if (lang === 'ur') return same ? `ص ${fmtNumber(from)}` : `ص ${fmtNumber(from)}–${fmtNumber(to)}`;
  return same ? `p. ${from}` : `pp. ${from}–${to}`;
}

const UiLangContext = createContext({ lang: 'en', dir: 'ltr', t: (key) => key, count: (n) => String(n), fmt: fmtNumber, pages: ({ printed_start: from, printed_end: to }) => (from === to ? `p. ${from}` : `pp. ${from}–${to}`), setLang: () => {} });

export function UiLanguageProvider({ children }) {
  const [lang, setLang] = useState(() => (storage.get('mr-ui-language', 'en') === 'ur' ? 'ur' : 'en'));
  const dir = lang === 'ur' ? 'rtl' : 'ltr';

  useLayoutEffect(() => {
    document.documentElement.lang = lang;
    document.documentElement.dir = dir;
    storage.set('mr-ui-language', lang);
  }, [lang, dir]);

  const value = useMemo(() => {
    const strings = dictionary[lang];
    const fallback = dictionary.en;
    const t = (key, values) => {
      const template = strings[key] ?? fallback[key] ?? key;
      return values ? interpolate(template, values) : template;
    };
    const count = (n, unit) => {
      const pair = (units[lang] ?? units.en)[unit] ?? units.en[unit] ?? [unit, unit];
      return `${fmtNumber(n)} ${n === 1 ? pair[0] : pair[1]}`;
    };
    const pages = (range) => formatPages(lang, range);
    return { lang, dir, t, count, fmt: fmtNumber, pages, setLang };
  }, [lang, dir]);

  return <UiLangContext.Provider value={value}>{children}</UiLangContext.Provider>;
}

export function useI18n() {
  return useContext(UiLangContext);
}
