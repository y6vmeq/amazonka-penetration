async () => {
  // Read-only extraction of an Instagram page (post, reel or profile), logged-out view.
  // Clicks only "load more comments" / "view replies" controls (they just load more of the same public page).
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const out = { url: location.href, fetched_at: new Date().toISOString(), title: document.title };

  // --- expand comments while the control exists and no login wall replaces the page ---
  const clickLog = [];
  const moreSel = () => {
    const svgs = [...document.querySelectorAll('svg[aria-label]')].filter(s => /Загрузить ещё комментарии|Load more comments/i.test(s.getAttribute('aria-label')));
    return svgs.map(s => s.closest('button,[role=button]')).filter(Boolean);
  };
  for (let i = 0; i < 25; i++) {
    const btns = moreSel();
    if (!btns.length) break;
    const before = document.querySelectorAll('time[datetime]').length;
    btns[0].click();
    await sleep(1800);
    const after = document.querySelectorAll('time[datetime]').length;
    clickLog.push('more:' + before + '->' + after);
    if (after === before) break;
  }
  for (let round = 0; round < 3; round++) {
    const replyBtns = [...document.querySelectorAll('button,[role=button],span')].filter(b => b.childElementCount === 0 && /^(Смотреть ответы|Посмотреть ответы|View replies)\s*\(?\d*\)?$/i.test((b.innerText || '').trim()));
    if (!replyBtns.length) break;
    for (const b of replyBtns.slice(0, 40)) { b.click(); await sleep(700); }
    clickLog.push('replies:' + replyBtns.length);
    await sleep(1200);
  }
  out.click_log = clickLog;

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
      const img = best(x.image_versions2 && x.image_versions2.candidates) || (x.display_uri ? { url: x.display_uri } : null);
      if (x.video_versions && x.video_versions.length) m.push({ kind: 'video', idx, url: x.video_versions[0].url, poster: img ? img.url : null, w: x.original_width || null, h: x.original_height || null, alt: x.accessibility_caption || null });
      else if (img) m.push({ kind: 'image', idx, url: img.url, w: img.width || x.original_width || null, h: img.height || x.original_height || null, alt: x.accessibility_caption || null, is_video_poster: x.media_type === 2 });
    };
    if (o.carousel_media && o.carousel_media.length) o.carousel_media.forEach((x, i) => one(x, i + 1)); else one(o, 1);
    return m;
  };
  const medias = []; const comments = []; const pageInfos = []; const profiles = [];
  const seenM = new Set(), seenC = new Set();
  const walk = (o, path, depth) => {
    if (!o || typeof o !== 'object' || depth > 70) return;
    if (Array.isArray(o)) { for (let i = 0; i < o.length; i++) walk(o[i], path + '[' + i + ']', depth + 1); return; }
    if (o.page_info && typeof o.page_info === 'object' && 'has_next_page' in o.page_info) pageInfos.push({ path: path.slice(-90), has_next_page: o.page_info.has_next_page, edges: Array.isArray(o.edges) ? o.edges.length : null });
    if (typeof o.code === 'string' && (o.taken_at !== undefined || o.caption !== undefined || o.display_uri !== undefined) && !seenM.has(o.code + '|' + (o.taken_at !== undefined))) {
      seenM.add(o.code + '|' + (o.taken_at !== undefined));
      medias.push({
        code: o.code, pk: o.pk || null, user: o.user ? (o.user.username || null) : null,
        taken_at: o.taken_at === undefined ? null : o.taken_at, iso: o.taken_at ? new Date(o.taken_at * 1000).toISOString() : null,
        caption: o.caption ? (o.caption.text === undefined ? null : o.caption.text) : null, caption_edited: o.caption_is_edited === undefined ? null : o.caption_is_edited,
        like_count: o.like_count === undefined ? null : o.like_count, comment_count: o.comment_count === undefined ? null : o.comment_count,
        view_count: o.view_count === undefined ? (o.play_count === undefined ? null : o.play_count) : o.view_count,
        likes_hidden: o.like_and_view_counts_disabled === undefined ? null : o.like_and_view_counts_disabled,
        media_type: o.media_type === undefined ? null : o.media_type, product_type: o.product_type || null,
        coauthors: (o.coauthor_producers || []).map(u => u.username), location: o.location ? (o.location.name || null) : null,
        usertags: o.usertags && o.usertags.in ? o.usertags.in.map(u => u.user && u.user.username).filter(Boolean) : [],
        audio: o.seo_original_audio ? JSON.stringify(o.seo_original_audio).slice(0, 300) : (o.clips_metadata ? JSON.stringify(o.clips_metadata).slice(0, 300) : null),
        ai_label: o.ai_label_info ? JSON.stringify(o.ai_label_info).slice(0, 200) : null,
        duration: o.video_duration === undefined ? null : o.video_duration, has_audio: o.has_audio === undefined ? null : o.has_audio,
          carousel_count: o.carousel_media_count === undefined ? (o.carousel_media ? o.carousel_media.length : null) : o.carousel_media_count,
        media: mediaOf(o), alt: o.accessibility_caption || null,
        is_main: /if_not_gated_logged_out$/.test(path) || /xig_polaris_media$/.test(path), path: path.slice(-110),
      });
    }
    if (typeof o.text === 'string' && o.user && typeof o.user.username === 'string' && ('created_at' in o) && o.pk && !seenC.has(o.pk)) {
      seenC.add(o.pk);
      comments.push({ pk: o.pk, user: o.user.username, created_at: o.created_at, iso: o.created_at ? new Date(o.created_at * 1000).toISOString() : null,
                      text: o.text, likes: o.comment_like_count === undefined ? null : o.comment_like_count, children: o.child_comment_count === undefined ? null : o.child_comment_count,
                      parent: o.parent_comment_id || null, path: path.slice(-80) });
    }
    if (typeof o.username === 'string' && ('follower_count' in o || 'edge_followed_by' in o || 'biography' in o)) {
      profiles.push({ username: o.username, full_name: o.full_name || null, biography: o.biography === undefined ? null : o.biography,
                      followers: o.follower_count === undefined ? (o.edge_followed_by ? o.edge_followed_by.count : null) : o.follower_count,
                      following: o.following_count === undefined ? null : o.following_count, media_count: o.media_count === undefined ? null : o.media_count,
                      category: o.category || o.category_name || null, external_url: o.external_url || null,
                      bio_links: (o.bio_links || []).map(b => b.url), address: o.address_street || null, phone: o.public_phone_number || o.contact_phone_number || null,
                      business: o.is_business === undefined ? null : o.is_business, private: o.is_private === undefined ? null : o.is_private });
    }
    for (const k of Object.keys(o)) walk(o[k], path + '.' + k, depth + 1);
  };
  const scripts = [...document.querySelectorAll('script[type="application/json"]')];
  scripts.forEach((s, i) => { const t = s.textContent; if (t.includes('"code"') || t.includes('"username"')) { try { walk(JSON.parse(t), 's' + i, 0); } catch (e) {} } });
  const gql = window.__gql || [];
  out.gql = [];
  gql.forEach((g, gi) => {
    const bm = medias.length, bc = comments.length;
    for (const line of String(g.text || '').split(String.fromCharCode(10))) {
      const t = line.trim(); if (!t || t[0] !== '{') continue;
      try { walk(JSON.parse(t), 'g' + gi, 0); } catch (e) {}
    }
    out.gql.push({ i: gi, friendly: g.friendly || null, status: g.status, len: String(g.text || '').length, medias: medias.length - bm, comments: comments.length - bc });
  });
  out.gql_raw = gql.filter(g => /comment|Comment|media|Media|profile|Profile|timeline|Timeline/.test(String(g.friendly || '')) || String(g.text || '').includes('"created_at"') || String(g.text || '').includes('"taken_at"')).map(g => ({ friendly: g.friendly || null, status: g.status, t: g.t, text: g.text }));
  out.medias = medias; out.comments = comments; out.page_infos = pageInfos.filter(p => /comment/i.test(p.path) || /timeline/i.test(p.path));
  out.profiles = profiles;

  // rendered DOM
  out.metas = {};
  for (const m of document.querySelectorAll('meta[property], meta[name]')) {
    const k = m.getAttribute('property') || m.getAttribute('name');
    if (/^(og:|description|twitter:title|twitter:description)/.test(k)) out.metas[k] = m.getAttribute('content');
  }
  out.times = [...document.querySelectorAll('time[datetime]')].map(t => ({ dt: t.getAttribute('datetime'), title: t.getAttribute('title'), text: t.textContent }));
  out.links_posts = [...new Set([...document.querySelectorAll('a[href]')].map(a => a.getAttribute('href')).filter(h => /^\/(?:[^/]+\/)?(p|reel)\/[A-Za-z0-9_-]+\/?/.test(h)))];
  out.videos = [...document.querySelectorAll('video')].map(v => ({ src: v.currentSrc || v.src, poster: v.poster || null, dur: isFinite(v.duration) ? v.duration : null }));
  out.imgs = [...document.querySelectorAll('img')].map(i => ({ src: i.currentSrc || i.src, alt: i.alt || null, w: i.naturalWidth, h: i.naturalHeight })).filter(i => i.w >= 300);
  const bt = document.body.innerText;
  out.body_text = bt;
  out.login_wall = /\/accounts\/login/.test(location.pathname);
  out.more_comments_left = moreSel().length;
  out.scroll_height = document.documentElement.scrollHeight;
  out.html = document.documentElement.outerHTML;
  return out;
}
