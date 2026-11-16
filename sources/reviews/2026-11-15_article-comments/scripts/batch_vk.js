// Пакетный обход записей ВКонтакте (без входа). Для каждого задания из window.__jobs накопителя:
// открыть запись, раскрыть «показать следующие комментарии / ответы» (window.__vk.expand),
// снять разметку (window.__ac.dump, в extra.vk — разобранные запись и комментарии),
// скрыть плавающую полосу «Войти / Зарегистрироваться» (только для снимка экрана, после снятия разметки)
// и сделать снимок всей страницы. Отметки не ставятся, формы не отправляются.
async (page) => {
  const context = page.context();
  let collector = null;
  for (const candidate of context.pages()) {
    const flag = await candidate.evaluate(() => window.__isCollector === true).catch(() => false);
    if (flag) { collector = candidate; break; }
  }
  if (!collector) return { error: 'collector tab not found' };
  const worker = context.pages().find((candidate) => candidate !== collector) || await context.newPage();
  await worker.setViewportSize({ width: 1280, height: 1000 });
  const jobs = await collector.evaluate(() => window.__jobs || []);
  await collector.evaluate(() => { window.__dumps = window.__dumps || []; });
  const results = [];
  for (const job of jobs) {
    const result = { name: job.name };
    try {
      const response = await worker.goto(job.url, { waitUntil: 'domcontentloaded', timeout: 60000 });
      result.status = response ? response.status() : null;
      await worker.waitForLoadState('load', { timeout: 25000 }).catch(() => { result.loadTimeout = true; });
      await worker.waitForTimeout(2500);
      result.scroll = (await worker.evaluate(async () => window.__ac.scrollAll(900, 150))).height;
      result.expand = await worker.evaluate(async () => (window.__vk ? window.__vk.expand(80) : 'no helper'));
      await worker.evaluate(async () => window.__ac.scrollAll(900, 120));
      const dump = await worker.evaluate(async (extra) => {
        extra.vk = window.__vk ? window.__vk.extract() : null;
        return window.__ac.dump(extra);
      }, { name: job.name, status: result.status, requested: job.url });
      await collector.evaluate((item) => { window.__dumps.push(item); }, dump);
      result.finalUrl = dump.url;
      result.title = dump.title.slice(0, 90);
      const vk = dump.extra.vk;
      if (vk) {
        result.loginWall = vk.loginWall;
        result.moreLeft = vk.moreButtonsLeft;
        result.post = vk.post ? { author: vk.post.author, date: vk.post.dateText, signer: vk.post.signer, likes: vk.post.likes, shares: vk.post.shares, text: vk.post.text.slice(0, 110), attachments: vk.post.attachments.length } : null;
        result.comments = vk.comments.length;
        result.commentHeads = vk.comments.map((comment) => `${comment.author} | ${comment.dateText} | ♥${comment.likes} | ${comment.text.slice(0, 90).replace(/\s+/g, ' ')}${comment.attachments.length ? ' | вложений: ' + comment.attachments.length : ''}`).slice(0, job.heads || 40);
      }
      result.textLen = dump.text.length;
      result.bodyHead = vk && vk.post ? '' : dump.text.slice(0, 500).replace(/\s+/g, ' ');
      if (job.shot) {
        await worker.evaluate(() => {
          for (const banner of document.querySelectorAll('.PageBottomBanner')) banner.style.display = 'none';
          window.scrollTo(0, 0);
        });
        await worker.waitForTimeout(600);
        await worker.screenshot({ path: job.shot, fullPage: true });
        result.shot = true;
      }
    } catch (error) {
      result.error = String(error).slice(0, 400);
    }
    results.push(result);
  }
  return results;
}
