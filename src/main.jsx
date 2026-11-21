import React, { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { HashRouter, Link, NavLink, Route, Routes, useLocation, useParams, useSearchParams } from 'react-router-dom';
import { ArrowDown, ArrowLeft, ArrowRight, ArrowUpRight, BookOpen, ChevronDown, ChevronRight, FileText, LibraryBig, Search, X } from 'lucide-react';
import '@fontsource-variable/dm-sans';
import '@fontsource-variable/lora';
import '@fontsource-variable/lora/wght-italic.css';
import '@fontsource/noto-naskh-arabic/400.css';
import './styles.css';
import { book, fmt, inventory, pageNumber, printed, qty, readingPath, searchable, spreadUrl, topicSlug, topics } from './book';
import { HeroArt } from './HeroArt';

const defaultOpen = [book.chapters[0].id];
const emptyReadings = new Map();
const storage = {
  get(key, fallback) { try { return JSON.parse(sessionStorage.getItem(key)) ?? fallback; } catch { return fallback; } },
  set(key, value) { try { sessionStorage.setItem(key, JSON.stringify(value)); } catch { /* optional */ } },
};
const icon = { size: 16, strokeWidth: 1.7, 'aria-hidden': true };

function openScan(url, children, className = 'text-link') {
  return <a className={className} href={url} target="_blank" rel="noreferrer">{children}<ArrowUpRight {...icon} /><span className="sr-only"> (opens in a new tab)</span></a>;
}

function Header() {
  return <header className="site-head">
    <div className="wrap masthead">
      <Link to="/" className="brand" aria-label="Muntakhab Reading Room home"><img src="./mark.svg" alt="" width="37" height="37" /><span>Muntakhab<small>READING ROOM</small></span></Link>
      <nav className="site-nav" aria-label="Primary"><NavLink end to="/">Contents</NavLink><NavLink to="/edition">About the edition</NavLink></nav>
      {openScan(book.sources.flipbook, <><span className="scan-long">Original scan</span><span className="scan-short">Scan</span></>, 'scan-link')}
    </div>
  </header>;
}

function Footer() {
  return <footer className="wrap site-foot"><span className="foot-mark"><BookOpen {...icon} /> The Muntakhab Reading Room</span><Link to="/edition">About the edition</Link></footer>;
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
        <p className="eyebrow hero-kicker"><span aria-hidden="true" className="diamond" /> THE READING ROOM</p>
        <h1 id="home-title">Muntakhab <em>Ahadith</em></h1>
        <p className="hero-description">A selection of Qur’an passages and Ahadith relating to the six qualities of Da‘wat and Tabligh.</p>
        <button className="primary-button" onClick={goToContents}>Browse chapters <ArrowDown {...icon} /></button>
      </div>
      <div className="hero-image"><HeroArt /></div>
    </section>
    <div className="collection-layout">
      <section aria-labelledby="chapters">
        <div className="collection-heading">
          <div><p className="eyebrow">TABLE OF CONTENTS</p><h2 id="chapters" tabIndex={-1}>Chapters</h2></div>
          <div className="search-box"><Search {...icon} /><label className="sr-only" htmlFor="topic-search">Find a chapter or topic</label><input id="topic-search" ref={searchBox} type="search" placeholder="Find a topic…" value={query} onChange={(e) => setFilter(e.target.value)} />{query && <button type="button" className="icon-button clear-search" aria-label="Clear search" onClick={() => { setFilter(''); searchBox.current?.focus(); }}><X {...icon} /></button>}</div>
        </div>
        <p className="collection-help" aria-live="polite">{normalized ? `${qty(groups.reduce((n, g) => n + g.matches.length, 0), 'matching topic')}` : 'Expand a chapter to explore its topics.'}</p>
        <div className="chapter-list">
          {groups.map(({ chapter, matches }) => {
            const isOpen = normalized ? (overrides[chapter.id] ?? true) : opened.includes(chapter.id);
            const conclusion = chapter.kind === 'concluding_section';
            return <section className={`chapter ${isOpen ? 'expanded' : ''}`} key={chapter.id}>
              <h3 className="chapter-heading"><button className="chapter-toggle" id={`chapter-${chapter.id}`} aria-expanded={isOpen} aria-controls={`topics-${chapter.id}`} onClick={() => toggle(chapter.id, isOpen)}>
                <span className="chapter-number" aria-hidden="true">{conclusion ? '✧' : pageNumber(chapter.position)}</span>
                <span className="chapter-copy"><span className="chapter-name">{chapter.title}</span><span className="chapter-meaning">{conclusion ? 'Concluding section' : chapter.meaning}</span></span>
                <span className="topic-count">{qty(matches.length, 'topic')}</span><ChevronDown className="chapter-chevron" {...icon} size={18} />
              </button></h3>
              <ul className="topic-list" id={`topics-${chapter.id}`} aria-labelledby={`chapter-${chapter.id}`} hidden={!isOpen}>
                {matches.map((topic) => <li key={topic.id}><Link to={readingPath(chapter, topic)}><span className="topic-name">{topic.title}</span><span className="topic-meta">{qty(topic.counts.ayat, 'ayat', 'ayat')} <i /> {qty(topic.counts.ahadith, 'hadith', 'ahadith')}</span><ArrowRight {...icon} size={15} /></Link></li>)}
              </ul>
            </section>;
          })}
          {!groups.length && <div className="empty-state"><Search {...icon} size={22} /><h3>No matching topics</h3><p>Try a chapter name, “prayer”, or “Wudu”.</p><button className="secondary-button" onClick={() => { setFilter(''); searchBox.current?.focus(); }}>Clear search</button></div>}
        </div>
      </section>
      <aside className="overview" aria-label="Edition information">
        <div className="overview-card">
          <div className="overview-label"><LibraryBig {...icon} /><span className="eyebrow">AT A GLANCE</span></div>
          <dl className="stats">
            <div><dt>Chapters</dt><dd>{fmt(book.chapters.filter((c) => c.kind === 'quality').length)}</dd></div>
            <div><dt>Topics</dt><dd>{fmt(topics.length)}</dd></div>
            <div><dt>Ayat</dt><dd>{fmt(book.totals.counts.ayat)}</dd></div>
            <div><dt>Ahadith</dt><dd>{fmt(book.totals.counts.ahadith)}</dd></div>
          </dl>
          <p className="stats-note">Six main chapters and a concluding section, in the order of the printed book.</p>
        </div>
        <div className="edition-teaser">
          <div className="edition-icon"><FileText {...icon} size={19} /></div>
          <div><h3>Arabic &amp; English</h3><p>Follow the original Arabic alongside the English translation or open the source scan.</p><Link to="/edition" className="text-link">About this edition <ArrowRight {...icon} /></Link></div>
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

function EntryCard({ entry, content, locator, topic, lang }) {
  const candidate = Array.isArray(locator) && Number.isInteger(locator[0]) && locator[0] >= topic.pages.printed_start && locator[0] <= topic.pages.printed_end ? locator : null;
  const from = content?.printed_start ?? candidate?.[0];
  const to = content?.printed_end ?? from;
  const sourcePage = from ? printed({ printed_start: from, printed_end: to }) : null;
  const showEnglish = !!content?.english && lang !== 'ar';
  const showArabic = !!content?.arabic && lang !== 'en';
  return <article className={`entry-card ${content ? '' : 'reference-card'}`} id={entry.id} tabIndex={-1} aria-labelledby={`${entry.id}-title`}>
    <div className="entry-head"><h3 id={`${entry.id}-title`}>{entry.title}</h3>{content ? <span className="entry-tag">{entry.kind === 'ayah' ? (content.excerpt ? 'Qur’an excerpt' : 'Qur’an passage') : 'Narration'}</span> : <span className="entry-tag is-reference">Reference only</span>}</div>
    {showArabic && <p className="arabic" dir="rtl" lang="ar">{content.arabic}</p>}
    {showEnglish && <p className="translation" lang="en">{content.english}</p>}
    {content && !showEnglish && !showArabic && <p className="source-hint">No {lang === 'ar' ? 'Arabic' : 'English'} transcription available for this entry.</p>}
    {content && lang === 'both' && (showEnglish !== showArabic) && <p className="source-hint">{showArabic ? 'English' : 'Arabic'} transcription not available.</p>}
    {content?.notes && lang !== 'ar' && <details className="reading-notes"><summary>Edition note</summary><p>{content.notes}</p></details>}
    <div className="entry-source">{content?.citation && <span>{content.citation}</span>}{openScan(from ? spreadUrl(from) : topic.pages.flipbook_url, content && sourcePage ? `Scan · ${sourcePage}` : from ? `Find in scan · near p. ${from}` : 'Open topic scan')}</div>
  </article>;
}

function ReaderRoute({ snapshot }) {
  const { chapterId, slug } = useParams();
  const index = topics.findIndex(({ chapter, topic }) => chapter.id === chapterId && topicSlug(topic) === slug);
  return index < 0 ? <NotFound /> : <Reader key={topics[index].topic.id} {...topics[index]} index={index} snapshot={snapshot} />;
}

function Reader({ chapter, topic, index, snapshot }) {
  const [params, setParams] = useSearchParams();
  const ayat = useMemo(() => inventory(topic, 'ayah'), [topic]);
  const ahadith = useMemo(() => inventory(topic, 'hadith'), [topic]);
  const targetId = params.get('entry');
  const targetKind = ayat.some((entry) => entry.id === targetId) ? 'ayah' : ahadith.some((entry) => entry.id === targetId) ? 'hadith' : null;
  const kind = targetKind || (['ayah', 'hadith'].includes(params.get('view')) ? params.get('view') : (ayat.length ? 'ayah' : 'hadith'));
  const [limit, setLimit] = useState(12);
  const [lang, setLang] = useState(() => { const pref = storage.get('mr-language', 'both'); return ['both', 'ar', 'en'].includes(pref) ? pref : 'both'; });
  const items = kind === 'ayah' ? ayat : ahadith;
  const visible = items.slice(0, Math.max(limit, items.findIndex((entry) => entry.id === targetId) + 1));
  const reviewed = ayat.concat(ahadith).filter((entry) => snapshot.records.has(entry.id)).length;
  const sectionTitle = kind === 'ayah' ? 'Ayat' : 'Ahadith';
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
  return <main id="main" className="wrap" tabIndex={-1}>
    <nav className="breadcrumbs" aria-label="Breadcrumb"><Link to="/">Contents</Link><ChevronRight {...icon} size={14} /><Link to="/" state={backState}>{chapter.title}</Link><ChevronRight {...icon} size={14} /><span aria-current="page">{topic.title}</span></nav>
    <section className="topic-hero" aria-labelledby="topic-title">
      <div><p className="eyebrow hero-kicker"><span aria-hidden="true" className="diamond" /> {chapter.kind === 'quality' ? `CHAPTER ${pageNumber(chapter.position)}` : 'CONCLUDING SECTION'} <span className="eyebrow-separator">/</span> TOPIC {pageNumber(topic.position)}</p>
        <h1 id="topic-title">{topic.title}</h1>
        <p className="reader-meta"><span>{printed(topic.pages)}</span><span>{qty(topic.counts.ayat, 'ayat', 'ayat')}</span><span>{qty(topic.counts.ahadith, 'hadith', 'ahadith')}</span></p>
      </div>
      <span className="topic-decoration" aria-hidden="true"><BookOpen size={72} strokeWidth={.65} /></span>
    </section>
    <div className="reader-layout">
      <section className="reading-section" id="reading-section" aria-labelledby="reading-title" tabIndex={-1}>
        <div className="reading-toolbar">
          <div className="segment content-filter" role="group" aria-label="Reading type"><button aria-pressed={kind === 'ayah'} onClick={() => selectKind('ayah')}>Ayat <span>{topic.counts.ayat}</span></button><button aria-pressed={kind === 'hadith'} onClick={() => selectKind('hadith')}>Ahadith <span>{topic.counts.ahadith}</span></button></div>
          <div className="segment language-filter" role="group" aria-label="Reading language">{[['both','Both'],['ar','Arabic'],['en','English']].map(([value, label]) => <button key={value} aria-pressed={lang === value} onClick={() => setLang(value)}>{label}</button>)}</div>
        </div>
        <div className="reading-heading"><h2 id="reading-title">{sectionTitle}</h2><span>{kind === 'ayah' ? qty(items.length, 'passage') : qty(items.length, 'entry', 'entries')}</span></div>
        {snapshot.status === 'loading' && <p className="data-message" role="status">Loading reviewed text…</p>}
        {snapshot.status === 'error' && <p className="data-message" role="status">Text could not be loaded. References and scan links are still available.</p>}
        {items.length ? <div className="entries">{visible.map((entry) => <EntryCard key={entry.id} entry={entry} content={snapshot.records.get(entry.id)} locator={snapshot.locators[entry.id]} topic={topic} lang={lang} />)}</div> : <div className="empty-state"><BookOpen {...icon} size={24} /><h3>No standalone Ayat in this topic</h3><p>The printed topic begins with Ahadith.</p><button className="secondary-button" onClick={() => selectKind('hadith')}>Read the Ahadith <ArrowRight {...icon} /></button></div>}
        {visible.length < items.length && <div className="load-more"><button className="secondary-button" onClick={() => {
          const next = items[visible.length]; setLimit(visible.length + 12);
          requestAnimationFrame(() => document.getElementById(next.id)?.focus());
        }}>Show more {kind === 'ayah' ? 'passages' : 'Ahadith'} <ArrowDown {...icon} /></button><span aria-live="polite">Showing {visible.length} of {items.length}</span></div>}
        <nav className="topic-navigation" aria-label="Adjacent topics">
          {before && <Link to={readingPath(before.chapter, before.topic)} className="previous-topic"><ArrowLeft {...icon} /><span><small>PREVIOUS TOPIC</small>{before.topic.title}</span></Link>}
          {after && <Link to={readingPath(after.chapter, after.topic)} className="next-topic"><span><small>NEXT TOPIC</small>{after.topic.title}</span><ArrowRight {...icon} /></Link>}
        </nav>
      </section>
      <aside className="reader-aside" aria-label="Topic guide">
        <div className="overview-card topic-guide">
          <p className="eyebrow">IN THIS TOPIC</p>
          <button className={kind === 'ayah' ? 'current-section' : ''} aria-current={kind === 'ayah' ? 'true' : undefined} onClick={() => selectKind('ayah', true)}>Ayat <span>{topic.counts.ayat}</span></button>
          <button className={kind === 'hadith' ? 'current-section' : ''} aria-current={kind === 'hadith' ? 'true' : undefined} onClick={() => selectKind('hadith', true)}>Ahadith <span>{topic.counts.ahadith}</span></button>
          <div className="guide-source"><p className="eyebrow">SOURCE EDITION</p>{openScan(topic.pages.flipbook_url, `Original scan · ${printed(topic.pages)}`)}</div>
        </div>
        <div className="preview-note"><p className="eyebrow">READING PREVIEW</p><p>{reviewed ? `${qty(reviewed, 'transcribed entry', 'transcribed entries')} in this topic. Other entries link to the scan.` : 'This topic currently shows references with links to the scan.'}</p></div>
      </aside>
    </div>
  </main>;
}

function Edition() {
  useEffect(() => { document.title = 'About the edition · Muntakhab'; }, []);
  return <main id="main" className="wrap" tabIndex={-1}>
    <nav className="breadcrumbs" aria-label="Breadcrumb"><Link to="/">Contents</Link><ChevronRight {...icon} size={14} /><span aria-current="page">About the edition</span></nav>
    <section className="topic-hero" aria-labelledby="edition-title"><div><p className="eyebrow hero-kicker"><span aria-hidden="true" className="diamond" /> THE SOURCE TEXT</p><h1 id="edition-title">About the edition</h1><p className="hero-description">{book.book.subtitle}</p></div><span className="topic-decoration" aria-hidden="true"><LibraryBig size={70} strokeWidth={.7} /></span></section>
    <div className="edition-layout">
      <section className="edition-body"><h2>The printed book</h2><p>This reading room follows the Arabic and English scan hosted by The Islamic Bulletin. The numbered pages in this reader refer to the book, not the PDF viewer’s page counter.</p>
        <dl className="credits"><div><dt>Compiled by</dt><dd>{book.book.compiler}</dd></div><div><dt>Organized and presented by</dt><dd>{book.book.organized_and_presented_by}</dd></div><div><dt>Imprint</dt><dd>{book.book.imprint}</dd></div></dl>
        <h2>What the preview includes</h2><p>Browse every topic. Where a transcription was checked for the prototype, the reader shows it; otherwise it shows the reference and a link to the scan. The counts are for the whole printed book, not the transcribed preview.</p><p>An opening Qur’an passage can contain more than one ayat. Ayat quoted inside numbered Ahadith are not counted separately.</p>
      </section>
      <aside className="overview-card edition-sources"><p className="eyebrow">SOURCE LINKS</p>{openScan(book.sources.flipbook, 'Open the original flipbook')}{openScan(book.sources.edition_pdf, 'Open the PDF scan')}{openScan(book.sources.contents[0], 'Printed table of contents')}</aside>
    </div>
  </main>;
}

function NotFound() {
  useEffect(() => { document.title = 'Topic not found · Muntakhab'; }, []);
  return <main id="main" className="wrap" tabIndex={-1}><div className="empty-state not-found"><BookOpen {...icon} size={27} /><h1>Topic not found</h1><p>Check the link or choose a topic from the table of contents.</p><Link className="primary-button" to="/"><ArrowLeft {...icon} /> Back to contents</Link></div></main>;
}

function App() {
  const [opened, setOpened] = useState(() => { const saved = storage.get('mr-chapters', defaultOpen); return Array.isArray(saved) ? saved : defaultOpen; });
  const [query, setQuery] = useState('');
  useEffect(() => { storage.set('mr-chapters', opened); }, [opened]);
  return <>
    <a className="skip-link" href="#main" onClick={(e) => { e.preventDefault(); document.getElementById('main')?.focus(); }}>Skip to content</a>
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

createRoot(document.getElementById('root')).render(<HashRouter><App /></HashRouter>);
