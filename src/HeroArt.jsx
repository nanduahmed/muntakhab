export function HeroArt() {
  return (
    <svg className="book-art" viewBox="0 0 464 300" preserveAspectRatio="xMidYMid slice" aria-hidden="true" focusable="false">
      <defs>
        <radialGradient id="art-ground" cx="50%" cy="44%" r="73%"><stop stopColor="#466651"/><stop offset="1" stopColor="#1b382e"/></radialGradient>
        <linearGradient id="art-page-l" x1="0" x2="1"><stop stopColor="#f0e1bc"/><stop offset="1" stopColor="#bfaa7e"/></linearGradient>
        <linearGradient id="art-page-r" x1="0" x2="1"><stop stopColor="#c8b38a"/><stop offset=".37" stopColor="#f3e4c2"/><stop offset="1" stopColor="#e2cfa4"/></linearGradient>
        <pattern id="art-lattice" x="16" width="44" height="44" patternUnits="userSpaceOnUse">
          <path d="M22 0l6.5 15.5L44 22l-15.5 6.5L22 44l-6.5-15.5L0 22l15.5-6.5ZM0 0l44 44M44 0 0 44" fill="none" stroke="#cfbd92" strokeOpacity=".12" strokeWidth=".65"/>
        </pattern>
        <pattern id="art-grain" width="7" height="9" patternUnits="userSpaceOnUse"><circle cx="1" cy="2" r=".45" fill="#fcf2d2" opacity=".24"/><circle cx="4" cy="6" r=".4" fill="#111f18" opacity=".8"/></pattern>
        <filter id="art-shadow" x="-25%" y="-48%" width="150%" height="200%"><feDropShadow dx="0" dy="13" stdDeviation="11" floodColor="#07170e" floodOpacity=".53"/></filter>
        <path id="art-spark" d="M0-7 1.7-1.7 7 0 1.7 1.7 0 7-1.7 1.7-7 0-1.7-1.7Z"/>
      </defs>
      <path fill="url(#art-ground)" d="M0 0h464v300H0z"/>
      <path fill="url(#art-lattice)" d="M0 0h464v300H0z"/>
      <path fill="url(#art-grain)" opacity=".42" d="M0 0h464v300H0z"/>
      <path d="M27 86V25h63m284 0h63v61m0 129v60h-63m-284 0H27v-60" fill="none" stroke="#d3bf8e" strokeWidth=".8" opacity=".76"/>
      <path d="M33 74V31h45m308 0h45v43m0 153v42h-45m-308 0H33v-42" fill="none" stroke="#d3bf8e" strokeWidth=".65" opacity=".4"/>
      <path d="M117 252v-88c0-61 54-92 115-133 61 41 115 72 115 133v88Z" fill="#203e31" fillOpacity=".72" stroke="#c9b78a" strokeWidth="1.1"/>
      <path d="M126 244v-80c0-56 50-85 106-122 56 37 106 66 106 122v80Z" fill="none" stroke="#c9b78a" strokeWidth=".6" opacity=".65"/>
      <g fill="#dbc59a"><use href="#art-spark" x="232" y="78"/><use href="#art-spark" x="83" y="149" opacity=".8"/><use href="#art-spark" x="381" y="149" opacity=".8"/></g>
      <g fill="#cfba87" opacity=".65"><circle cx="183" cy="95" r="1.4"/><circle cx="281" cy="95" r="1.4"/><circle cx="232" cy="98" r="1.4"/><circle cx="83" cy="166" r="1.3"/><circle cx="381" cy="166" r="1.3"/></g>
      <g filter="url(#art-shadow)" strokeLinejoin="round">
        <path d="M146 132c29-8 66-5 86 10 22-15 56-18 86-10l35 74c-41-9-85-6-121 15-34-21-80-24-121-15Z" fill="#172b24" stroke="#bcaa7a" strokeWidth="1.2"/>
        <path d="M149 129c32-7 63-2 83 13 20-15 51-20 83-13l31 69c-42-6-81-2-114 18-31-20-73-24-114-18Z" fill="#b39b6b" stroke="#d3b988" strokeWidth="1"/>
        <path d="M149 122c32-8 63-1 83 16v73c-30-22-69-28-112-20Z" fill="url(#art-page-l)" stroke="#ad986c" strokeWidth=".9"/>
        <path d="M315 122c-32-8-63-1-83 16v73c30-22 69-28 112-20Z" fill="url(#art-page-r)" stroke="#ad986c" strokeWidth=".9"/>
        <path d="M232 138v71m-112-16c44-7 83 0 112 21 29-21 68-28 112-21" fill="none" stroke="#7e6948" opacity=".64"/>
        <path d="M155 131c22-4 49 2 67 15l-3 50c-21-12-50-17-83-13Zm154 0c-22-4-49 2-67 15l3 50c21-12 50-17 83-13Z" fill="none" stroke="#987c53" strokeWidth=".8"/>
        <g fill="none" stroke="#8e7754" strokeWidth="1.05" opacity=".68" strokeLinecap="round">
          <path d="M156 141c20-2 43 4 57 12m-60-3c16-1 44 4 61 14m-65-5c21-1 48 5 64 14m-68-5c19 0 46 4 62 11m101-38c-20-2-43 4-57 12m60-3c-16-1-44 4-61 14m65-5c-21-1-48 5-64 14m68-5c-19 0-46 4-62 11"/>
        </g>
        <path d="M246 200c-1 9 2 18 6 22l-7-1-4 6c-5-7-6-15-4-22Z" fill="#9d7545" stroke="#725435" strokeWidth=".6"/>
      </g>
      <path d="M204 249h16m24 0h16m-28-4 4 4-4 4-4-4Z" fill="none" stroke="#cfbd90" strokeWidth=".85"/>
    </svg>
  );
}
