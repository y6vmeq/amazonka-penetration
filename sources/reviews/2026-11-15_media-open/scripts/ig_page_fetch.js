async () => {
  // Read-only, no login. Runs on the ordinary page https://www.instagram.com/reel/<code>/ or /p/<code>/ as it is
  // shown to a visitor who is not logged in. Used only when the embed player gives no file (the embed marks the reel
  // "copyright_blocked" or says the publication is unavailable). Finds the publication in the JSON data of the page,
  // GETs the media without cookies, returns base64 + SHA-256 computed in the page. No dialogs are clicked.
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const hex = buf => [...new Uint8Array(buf)].map(b => b.toString(16).padStart(2, '0')).join('');
  const b64 = buf => { const u = new Uint8Array(buf); let s = ''; const c = 0x8000; for (let i = 0; i < u.length; i += c) s += String.fromCharCode.apply(null, u.subarray(i, i + c)); return btoa(s); };
  await sleep(2000);
  const m = location.pathname.match(/\/(?:p|reel|reels)\/([^/]+)/);
  const code = m ? m[1] : '';
  const out = { platform: 'instagram', fetched_at: new Date().toISOString(), page: location.href, title: document.title,
    login_cookie: /sessionid|ds_user_id/.test(document.cookie), login_wall: /\/accounts\/login/.test(location.pathname), items: [] };
  let post = null;
  const walk = (o, depth) => {
    if (post || !o || typeof o !== 'object' || depth > 70) return;
    if (o.code === code && (o.video_versions !== undefined || o.image_versions2 !== undefined || o.carousel_media !== undefined)) { post = o; return; }
    if (Array.isArray(o)) { for (const x of o) walk(x, depth + 1); } else for (const k of Object.keys(o)) walk(o[k], depth + 1);
  };
  for (const s of document.querySelectorAll('script[type="application/json"]')) {
    const t = s.textContent || '';
    if (!code || !t.includes('"' + code + '"')) continue;
    try { walk(JSON.parse(t), 0); } catch (e) {}
    if (post) break;
  }
  const plan = [];
  let vi = 0, ii = 0;
  if (post) {
    out.meta = { source: 'page-json', code, pk: post.pk, owner: post.user && post.user.username, caption: post.caption ? post.caption.text : '',
      taken_at: post.taken_at || null, media_type: post.media_type, product_type: post.product_type || null,
      video_duration: post.video_duration == null ? null : post.video_duration, has_audio: post.has_audio == null ? null : post.has_audio,
      original_width: post.original_width, original_height: post.original_height,
      likes: post.like_count == null ? null : post.like_count, comments: post.comment_count == null ? null : post.comment_count,
      location: post.location ? post.location.name : null,
      tagged: post.usertags && post.usertags.in ? post.usertags.in.map(u => u.user && u.user.username) : null,
      carousel_count: post.carousel_media ? post.carousel_media.length : 0 };
    const nodes = post.carousel_media && post.carousel_media.length ? post.carousel_media : [post];
    for (const n of nodes) {
      if (n.video_versions && n.video_versions.length) {
        plan.push({ key: 'video' + (++vi), kind: 'video', url: n.video_versions[0].url, w: n.original_width, h: n.original_height, dur: n.video_duration == null ? null : n.video_duration });
      } else if (n.image_versions2 && n.image_versions2.candidates && n.image_versions2.candidates.length) {
        const c = n.image_versions2.candidates.slice().sort((a, b) => b.width - a.width)[0];
        plan.push({ key: 'img' + (++ii), kind: 'image', url: c.url, w: c.width, h: c.height });
      }
    }
  } else {
    out.error = 'publication data not found in page';
    out.meta = { source: 'dom', code, owner: null, text: document.body.innerText.slice(0, 800) };
  }
  for (const p of plan) {
    const rec = Object.assign({}, p);
    try {
      const r = await fetch(p.url, { credentials: 'omit' });
      rec.status = r.status; rec.type = r.headers.get('content-type');
      if (r.ok) { const buf = await r.arrayBuffer(); rec.bytes = buf.byteLength; rec.sha256 = hex(await crypto.subtle.digest('SHA-256', buf)); rec.b64 = b64(buf); }
    } catch (e) { rec.error = String(e); }
    out.items.push(rec);
    await sleep(600);
  }
  return JSON.parse(JSON.stringify(out)); // без undefined и NaN: иначе Playwright пишет файл не в JSON
}
