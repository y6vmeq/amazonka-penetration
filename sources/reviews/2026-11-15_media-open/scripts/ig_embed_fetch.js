async () => {
  // Read-only, no login. Runs on https://www.instagram.com/p/<code>/embed/captioned/ (public embed player).
  // Takes the media addresses from the data of the page itself (contextJSON -> shortcode_media, or the DOM as a
  // fallback), GETs every file without cookies, returns base64 + SHA-256 computed in the page.
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const hex = buf => [...new Uint8Array(buf)].map(b => b.toString(16).padStart(2, '0')).join('');
  const b64 = buf => { const u = new Uint8Array(buf); let s = ''; const c = 0x8000; for (let i = 0; i < u.length; i += c) s += String.fromCharCode.apply(null, u.subarray(i, i + c)); return btoa(s); };
  await sleep(1500);
  const out = { platform: 'instagram', fetched_at: new Date().toISOString(), page: location.href, title: document.title,
    login_cookie: /sessionid|ds_user_id/.test(document.cookie), items: [] };
  const plan = [];
  let sm = null;
  const t = [...document.scripts].map(s => s.textContent || '').find(x => x.includes('"contextJSON":"'));
  if (t) {
    try {
      const start = t.indexOf('"contextJSON":') + 14;
      let j = start + 1; while (j < t.length) { if (t[j] === '\\') { j += 2; continue; } if (t[j] === '"') break; j++; }
      const ctx = JSON.parse(JSON.parse(t.slice(start, j + 1)));
      out.context = ctx.context ? { type: ctx.context.type, shortcode: ctx.context.shortcode, copyright_blocked: ctx.context.copyright_blocked } : null;
      sm = ctx.gql_data && ctx.gql_data.shortcode_media;
    } catch (e) { out.parse_error = String(e); }
  }
  if (sm) {
    const cap = sm.edge_media_to_caption && sm.edge_media_to_caption.edges[0];
    out.meta = { source: 'contextJSON', code: sm.shortcode, id: sm.id, typename: sm.__typename, owner: sm.owner && sm.owner.username,
      caption: cap ? cap.node.text : '', taken_at: sm.taken_at_timestamp || null, video_duration: sm.video_duration || null,
      dimensions: sm.dimensions || null, product_type: sm.product_type || null, music: sm.clips_music_attribution_info || null,
      likes: sm.edge_liked_by ? sm.edge_liked_by.count : null, comments: sm.edge_media_to_comment ? sm.edge_media_to_comment.count : null,
      views: sm.video_view_count == null ? null : sm.video_view_count, location: sm.location ? sm.location.name : null,
      tagged: sm.edge_media_to_tagged_user ? sm.edge_media_to_tagged_user.edges.map(e => e.node.user && e.node.user.username) : null };
    const nodes = sm.edge_sidecar_to_children ? sm.edge_sidecar_to_children.edges.map(e => e.node) : [sm];
    let vi = 0, ii = 0;
    for (const n of nodes) {
      const d = n.dimensions || {};
      if (n.is_video && n.video_url) plan.push({ key: 'video' + (++vi), kind: 'video', url: n.video_url, w: d.width, h: d.height, dur: n.video_duration || null });
      else if (n.display_url) plan.push({ key: 'img' + (++ii), kind: 'image', url: n.display_url, w: d.width, h: d.height });
    }
  } else {
    // fallback: what the static embed shows
    const user = document.querySelector('.UsernameText');
    const capEl = document.querySelector('.Caption');
    out.meta = { source: 'dom', code: (location.pathname.split('/')[2] || ''), owner: user ? user.textContent.trim() : null,
      caption: capEl ? capEl.innerText : '', text: document.body.innerText.slice(0, 800) };
    let vi = 0, ii = 0;
    for (const v of document.querySelectorAll('video')) { const u = v.currentSrc || v.src; if (u && !u.startsWith('blob:')) plan.push({ key: 'video' + (++vi), kind: 'video', url: u }); }
    if (!vi) for (const im of document.querySelectorAll('img.EmbeddedMediaImage')) {
      let u = im.src;
      if (im.srcset) { const c = im.srcset.split(',').map(s => s.trim().split(/\s+/)).map(a => ({ u: a[0], w: parseInt(a[1] || '0', 10) })).sort((a, b) => b.w - a.w)[0]; if (c && c.u) u = c.u; }
      plan.push({ key: 'img' + (++ii), kind: 'image', url: u, w: im.naturalWidth, h: im.naturalHeight });
    }
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
