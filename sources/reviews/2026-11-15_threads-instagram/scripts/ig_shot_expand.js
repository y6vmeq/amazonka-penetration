() => {
  // For a screenshot that shows the whole caption and all comments the page gives without login:
  // the scrollable comment pane of the post card is stretched to its full content height (styles only,
  // no text is changed, nothing is clicked except the close button of the sign-up prompt).
  const close = document.querySelector('[role=dialog] [aria-label="Закрыть"]');
  if (close) (close.closest('[role=button],button') || close).click();
  const out = { url: location.href, t: new Date().toISOString(), closedDialog: !!close, expanded: false };
  const pane = [...document.querySelectorAll('div')].find((e) => {
    const s = getComputedStyle(e);
    return /scroll|auto/.test(s.overflowY) && e.scrollHeight > e.clientHeight + 5 && e.clientWidth < 500;
  });
  if (pane) {
    let row = pane.parentElement;
    const isRow = (e) => {
      const s = getComputedStyle(e);
      return s.display === 'flex' && s.flexDirection === 'row' && e.children.length === 2
        && [...e.children].some((c) => !c.contains(pane) && c.querySelector('img, video'));
    };
    while (row && !isRow(row)) row = row.parentElement;
    if (row) {
      const media = [...row.children].find((c) => !c.contains(pane));
      const mr = media.getBoundingClientRect();
      media.style.height = mr.height + 'px';
      media.style.width = mr.width + 'px';
      media.style.alignSelf = 'flex-start';
      const full = pane.scrollHeight;
      pane.style.height = full + 'px';
      pane.style.maxHeight = 'none';
      pane.style.overflowY = 'visible';
      pane.style.flex = '0 0 auto';
      let e = pane.parentElement;
      while (e && e !== row.parentElement) {
        e.style.height = 'auto';
        e.style.maxHeight = 'none';
        e = e.parentElement;
      }
      out.expanded = true;
      out.paneFull = full;
    } else {
      out.err = 'no row';
    }
  } else {
    out.err = 'no scrollable pane (everything is already visible)';
  }
  const info = () => {
    out.docH = document.documentElement.scrollHeight;
    out.dialogs = document.querySelectorAll('[role=dialog]').length;
    out.scrollY = scrollY;
    if (pane) {
      const pr = pane.getBoundingClientRect();
      out.pane = [Math.round(pr.x), Math.round(pr.y + scrollY), Math.round(pr.width), Math.round(pr.height)];
      out.paneClient = pane.clientHeight;
      out.paneScroll = pane.scrollHeight;
      out.authors = [...pane.querySelectorAll('a[href^="/"]')]
        .filter((a) => a.innerText.trim() && a.getAttribute('href') === '/' + a.innerText.trim() + '/')
        .map((a) => a.innerText.trim() + ' y=' + Math.round(a.getBoundingClientRect().top + scrollY));
    }
    return out;
  };
  return new Promise((res) => setTimeout(() => res(info()), 900));
}
