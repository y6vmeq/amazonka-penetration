() => {
  // Read-only helper library for collecting the reviews that Google Maps renders in the side panel.
  // UI actions used: sort menu, the panel's own "search reviews" box, expanding truncated texts.
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const lab = s => (s == null ? null : s.replace(/ /g, ' ').replace(/\s+/g, ' ').trim());
  const S = window.__gmState || (window.__gmState = {});
  const fidOf = () => { const m = /!1s(0x[0-9a-f]+:0x[0-9a-f]+)/.exec(location.href); return m ? m[1] : location.href; };
  const store = () => { const k = fidOf(); return S[k] || (S[k] = {reviews: {}, order: [], log: [], panels: [], dumped: 0}); };
  const SORTS = ['Самые релевантные', 'Сначала новые', 'По убыванию рейтинга', 'По возрастанию рейтинга'];

  const els = () => [...document.querySelectorAll('div.jftiEf[data-review-id]')];
  const scroller = () => document.querySelector('div.m6QErb.DxyBCb.kA9KIf.dS8AEf');
  const input = () => document.querySelector('div[role="main"] input.yBHhWb');
  const sortBtn = () => document.querySelector('button.FNe70d');
  const curSort = () => { const b = sortBtn(); return b ? lab(b.getAttribute('aria-label')) : null; };
  const live = () => [...document.querySelectorAll('[aria-live]')].map(e => lab(e.innerText || '')).filter(Boolean);
  const dialogs = () => [...document.querySelectorAll('[role="dialog"]')].filter(d => d.offsetWidth).map(d => lab(d.innerText).slice(0, 300));

  async function waitReplaced(oldSet, oldLive, timeout) {
    const t0 = Date.now();
    let replaced = false;
    while (Date.now() - t0 < timeout) {
      await sleep(250);
      const cur = els();
      const liveNow = live().join('|');
      const anyOld = cur.some(e => oldSet.has(e));
      if (!anyOld && (cur.length > 0 || liveNow !== oldLive)) { replaced = true; break; }
    }
    await sleep(1200);
    return replaced;
  }

  async function setSort(idx) {
    if (curSort() === SORTS[idx]) return {changed: false, replaced: null};
    const b = sortBtn();
    if (!b) return {changed: false, error: 'no sort button'};
    const oldSet = new Set(els()); const oldLive = live().join('|');
    b.click();
    await sleep(700);
    const items = [...document.querySelectorAll('[role="menuitemradio"]')];
    if (!items[idx]) return {changed: false, error: 'no menu item'};
    items[idx].click();
    const replaced = await waitReplaced(oldSet, oldLive, 8000);
    return {changed: true, replaced: replaced};
  }

  async function setQuery(q) {
    const i = input();
    if (!i) return {error: 'no search input'};
    const oldSet = new Set(els()); const oldLive = live().join('|');
    i.focus();
    const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
    setter.call(i, q);
    i.dispatchEvent(new Event('input', {bubbles: true}));
    await sleep(150);
    for (const type of ['keydown', 'keypress', 'keyup']) {
      i.dispatchEvent(new KeyboardEvent(type, {key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true, cancelable: true}));
    }
    const replaced = await waitReplaced(oldSet, oldLive, 8000);
    return {replaced: replaced, value: i.value};
  }

  async function expandAll() {
    let n = 0;
    for (let pass = 0; pass < 6; pass++) {
      const btns = [...document.querySelectorAll('div.jftiEf[data-review-id] button.w8nwRe[aria-expanded="false"]')];
      if (!btns.length) break;
      for (const b of btns) { b.click(); n++; await sleep(200); }
      await sleep(400);
    }
    let originals = 0;
    for (const b of [...document.querySelectorAll('div.jftiEf[data-review-id] button')]) {
      const t = (b.innerText || '').trim();
      if (/оригинал/i.test(t)) { b.click(); originals++; await sleep(500); }
    }
    return {expanded: n, originals: originals};
  }

  const bgUrl = el => { const m = /url\(["']?([^"')]+)["']?\)/.exec(el.getAttribute('style') || ''); return m ? m[1] : null; };

  function extractReview(r) {
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
      reply = {label: spans.length ? spans[0] : null, date_shown: rd ? lab(rd.textContent) : null, text: rt ? rt.textContent : null, all_text: replyBox.innerText};
    }
    const photos = [...r.querySelectorAll('button.Tya61d')].map(b => ({aria: lab(b.getAttribute('aria-label')), thumb_url: bgUrl(b), overlay_text: lab(b.innerText) || null}));
    let photoCount = 0;
    for (const p of photos) { const m = /^Ещё (\d+) фото/.exec(p.aria || ''); photoCount += m ? parseInt(m[1], 10) : 1; }
    const structured = [...r.querySelectorAll('div[jslog^="126926"]')]
      .filter(b => !replyBox || !replyBox.contains(b))
      .map(b => [...b.querySelectorAll('span.RfDO5c')].map(s => lab(s.textContent)).filter(Boolean))
      .filter(a => a.length);
    const badge = q('div.J7sVM');
    const translate = [...r.querySelectorAll('button, span')].filter(e => e.children.length === 0)
      .map(e => lab(e.textContent)).filter(t => t && /оригинал|Переведено|перевод/i.test(t) && t.length < 80);
    const rect = r.getBoundingClientRect();
    return {
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
      translate_controls: translate,
      still_collapsed: r.querySelectorAll('button.w8nwRe[aria-expanded="false"]').length,
      rect: {x: rect.x, y: rect.y, w: rect.width, h: rect.height},
      outer_html: r.outerHTML
    };
  }

  function summaryBlock() {
    const big = document.querySelector('div.fontDisplayLarge');
    const cnt = [...document.querySelectorAll('div, button, span')].find(x => x.children.length === 0 && /^Отзывов:\s*[\d\s]+$/.test(lab(x.textContent) || ''));
    return {
      rating: big ? lab(big.textContent) : null,
      distribution: [...document.querySelectorAll('tr.BHOKXe')].map(tr => lab(tr.getAttribute('aria-label'))),
      count_text: cnt ? lab(cnt.textContent) : null
    };
  }

  async function capture(tag) {
    const sc = scroller();
    if (sc) sc.scrollTop = 0;
    const ex = await expandAll();
    if (sc) sc.scrollTop = 0;
    await sleep(300);
    const st = store();
    const i = input();
    const main = document.querySelector('div[role="main"]');
    const more = [...document.querySelectorAll('button')].find(b => /Показать другие отзывы|Ещё отзывы/.test(b.innerText || ''));
    const limited = [...document.querySelectorAll('span')].filter(e => /ограниченная версия/i.test(e.textContent || '') && e.querySelectorAll('span').length === 0).map(e => lab(e.textContent));
    const reviews = els().map(extractReview);
    const scRect = sc ? sc.getBoundingClientRect() : null;
    const state = {
      seq: st.log.length + 1,
      tag: tag || null,
      captured_at: new Date().toISOString(),
      url: location.href,
      fid: fidOf(),
      place_name: main ? main.getAttribute('aria-label') : null,
      query: i ? i.value : null,
      sort_label: curSort(),
      aria_live: live(),
      summary: summaryBlock(),
      rendered_reviews: reviews.length,
      expanded_clicks: ex.expanded,
      original_clicks: ex.originals,
      more_button: more ? lab(more.innerText) : null,
      limited_notice: limited,
      dialogs: dialogs(),
      viewport: {w: innerWidth, h: innerHeight, dpr: devicePixelRatio},
      scroller: sc ? {scrollHeight: sc.scrollHeight, clientHeight: sc.clientHeight, scrollTop: sc.scrollTop, rect: {x: scRect.x, y: scRect.y, w: scRect.width, h: scRect.height}} : null,
      empty_text: reviews.length ? null : (sc ? lab(sc.innerText).slice(-400) : null),
      reviews: reviews
    };
    const newIds = [];
    reviews.forEach((rv, idx) => {
      const seen = {seq: state.seq, query: state.query, sort: state.sort_label, position: idx + 1, captured_at: state.captured_at};
      if (!st.reviews[rv.review_id]) {
        const copy = Object.assign({}, rv); delete copy.rect;
        copy.seen_in = [seen];
        st.reviews[rv.review_id] = copy; st.order.push(rv.review_id); newIds.push(rv.review_id);
      } else {
        const old = st.reviews[rv.review_id];
        old.seen_in.push(seen);
        if (!old.outer_html) old.outer_html = rv.outer_html;
        if ((rv.text || '') !== (old.text || '') || (rv.date_shown || '') !== (old.date_shown || '') || rv.rating !== old.rating) {
          old.variants = old.variants || [];
          old.variants.push({seq: state.seq, text: rv.text, date_shown: rv.date_shown, rating: rv.rating});
        }
      }
    });
    state.new_ids = newIds;
    for (const rv of state.reviews) { if (!newIds.includes(rv.review_id)) delete rv.outer_html; }
    st.log.push(state);
    return state;
  }

  function brief(state) {
    return {
      seq: state.seq, query: state.query, sort: state.sort_label, live: state.aria_live, n: state.rendered_reviews,
      more: state.more_button, dialogs: state.dialogs, scroller: state.scroller ? [state.scroller.scrollHeight, state.scroller.clientHeight] : null,
      empty_text: state.empty_text,
      total_unique: store().order.length,
      reviews: state.reviews.map(r => ({id: r.review_id.slice(-14), a: r.author, r: r.rating, d: r.date_shown, len: (r.text || '').length, new: state.new_ids.includes(r.review_id), reply: !!r.reply, ph: r.photo_count, coll: r.still_collapsed, tr: r.translate_controls.length ? r.translate_controls : undefined}))
    };
  }

  async function run(query, sortIdx, tag) {
    const out = {};
    if (sortIdx != null) out.sort = await setSort(sortIdx);
    if (query != null) {
      const i = input();
      if (!i || i.value !== query) out.query = await setQuery(query);
    }
    const state = await capture(tag);
    const b = brief(state);
    b.actions = out;
    return b;
  }

  async function runBatch(queries, sortIdx, tag) {
    const t0 = Date.now();
    const out = [];
    for (const q of queries) {
      const b = await run(q, sortIdx, tag);
      out.push({
        seq: b.seq, q: b.query, sort: b.sort, n: b.n, more: !!b.more, dlg: b.dialogs.length ? b.dialogs : undefined,
        live: (b.live || []).join(' / '), repl: b.actions.query ? b.actions.query.replaced : null,
        fit: b.scroller ? b.scroller[0] <= b.scroller[1] : null,
        empty: b.empty_text || undefined,
        new: b.reviews.filter(r => r.new).map(r => r.a + ' | ' + r.r + ' | ' + r.d + ' | len ' + r.len),
        coll: b.reviews.some(r => r.coll) || undefined
      });
      if (b.dialogs.length) break;
      await sleep(1200 + Math.floor(Math.random() * 900));
    }
    return {ms: Date.now() - t0, total_unique: store().order.length, states: out};
  }

  // ---- systematic enumeration through the panel's own review search (AND / -NOT of exact words) ----
  const BASE = {t: 'ъъъ', neg: true};
  const qstr = cons => cons.map(c => (c.neg ? '-' : '') + c.t).join(' ');
  const toks = text => [...new Set((text || '').toLowerCase().split(/[^a-zа-яё0-9]+/).filter(w => w.length >= 2 && w.length <= 20 && /^[a-zа-я]+$/.test(w)))];

  function chooseToken(reviews, cons) {
    const used = new Set(cons.map(c => c.t));
    const n = reviews.length;
    const count = new Map();
    for (const rv of reviews) for (const t of toks(rv.text)) count.set(t, (count.get(t) || 0) + 1);
    let best = null;
    for (const [t, k] of count) {
      if (used.has(t) || k < 1 || k > n - 1) continue;
      const score = Math.abs(k - n / 2) * 100 - Math.min(t.length, 8);
      if (!best || score < best.score) best = {t: t, k: k, score: score};
    }
    return best;
  }

  function explorer() {
    const st = store();
    if (!st.explore) st.explore = {queue: [{cons: [BASE], depth: 0, prio: 0}], nodes: [], residual: [], aborted: null};
    return st.explore;
  }

  async function exploreStep(maxNodes, maxMs) {
    const X = explorer();
    const t0 = Date.now();
    const out = [];
    let processed = 0;
    while (X.queue.length && processed < maxNodes && Date.now() - t0 < maxMs && !X.aborted) {
      X.queue.sort((a, b) => (a.prio - b.prio) || (a.depth - b.depth));
      const node = X.queue.shift();
      const q = qstr(node.cons);
      if (q.length > 500) { X.residual.push({q: q, reason: 'query too long'}); continue; }
      const b = await run(q, 3, 'explore');
      processed++;
      const st = store();
      const state = st.log[st.log.length - 1];
      if (state.dialogs.length) { X.aborted = {q: q, dialogs: state.dialogs}; X.queue.unshift(node); break; }
      const rec = {seq: state.seq, q: q, depth: node.depth, n: state.rendered_reviews, more: !!state.more_button, ratings: state.reviews.map(r => r.rating), newc: state.new_ids.length, split: null};
      if (state.more_button) {
        let basis = state.reviews;
        let pick = chooseToken(basis, node.cons);
        if (!pick) {
          // no usable word among the visible reviews (e.g. only ratings without text): look at the same subset by relevance
          await run(q, 0, 'explore-relevant');
          const st2 = store().log[store().log.length - 1];
          basis = st2.reviews;
          pick = chooseToken(basis, node.cons);
          rec.fallback = {seq: st2.seq, n: st2.rendered_reviews, with_text: st2.reviews.filter(r => r.text).length};
          if (!pick) {
            await run(q, 1, 'explore-newest');
            const st3 = store().log[store().log.length - 1];
            basis = st3.reviews;
            pick = chooseToken(basis, node.cons);
            rec.fallback.newest = {seq: st3.seq, with_text: st3.reviews.filter(r => r.text).length};
            if (!pick) {
              await run(q, 2, 'explore-highest');
              const st4 = store().log[store().log.length - 1];
              basis = st4.reviews;
              pick = chooseToken(basis, node.cons);
              rec.fallback.highest = {seq: st4.seq, with_text: st4.reviews.filter(r => r.text).length};
            }
          }
        }
        if (pick) {
          rec.split = pick.t + ' (' + pick.k + '/' + basis.length + ')';
          const withT = basis.filter(r => toks(r.text).includes(pick.t));
          const without = basis.filter(r => !toks(r.text).includes(pick.t));
          const minr = arr => arr.length ? Math.min(...arr.map(r => r.rating || 5)) : 5;
          X.queue.push({cons: node.cons.concat([{t: pick.t, neg: false}]), depth: node.depth + 1, prio: minr(withT)});
          X.queue.push({cons: node.cons.concat([{t: pick.t, neg: true}]), depth: node.depth + 1, prio: minr(without)});
        } else {
          rec.split = 'RESIDUAL (no text in visible reviews under any sort)';
          X.residual.push({q: q, seq: state.seq, reason: 'truncated subset without text'});
        }
      }
      X.nodes.push(rec);
      out.push(rec);
      await sleep(1000 + Math.floor(Math.random() * 800));
    }
    const st = store();
    const byRating = {};
    for (const id of st.order) { const r = st.reviews[id].rating; byRating[r] = (byRating[r] || 0) + 1; }
    return {ms: Date.now() - t0, processed: processed, queue: X.queue.length, nodes: X.nodes.length, residual: X.residual.length, aborted: X.aborted, total_unique: st.order.length, by_rating: byRating, with_text: st.order.filter(id => st.reviews[id].text).length, last_seq: st.log.length, out: out};
  }

  function importLegacy() {
    const st = store();
    const legacy = (window.__gmAcc && window.__gmAcc[fidOf()]) || [];
    let added = 0;
    for (const old of legacy) {
      if (st.panels.some(p => p.captured_at === old.captured_at)) continue;
      const seq = st.log.length + 1;
      st.panels.push({seq: seq, query: '', sort_label: old.sort_label, captured_at: old.captured_at, rendered_reviews: old.rendered_reviews, panel_html: old.panel_html});
      const state = Object.assign({}, old, {seq: seq, tag: 'legacy-no-query', query: ''});
      delete state.panel_html;
      state.new_ids = [];
      old.reviews.forEach((rv, idx) => {
        const seen = {seq: seq, query: '', sort: old.sort_label, position: idx + 1, captured_at: old.captured_at};
        if (!st.reviews[rv.review_id]) {
          const copy = Object.assign({}, rv); delete copy.position; delete copy.translated_note;
          copy.seen_in = [seen];
          st.reviews[rv.review_id] = copy; st.order.push(rv.review_id); state.new_ids.push(rv.review_id); added++;
        } else {
          st.reviews[rv.review_id].seen_in.push(seen);
        }
      });
      st.log.push(state);
    }
    return {legacy_states: legacy.length, added: added, total_unique: st.order.length, log: st.log.length};
  }

  function dumpAll() {
    const st = store();
    const lastState = st.log[st.log.length - 1] || {};
    return {
      generated_at: new Date().toISOString(),
      source: 'Google Maps side panel (hl=ru), signed out, "limited version": at most 5 reviews per sort order / per review-search query. Reviews merged by data-review-id.',
      url: location.href,
      fid: fidOf(),
      place_name: lastState.place_name || null,
      summary: lastState.summary || null,
      states: st.log.map(s => ({seq: s.seq, tag: s.tag, captured_at: s.captured_at, query: s.query, sort_label: s.sort_label, aria_live: s.aria_live, rendered_reviews: s.rendered_reviews, more_button: s.more_button, limited_notice: s.limited_notice, empty_text: s.empty_text, review_ids: s.reviews.map(r => r.review_id), new_ids: s.new_ids})),
      unique_reviews: st.order.length,
      reviews: st.order.map(id => { const c = Object.assign({}, st.reviews[id]); delete c.outer_html; return c; })
    };
  }

  function dumpHtml() {
    const st = store();
    return {
      generated_at: new Date().toISOString(),
      source: 'Google Maps side panel (hl=ru), signed out. panels: outerHTML of the whole reviews panel per sort order (no search query), texts expanded. review_html: outerHTML of every collected review element with the text expanded.',
      url: location.href,
      fid: fidOf(),
      panels: st.panels,
      review_html: st.order.map(id => ({review_id: id, author: st.reviews[id].author, outer_html: st.reviews[id].outer_html || null}))
    };
  }

  function dumpStates(fromSeq, toSeq) {
    const st = store();
    return {
      generated_at: new Date().toISOString(),
      source: 'Google Maps side panel (hl=ru), signed out; raw per-state captures (review-search query + sort order)',
      fid: fidOf(),
      states: st.log.filter(s => s.seq >= fromSeq && s.seq <= toSeq)
    };
  }

  window.__gm = {run, runBatch, capture, brief, setSort, setQuery, importLegacy, dumpAll, dumpHtml, dumpStates, store, SORTS, exploreStep, explorer, qstr, toks};
  return {installed: true, fid: fidOf(), states: store().log.length, unique: store().order.length};
}
