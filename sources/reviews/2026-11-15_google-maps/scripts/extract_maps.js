async () => {
  // Read-only extraction of the reviews currently rendered in the Google Maps side panel.
  // Only UI actions: expanding truncated texts ("Ещё") and switching translated texts to the original.
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const lab = s => (s == null ? null : s.replace(/ /g, ' ').replace(/\s+/g, ' ').trim());

  let expanded = 0;
  for (let pass = 0; pass < 6; pass++) {
    const btns = [...document.querySelectorAll('div.jftiEf[data-review-id] button.w8nwRe[aria-expanded="false"]')];
    if (!btns.length) break;
    for (const b of btns) { b.click(); expanded++; await sleep(250); }
    await sleep(500);
  }
  let originals = 0;
  for (const b of [...document.querySelectorAll('div.jftiEf[data-review-id] button')]) {
    const t = (b.innerText || '').trim();
    if (/оригинал/i.test(t)) { b.click(); originals++; await sleep(500); }
  }
  await sleep(300);

  const bgUrl = el => {
    const m = /url\(["']?([^"')]+)["']?\)/.exec(el.getAttribute('style') || '');
    return m ? m[1] : null;
  };

  const els = [...document.querySelectorAll('div.jftiEf[data-review-id]')];
  const reviews = els.map((r, i) => {
    const q = s => r.querySelector(s);
    const ratingEl = q('span.kvMYJc');
    const ratingLabel = ratingEl ? lab(ratingEl.getAttribute('aria-label')) : null;
    const altRating = q('span.fzvQIb') ? lab(q('span.fzvQIb').textContent) : null;
    let rating = null;
    const src = ratingLabel || altRating;
    if (src) { const m = /(\d+)/.exec(src); if (m) rating = parseInt(m[1], 10); }
    const textEl = q('div.MyEned span.wiI7pd');
    const replyBox = q('div.CDe7pd');
    let reply = null;
    if (replyBox) {
      const rt = replyBox.querySelector('.wiI7pd');
      const rd = replyBox.querySelector('.DZSIDd');
      const spans = [...replyBox.querySelectorAll('span')].map(s => lab(s.textContent)).filter(Boolean);
      reply = {
        label: spans.length ? spans[0] : null,
        date_shown: rd ? lab(rd.textContent) : null,
        text: rt ? rt.textContent : null,
        all_text: replyBox.innerText,
        lang: rt && rt.parentElement ? rt.parentElement.getAttribute('lang') : null
      };
    }
    const photoBtns = [...r.querySelectorAll('button.Tya61d')];
    const photos = photoBtns.map(b => ({
      aria: lab(b.getAttribute('aria-label')),
      thumb_url: bgUrl(b),
      overlay_text: lab(b.innerText) || null
    }));
    let photoCount = 0;
    for (const p of photos) {
      const m = /^Ещё (\d+) фото/.exec(p.aria || '');
      photoCount += m ? parseInt(m[1], 10) : 1;
    }
    const structured = [...r.querySelectorAll('div[jslog^="126926"]')]
      .filter(b => !replyBox || !replyBox.contains(b))
      .map(b => [...b.querySelectorAll('span.RfDO5c')].map(s => lab(s.textContent)).filter(Boolean))
      .filter(a => a.length);
    const badge = q('div.J7sVM');
    const translateBtns = [...r.querySelectorAll('button')]
      .map(b => lab(b.innerText)).filter(t => t && /оригинал|перевод|Переведено/i.test(t));
    const translatedNote = [...r.querySelectorAll('span, div')]
      .filter(e => e.children.length === 0 && /Переведено|перевод Google/i.test(e.textContent || ''))
      .map(e => lab(e.textContent));
    const stillCollapsed = r.querySelectorAll('button.w8nwRe[aria-expanded="false"]').length;
    return {
      position: i + 1,
      review_id: r.getAttribute('data-review-id'),
      author: lab(q('.d4r55') ? q('.d4r55').textContent : r.getAttribute('aria-label')),
      rating_label: ratingLabel || altRating,
      rating: rating,
      date_shown: lab(q('span.rsqaWe') ? q('span.rsqaWe').textContent : null),
      badge: badge ? lab(badge.textContent) : null,
      text: textEl ? textEl.textContent : null,
      text_lang: q('div.MyEned') ? q('div.MyEned').getAttribute('lang') : null,
      structured: structured,
      reply: reply,
      photo_count: photoCount,
      photos: photos,
      translate_controls: translateBtns,
      translated_note: translatedNote,
      still_collapsed: stillCollapsed
    };
  });

  const main = document.querySelector('div[role="main"]');
  const scroller = document.querySelector('div.m6QErb.DxyBCb.kA9KIf.dS8AEf');
  const sortBtn = document.querySelector('button.FNe70d');
  const moreBtn = [...document.querySelectorAll('button')].find(b => /Показать другие отзывы|Ещё отзывы/.test(b.innerText || ''));
  const fidMatch = /!1s(0x[0-9a-f]+:0x[0-9a-f]+)/.exec(location.href);
  const fid = fidMatch ? fidMatch[1] : null;
  const live = [...document.querySelectorAll('[aria-live]')].map(e => lab(e.innerText || '')).filter(Boolean);
  const limited = [...document.querySelectorAll('span')]
    .filter(e => /ограниченная версия/i.test(e.textContent || '') && e.querySelectorAll('span').length === 0)
    .map(e => lab(e.textContent));
  const result = {
    captured_at: new Date().toISOString(),
    url: location.href,
    fid: fid,
    place_name: main ? main.getAttribute('aria-label') : null,
    sort_label: sortBtn ? lab(sortBtn.getAttribute('aria-label')) : null,
    aria_live: live,
    summary: {
      rating: document.querySelector('div.fontDisplayLarge') ? lab(document.querySelector('div.fontDisplayLarge').textContent) : null,
      distribution: [...document.querySelectorAll('tr.BHOKXe')].map(tr => lab(tr.getAttribute('aria-label'))),
      count_text: (() => { const e = [...document.querySelectorAll('div, button, span')].find(x => x.children.length === 0 && /^Отзывов:\s*[\d\s]+$/.test(lab(x.textContent) || '')); return e ? lab(e.textContent) : null; })()
    },
    rendered_reviews: reviews.length,
    expanded_clicks: expanded,
    original_clicks: originals,
    more_button: moreBtn ? lab(moreBtn.innerText) : null,
    limited_notice: limited,
    reviews: reviews,
    panel_html: scroller ? scroller.outerHTML : (main ? main.outerHTML : null)
  };
  window.__gmAcc = window.__gmAcc || {};
  const key = fid || location.href;
  window.__gmAcc[key] = window.__gmAcc[key] || [];
  window.__gmAcc[key].push(result);
  return result;
}
