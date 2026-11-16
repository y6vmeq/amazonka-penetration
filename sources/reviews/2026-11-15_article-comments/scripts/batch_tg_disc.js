// Обсуждения под записями каналов Telegram без входа (только виджет обсуждения).
// Задание { name, channel, post, shot }: открыть https://t.me/<канал>/<пост>?embed=1&discussion=1&comments_limit=100,
// догрузить комментарии кнопкой виджета, снять разметку (extra.tgDiscussion). Снимок экрана всей страницы
// делается, только если комментарии есть. В ответ — число комментариев и те из них, где названы заведения.
async (page) => {
  const context = page.context();
  let collector = null;
  for (const candidate of context.pages()) {
    const flag = await candidate.evaluate(() => window.__isCollector === true).catch(() => false);
    if (flag) { collector = candidate; break; }
  }
  if (!collector) return { error: 'collector tab not found' };
  const worker = context.pages().find((candidate) => candidate !== collector) || await context.newPage();
  await worker.setViewportSize({ width: 1000, height: 1000 });
  const jobs = await collector.evaluate(() => window.__jobs || []);
  await collector.evaluate(() => { window.__dumps = window.__dumps || []; });
  const venue = /амазонк|amazonk|смак|colette|колетт|\b\[исключено\]\b|\[исключено\][аеуы]\b|зме[йяюи]|рептил|ящериц|геккон|таракан|отрав|хозяйк|владел/i;
  const results = [];
  for (const job of jobs) {
    const result = { n: job.name };
    try {
      const url = `https://t.me/${job.channel}/${job.post}?embed=1&discussion=1&comments_limit=100`;
      await worker.goto(url, { waitUntil: 'load', timeout: 60000 });
      await worker.waitForTimeout(1200);
      const expand = await worker.evaluate(async () => window.__tg.expand(150));
      const dump = await worker.evaluate(async (extra) => { extra.tgDiscussion = window.__tg.extractDiscussion(); return window.__ac.dump(extra); }, { name: job.name, status: 200, requested: url, channel: job.channel, post: job.post });
      await collector.evaluate((item) => { window.__dumps.push(item); }, dump);
      const discussion = dump.extra.tgDiscussion;
      result.c = discussion.comments.length;
      if (expand.length) result.expand = expand.length;
      if (discussion.moreLeft) result.moreLeft = true;
      if (!discussion.comments.length) result.h = (discussion.header + ' / ' + discussion.bodyText.replace(/\s+/g, ' ')).slice(0, 90);
      const hits = discussion.comments.filter((comment) => venue.test(comment.text));
      if (hits.length) result.hits = hits.map((comment) => `${comment.author}: ${comment.text.slice(0, 160).replace(/\s+/g, ' ')}`);
      if (discussion.comments.length && job.shot) {
        await worker.evaluate(() => window.scrollTo(0, 0));
        await worker.screenshot({ path: job.shot, fullPage: true });
      }
    } catch (error) {
      result.error = String(error).slice(0, 200);
    }
    results.push(result);
  }
  return results;
}
