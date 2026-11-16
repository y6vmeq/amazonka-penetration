async () => {
  // Read-only, no login. Runs on https://www.threads.com/@<user>/post/<code>.
  // Finds the post in the JSON data that the page itself carries, takes the media addresses from it,
  // GETs every file without cookies, returns base64 + SHA-256 computed in the page.
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const hex = buf => [...new Uint8Array(buf)].map(b => b.toString(16).padStart(2, '0')).join('');
  const b64 = buf => { const u = new Uint8Array(buf); let s = ''; const c = 0x8000; for (let i = 0; i < u.length; i += c) s += String.fromCharCode.apply(null, u.subarray(i, i + c)); return btoa(s); };
  await sleep(1500);
  const code = ((location.pathname.split('/post/')[1] || '').split('/')[0]) || '';
  const out = { platform: 'threads', fetched_at: new Date().toISOString(), page: location.href, title: document.title,
    login_cookie: /sessionid|ds_user_id/.test(document.cookie), login_button: /Войти|Log in/.test(document.body.innerText.slice(0, 2000)), items: [] };
  let post = null;
  const walk = (o, depth) => {
    if (post || !o || typeof o !== 'object' || depth > 45) return;
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
    const info = post.text_post_app_info || {};
    out.meta = { source: 'page-json', code, pk: post.pk, owner: post.user && post.user.username, caption: post.caption ? post.caption.text : '',
      taken_at: post.taken_at || null, media_type: post.media_type, original_width: post.original_width, original_height: post.original_height,
      has_audio: post.has_audio == null ? null : post.has_audio, permalink: post.permalink || post.canonical_url || null,
      like_count: post.like_count == null ? null : post.like_count, reply_count: info.direct_reply_count == null ? null : info.direct_reply_count,
      carousel_count: post.carousel_media ? post.carousel_media.length : 0 };
    const nodes = post.carousel_media && post.carousel_media.length ? post.carousel_media : [post];
    for (const n of nodes) {
      if (n.video_versions && n.video_versions.length) {
        plan.push({ key: 'video' + (++vi), kind: 'video', url: n.video_versions[0].url, w: n.original_width, h: n.original_height, has_audio: n.has_audio == null ? null : n.has_audio });
      } else if (n.image_versions2 && n.image_versions2.candidates && n.image_versions2.candidates.length) {
        const c = n.image_versions2.candidates.slice().sort((a, b) => b.width - a.width)[0];
        plan.push({ key: 'img' + (++ii), kind: 'image', url: c.url, w: c.width, h: c.height, ow: n.original_width, oh: n.original_height });
      }
    }
  } else {
    out.error = 'post data not found in page';
    out.meta = { source: 'dom', code, owner: (location.pathname.match(/@([^/]+)/) || [])[1] || null, text: document.body.innerText.slice(0, 800) };
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
