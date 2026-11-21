import React, { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { HashRouter, Link, NavLink, Route, Routes, useLocation, useParams, useSearchParams } from 'react-router-dom';
import { ArrowDown, ArrowLeft, ArrowRight, ArrowUpRight, BookOpen, ChevronDown, ChevronRight, FileText, LibraryBig, Search, X } from 'lucide-react';
import '@fontsource-variable/dm-sans';
import '@fontsource-variable/lora';
import '@fontsource-variable/lora/wght-italic.css';
import '@fontsource/noto-naskh-arabic/400.css';
import '@fontsource/noto-nastaliq-urdu/400.css';
import '@fontsource/noto-nastaliq-urdu/600.css';
import './styles.css';
import { book, fmt, inventory, pageNumber, readingPath, searchable, spreadUrl, topicSlug, topics } from './book';
import { UI_LANGUAGES, UiLanguageProvider, useI18n } from './i18n.jsx';
import { storage } from './storage';
import { HeroArt } from './HeroArt';

const defaultOpen = [book.chapters[0].id];
const emptyReadings = new Map();
const icon = { size: 16, strokeWidth: 1.7, 'aria-hidden': true };
const flip = 'flip-rtl';

function openScan(url, children, className = 'text-link', t) {
  return <a className={className} href={url} target="_blank" rel="noreferrer">{children}<ArrowUpRight {...icon} /><span className="sr-only"> ({t('action.opensNewTab')})</span></a>;
}

function Header() {
  const { t, lang, setLang } = useI18n();
  return <header className="site-head">
    <div className="wrap masthead">
      <Link to="/" className="brand" aria-label={t('brand.home')}><img src="./mark.svg" alt="" width="37" height="37" /><span>Muntakhab<small>{t('brand.tagline')}</small></span></Link>
      <nav className="site-nav" aria-label={t('nav.primary')}><NavLink end to="/">{t('nav.contents')}</NavLink><NavLink to="/edition">{t('nav.edition')}</NavLink></nav>
      <div className="header-actions">
        <div className="ui-language" role="group" aria-label={t('header.uiLanguage')}>
          {UI_LANGUAGES.map(({ code, label }) => <button key={code} type="button" aria-pressed={lang === code} onClick={() => setLang(code)}>{label}</button>)}
        </div>
        {openScan(book.sources.flipbook, <><span className="scan-long">{t('action.originalScan')}</span><span className="scan-short">{t('action.scanShort')}</span></>, 'scan-link', t)}
      </div>
    </div>
  </header>;
}

function Footer() {
  const { t } = useI18n();
  return <footer className="wrap site-foot"><span className="foot-mark"><BookOpen {...icon} /> {t('footer.mark')}</span><Link to="/edition">{t('footer.about')}</Link></footer>;
}

function FocusRoute() {
  const { pathname, state } = useLocation();
  const previous = useRef(null);
  useLayoutEffect(() => {
    if (previous.current !== null && !(pathname === '/' && state?.chapter)) {
      window.scrollTo(0, 0);
      document.getElementById('main')?.focus({ preventScroll: true });
    }
    previous.current = pathname;
  }, [pathname]); // changes to entry filters don't reset position
  return null;
}

function Contents({ opened, setOpened, query, setQuery }) {
  const { t, count, fmt } = useI18n();
  const location = useLocation();
  const [overrides, setOverrides] = useState({});
  const searchBox = useRef(null);
  const normalized = searchable(query);
  const groups = useMemo(() => book.chapters.map((chapter) => {
    if (!normalized) return { chapter, matches: chapter.subchapters };
    const attr = searchable([chapter.title, chapter.meaning, ...(chapter.aliases || [])].join(' '));
    return { chapter, matches: chapter.subchapters.filter((topic) => normalized.split(' ').every((word) => attr.includes(word) || searchable(topic.title).includes(word))) };
  }).filter(({ matches }) => matches.length), [normalized]);

  useEffect(() => { document.title = 'Muntakhab · Reading Room'; }, []);
  useLayoutEffect(() => {
    const chapter = location.state?.chapter;
    if (!chapter || !book.chapters.some((x) => x.id === chapter)) return;
    setQuery('');
    setOpened((old) => old.includes(chapter) ? old : [...old, chapter]);
    const id = requestAnimationFrame(() => {
      const element = document.getElementById(`chapter-${chapter}`);
      element?.scrollIntoView({ block: 'start' });
      element?.focus({ preventScroll: true });
    });
    return () => cancelAnimationFrame(id);
  }, [location.key, location.state?.chapter, setOpened, setQuery]);

  function setFilter(value) { setQuery(value); setOverrides({}); }
  function toggle(id, isOpen) {
    if (normalized) setOverrides((prev) => ({ ...prev, [id]: !isOpen }));
    else setOpened((old) => old.includes(id) ? old.filter((it) => it !== id) : [...old, id]);
  }
  function goToContents() {
    const target = document.getElementById('chapters');
    target?.scrollIntoView({ block: 'start' }); target?.focus({ preventScroll: true });
  }

  return <main id="main" className="wrap" tabIndex={-1}>
    <section className="hero" aria-labelledby="home-title">
      <div className="hero-copy">
        <p className="eyebrow hero-kicker"><span aria-hidden="true" className="diamond" /> {t('hero.kicker')}</p>
        <h1 id="home-title">Muntakhab <em>Ahadith</em></h1>
        <p className="hero-description">{t('hero.description')}</p>
        <button className="primary-button" onClick={goToContents}>{t('hero.browse')} <ArrowDown {...icon} /></button>
      </div>
      <div className="hero-image"><HeroArt /></div>
    </section>
    <div className="collection-layout">
      <section aria-labelledby="chapters">
        <div className="collection-heading">
          <div><p className="eyebrow">{t('contents.kicker')}</p><h2 id="chapters" tabIndex={-1}>{t('contents.heading')}</h2></div>
          <div className="search-box"><Search {...icon} /><label className="sr-only" htmlFor="topic-search">{t('contents.searchLabel')}</label><input id="topic-search" ref={searchBox} type="search" placeholder={t('contents.searchPlaceholder')} value={query} onChange={(e) => setFilter(e.target.value)} />{query && <button type="button" className="icon-button clear-search" aria-label={t('contents.clearSearch')} onClick={() => { setFilter(''); searchBox.current?.focus(); }}><X {...icon} /></button>}</div>
        </div>
        <p className="collection-help" aria-live="polite">{normalized ? count(groups.reduce((n, g) => n + g.matches.length, 0), 'matching-topic') : t('contents.helpDefault')}</p>
        <div className="chapter-list">
          {groups.map(({ chapter, matches }) => {
            const isOpen = normalized ? (overrides[chapter.id] ?? true) : opened.includes(chapter.id);
            const conclusion = chapter.kind === 'concluding_section';
            return <section className={`chapter ${isOpen ? 'expanded' : ''}`} key={chapter.id}>
              <h3 className="chapter-heading"><button className="chapter-toggle" id={`chapter-${chapter.id}`} aria-expanded={isOpen} aria-controls={`topics-${chapter.id}`} onClick={() => toggle(chapter.id, isOpen)}>
                <span className="chapter-number" aria-hidden="true">{conclusion ? '✧' : pageNumber(chapter.position)}</span>
                <span className="chapter-copy"><span className="chapter-name">{chapter.title}</span><span className="chapter-meaning">{conclusion ? t('contents.conclusionLabel') : chapter.meaning}</span></span>
                <span className="topic-count">{count(matches.length, 'topic')}</span><ChevronDown className="chapter-chevron" {...icon} size={18} />
              </button></h3>
              <ul className="topic-list" id={`topics-${chapter.id}`} aria-labelledby={`chapter-${chapter.id}`} hidden={!isOpen}>
                {matches.map((topic) => <li key={topic.id}><Link to={readingPath(chapter, topic)}><span className="topic-name">{topic.title}</span><span className="topic-meta">{count(topic.counts.ayat, 'ayat')} <i /> {count(topic.counts.ahadith, 'ahadith')}</span><ArrowRight className={flip} {...icon} size={15} /></Link></li>)}
              </ul>
            </section>;
          })}
          {!groups.length && <div className="empty-state"><Search {...icon} size={22} /><h3>{t('contents.emptyTitle')}</h3><p>{t('contents.emptyHelp')}</p><button className="secondary-button" onClick={() => { setFilter(''); searchBox.current?.focus(); }}>{t('contents.clearSearch')}</button></div>}
        </div>
      </section>
      <aside className="overview" aria-label={t('overview.kicker')}>
        <div className="overview-card">
          <div className="overview-label"><LibraryBig {...icon} /><span className="eyebrow">{t('overview.kicker')}</span></div>
          <dl className="stats">
            <div><dt>{t('overview.chapters')}</dt><dd>{fmt(book.chapters.filter((c) => c.kind === 'quality').length)}</dd></div>
            <div><dt>{t('overview.topics')}</dt><dd>{fmt(topics.length)}</dd></div>
            <div><dt>{t('overview.ayat')}</dt><dd>{fmt(book.totals.counts.ayat)}</dd></div>
            <div><dt>{t('overview.ahadith')}</dt><dd>{fmt(book.totals.counts.ahadith)}</dd></div>
          </dl>
          <p className="stats-note">{t('overview.note')}</p>
        </div>
        <div className="edition-teaser">
          <div className="edition-icon"><FileText {...icon} size={19} /></div>
          <div><h3>{t('teaser.title')}</h3><p>{t('teaser.body')}</p><Link to="/edition" className="text-link">{t('teaser.link')} <ArrowRight className={flip} {...icon} /></Link></div>
        </div>
      </aside>
    </div>
  </main>;
}

function ReadingsProvider({ children }) {
  const [snapshot, setSnapshot] = useState({ records: emptyReadings, locators: {}, status: 'loading' });
  useEffect(() => {
    const abort = new AbortController();
    fetch(`${import.meta.env.BASE_URL}data/readings.json`, { signal: abort.signal })
      .then((response) => { if (!response.ok) throw new Error('Reading data unavailable'); return response.json(); })
      .then((data) => {
        if (data.schema_version !== 1 || data.pdf_sha256 !== book.sources.edition_pdf_sha256 || !Array.isArray(data.records)) throw new Error('Unrecognized reading data');
        setSnapshot({ records: new Map(data.records.filter((r) => r.status === 'reviewed').map((r) => [r.id, r])), locators: data.locators || {}, status: 'ready' });
      }).catch((error) => { if (error.name !== 'AbortError') setSnapshot({ records: emptyReadings, locators: {}, status: 'error' }); });
    return () => abort.abort();
  }, []);
  return children(snapshot);
}

const languageFields = { ar: 'arabic', en: 'english', ur: 'urdu' };

function EntryCard({ entry, content, locator, topic, lang }) {
  const { t, pages } = useI18n();
  const candidate = Array.isArray(locator) && Number.isInteger(locator[0]) && locator[0] >= topic.pages.printed_start && locator[0] <= topic.pages.printed_end ? locator : null;
  const from = content?.printed_start ?? candidate?.[0];
  const to = content?.printed_end ?? from;
  const sourcePage = from ? pages({ printed_start: from, printed_end: to }) : null;
  const showArabic = !!content?.arabic && (lang === 'all' || lang === 'ar');
  const showEnglish = !!content?.english && (lang === 'all' || lang === 'en');
  const showUrdu = !!content?.urdu && (lang === 'all' || lang === 'ur');
  const languageName = { ar: t('reader.arabic'), en: t('reader.english'), ur: t('reader.urdu') };
  const missing = content ? ['ar', 'en', 'ur'].filter((key) => !content[languageFields[key]]) : [];
  const nothingShown = content && !showArabic && !showEnglish && !showUrdu;
  return <article className={`entry-card ${content ? '' : 'reference-card'}`} id={entry.id} tabIndex={-1} aria-labelledby={`${entry.id}-title`}>
    <div className="entry-head"><h3 id={`${entry.id}-title`}>{entry.title}</h3>{content ? <span className="entry-tag">{entry.kind === 'ayah' ? (content.excerpt ? t('entry.excerpt') : t('entry.passage')) : t('entry.narration')}</span> : <span className="entry-tag is-reference">{t('entry.referenceOnly')}</span>}</div>
    {showArabic && <p className="arabic" dir="rtl" lang="ar">{content.arabic}</p>}
    {showUrdu && <p className="urdu" dir="rtl" lang="ur">{content.urdu}</p>}
    {showEnglish && <p className="translation" lang="en">{content.english}</p>}
    {nothingShown && lang !== 'all' && <p className="source-hint">{t('entry.noTranscript', { language: languageName[lang] })}</p>}
    {nothingShown && lang === 'all' && <p className="source-hint">{t('entry.noTranscript', { language: languageName.ar })}</p>}
    {content && lang === 'all' && missing.length > 0 && missing.length < 3 && <p className="source-hint">{t('entry.notAvailableIn', { languages: missing.map((key) => languageName[key]).join('، ') })}</p>}
    {content?.notes && (lang === 'all' || lang === 'en') && <details className="reading-notes"><summary>{t('entry.editionNote')}</summary><p>{content.notes}</p></details>}
    <div className="entry-source">{content?.citation && <span>{content.citation}</span>}{openScan(from ? spreadUrl(from) : topic.pages.flipbook_url, content && sourcePage ? t('entry.scanWithPages', { pages: sourcePage }) : from ? t('entry.scanNear', { page: from }) : t('entry.openTopicScan'), 'text-link', t)}</div>
  </article>;
}

function ReaderRoute({ snapshot }) {
  const { chapterId, slug } = useParams();
  const index = topics.findIndex(({ chapter, topic }) => chapter.id === chapterId && topicSlug(topic) === slug);
  return index < 0 ? <NotFound /> : <Reader key={topics[index].topic.id} {...topics[index]} index={index} snapshot={snapshot} />;
}

function Reader({ chapter, topic, index, snapshot }) {
  const { t, count, pages } = useI18n();
  const [params, setParams] = useSearchParams();
  const ayat = useMemo(() => inventory(topic, 'ayah', t('entry.quran')), [topic, t]);
  const ahadith = useMemo(() => inventory(topic, 'hadith', t('entry.hadith')), [topic, t]);
  const targetId = params.get('entry');
  const targetKind = ayat.some((entry) => entry.id === targetId) ? 'ayah' : ahadith.some((entry) => entry.id === targetId) ? 'hadith' : null;
  const kind = targetKind || (['ayah', 'hadith'].includes(params.get('view')) ? params.get('view') : (ayat.length ? 'ayah' : 'hadith'));
  const [limit, setLimit] = useState(12);
  const [lang, setLang] = useState(() => { const pref = storage.get('mr-language', 'all'); return ['all', 'ar', 'en', 'ur'].includes(pref) ? pref : 'all'; });
  const items = kind === 'ayah' ? ayat : ahadith;
  const visible = items.slice(0, Math.max(limit, items.findIndex((entry) => entry.id === targetId) + 1));
  const reviewed = ayat.concat(ahadith).filter((entry) => snapshot.records.has(entry.id)).length;
  const sectionTitle = kind === 'ayah' ? t('topic.ayat') : t('topic.ahadith');
  useEffect(() => { document.title = `${topic.title} · Muntakhab`; }, [topic.title]);
  useEffect(() => { storage.set('mr-language', lang); }, [lang]);
  useEffect(() => {
    if (targetKind && snapshot.status !== 'loading') {
      const target = document.getElementById(targetId);
      target?.scrollIntoView({ block: 'start' }); target?.focus({ preventScroll: true });
    }
  }, [targetId, targetKind, snapshot.status]);
  function selectKind(value, jump = false) {
    setLimit(12); setParams({ view: value }, { replace: true });
    if (jump) requestAnimationFrame(() => { const target = document.getElementById('reading-section'); target?.scrollIntoView({ block: 'start' }); target?.focus({ preventScroll: true }); });
  }
  const backState = { chapter: chapter.id };
  const before = topics[index - 1]; const after = topics[index + 1];
  const languageOptions = [['all', t('reader.all')], ['ar', t('reader.arabic')], ['en', t('reader.english')], ['ur', t('reader.urdu')]];
  return <main id="main" className="wrap" tabIndex={-1}>
    <nav className="breadcrumbs" aria-label={t('nav.breadcrumb')}><Link to="/">{t('nav.contents')}</Link><ChevronRight className={flip} {...icon} size={14} /><Link to="/" state={backState}>{chapter.title}</Link><ChevronRight className={flip} {...icon} size={14} /><span aria-current="page">{topic.title}</span></nav>
    <section className="topic-hero" aria-labelledby="topic-title">
      <div><p className="eyebrow hero-kicker"><span aria-hidden="true" className="diamond" /> {chapter.kind === 'quality' ? `${t('topic.chapter')} ${pageNumber(chapter.position)}` : t('topic.conclusion')} <span className="eyebrow-separator">/</span> {t('topic.topic')} {pageNumber(topic.position)}</p>
        <h1 id="topic-title">{topic.title}</h1>
        <p className="reader-meta"><span>{pages(topic.pages)}</span><span>{count(topic.counts.ayat, 'ayat')}</span><span>{count(topic.counts.ahadith, 'ahadith')}</span></p>
      </div>
      <span className="topic-decoration" aria-hidden="true"><BookOpen size={72} strokeWidth={.65} /></span>
    </section>
    <div className="reader-layout">
      <section className="reading-section" id="reading-section" aria-labelledby="reading-title" tabIndex={-1}>
        <div className="reading-toolbar">
          <div className="segment content-filter" role="group" aria-label={t('reader.readingType')}><button aria-pressed={kind === 'ayah'} onClick={() => selectKind('ayah')}>{t('topic.ayat')} <span>{topic.counts.ayat}</span></button><button aria-pressed={kind === 'hadith'} onClick={() => selectKind('hadith')}>{t('topic.ahadith')} <span>{topic.counts.ahadith}</span></button></div>
          <div className="segment language-filter" role="group" aria-label={t('reader.readingLanguage')}>{languageOptions.map(([value, label]) => <button key={value} aria-pressed={lang === value} onClick={() => setLang(value)}>{label}</button>)}</div>
        </div>
        <div className="reading-heading"><h2 id="reading-title">{sectionTitle}</h2><span>{count(items.length, kind === 'ayah' ? 'passage' : 'entry')}</span></div>
        {snapshot.status === 'loading' && <p className="data-message" role="status">{t('reader.loading')}</p>}
        {snapshot.status === 'error' && <p className="data-message" role="status">{t('reader.loadFailed')}</p>}
        {items.length ? <div className="entries">{visible.map((entry) => <EntryCard key={entry.id} entry={entry} content={snapshot.records.get(entry.id)} locator={snapshot.locators[entry.id]} topic={topic} lang={lang} />)}</div> : <div className="empty-state"><BookOpen {...icon} size={24} /><h3>{t('reader.noAyatTitle')}</h3><p>{t('reader.noAyatBody')}</p><button className="secondary-button" onClick={() => selectKind('hadith')}>{t('reader.readAhadith')} <ArrowRight className={flip} {...icon} /></button></div>}
        {visible.length < items.length && <div className="load-more"><button className="secondary-button" onClick={() => {
          const next = items[visible.length]; setLimit(visible.length + 12);
          requestAnimationFrame(() => document.getElementById(next.id)?.focus());
        }}>{kind === 'ayah' ? t('reader.showMorePassages') : t('reader.showMoreAhadith')} <ArrowDown {...icon} /></button><span aria-live="polite">{t('reader.showingOf', { shown: visible.length, total: items.length })}</span></div>}
        <nav className="topic-navigation" aria-label={t('reader.adjacentTopics')}>
          {before && <Link to={readingPath(before.chapter, before.topic)} className="previous-topic"><ArrowLeft className={flip} {...icon} /><span><small>{t('reader.previous')}</small>{before.topic.title}</span></Link>}
          {after && <Link to={readingPath(after.chapter, after.topic)} className="next-topic"><span><small>{t('reader.next')}</small>{after.topic.title}</span><ArrowRight className={flip} {...icon} /></Link>}
        </nav>
      </section>
      <aside className="reader-aside" aria-label={t('reader.guideKicker')}>
        <div className="overview-card topic-guide">
          <p className="eyebrow">{t('reader.guideKicker')}</p>
          <button className={kind === 'ayah' ? 'current-section' : ''} aria-current={kind === 'ayah' ? 'true' : undefined} onClick={() => selectKind('ayah', true)}>{t('topic.ayat')} <span>{topic.counts.ayat}</span></button>
          <button className={kind === 'hadith' ? 'current-section' : ''} aria-current={kind === 'hadith' ? 'true' : undefined} onClick={() => selectKind('hadith', true)}>{t('topic.ahadith')} <span>{topic.counts.ahadith}</span></button>
          <div className="guide-source"><p className="eyebrow">{t('reader.sourceEdition')}</p>{openScan(topic.pages.flipbook_url, `${t('reader.originalScan')} · ${pages(topic.pages)}`, 'text-link', t)}</div>
        </div>
        <div className="preview-note"><p className="eyebrow">{t('reader.previewKicker')}</p><p>{reviewed ? t('reader.previewSome', { count: count(reviewed, 'transcribed') }) : t('reader.previewNone')}</p></div>
      </aside>
    </div>
  </main>;
}

function Edition() {
  const { t } = useI18n();
  useEffect(() => { document.title = `${t('edition.title')} · Muntakhab`; }, [t]);
  return <main id="main" className="wrap" tabIndex={-1}>
    <nav className="breadcrumbs" aria-label={t('nav.breadcrumb')}><Link to="/">{t('nav.contents')}</Link><ChevronRight className={flip} {...icon} size={14} /><span aria-current="page">{t('edition.title')}</span></nav>
    <section className="topic-hero" aria-labelledby="edition-title"><div><p className="eyebrow hero-kicker"><span aria-hidden="true" className="diamond" /> {t('edition.kicker')}</p><h1 id="edition-title">{t('edition.title')}</h1><p className="hero-description">{book.book.subtitle}</p></div><span className="topic-decoration" aria-hidden="true"><LibraryBig size={70} strokeWidth={.7} /></span></section>
    <div className="edition-layout">
      <section className="edition-body"><h2>{t('edition.printedBook')}</h2><p>{t('edition.printedBookBody')}</p>
        <dl className="credits"><div><dt>{t('edition.compiledBy')}</dt><dd>{book.book.compiler}</dd></div><div><dt>{t('edition.organizedBy')}</dt><dd>{book.book.organized_and_presented_by}</dd></div><div><dt>{t('edition.imprint')}</dt><dd>{book.book.imprint}</dd></div></dl>
        <h2>{t('edition.preview')}</h2><p>{t('edition.previewBody1')}</p><p>{t('edition.previewBody2')}</p>
      </section>
      <aside className="overview-card edition-sources"><p className="eyebrow">{t('edition.sourcesKicker')}</p>{openScan(book.sources.flipbook, t('edition.flipbook'), 'text-link', t)}{openScan(book.sources.edition_pdf, t('edition.pdf'), 'text-link', t)}{openScan(book.sources.contents[0], t('edition.contents'), 'text-link', t)}</aside>
    </div>
  </main>;
}

function NotFound() {
  const { t } = useI18n();
  useEffect(() => { document.title = `${t('notfound.title')} · Muntakhab`; }, [t]);
  return <main id="main" className="wrap" tabIndex={-1}><div className="empty-state not-found"><BookOpen {...icon} size={27} /><h1>{t('notfound.title')}</h1><p>{t('notfound.body')}</p><Link className="primary-button" to="/"><ArrowLeft className={flip} {...icon} /> {t('notfound.back')}</Link></div></main>;
}

function App() {
  const { t } = useI18n();
  const [opened, setOpened] = useState(() => { const saved = storage.get('mr-chapters', defaultOpen); return Array.isArray(saved) ? saved : defaultOpen; });
  const [query, setQuery] = useState('');
  useEffect(() => { storage.set('mr-chapters', opened); }, [opened]);
  return <>
    <a className="skip-link" href="#main" onClick={(e) => { e.preventDefault(); document.getElementById('main')?.focus(); }}>{t('skip.toContent')}</a>
    <Header />
    <ReadingsProvider>{(snapshot) => <Routes>
      <Route path="/" element={<Contents {...{ opened, setOpened, query, setQuery }} />} />
      <Route path="/read/:chapterId/:slug" element={<ReaderRoute snapshot={snapshot} />} />
      <Route path="/edition" element={<Edition />} />
      <Route path="*" element={<NotFound />} />
    </Routes>}</ReadingsProvider>
    <FocusRoute /><Footer />
  </>;
}

createRoot(document.getElementById('root')).render(<HashRouter><UiLanguageProvider><App /></UiLanguageProvider></HashRouter>);
