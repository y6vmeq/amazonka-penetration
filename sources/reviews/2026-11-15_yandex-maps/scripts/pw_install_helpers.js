// Вспомогательные функции для выгрузки отзывов с карточки организации на Яндекс Картах.
// Запускается через Playwright MCP: browser_run_code_unsafe с параметром filename (этот файл).
// Только чтение страницы: прокрутка списка, раскрытие текстов и ответов, чтение DOM.
// Никаких входов, отправки форм, отметок «нравится» и т. п.
async (page) => {
  // Даты на странице браузер показывает в своём часовом поясе. Ставим минский (UTC+3),
  // чтобы дата на странице и на скриншотах совпадала с тем, что видит читатель в Беларуси.
  const client = await page.context().newCDPSession(page);
  await client.send('Emulation.setTimezoneOverride', { timezoneId: 'Europe/Minsk' }).catch(() => {});

  const install = () => {
    const SHARE = (orgId, pubId) => `https://yandex.by/maps/org/${orgId}/reviews?reviews%5BpublicId%5D=${pubId}&utm_source=review`;
    const getModel = (el) => {
      const fk = Object.keys(el).find((k) => k.startsWith('__reactFiber'));
      let f = fk ? el[fk] : null;
      let d = 0;
      while (f && d < 20) {
        const p = f.memoizedProps;
        if (p && p.review && p.review.reviewId) return p.review;
        f = f.return;
        d++;
      }
      return null;
    };
    const txt = (el) => (el ? el.textContent : null);
    const meta = (root, n) => {
      const m = root && root.querySelector(`meta[itemprop="${n}"]`);
      return m ? m.getAttribute('content') : null;
    };
    const sha = async (s) => {
      const buf = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(s));
      return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, '0')).join('');
    };
    const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
    const cardsNow = () => document.querySelectorAll('.business-review-view').length;

    // Догружает список отзывов прокруткой контейнера, пока число карточек растёт.
    const loadAll = async (maxMs = 22000) => {
      const sc = document.querySelector('.scroll__container');
      const t0 = Date.now();
      let last = cardsNow();
      let stable = 0;
      const log = [];
      while (Date.now() - t0 < maxMs) {
        sc.scrollTop = sc.scrollHeight;
        await sleep(700);
        const n = cardsNow();
        if (n !== last) { log.push([Date.now() - t0, n]); last = n; stable = 0; } else { stable++; if (stable >= 8) break; }
      }
      const li = document.querySelector('.business-reviews-card-view__review');
      return { cards: last, setsize: li ? li.getAttribute('aria-setsize') : null, header: txt(document.querySelector('.business-reviews-card-view__title h2')), log, stable };
    };

    // Раскрывает полные тексты («Ещё») и ответы организации («Посмотреть ответ организации»).
    const expandAll = async (maxMs = 22000) => {
      const t0 = Date.now();
      let ct = 0;
      let cr = 0;
      for (const b of [...document.querySelectorAll('.business-review-view__expand')]) { b.click(); ct++; if (ct % 20 === 0) await sleep(50); }
      await sleep(400);
      for (const b of [...document.querySelectorAll('.business-review-comment-expandable-view__expand[aria-expanded="false"]')]) {
        if (Date.now() - t0 > maxMs) break;
        b.click(); cr++; await sleep(120);
      }
      await sleep(800);
      return {
        clickedText: ct,
        clickedReply: cr,
        remainingTextButtons: document.querySelectorAll('.business-review-view__expand').length,
        collapsedTexts: document.querySelectorAll('.spoiler-view__text._collapsed').length,
        replyContainers: document.querySelectorAll('.business-review-view__business-comment').length,
        replyNotExpanded: document.querySelectorAll('.business-review-comment-expandable-view__expand[aria-expanded="false"]').length,
        replyBubbles: document.querySelectorAll('.business-review-comment-content__bubble').length,
      };
    };

    const extract = () => {
      const cards = [...document.querySelectorAll('.business-review-view')];
      const orgEl = document.querySelector('.business-card-view');
      const orgId = orgEl ? orgEl.dataset.id : null;
      const agg = document.querySelector('[itemprop="aggregateRating"]');
      const reviews = cards.map((c, i) => {
        const m = getModel(c) || {};
        const a = c.querySelector('a.business-review-view__link');
        const li = c.closest('.business-reviews-card-view__review');
        const bc = c.querySelector('.business-review-view__business-comment');
        const bubble = bc && bc.querySelector('.business-review-comment-content__bubble');
        const stars = c.querySelector('.business-review-view__rating .business-rating-badge-view__stars');
        const counters = [...c.querySelectorAll('.business-reactions-view__container')].map((x) => ({ label: x.getAttribute('aria-label'), count: txt(x.querySelector('.business-reactions-view__counter')) }));
        const pub = m.author && m.author.publicId ? m.author.publicId : null;
        const hdr = bc && bc.querySelector('.business-review-comment-content__header');
        let hdrOwn = null;
        if (hdr) { hdrOwn = ''; for (const n of hdr.childNodes) if (n.nodeType === 3) hdrOwn += n.textContent; }
        return {
          position: i + 1,
          aria_posinset: li ? li.getAttribute('aria-posinset') : null,
          review_id: m.reviewId || null,
          review_url: pub && orgId ? SHARE(orgId, pub) : null,
          author_name: txt(c.querySelector('.business-review-view__author-name [itemprop="name"]')),
          author_profile_url: a ? a.href : null,
          date_shown: txt(c.querySelector('.business-review-view__date > span')),
          date_published: meta(c, 'datePublished'),
          model_updated_time: m.updatedTime || null,
          rating: meta(c, 'ratingValue'),
          rating_aria_label: stars ? stars.getAttribute('aria-label') : null,
          model_rating: m.rating === undefined ? null : m.rating,
          text: txt(c.querySelector('.business-review-view__body .spoiler-view__text-container')),
          model_text: m.text === undefined ? null : m.text,
          text_still_collapsed: !!c.querySelector('.spoiler-view__text._collapsed') || !!c.querySelector('.business-review-view__expand'),
          text_language: m.textLanguage || null,
          reactions_shown: counters,
          model_reactions: m.reactions ? { likes: m.reactions.likes, dislikes: m.reactions.dislikes } : null,
          photos_count: (m.photos || []).length,
          photos: (m.photos || []).map((p) => p.urlTemplate),
          videos_count: (m.videos || []).length,
          videos: (m.videos || []).map((v) => ({ video_url: v.videoUrl, poster: v.urlTemplate })),
          dom_media_items: c.querySelectorAll('.business-review-view__carousel .carousel__item').length,
          dom_media_thumbnails: [...c.querySelectorAll('.business-review-media__item-img')].map((im) => im.getAttribute('src')),
          pinned: m.pinned === undefined ? null : m.pinned,
          has_org_reply: !!bc,
          org_reply: bc ? {
            header_shown: hdrOwn,
            date_shown: txt(bc.querySelector('.business-review-comment-content__date')),
            text: bubble ? bubble.textContent : null,
            model_text: m.businessComment ? m.businessComment.text : null,
            model_updated_time: m.businessComment ? m.businessComment.updatedTime : null,
            expanded: !!bubble,
          } : null,
        };
      });
      const byRating = {};
      reviews.forEach((r) => { byRating[r.rating] = (byRating[r.rating] || 0) + 1; });
      const li0 = document.querySelector('.business-reviews-card-view__review');
      return {
        source_url: location.href,
        captured_at_browser: new Date().toISOString(),
        browser_timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
        page_title: document.title,
        org: {
          name_h1: txt(document.querySelector('h1.orgpage-header-view__header')),
          permalink_id: orgId,
          coordinates: orgEl ? orgEl.dataset.coordinates : null,
        },
        header: {
          reviews_header_as_shown: txt(document.querySelector('.business-reviews-card-view__title h2')),
          sort_as_shown: txt(document.querySelector('.rating-ranking-view')),
          list_aria_setsize: li0 ? li0.getAttribute('aria-setsize') : null,
          rating_as_shown: txt(document.querySelector('.business-summary-rating-badge-view__rating')),
          rating_count_as_shown: txt(document.querySelector('.business-summary-rating-badge-view__rating-count')),
          aggregateRating_meta: { ratingValue: meta(agg, 'ratingValue'), ratingCount: meta(agg, 'ratingCount'), reviewCount: meta(agg, 'reviewCount') },
        },
        method: 'DOM of the Yandex Maps reviews tab in Playwright (Chromium), no login. All cards loaded by scrolling .scroll__container; texts expanded via .business-review-view__expand; organisation replies expanded via .business-review-comment-expandable-view__expand. Fields without prefix are read from DOM elements/attributes; fields with prefix model_ and review_id/photos/videos/pinned are read from the React props object (review) attached to the same card element. review_url is built by the template shown in the page dialog "Поделиться отзывом" (org id + author publicId); null when the author has no public profile (no share button on the card). date_shown and org_reply.date_shown are rendered by the page in the browser time zone (see browser_timezone); date_published is the exact UTC time from meta[itemprop=datePublished].',
        counts: {
          cards_in_dom: cards.length,
          by_rating: byRating,
          with_org_reply: reviews.filter((r) => r.has_org_reply).length,
          with_photos: reviews.filter((r) => r.photos_count > 0).length,
          with_videos: reviews.filter((r) => r.videos_count > 0).length,
          photos_total: reviews.reduce((s, r) => s + r.photos_count, 0),
          videos_total: reviews.reduce((s, r) => s + r.videos_count, 0),
          without_review_url: reviews.filter((r) => !r.review_url).length,
          text_dom_ne_model: reviews.filter((r) => r.text !== r.model_text).length,
          reply_dom_ne_model: reviews.filter((r) => r.org_reply && r.org_reply.text !== r.org_reply.model_text).length,
          rating_dom_ne_model: reviews.filter((r) => parseFloat(r.rating) !== r.model_rating).length,
          text_still_collapsed: reviews.filter((r) => r.text_still_collapsed).length,
          reply_not_expanded: reviews.filter((r) => r.org_reply && !r.org_reply.expanded).length,
          unique_review_ids: new Set(reviews.map((r) => r.review_id)).size,
        },
        reviews,
      };
    };

    // outerHTML элемента; хеш и длина сохраняются в window.__ymLastHtml для сверки после записи в файл.
    const listHtml = async (selector) => {
      const el = document.querySelector(selector);
      if (!el) return null;
      const html = el.outerHTML;
      window.__ymLastHtml = { selector, length: html.length, sha256: await sha(html), bytes: new TextEncoder().encode(html).length, at: new Date().toISOString(), url: location.href };
      return html;
    };

    // Помечает карточки атрибутом data-ym-shot="<id записи>" по reviewId (для скриншотов).
    const mark = (map) => {
      let n = 0;
      for (const c of document.querySelectorAll('.business-review-view')) {
        const m = getModel(c);
        if (m && map[m.reviewId]) { c.setAttribute('data-ym-shot', map[m.reviewId]); n++; }
      }
      return n;
    };

    // Ставит карточку ниже «липких» шапок панели, чтобы они её не перекрывали.
    const place = async (id, top = 330) => {
      const sc = document.querySelector('.scroll__container');
      const c = document.querySelector(`[data-ym-shot="${id}"]`);
      if (!c) return null;
      sc.scrollTop += c.getBoundingClientRect().top - top;
      await sleep(250);
      const r = c.getBoundingClientRect();
      return { top: Math.round(r.top), height: Math.round(r.height), width: Math.round(r.width), bottom: Math.round(r.bottom), vh: innerHeight };
    };

    window.__ym = { loadAll, expandAll, extract, listHtml, mark, place, getModel, sha, sleep };
    return { installed: true, tz: Intl.DateTimeFormat().resolvedOptions().timeZone, url: location.href, cards: cardsNow(), title: document.title };
  };
  // Чтобы функции были доступны и после перехода на другую карточку (новый документ).
  await page.addInitScript(install);
  return await page.evaluate(install);
}
