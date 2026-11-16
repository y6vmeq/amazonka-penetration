() => {
  // Read-only: GET Instagram pages (posts, reels, profiles, embeds) from the page context, logged-out,
  // and parse the data embedded in the returned HTML. Config: window.__igcfg = {urls: [...], delayMs}.
  // Runs in background; state in window.__ig. Stops on a login redirect streak or HTTP 429/403.
  const cfg = window.__igcfg || {};
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const st = window.__ig = window.__ig || { pages: [], log: [], done: {} };
  const delayMs = cfg.delayMs || 5000;
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
  const extract = html => {
    const doc = new DOMParser().parseFromString(html, 'text/html');
    const medias = [], comments = [], profiles = [], pageInfos = [];
    const seenM = new Set(), seenC = new Set();
    const walk = (o, path, depth) => {
      if (!o || typeof o !== 'object' || depth > 70) return;
      if (Array.isArray(o)) { for (let i = 0; i < o.length; i++) walk(o[i], path + '[' + i + ']', depth + 1); return; }
      if (o.page_info && typeof o.page_info === 'object' && 'has_next_page' in o.page_info && /comment|timeline/i.test(path)) pageInfos.push({ path: path.slice(-90), has_next_page: o.page_info.has_next_page, edges: Array.isArray(o.edges) ? o.edges.length : null });
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
          audio: o.seo_original_audio ? JSON.stringify(o.seo_original_audio).slice(0, 300) : null,
          ai_label: o.ai_label_info ? JSON.stringify(o.ai_label_info).slice(0, 200) : null,
          duration: o.video_duration === undefined ? null : o.video_duration, has_audio: o.has_audio === undefined ? null : o.has_audio,
          carousel_count: o.carousel_media_count === undefined ? (o.carousel_media ? o.carousel_media.length : null) : o.carousel_media_count,
          media: mediaOf(o), alt: o.accessibility_caption || null, path: path.slice(-110),
        });
      }
      if (typeof o.text === 'string' && o.user && typeof o.user.username === 'string' && ('created_at' in o) && o.pk && !seenC.has(o.pk)) {
        seenC.add(o.pk);
        comments.push({ pk: o.pk, user: o.user.username, created_at: o.created_at, iso: o.created_at ? new Date(o.created_at * 1000).toISOString() : null,
                        text: o.text, likes: o.comment_like_count === undefined ? null : o.comment_like_count, children: o.child_comment_count === undefined ? null : o.child_comment_count,
                        parent: o.parent_comment_id || null });
      }
      if (typeof o.username === 'string' && ('follower_count' in o || 'edge_followed_by' in o || 'biography' in o)) {
        profiles.push({ username: o.username, full_name: o.full_name || null, biography: o.biography === undefined ? null : o.biography,
                        followers: o.follower_count === undefined ? (o.edge_followed_by ? o.edge_followed_by.count : null) : o.follower_count,
                        following: o.following_count === undefined ? null : o.following_count, media_count: o.media_count === undefined ? null : o.media_count,
                        category: o.category || o.category_name || null, external_url: o.external_url || null, bio_links: (o.bio_links || []).map(b => b.url),
                        address: o.address_street || null, phone: o.public_phone_number || o.contact_phone_number || null,
                        business: o.is_business === undefined ? null : o.is_business, private: o.is_private === undefined ? null : o.is_private });
      }
      for (const k of Object.keys(o)) walk(o[k], path + '.' + k, depth + 1);
    };
    const scripts = [...doc.querySelectorAll('script[type="application/json"]')];
    scripts.forEach((s, i) => { const t = s.textContent; if (t.includes('"code"') || t.includes('"username"')) { try { walk(JSON.parse(t), 's' + i, 0); } catch (e) {} } });
    const metas = {};
    for (const m of doc.querySelectorAll('meta[property], meta[name]')) {
      const k = m.getAttribute('property') || m.getAttribute('name');
      if (/^(og:|description|twitter:title|twitter:description)/.test(k)) metas[k] = m.getAttribute('content');
    }
    // embed pages: caption and media are plain markup
    const embed = {};
    const cap = doc.querySelector('.Caption'); if (cap) embed.caption_text = cap.innerText || cap.textContent;
    embed.imgs = [...doc.querySelectorAll('img.EmbeddedMediaImage')].map(i => i.getAttribute('src'));
    const vm = html.match(/"video_url":"([^"]+)"/) || html.match(/\\"video_url\\":\\"([^"\\]+(?:\\\\[^"\\]+)*)\\"/);
    embed.video_url_raw = vm ? vm[1].slice(0, 2000) : null;
    return { medias, comments, profiles, pageInfos, metas, embed, title: doc.title, links_posts: [...new Set([...doc.querySelectorAll('a[href]')].map(a => a.getAttribute('href')).filter(h => /\/(p|reel)\/[A-Za-z0-9_-]+/.test(h || '')))] };
  };
  st.running = true; st.stopReason = null;
  (async () => {
    let loginStreak = 0;
    for (const url of (cfg.urls || [])) {
      if (st.done[url]) continue;
      const fetched_at = new Date().toISOString();
      let status = null, finalUrl = null, html = null, err = null;
      try {
        const r = await fetch(url, { credentials: 'include', headers: { 'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8' } });
        status = r.status; finalUrl = r.url; html = await r.text();
      } catch (e) { err = String(e); }
      st.done[url] = true;
      const login = /\/accounts\/login/.test(finalUrl || '');
      if (err || status !== 200 || !html) {
        st.log.push([url.replace('https://www.instagram.com', ''), status, err || ''].join(' '));
        st.pages.push({ url, finalUrl, status, fetched_at, error: err, medias: [], comments: [], profiles: [], html: html || '', login });
        if (status === 429 || status === 403 || status === 401) { st.stopReason = 'http ' + status; break; }
        await sleep(delayMs); continue;
      }
      const ex = extract(html);
      loginStreak = login ? loginStreak + 1 : 0;
      st.pages.push({ url, finalUrl, status, fetched_at, login, title: ex.title, medias: ex.medias, comments: ex.comments, profiles: ex.profiles, page_infos: ex.pageInfos, metas: ex.metas, embed: ex.embed, links_posts: ex.links_posts, html, retrieved: false });
      const code = (url.match(/\/(?:p|reel)\/([A-Za-z0-9_-]+)/) || [])[1];
      const main = ex.medias.filter(m => m.code === code).sort((a, b) => (b.media || []).length - (a.media || []).length)[0];
      st.log.push([url.replace('https://www.instagram.com', ''), status, 'len=' + html.length, login ? 'LOGIN' : '', 'medias=' + ex.medias.length, 'comments=' + ex.comments.length,
                   main ? ('by=' + main.user + ' ' + (main.iso || '').slice(0, 10) + ' kinds=' + (main.media || []).map(m => m.kind[0]).join('') + ' cc=' + main.comment_count) : 'nomain'].join(' '));
      if (loginStreak >= 3) { st.stopReason = 'login wall'; break; }
      await sleep(delayMs + Math.floor(Math.random() * 1500));
    }
    st.running = false;
  })().catch(e => { st.running = false; st.stopReason = 'error ' + String(e); });
  return { started: true, urls: (cfg.urls || []).length };
}
