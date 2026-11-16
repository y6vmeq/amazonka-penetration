async () => {
  // Read-only extraction of a Threads page (post or profile), logged-out view.
  // Returns: {url, fetched_at, title, posts (from embedded JSON), dom (rendered items), html (outerHTML)}.
  // Nothing is clicked here.
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  // --- scroll to the end until nothing new loads (read-only, no clicks) ---
  {
    const count = () => document.querySelectorAll('div[data-pressable-container="true"]').length;
    let stable = 0, last = '';
    const scrollLog = [];
    for (let i = 0; i < 40 && stable < 4; i++) {
      window.scrollTo(0, document.documentElement.scrollHeight);
      await sleep(1500);
      const sig = [count(), document.documentElement.scrollHeight, (window.__gql || []).length].join('/');
      scrollLog.push(sig);
      if (sig === last) stable++; else stable = 0;
      last = sig;
    }
    window.scrollTo(0, 0);
    await sleep(700);
    window.__scrollLog = scrollLog;
  }
  const out = { url: location.href, fetched_at: new Date().toISOString(), title: document.title };
  out.scroll_log = window.__scrollLog || null;

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
  const brief = o => !o ? null : {
    code: o.code || null, user: o.user ? o.user.username : null,
    text: o.caption ? o.caption.text : null, taken_at: o.taken_at || null,
  };
  const ctxOf = path => {
    let m;
    if ((m = path.match(/direct_replies\.edges\[(\d+)\]\.node\.posts\.edges\[(\d+)\]\.node$/))) return { kind: 'direct_reply', chain: +m[1], pos: +m[2] };
    if ((m = path.match(/self_thread\.posts\.edges\[(\d+)\]\.node$/))) return { kind: 'self_thread', pos: +m[1] };
    if ((m = path.match(/pinned_replies\.edges\[(\d+)\]/))) return { kind: 'pinned_reply', chain: +m[1] };
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

  const posts = []; const seen = new Set();
  const pageInfos = [];
  const walk = (o, path, depth) => {
    if (!o || typeof o !== 'object' || depth > 70) return;
    if (Array.isArray(o)) { for (let i = 0; i < o.length; i++) walk(o[i], path + '[' + i + ']', depth + 1); return; }
    if (o.page_info && typeof o.page_info === 'object' && 'has_next_page' in o.page_info) {
      pageInfos.push({ path: path.slice(-110), has_next_page: o.page_info.has_next_page, end_cursor: o.page_info.end_cursor ? String(o.page_info.end_cursor).slice(0, 40) : null, edges: Array.isArray(o.edges) ? o.edges.length : null });
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
          ctx: Object.assign(ctxOf(path), { src: path.split('.')[0] }), path: path.slice(-140),
        });
      }
    }
    for (const k of Object.keys(o)) walk(o[k], path + '.' + k, depth + 1);
  };
  const scripts = [...document.querySelectorAll('script[type="application/json"]')];
  let parsed = 0;
  scripts.forEach((s, i) => {
    const t = s.textContent;
    if (t.includes('"taken_at"') || t.includes('"page_info"')) { try { walk(JSON.parse(t), 's' + i, 0); parsed++; } catch (e) {} }
  });
  out.json_scripts = scripts.length; out.json_scripts_parsed = parsed;
  // responses the page itself received from its GraphQL endpoint after load (captured passively by the init hook)
  const gql = window.__gql || [];
  out.gql = [];
  gql.forEach((g, gi) => {
    const before = posts.length;
    let parts = 0;
    for (const line of String(g.text || '').split(String.fromCharCode(10))) {
      const t = line.trim();
      if (!t || t[0] !== '{') continue;
      try { walk(JSON.parse(t), 'g' + gi + (parts ? '_' + parts : ''), 0); parts++; } catch (e) {}
    }
    out.gql.push({ i: gi, friendly: g.friendly || null, status: g.status, len: String(g.text || '').length, parts, posts: posts.length - before, t: g.t });
  });
  out.gql_raw = gql.map(g => ({ friendly: g.friendly || null, status: g.status, t: g.t, text: g.text }));
  out.posts = posts; out.page_infos = pageInfos;

  // profile data (only public business-relevant fields: username, follower_count, biography of the page owner)
  const profile = [];
  const walkP = (o, depth) => {
    if (!o || typeof o !== 'object' || depth > 70) return;
    if (Array.isArray(o)) { o.forEach(v => walkP(v, depth + 1)); return; }
    if (typeof o.username === 'string' && ('follower_count' in o)) {
      profile.push({ username: o.username, full_name: o.full_name || null, follower_count: o.follower_count, biography: o.biography || null,
                     bio_links: (o.bio_links || []).map(b => b.url), is_verified: !!o.is_verified, private: o.text_post_app_is_private === undefined ? null : o.text_post_app_is_private });
    }
    for (const k of Object.keys(o)) walkP(o[k], depth + 1);
  };
  if (/^\/@[^/]+\/?(replies|reposts|media)?\/?$/.test(location.pathname)) {
    scripts.forEach(s => { const t = s.textContent; if (t.includes('"follower_count"')) { try { walkP(JSON.parse(t), 0); } catch (e) {} } });
  }
  out.profile = profile;

  // rendered DOM items
  const relHdr = [...document.querySelectorAll('span, h2, div')].find(e => e.childElementCount === 0 && /^(Связанные ветки|Related threads)$/.test((e.textContent || '').trim()));
  const dom = [];
  for (const pc of document.querySelectorAll('div[data-pressable-container="true"]')) {
    const t = pc.querySelector('time[datetime]');
    const a = t ? t.closest('a') : null;
    const ua = pc.querySelector('a[href^="/@"]');
    const counts = {};
    pc.querySelectorAll('svg').forEach(s => {
      const ti = s.querySelector('title'); if (!ti) return;
      const holder = s.closest('[role=button]') || s.parentElement;
      const label = ti.textContent.trim();
      const val = holder ? (holder.innerText || '').trim() : '';
      if (/Нравится|Like/.test(label)) counts.likes = val;
      else if (/Комментировать|Reply|Ответить/.test(label)) counts.replies = val;
      else if (/репост|Repost/i.test(label)) counts.reposts = val;
      else if (/Поделиться|Share/.test(label)) counts.shares = val;
      else if (/Отредактировано|Edited/.test(label)) counts.edited = true;
    });
    dom.push({
      user: ua ? ua.getAttribute('href') : null,
      datetime: t ? t.getAttribute('datetime') : null,
      time_title: t ? (t.getAttribute('title') || t.textContent) : null,
      href: a ? a.getAttribute('href') : null,
      text: pc.innerText,
      counts,
      imgs: [...pc.querySelectorAll('img')].filter(i => !/^(Фото профиля|.*profile picture)/i.test(i.alt || '')).map(i => ({ src: i.currentSrc || i.src, alt: i.alt || null, w: i.naturalWidth, h: i.naturalHeight })),
      videos: [...pc.querySelectorAll('video')].map(v => ({ src: v.currentSrc || v.src, poster: v.poster || null, dur: isFinite(v.duration) ? v.duration : null })),
      links: [...pc.querySelectorAll('a[href]')].map(x => x.getAttribute('href')).filter(h => h && !h.startsWith('/@') ).slice(0, 20),
      related: relHdr ? !!(relHdr.compareDocumentPosition(pc) & Node.DOCUMENT_POSITION_FOLLOWING) : false,
    });
  }
  out.dom = dom;
  out.dom_count = dom.length;
  const bt = document.body.innerText;
  const vm = bt.match(/([\d\s .,]+(?:тыс\.|млн)?)\s*просмотр/);
  out.views_text = vm ? vm[0].trim() : null;
  out.login_wall = /Войдите, чтобы|Log in to see|Чтобы продолжить, войдите|Присоединяйтесь к Threads|Зарегистрируйтесь, чтобы/i.test(bt);
  out.not_found = /Страница недоступна|К сожалению, эта страница недоступна|Not all who wander are lost|Ссылка не работает|Публикация недоступна/i.test(bt);
  out.body_text = bt;
  out.scroll_height = document.documentElement.scrollHeight;
  out.viewport = [window.innerWidth, window.innerHeight];
  out.html = document.documentElement.outerHTML;
  return out;
}
