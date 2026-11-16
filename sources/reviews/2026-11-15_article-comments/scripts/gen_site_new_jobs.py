"""Собирает scripts/set_jobs_site_new.js: задания batch_pages.js для новых статей komkur.info и masheka.by
(work/site_new_articles.json)."""
import json
import re
from pathlib import Path

BASE = Path("sources/reviews/2026-11-15_article-comments")
want = json.loads((BASE / "work" / "site_new_articles.json").read_text(encoding="utf-8"))
items = []
for url in want["komkur-info"]:
    items.append("K" + url.replace("https://komkur.info/", ""))
for url in want["masheka-by"]:
    items.append("M" + url.replace("https://masheka.by/", ""))
template = """async (page) => { const list = __LIST__; for (const p of page.context().pages()) { if (await p.evaluate(() => window.__isCollector === true).catch(() => false)) { return await p.evaluate((items) => { const S = 'C:/Users/y6vme/OneDrive/myDocuments/belarus/sources/reviews/2026-11-15_article-comments/screenshots/'; window.__dumps = []; window.__jobs = items.map((item) => { const path = item.slice(1); const komkur = item[0] === 'K'; const tail = path.split('/').pop().replace(/[.]html$/, ''); const name = (komkur ? 'komkur_new_' : 'masheka_new_') + tail.replace(/[^a-z0-9]+/g, '-').slice(0, 40).replace(/^-+|-+$/g, ''); const job = { name, url: (komkur ? 'https://komkur.info/' : 'https://masheka.by/') + path, quiet: true, shot: S + name + '_konec-stati.png' }; if (komkur) job.shotText = 'Подписывайтесь на нас'; else job.shotSelector = '.frating'; return job; }); return window.__jobs.length; }, list); } } return 'no collector'; }
"""
code = template.replace("__LIST__", json.dumps(items, ensure_ascii=False, separators=(",", ":")))
(BASE / "scripts" / "set_jobs_site_new.js").write_text(code, encoding="utf-8", newline="\n")
print(len(items), len(code))
