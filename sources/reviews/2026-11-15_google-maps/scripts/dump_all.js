() => {
  // Merges the states accumulated by extract_maps.js for the place currently open (by feature id from the URL).
  const fidMatch = /!1s(0x[0-9a-f]+:0x[0-9a-f]+)/.exec(location.href);
  const key = fidMatch ? fidMatch[1] : location.href;
  const states = (window.__gmAcc && window.__gmAcc[key]) || [];
  const byId = new Map();
  for (const st of states) {
    for (const rv of st.reviews) {
      if (!byId.has(rv.review_id)) {
        const copy = Object.assign({}, rv);
        delete copy.position;
        copy.seen_in = [];
        byId.set(rv.review_id, copy);
      }
      byId.get(rv.review_id).seen_in.push({sort: st.sort_label, position: rv.position, captured_at: st.captured_at});
    }
  }
  const last = states[states.length - 1] || {};
  return {
    generated_at: new Date().toISOString(),
    source: 'Google Maps side panel (hl=ru), signed out; reviews merged by data-review-id across sort orders',
    url: location.href,
    fid: key,
    place_name: last.place_name || null,
    summary: last.summary || null,
    limited_notice: last.limited_notice || null,
    more_button: last.more_button || null,
    states: states.map(st => ({
      sort_label: st.sort_label, aria_live: st.aria_live, captured_at: st.captured_at,
      rendered_reviews: st.rendered_reviews, more_button: st.more_button,
      review_ids: st.reviews.map(r => r.review_id)
    })),
    unique_reviews: byId.size,
    reviews: [...byId.values()]
  };
}
