() => {
  // Returns the HTML of the reviews panel (texts expanded) for every state accumulated by extract_maps.js.
  const fidMatch = /!1s(0x[0-9a-f]+:0x[0-9a-f]+)/.exec(location.href);
  const key = fidMatch ? fidMatch[1] : location.href;
  const states = (window.__gmAcc && window.__gmAcc[key]) || [];
  return {
    generated_at: new Date().toISOString(),
    source: 'Google Maps side panel (hl=ru), signed out; outerHTML of the reviews panel after expanding all texts, one entry per sort order',
    url: location.href,
    fid: key,
    panels: states.map(st => ({sort_label: st.sort_label, captured_at: st.captured_at, rendered_reviews: st.rendered_reviews, panel_html: st.panel_html}))
  };
}
