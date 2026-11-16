// Поиск по сайту magilev.by через его собственную форму (страница /search/?query=...).
// Для каждого запроса из window.__queries (вкладка-накопитель) рабочая вкладка открывает
// страницу поиска и листает выдачу кнопкой «Вперед», пока она есть. Результат каждого
// запроса (список карточек и разметка блока выдачи по страницам) складывается в
// window.__dumps накопителя. Запросы к API сайта вручную не строятся: всё делает сама
// страница. Если выдача не появляется (например, сайт требует проверку) — это
// записывается в результат, проверка не проходится.
async (page) => {
  const context = page.context();
  let collector = null;
  for (const candidate of context.pages()) {
    const flag = await candidate.evaluate(() => window.__isCollector === true).catch(() => false);
    if (flag) { collector = candidate; break; }
  }
  if (!collector) return { error: 'collector tab not found' };
  const worker = context.pages().find((candidate) => candidate !== collector) || await context.newPage();
  const queries = await collector.evaluate(() => window.__queries || []);
  const maxPages = await collector.evaluate(() => window.__maxPages || 80);
  await collector.evaluate(() => { window.__dumps = window.__dumps || []; });
  const summary = [];
  for (const query of queries) {
    const item = { query };
    try {
      await worker.goto('https://magilev.by/search/?query=' + encodeURIComponent(query), { waitUntil: 'domcontentloaded', timeout: 60000 });
      const result = await worker.evaluate(async (limit) => {
        const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
        const root = () => document.querySelector('.search-page__form') || document.querySelector('main');
        const cards = () => [...document.querySelectorAll('article[class^="_card_"]')].map((card) => {
          const anchor = card.querySelector('a[href]');
          return { href: anchor ? anchor.href : null, text: (card.innerText || '').replace(/\s+/g, ' ').trim() };
        });
        const listText = () => { const list = document.querySelector('div[class^="_list_"]'); return list ? list.innerText : ''; };
        // ждём первую выдачу или сообщение о пустом результате
        let waited = 0;
        while (waited < 20000 && cards().length === 0 && !/ничего не найдено|не найдено|нет результатов|по вашему запросу/i.test(root() ? root().innerText : '')) {
          await sleep(300); waited += 300;
        }
        await sleep(500);
        const pages = [];
        let pageNumber = 1;
        let stop = '';
        while (true) {
          pages.push({ page: pageNumber, at: new Date().toISOString(), url: location.href, items: cards(), text: root() ? root().innerText : '', html: root() ? root().outerHTML : '' });
          const next = [...document.querySelectorAll('button[class^="_navigationbtn_"]')].find((button) => button.innerText.trim() === 'Вперед');
          if (!next || next.disabled) { stop = 'нет кнопки «Вперед»'; break; }
          if (pageNumber >= limit) { stop = 'достигнут предел страниц'; break; }
          const before = listText();
          next.click();
          let changed = false;
          for (let attempt = 0; attempt < 80; attempt += 1) {
            await sleep(250);
            if (listText() !== before) { changed = true; break; }
          }
          if (!changed) { stop = 'после нажатия «Вперед» выдача не изменилась за 20 с'; break; }
          await sleep(500);
          pageNumber += 1;
        }
        const frames = [...document.querySelectorAll('iframe')].map((frame) => frame.src).filter((src) => /recaptcha|captcha/i.test(src));
        return { query: new URLSearchParams(location.search).get('query'), finalUrl: location.href, waitedMs: waited, stop, captchaFrames: frames, pages };
      }, maxPages);
      await collector.evaluate((entry) => { window.__dumps.push(entry); }, result);
      item.pages = result.pages.length;
      item.items = result.pages.reduce((sum, entry) => sum + entry.items.length, 0);
      item.stop = result.stop;
      item.waitedMs = result.waitedMs;
      item.firstText = result.pages[0] ? result.pages[0].text.slice(0, 120) : '';
      item.captchaFrames = result.captchaFrames.length;
    } catch (error) {
      item.error = String(error).slice(0, 300);
    }
    summary.push(item);
  }
  return summary;
}
