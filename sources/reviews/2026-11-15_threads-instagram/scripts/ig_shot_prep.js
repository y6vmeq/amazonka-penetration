() => {
  // Before a screenshot of an Instagram post page (logged out): close the sign-up prompt (its own close button)
  // and report what the comment pane contains. Nothing else on the page is touched.
  const close = document.querySelector('[role=dialog] [aria-label="Закрыть"]');
  if (close) (close.closest('[role=button],button') || close).click();
  const info = () => {
    const pane = [...document.querySelectorAll('div')].find((e) => {
      const s = getComputedStyle(e);
      return /scroll|auto/.test(s.overflowY) && e.scrollHeight > e.clientHeight + 5 && e.clientWidth < 500;
    });
    const out = {
      url: location.href,
      t: new Date().toISOString(),
      iw: innerWidth,
      ih: innerHeight,
      docH: document.documentElement.scrollHeight,
      dialogs: document.querySelectorAll('[role=dialog]').length,
      closedDialog: !!close,
      title: document.title.slice(0, 120),
    };
    if (!pane) { out.pane = null; return out; }
    const pr = pane.getBoundingClientRect();
    out.pane = [Math.round(pr.x), Math.round(pr.y), Math.round(pr.width), Math.round(pr.height)];
    out.paneScrollHeight = pane.scrollHeight;
    out.authors = [...pane.querySelectorAll('a[href^="/"]')]
      .filter((a) => a.innerText.trim() && a.getAttribute('href') === '/' + a.innerText.trim() + '/')
      .map((a) => a.innerText.trim() + ' y=' + Math.round(a.getBoundingClientRect().top - pr.top + pane.scrollTop));
    return out;
  };
  return new Promise((res) => setTimeout(() => res(info()), 900));
}
