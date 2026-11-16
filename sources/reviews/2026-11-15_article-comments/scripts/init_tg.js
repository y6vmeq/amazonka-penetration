// Разбор открытых гостю виджетов Telegram (t.me/<канал>/<пост>?embed=1...): window.__tg.
// extractPost() — запись канала из виджета записи; extractDiscussion() — комментарии из виджета обсуждения;
// expand() — догрузка комментариев кнопкой виджета. Ничего не отправляет, в аккаунт не входит.
async (page) => {
  const init = () => {
    const tg = {};
    const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
    const clean = (text) => (text || '').replace(/ /g, ' ').trim();

    const textOf = (element) => {
      if (!element) return '';
      const copy = element.cloneNode(true);
      for (const emoji of copy.querySelectorAll('tg-emoji')) {
        const bold = emoji.querySelector('i.emoji b, b');
        emoji.replaceWith(document.createTextNode(bold ? bold.textContent : ''));
      }
      for (const emoji of copy.querySelectorAll('i.emoji')) emoji.replaceWith(document.createTextNode(emoji.textContent || ''));
      for (const br of copy.querySelectorAll('br')) br.replaceWith(document.createTextNode('\n'));
      return clean(copy.textContent);
    };

    const backgroundUrl = (element) => {
      const match = /url\(["']?([^"')]+)["']?\)/.exec(element.getAttribute('style') || '');
      return match ? match[1] : '';
    };

    const mediaOf = (message) => {
      const items = [];
      for (const photo of message.querySelectorAll('.tgme_widget_message_photo_wrap')) items.push({ type: 'photo', src: backgroundUrl(photo), href: photo.href || '' });
      for (const video of message.querySelectorAll('.tgme_widget_message_video_player, .tgme_widget_message_video_wrap')) {
        const tag = video.querySelector('video');
        const thumb = video.querySelector('.tgme_widget_message_video_thumb');
        items.push({ type: 'video', src: tag ? (tag.currentSrc || tag.src || '') : '', thumb: thumb ? backgroundUrl(thumb) : '', href: video.href || '', duration: clean((video.querySelector('.message_video_duration') || {}).textContent) });
      }
      for (const round of message.querySelectorAll('.tgme_widget_message_roundvideo_player')) { const tag = round.querySelector('video'); items.push({ type: 'roundvideo', src: tag ? tag.src : '' }); }
      for (const sticker of message.querySelectorAll('.tgme_widget_message_sticker, .tgme_widget_message_sticker_wrap i')) items.push({ type: 'sticker', src: backgroundUrl(sticker) || sticker.getAttribute('data-webp') || '' });
      for (const voice of message.querySelectorAll('.tgme_widget_message_voice, audio')) items.push({ type: 'voice', src: voice.src || voice.getAttribute('data-ogg') || '' });
      for (const doc of message.querySelectorAll('.tgme_widget_message_document_wrap, .tgme_widget_message_document')) items.push({ type: 'document', title: clean(doc.textContent).slice(0, 120), href: doc.href || '' });
      for (const preview of message.querySelectorAll('.tgme_widget_message_link_preview')) items.push({ type: 'link-preview', href: preview.href || '', title: clean((preview.querySelector('.link_preview_title') || {}).textContent), text: clean((preview.querySelector('.link_preview_description') || {}).textContent).slice(0, 300), image: (() => { const image = preview.querySelector('.link_preview_image, .link_preview_right_image'); return image ? backgroundUrl(image) : ''; })() });
      for (const poll of message.querySelectorAll('.tgme_widget_message_poll')) items.push({ type: 'poll', text: clean(poll.innerText).slice(0, 600) });
      for (const unsupported of message.querySelectorAll('.message_media_not_supported_label')) items.push({ type: 'not-supported', text: clean(unsupported.textContent) });
      return items;
    };

    tg.parseMessage = (message) => {
      const bubble = message.querySelector('.tgme_widget_message_bubble') || message;
      const direct = (selector) => [...bubble.querySelectorAll(selector)].find((element) => !element.closest('.js-reply_tpl'));
      const author = direct('.tgme_widget_message_author_name, .tgme_widget_message_owner_name');
      const dateLink = direct('a.tgme_widget_message_date');
      const time = dateLink ? dateLink.querySelector('time') : direct('time');
      const reply = direct('a.tgme_widget_message_reply');
      const textElement = direct('.tgme_widget_message_text.js-message_text') || direct('.tgme_widget_message_text');
      const forwarded = direct('.tgme_widget_message_forwarded_from');
      const views = direct('.tgme_widget_message_views');
      const meta = direct('.tgme_widget_message_meta');
      const reactions = [...bubble.querySelectorAll('.tgme_widget_message_reactions .tgme_reaction, .tgme_widget_message_reactions span')].filter((element) => !element.closest('.js-reply_tpl')).map((element) => clean(element.textContent)).filter(Boolean);
      const signature = direct('.tgme_widget_message_from_author');
      return {
        id: message.getAttribute('data-post-id') || message.getAttribute('data-post') || '',
        author: author ? clean(author.textContent) : '',
        authorHref: author && author.href ? author.href : '',
        text: textOf(textElement),
        dateText: time ? clean(time.textContent) : '',
        datetime: time ? time.getAttribute('datetime') : '',
        url: dateLink ? dateLink.href : '',
        replyTo: reply ? { href: reply.href || '', author: clean((reply.querySelector('.tgme_widget_message_author_name') || {}).textContent), text: clean((reply.querySelector('.tgme_widget_message_metatext, .tgme_widget_message_text') || {}).textContent).slice(0, 200) } : null,
        forwardedFrom: forwarded ? clean(forwarded.textContent) : '',
        views: views ? clean(views.textContent) : '',
        metaText: meta ? clean(meta.textContent) : '',
        signature: signature ? clean(signature.textContent) : '',
        reactions,
        media: mediaOf(bubble),
      };
    };

    tg.extractPost = () => {
      const message = document.querySelector('.tgme_widget_message');
      const error = document.querySelector('.tgme_widget_message_error');
      const commentsLink = document.querySelector('.tgme_widget_message_replies, .tgme_widget_message_inline_button, a[href*="comment"]');
      return { url: location.href, at: new Date().toISOString(), error: error ? clean(error.textContent) : '', post: message ? tg.parseMessage(message) : null, repliesText: commentsLink ? clean(commentsLink.textContent) : '', bodyText: clean(document.body.innerText).slice(0, 400) };
    };

    tg.moreButton = () => [...document.querySelectorAll('.js-messages_more')].find((element) => !element.classList.contains('hide') && element.offsetParent !== null);

    tg.expand = async (limit = 80) => {
      const log = [];
      for (let round = 0; round < limit; round += 1) {
        const button = tg.moreButton();
        if (!button) break;
        const before = document.querySelectorAll('.js-widget_message').length;
        button.scrollIntoView({ block: 'center' });
        button.click();
        let changed = false;
        for (let attempt = 0; attempt < 40; attempt += 1) {
          await sleep(250);
          if (document.querySelectorAll('.js-widget_message').length !== before) { changed = true; break; }
        }
        log.push({ label: clean(button.textContent).slice(0, 40), before, after: document.querySelectorAll('.js-widget_message').length, changed });
        if (!changed) break;
        await sleep(300);
      }
      return log;
    };

    tg.extractDiscussion = () => {
      const header = document.querySelector('.tgme_post_discussion_header, .js-header');
      const error = document.querySelector('.tgme_widget_message_error, .tgme_post_discussion_error');
      const comments = [...document.querySelectorAll('.js-widget_message, .tgme_post_discussion .tgme_widget_message')].map((message) => tg.parseMessage(message));
      const seen = new Set();
      return {
        url: location.href,
        at: new Date().toISOString(),
        header: header ? clean(header.textContent) : '',
        error: error ? clean(error.textContent) : '',
        comments: comments.filter((comment) => { const key = comment.id + '|' + comment.url; if (seen.has(key)) return false; seen.add(key); return true; }),
        moreLeft: Boolean(tg.moreButton()),
        moreState: [...document.querySelectorAll('.js-messages_more')].map((element) => `${element.className}|after=${element.getAttribute('data-after') || ''}|before=${element.getAttribute('data-before') || ''}`),
        bodyText: clean(document.body.innerText).slice(0, 300),
      };
    };

    Object.defineProperty(window, '__tg', { value: tg, enumerable: false, configurable: true, writable: true });
  };
  await page.context().addInitScript(init);
  for (const candidate of page.context().pages()) await candidate.evaluate(init).catch(() => {});
  return 'tg helper added';
}
