async () => {
  // Read-only breadth-first crawl of Threads post pages (logged-out) using same-origin GET requests
  // from the page context. Config comes from window.__cfg = {seeds: [url...], maxPages, delayMs, follow}.
  // Fetched HTML is kept in window.__crawl.pages for later retrieval in chunks (threads_crawl_get.js).
  const cfg = window.__cfg || {};
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const st = window.__crawl = window.__crawl || { pages: [], visited: {}, posts: {}, parent: {}, queue: [] };
  const maxPages = cfg.maxPages || 12;
  const delayMs = cfg.delayMs || 2200;

  const best = cands => {
    if (!cands || !cands.length) return null;
    let b = cands[0];
    for (const c of cands) if ((c.width || 0) * (c.height || 0) > (b.width || 0) * (b.height || 0)) b = c;
    return { url: b.url, width: b.width || null, height: b.height || null };
  };
  const mediaOf = o => {
    const m = [];
    const one = (x, idx) => {
      if (!x) return;
      if (x.video_versions && x.video_versions.length) {
        m.push({ kind: 'video', idx, url: x.video_versions[0].url, has_audio: x.has_audio === undefined ? null : x.has_audio,
                 w: x.original_width || null, h: x.original_height || null, poster: (best(x.image_versions2 && x.image_versions2.candidates) || {}).url || null,
                 alt: x.accessibility_caption || null });
      } else {
        const b = best(x.image_versions2 && x.image_versions2.candidates);
        if (b) m.push({ kind: 'image', idx, url: b.url, w: b.width, h: b.height, alt: x.accessibility_caption || null });
      }
    };
    if (o.carousel_media && o.carousel_media.length) o.carousel_media.forEach((x, i) => one(x, i + 1));
    else one(o, 1);
    if (o.giphy_media_info && o.giphy_media_info.images) {
      const g = o.giphy_media_info.images;
      const u = (g.fixed_height && (g.fixed_height.webp || g.fixed_height.url)) || null;
      if (u) m.push({ kind: 'gif', idx: 1, url: u });
    }
    return m;
  };
  const brief = o => !o ? null : { code: o.code || null, user: o.user ? o.user.username : null, text: o.caption ? o.caption.text : null, taken_at: o.taken_at || null };
  const ctxOf = path => {
    let m;
    if ((m = path.match(/direct_replies\.edges\[(\d+)\]\.node\.posts\.edges\[(\d+)\]\.node$/))) return { kind: 'direct_reply', chain: +m[1], pos: +m[2] };
    if ((m = path.match(/self_thread\.posts\.edges\[(\d+)\]\.node$/))) return { kind: 'self_thread', pos: +m[1] };
    if ((m = path.match(/pinned_replies\.edges\[(\d+)\]\.node\.posts\.edges\[(\d+)\]\.node$/))) return { kind: 'pinned_reply', chain: +m[1], pos: +m[2] };
    if ((m = path.match(/containing_thread\.posts\.edges\[(\d+)\]\.node$/))) return { kind: 'ancestor', pos: +m[1] };
    if (/relatedPosts/.test(path)) return { kind: 'related' };
    if (/quoted_post$/.test(path)) return { kind: 'quoted' };
    if (/reposted_post$/.test(path)) return { kind: 'reposted' };
    if ((m = path.match(/thread_items\[(\d+)\]\.post$/))) {
      const e = path.match(/edges\[(\d+)\]\.node\.thread_items/);
      return { kind: 'thread_item', chain: e ? +e[1] : null, pos: +m[1] };
    }
    if (/result\.data\.media$/.test(path) || /result\.data\.data$/.test(path)) return { kind: 'main' };
    return { kind: 'other' };
  };
  const extract = html => {
    const doc = new DOMParser().parseFromString(html, 'text/html');
    const posts = []; const seen = new Set(); const pageInfos = [];
    const walk = (o, path, depth) => {
      if (!o || typeof o !== 'object' || depth > 70) return;
      if (Array.isArray(o)) { for (let i = 0; i < o.length; i++) walk(o[i], path + '[' + i + ']', depth + 1); return; }
      if (o.page_info && typeof o.page_info === 'object' && 'has_next_page' in o.page_info && o.page_info.has_next_page) {
        pageInfos.push({ path: path.slice(-100), edges: Array.isArray(o.edges) ? o.edges.length : null });
      }
      if (typeof o.code === 'string' && o.user && typeof o.user.username === 'string' && ('taken_at' in o)) {
        const tpa = o.text_post_app_info || {};
        const si = tpa.share_info || {};
        const frags = (tpa.text_fragments && tpa.text_fragments.fragments) || [];
        const mentions = []; const links = [];
        for (const f of frags) {
          if (f.mention_fragment && f.mention_fragment.mentioned_user) mentions.push(f.mention_fragment.mentioned_user.username);
          if (f.link_fragment && f.link_fragment.uri) links.push(f.link_fragment.uri);
        }
        const key = o.code + '|' + path;
        if (!seen.has(key)) {
          seen.add(key);
          posts.push({
            code: o.code, pk: o.pk || null, user: o.user.username,
            taken_at: o.taken_at, iso: o.taken_at ? new Date(o.taken_at * 1000).toISOString() : null,
            text: o.caption ? o.caption.text : null, edited: !!o.caption_is_edited,
            permalink: o.permalink || null,
            like_count: o.like_count === undefined ? null : o.like_count,
            direct_reply_count: tpa.direct_reply_count === undefined ? null : tpa.direct_reply_count,
            repost_count: tpa.repost_count === undefined ? null : tpa.repost_count,
            quote_count: tpa.quote_count === undefined ? null : tpa.quote_count,
            reshare_count: tpa.reshare_count === undefined ? null : tpa.reshare_count,
            is_reply: tpa.is_reply === undefined ? null : tpa.is_reply,
            reply_level: tpa.reply_level === undefined ? null : tpa.reply_level,
            reply_to: tpa.reply_to_author ? tpa.reply_to_author.username : null,
            root_author: tpa.root_post_author ? tpa.root_post_author.username : null,
            liked_by_root_author: tpa.is_liked_by_root_author === undefined ? null : tpa.is_liked_by_root_author,
            tag: tpa.tag_header ? (tpa.tag_header.display_name || tpa.tag_header.title || JSON.stringify(tpa.tag_header).slice(0, 200)) : null,
            quoted: brief(si.quoted_post), reposted: brief(si.reposted_post),
            link_preview: tpa.link_preview_attachment ? { url: tpa.link_preview_attachment.url || null, title: tpa.link_preview_attachment.title || null, display_url: tpa.link_preview_attachment.display_url || null } : null,
            mentions, links,
            usertags: o.usertags && o.usertags.in ? o.usertags.in.map(u => u.user && u.user.username).filter(Boolean) : [],
            media_type: o.media_type === undefined ? null : o.media_type,
            media: mediaOf(o),
            transcription: o.transcription_data || null,
            unavailable: tpa.is_post_unavailable || false,
            ctx: ctxOf(path), path: path.slice(-150),
          });
        }
      }
      for (const k of Object.keys(o)) walk(o[k], path + '.' + k, depth + 1);
    };
    const scripts = [...doc.querySelectorAll('script[type="application/json"]')];
    scripts.forEach((s, i) => { const t = s.textContent; if (t.includes('"taken_at"') || t.includes('"page_info"')) { try { walk(JSON.parse(t), 's' + i, 0); } catch (e) {} } });
    return { posts, pageInfos, title: doc.title };
  };
  const codeOf = url => { const m = url.match(/\/post\/([A-Za-z0-9_-]+)/); return m ? m[1] : url; };

  for (const v of (cfg.visited || [])) st.visited[v] = true;
  for (const s of (cfg.seeds || [])) { const c = codeOf(s); if (!st.visited[c] && !st.queue.some(q => codeOf(q) === c)) st.queue.push(s); }
  const log = st.log = st.log || [];
  let fetched = 0;
  st.running = true; st.stopReason = null;
  const run = async () => {
  while (st.queue.length && fetched < maxPages) {
    const url = st.queue.shift();
    const code = codeOf(url);
    if (st.visited[code]) continue;
    let html = null, status = null, finalUrl = null, err = null;
    const fetched_at = new Date().toISOString();
    try {
      const r = await fetch(url, { credentials: 'include', headers: { 'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8' } });
      status = r.status; finalUrl = r.url; html = await r.text();
    } catch (e) { err = String(e); }
    fetched++;
    st.visited[code] = true;
    if (err || status !== 200 || !html) { log.push({ url, status, err }); if (status === 429 || status === 403) { st.stopReason = 'http ' + status; break; } await sleep(delayMs); continue; }
    const ex = extract(html);
    const loginRedirect = /\/login/.test(finalUrl || '');
    const main = ex.posts.find(p => p.ctx.kind === 'main');
    const mainCode = main ? main.code : code;
    // parent inference
    const chains = {};
    for (const p of ex.posts) {
      const c = p.ctx;
      if (c.kind === 'direct_reply' || c.kind === 'pinned_reply') (chains[c.kind + c.chain] = chains[c.kind + c.chain] || {})[c.pos] = p.code;
      if (c.kind === 'self_thread') (chains.self = chains.self || {})[c.pos] = p.code;
      if (c.kind === 'ancestor') (chains.anc = chains.anc || {})[c.pos] = p.code;
    }
    if (chains.anc) {
      const ks = Object.keys(chains.anc).map(Number).sort((a, b) => a - b);
      const last = chains.anc[ks[ks.length - 1]];
      if (last && last !== mainCode && !st.parent[mainCode]) st.parent[mainCode] = last;
    }
    let newPosts = 0;
    for (const p of ex.posts) {
      const c = p.ctx;
      if (c.kind === 'related') continue;
      let parent = null;
      if (c.kind === 'direct_reply' || c.kind === 'pinned_reply') parent = c.pos > 0 ? (chains[c.kind + c.chain][c.pos - 1] || null) : mainCode;
      if (c.kind === 'self_thread') parent = c.pos > 0 ? (chains.self[c.pos - 1] || null) : mainCode;
      if (c.kind === 'ancestor' && c.pos > 0) parent = chains.anc[c.pos - 1] || null;
      if (parent && !st.parent[p.code]) st.parent[p.code] = parent;
      if (!st.posts[p.code]) { st.posts[p.code] = { code: p.code, user: p.user, drc: p.direct_reply_count, ctx: c.kind, url: p.permalink }; newPosts++; }
      else if (p.direct_reply_count !== null) st.posts[p.code].drc = p.direct_reply_count;
    }
    st.pages.push({ url, finalUrl, status, fetched_at, code, mainCode, title: ex.title, posts: ex.posts, pageInfos: ex.pageInfos, html, loginRedirect, retrieved: false });
    log.push({ url: url.replace('https://www.threads.com', ''), status, len: html.length, posts: ex.posts.filter(p => p.ctx.kind !== 'related').length, newPosts, more: ex.pageInfos.length, loginRedirect, kinds: [...new Set(ex.posts.map(p => p.ctx.kind))].join(',') });
    // enqueue posts whose direct replies are not all known
    if (cfg.follow !== false) {
      const childCount = {};
      for (const k of Object.keys(st.parent)) childCount[st.parent[k]] = (childCount[st.parent[k]] || 0) + 1;
      for (const k of Object.keys(st.posts)) {
        const p = st.posts[k];
        if (p.ctx === 'quoted' || p.ctx === 'reposted' || p.ctx === 'other') continue;
        if ((p.drc || 0) > (childCount[k] || 0) && !st.visited[k] && p.url && !st.queue.some(q => codeOf(q) === k)) st.queue.push(p.url);
      }
    }
    await sleep(delayMs + Math.floor(Math.random() * 600));
  }
  st.running = false;
  };
  run().catch(e => { st.running = false; st.stopReason = 'error ' + String(e); });
  return { started: true, queue: st.queue.length, maxPages };
}
