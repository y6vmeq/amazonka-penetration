() => {
  // Read-only: summary and HTML of the place panel that is currently open in Google Maps.
  const lab = s => (s == null ? null : s.replace(/ /g, ' ').replace(/\s+/g, ' ').trim());
  const h1 = [...document.querySelectorAll('h1')].find(h => h.innerText.trim());
  let panel = h1;
  while (panel && panel.getAttribute('role') !== 'main') panel = panel.parentElement;
  if (!panel) return {error: 'no panel', url: location.href, title: document.title};
  return {
    captured_at: new Date().toISOString(), url: location.href, name: lab(h1.innerText), panel_label: panel.getAttribute('aria-label'),
    rating: panel.querySelector('div.fontDisplayLarge') ? lab(panel.querySelector('div.fontDisplayLarge').textContent) : null,
    distribution: [...panel.querySelectorAll('tr.BHOKXe')].map(tr => lab(tr.getAttribute('aria-label'))),
    items: [...panel.querySelectorAll('button[data-item-id], a[data-item-id]')].map(b => ({id: b.getAttribute('data-item-id'), label: lab(b.getAttribute('aria-label') || b.innerText), href: b.href || null})),
    hours: [...panel.querySelectorAll('button[aria-label*="Скопировать часы работы"]')].map(b => lab(b.getAttribute('aria-label')).replace(', Скопировать часы работы', '')),
    tabs: [...panel.querySelectorAll('[role="tab"]')].map(t => lab(t.innerText)),
    headings: [...panel.querySelectorAll('h2')].map(h => lab(h.innerText)),
    text: lab(panel.innerText).slice(0, 2500),
    html: panel.outerHTML
  };
}
