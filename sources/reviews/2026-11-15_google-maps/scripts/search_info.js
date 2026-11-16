async () => {
  // Read-only: describes what Google Maps shows after a search (result list or a place card).
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const lab = s => (s == null ? null : s.replace(/ /g, ' ').replace(/\s+/g, ' ').trim());
  await sleep(3500);
  const out = {captured_at: new Date().toISOString(), url: location.href, title: document.title};
  out.consent = /consent\.google/.test(location.href);
  out.sorry = /\/sorry\//.test(location.href) || /необычный трафик|unusual traffic/i.test(document.body.innerText.slice(0, 2000));
  const feed = document.querySelector('[role="feed"]');
  const links = [...document.querySelectorAll('a.hfpxzc')];
  out.results = links.map(a => {
    const card = a.closest('div.Nv2PK') || a.parentElement;
    return {name: a.getAttribute('aria-label'), href: a.href, text: card ? lab(card.innerText).slice(0, 260) : null};
  });
  out.has_feed = !!feed;
  const main = document.querySelector('div[role="main"]');
  const h1 = document.querySelector('h1');
  out.h1 = h1 ? lab(h1.innerText) : null;
  out.main_label = main ? main.getAttribute('aria-label') : null;
  if (main && h1 && !links.length) {
    out.card = {
      name: lab(h1.innerText),
      rating: document.querySelector('div.fontDisplayLarge') ? lab(document.querySelector('div.fontDisplayLarge').textContent) : null,
      distribution: [...document.querySelectorAll('tr.BHOKXe')].map(tr => lab(tr.getAttribute('aria-label'))),
      items: [...main.querySelectorAll('button[data-item-id], a[data-item-id]')].map(b => ({id: b.getAttribute('data-item-id'), label: lab(b.getAttribute('aria-label') || b.innerText), href: b.href || null})),
      hours: [...main.querySelectorAll('button[aria-label*="Скопировать часы работы"]')].map(b => lab(b.getAttribute('aria-label')).replace(', Скопировать часы работы', '')),
      tabs: [...document.querySelectorAll('[role="tab"]')].map(t => lab(t.innerText)),
      headings: [...main.querySelectorAll('h2')].map(h => lab(h.innerText)),
      text: lab(main.innerText).slice(0, 1500)
    };
  } else {
    out.body_text = lab((main || document.body).innerText).slice(0, 1200);
  }
  return out;
}
