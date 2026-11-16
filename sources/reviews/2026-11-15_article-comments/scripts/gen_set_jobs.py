"""Собирает сценарий scripts/set_jobs_magilev.js: кладёт во вкладку-накопитель задания для batch_pages.js
(новые статьи magilev.by из work/magilev_jobs.json). Сценарий короткий: список путей и правило сборки."""
import json
from pathlib import Path

BASE = Path("sources/reviews/2026-11-15_article-comments")
jobs = json.loads((BASE / "work" / "magilev_jobs.json").read_text(encoding="utf-8"))
compact = []
for name, path, pattern in jobs:
    code = "A" if pattern == "Амазонк" else ("C" if pattern.startswith("Colette") else "L")
    compact.append(code + path)
template = r"""async (page) => { const list = __LIST__; const n = await page.evaluate((items) => { const S = 'C:/Users/y6vme/OneDrive/myDocuments/belarus/sources/reviews/2026-11-15_article-comments/screenshots/'; const P = { A: 'Амазонк', C: 'Colette|COLETTE|Колетт', L: 'Ленинская, 38' }; window.__isCollector = true; window.__dumps = []; window.__jobs = items.map((item) => { const path = item.slice(1); const m = /^(\d{4})\/(\d{2})\/(\d{2})\/(.+)$/.exec(path); const name = `magilev_${m[1]}-${m[2]}-${m[3]}_${m[4].replace(/[^a-z0-9]+/g, '-').slice(0, 38).replace(/^-+|-+$/g, '')}`; return { name, url: 'https://magilev.by/news/' + path, quiet: true, find: 'амазонк|colette|колетт|\b\[исключено\]\b|смак\.by', shot: S + name + '_konec-stati.png', shotSelector: '.content-detail-footer', extraShots: [{ pattern: P[item[0]], path: S + name + '_fragment.png' }] }; }); return window.__jobs.length; }, list); return n; }
"""
code = template.replace("__LIST__", json.dumps(compact, ensure_ascii=False, separators=(",", ":")))
(BASE / "scripts" / "set_jobs_magilev.js").write_text(code, encoding="utf-8", newline="\n")
print(len(code))
