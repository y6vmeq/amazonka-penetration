() => {
  // Return up to window.__getN (default 6) not-yet-retrieved crawled pages (with html) and mark them retrieved.
  const st = window.__crawl; const n = window.__getN || 6;
  const outp = [];
  for (const pg of st.pages) {
    if (pg.retrieved) continue;
    outp.push({ url: pg.url, finalUrl: pg.finalUrl, status: pg.status, fetched_at: pg.fetched_at, code: pg.code, mainCode: pg.mainCode,
                title: pg.title, posts: pg.posts, pageInfos: pg.pageInfos, loginRedirect: pg.loginRedirect, html: pg.html });
    pg.retrieved = true; pg.html = null;
    if (outp.length >= n) break;
  }
  return { pages: outp, left: st.pages.filter(p => !p.retrieved).length, parent: st.parent };
}
