async () => {
  // Read-only: GET the media files listed in window.__mcfg.items ([{key, url}]) and return them as base64
  // together with SHA-256 computed in the page. Nothing else is requested.
  const items = (window.__mbatches && window.__mbatches[window.__mb++]) || [];
  const out = { fetched_at: new Date().toISOString(), page: location.href, items: [] };
  const hex = buf => [...new Uint8Array(buf)].map(b => b.toString(16).padStart(2, '0')).join('');
  const b64 = buf => {
    const bytes = new Uint8Array(buf); let s = ''; const chunk = 0x8000;
    for (let i = 0; i < bytes.length; i += chunk) s += String.fromCharCode.apply(null, bytes.subarray(i, i + chunk));
    return btoa(s);
  };
  for (const it of items) {
    const rec = { key: it.key, url: it.url };
    try {
      const r = await fetch(it.url, { credentials: 'omit' });
      rec.status = r.status; rec.type = r.headers.get('content-type');
      if (r.ok) {
        const buf = await r.arrayBuffer();
        rec.bytes = buf.byteLength;
        rec.sha256 = hex(await crypto.subtle.digest('SHA-256', buf));
        rec.b64 = b64(buf);
      }
    } catch (e) { rec.error = String(e); }
    out.items.push(rec);
    await new Promise(r => setTimeout(r, 400));
  }
  return out;
}
