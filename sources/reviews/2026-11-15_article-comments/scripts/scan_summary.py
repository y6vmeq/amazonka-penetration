"""Краткая сводка work/scan_<сайт>.json: по каждой статье — какие упоминания найдены.

Запуск: python -I -X utf8 .../scripts/scan_summary.py <сайт-слаг> [категория ...]
Без категорий печатает одну строку на статью; с категориями — контексты этих категорий.
"""
import json
import sys
from pathlib import Path

BASE = Path("sources/reviews/2026-11-15_article-comments")
site = sys.argv[1]
categories = sys.argv[2:]
results = json.loads((BASE / "work" / f"scan_{site}.json").read_text(encoding="utf-8"))
out = []
for result in results:
    hits = result["hits"]
    if not hits:
        continue
    if categories:
        chosen = {name: hit for name, hit in hits.items() if name in categories}
        if not chosen:
            continue
        out.append(f"## {result['url']}\n   {result['title']}")
        for name, hit in chosen.items():
            out.append(f"   [{name}] x{hit['count']}")
            for context in hit["contexts"][:4]:
                out.append(f"      …{context}…")
    else:
        out.append(f"{result['url'].replace('https://magilev.by', '')} | {result['title'][:70]} | " + ", ".join(f"{name}x{hit['count']}" for name, hit in hits.items()))
target = BASE / "work" / f"scan_{site}_summary{'_' + '-'.join(categories) if categories else ''}.txt"
target.write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
print(len(out), target.name)
