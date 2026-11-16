async () => {
  // Читает данные страницы видео TikTok (без входа) и возвращает метаданные и файлы в base64.
  const el = document.getElementById('__UNIVERSAL_DATA_FOR_REHYDRATION__');
  if (!el) return {error: 'no rehydration script', title: document.title, url: location.href};
  const data = JSON.parse(el.textContent);
  const scope = data.__DEFAULT_SCOPE__ || {};
  const detail = scope['webapp.video-detail'] || {};
  const item = detail.itemInfo && detail.itemInfo.itemStruct;
  if (!item) return {error: 'no itemStruct', statusCode: detail.statusCode, statusMsg: detail.statusMsg, url: location.href, title: document.title};
  const toHex = buf => Array.from(new Uint8Array(buf)).map(b => b.toString(16).padStart(2, '0')).join('');
  const toB64 = buf => { const bytes = new Uint8Array(buf); let s = ''; const chunk = 0x8000; for (let i = 0; i < bytes.length; i += chunk) s += String.fromCharCode.apply(null, bytes.subarray(i, i + chunk)); return btoa(s); };
  const grab = async (name, urls) => {
    const errors = [];
    for (const url of urls.filter(Boolean)) {
      for (const credentials of ['include', 'omit']) {
        try {
          const r = await fetch(url, {credentials});
          if (!r.ok) { errors.push(r.status + ' ' + url.slice(0, 90)); continue; }
          const buf = await r.arrayBuffer();
          if (!buf.byteLength) { errors.push('empty ' + url.slice(0, 90)); continue; }
          return {name, url, status: r.status, type: r.headers.get('content-type'), size: buf.byteLength, sha256: toHex(await crypto.subtle.digest('SHA-256', buf)), b64: toB64(buf)};
        } catch (e) { errors.push(String(e) + ' (' + credentials + ') ' + url.slice(0, 90)); }
      }
    }
    return {name, error: errors};
  };
  const v = item.video || {};
  const files = [];
  const variants = (v.bitrateInfo || []).map(b => ({gear: b.GearName, codec: b.CodecType, bitrate: b.Bitrate, w: b.PlayAddr && b.PlayAddr.Width, h: b.PlayAddr && b.PlayAddr.Height, size: b.PlayAddr && b.PlayAddr.DataSize, urls: (b.PlayAddr && b.PlayAddr.UrlList) || []}));
  const byQuality = (a, b) => (b.w || 0) - (a.w || 0) || (b.bitrate || 0) - (a.bitrate || 0);
  const h264 = variants.filter(x => (x.codec || '').startsWith('h264')).sort(byQuality)[0];
  const best = variants.slice().sort(byQuality)[0];
  if (!item.imagePost) {
    if (h264) files.push(await grab('video_' + Math.min(h264.w, h264.h) + 'p_h264', h264.urls));
    else if (v.playAddr) files.push(await grab('video_play_' + (v.codecType || 'x'), [v.playAddr, v.downloadAddr]));
    if (best && best !== h264) files.push(await grab('video_' + Math.min(best.w, best.h) + 'p_' + (best.codec || 'x').split('_')[0], best.urls));
  } else {
    let n = 0;
    for (const img of (item.imagePost.images || [])) { n += 1; files.push(await grab('image_' + String(n).padStart(2, '0'), (img.imageURL && img.imageURL.urlList) || [])); }
    if (item.music && item.music.playUrl) files.push(await grab('music', [item.music.playUrl]));
  }
  const subs = v.subtitleInfos || [];
  for (const s of subs) {
    if (s.Source === 'ASR' || subs.length <= 2) files.push(await grab('tiktok_subtitles_' + (s.Source || 'x').toLowerCase() + '_' + s.LanguageCodeName, [s.Url]));
  }
  files.push(await grab('cover', [v.originCover, v.cover, v.dynamicCover]));
  const meta = {
    page_url: location.href, captured_at: new Date().toISOString(),
    id: item.id, desc: item.desc, createTime: item.createTime, createTimeISO: new Date(Number(item.createTime) * 1000).toISOString(),
    author: item.author && {uniqueId: item.author.uniqueId, nickname: item.author.nickname},
    stats: item.stats, statsV2: item.statsV2,
    music: item.music && {id: item.music.id, title: item.music.title, authorName: item.music.authorName, original: item.music.original, duration: item.music.duration},
    challenges: (item.challenges || []).map(c => c.title),
    textExtra: (item.textExtra || []).map(t => ({hashtag: t.hashtagName || null, user: t.userUniqueId || null})).filter(t => t.hashtag || t.user),
    contents: (item.contents || []).map(c => c.desc),
    stickersOnItem: item.stickersOnItem || null,
    locationCreated: item.locationCreated, textLanguage: item.textLanguage,
    isAd: item.isAd, adAuthorization: item.adAuthorization, adLabelVersion: item.adLabelVersion, brandOrganicType: item.brandOrganicType, isECVideo: item.isECVideo,
    poi: item.poi || null, anchors: item.anchors || null, itemCommentStatus: item.itemCommentStatus, AIGCDescription: item.AIGCDescription, IsAigc: item.IsAigc,
    imagePostCount: item.imagePost ? (item.imagePost.images || []).length : 0,
    video: {duration: v.duration, width: v.width, height: v.height, ratio: v.ratio, format: v.format, codecType: v.codecType, definition: v.definition, size: v.size,
      variants: variants.map(x => ({gear: x.gear, codec: x.codec, bitrate: x.bitrate, w: x.w, h: x.h, size: x.size})),
      subtitles: subs.map(s => ({lang: s.LanguageCodeName, format: s.Format, source: s.Source, size: s.Size}))}
  };
  return {meta, files};
}
