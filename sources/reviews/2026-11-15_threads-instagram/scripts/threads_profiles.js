async () => {
  // Read-only scan of Threads profile pages (logged-out): /@user and /@user/replies.
  // Config: window.__pcfg = {users: [...], tabs: ['', '/replies'], delayMs}. Results kept in window.__prof.
  const cfg = window.__pcfg || {};
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const st = window.__prof = window.__prof || { results: {}, log: [], running: false };
  const tabs = cfg.tabs || ['', '/replies'];
  const delayMs = cfg.delayMs || 2500;
  const mediaKinds = o => {
    const k = [];
    const one = x => { if (!x) return; if (x.video_versions && x.video_versions.length) k.push('video'); else if (x.image_versions2 && x.image_versions2.candidates && x.image_versions2.candidates.length) k.push('image'); };
    if (o.carousel_media && o.carousel_media.length) o.carousel_media.forEach(one); else one(o);
    return k;
  };
  const extract = html => {
    const doc = new DOMParser().parseFromString(html, 'text/html');
    const posts = []; const profile = [];
    const walk = (o, path, depth) => {
      if (!o || typeof o !== 'object' || depth > 70) return;
      if (Array.isArray(o)) { for (let i = 0; i < o.length; i++) walk(o[i], path + '[' + i + ']', depth + 1); return; }
      if (typeof o.username === 'string' && ('follower_count' in o)) {
        profile.push({ username: o.username, full_name: o.full_name || null, follower_count: o.follower_count, biography: o.biography || null,
                       bio_links: (o.bio_links || []).map(b => b.url), private: o.text_post_app_is_private === undefined ? null : o.text_post_app_is_private });
      }
      if (typeof o.code === 'string' && o.user && typeof o.user.username === 'string' && ('taken_at' in o)) {
        const tpa = o.text_post_app_info || {};
        const si = tpa.share_info || {};
        let m = path.match(/edges\[(\d+)\]\.node\.thread_items\[(\d+)\]\.post$/);
        posts.push({
          code: o.code, user: o.user.username, iso: o.taken_at ? new Date(o.taken_at * 1000).toISOString() : null,
          text: o.caption ? o.caption.text : null, permalink: o.permalink || null,
          drc: tpa.direct_reply_count === undefined ? null : tpa.direct_reply_count, likes: o.like_count === undefined ? null : o.like_count,
          is_reply: tpa.is_reply === undefined ? null : tpa.is_reply, reply_to: tpa.reply_to_author ? tpa.reply_to_author.username : null,
          root_author: tpa.root_post_author ? tpa.root_post_author.username : null,
          quoted: si.quoted_post ? { code: si.quoted_post.code, user: si.quoted_post.user ? si.quoted_post.user.username : null } : null,
          reposted: si.reposted_post ? { code: si.reposted_post.code, user: si.reposted_post.user ? si.reposted_post.user.username : null } : null,
          media: mediaKinds(o), chain: m ? +m[1] : null, pos: m ? +m[2] : null,
          kind: /quoted_post$/.test(path) ? 'quoted' : /reposted_post$/.test(path) ? 'reposted' : (m ? 'item' : 'other'),
        });
      }
      for (const k of Object.keys(o)) walk(o[k], path + '.' + k, depth + 1);
    };
    const scripts = [...doc.querySelectorAll('script[type="application/json"]')];
    scripts.forEach((s, i) => { const t = s.textContent; if (t.includes('"taken_at"') || t.includes('"follower_count"')) { try { walk(JSON.parse(t), 's' + i, 0); } catch (e) {} } });
    return { posts, profile, title: doc.title };
  };
  st.running = true; st.stopReason = null;
  const run = async () => {
    for (const u of (cfg.users || [])) {
      for (const tab of tabs) {
        const key = u + tab;
        if (st.results[key]) continue;
        const url = 'https://www.threads.com/@' + u + tab;
        const fetched_at = new Date().toISOString();
        let status = null, finalUrl = null, html = null, err = null;
        try {
          const r = await fetch(url, { credentials: 'include', headers: { 'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8' } });
          status = r.status; finalUrl = r.url; html = await r.text();
        } catch (e) { err = String(e); }
        if (err || status !== 200 || !html) {
          st.results[key] = { url, fetched_at, status, err, posts: [], profile: [] };
          st.log.push(key + ' ' + status + ' ' + (err || ''));
          if (status === 429 || status === 403) { st.stopReason = 'http ' + status; st.running = false; return; }
          await sleep(delayMs); continue;
        }
        const ex = extract(html);
        const own = ex.profile.find(p => p.username === u) || null;
        st.results[key] = { url, finalUrl, fetched_at, status, len: html.length, title: ex.title, posts: ex.posts, own, html: cfg.keepHtml && cfg.keepHtml.includes(u) ? html : null,
                            notFound: !own && !ex.posts.length };
        st.log.push(key + ' ' + status + ' posts=' + ex.posts.length + ' own=' + (own ? own.follower_count : 'none') + (finalUrl !== url ? ' -> ' + finalUrl : ''));
        await sleep(delayMs + Math.floor(Math.random() * 600));
      }
    }
    st.running = false;
  };
  run().catch(e => { st.running = false; st.stopReason = 'error ' + String(e); });
  return { started: true, users: (cfg.users || []).length };
}
