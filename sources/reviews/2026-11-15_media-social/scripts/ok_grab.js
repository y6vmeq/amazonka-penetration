async () => {
  // Страница видео Одноклассников (без входа): берёт адрес файла из данных плеера и возвращает его в base64.
  // Желаемые качества по порядку — window.__okWant (по умолчанию hd, sd, low).
  const el = document.querySelector('[data-module="OKVideo"]');
  if (!el) return {error: 'no OKVideo element', title: document.title, url: location.href};
  const opts = JSON.parse(el.getAttribute('data-options'));
  let md = (opts.flashvars || {}).metadata;
  if (typeof md === 'string') md = JSON.parse(md);
  if (!md || !md.videos) return {error: 'no metadata', url: location.href};
  const toHex = buf => Array.from(new Uint8Array(buf)).map(b => b.toString(16).padStart(2, '0')).join('');
  const toB64 = buf => { const bytes = new Uint8Array(buf); let s = ''; const chunk = 0x8000; for (let i = 0; i < bytes.length; i += chunk) s += String.fromCharCode.apply(null, bytes.subarray(i, i + chunk)); return btoa(s); };
  const grab = async (name, url) => {
    const errors = [];
    for (const credentials of ['omit', 'include']) {
      try {
        const r = await fetch(url, {credentials});
        if (!r.ok) { errors.push(r.status + ' (' + credentials + ')'); continue; }
        const buf = await r.arrayBuffer();
        if (!buf.byteLength) { errors.push('empty'); continue; }
        return {name, url, status: r.status, type: r.headers.get('content-type'), size: buf.byteLength, sha256: toHex(await crypto.subtle.digest('SHA-256', buf)), b64: toB64(buf)};
      } catch (e) { errors.push(String(e) + ' (' + credentials + ')'); }
    }
    return {name, error: errors};
  };
  const want = window.__okWant || ['hd', 'sd', 'low'];
  const available = md.videos.map(v => v.name);
  const files = [];
  for (const q of want) {
    const v = md.videos.find(x => x.name === q);
    if (!v) continue;
    const f = await grab('video_' + q, v.url);
    files.push(f);
    if (f.b64) break;
  }
  if (md.movie && md.movie.poster) files.push(await grab('poster', md.movie.poster));
  const metaTag = name => { const m = document.querySelector('meta[property="' + name + '"], meta[name="' + name + '"]'); return m ? m.content : null; };
  const info = document.querySelector('.vp-layer-info_cnt, .vp-layer-info');
  const meta = {
    page_url: location.href, captured_at: new Date().toISOString(), title: document.title,
    movie: md.movie && {id: md.movie.id, title: md.movie.title, duration: md.movie.duration, contentId: md.movie.contentId, status: md.movie.status},
    provider: md.provider, available_qualities: available,
    og: {title: metaTag('og:title'), description: metaTag('og:description'), duration: metaTag('video:duration'), upload_date: metaTag('video:release_date') || metaTag('ya:ovs:upload_date'), views_total: metaTag('ya:ovs:views_total')},
    info_text: info ? info.innerText.slice(0, 800) : null
  };
  return {meta, files};
}
