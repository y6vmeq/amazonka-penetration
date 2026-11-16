() => {
  // Return up to window.__getN (default 5) not-yet-retrieved Instagram pages (with html) and mark them retrieved.
  const st = window.__ig; const n = window.__getN || 5;
  const outp = [];
  for (const pg of st.pages) {
    if (pg.retrieved) continue;
    outp.push(Object.assign({}, pg));
    pg.retrieved = true; pg.html = null;
    if (outp.length >= n) break;
  }
  return { ig_pages: outp, left: st.pages.filter(p => !p.retrieved).length, running: st.running, stopReason: st.stopReason, log: st.log };
}
