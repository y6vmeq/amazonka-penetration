"""Печатает краткое содержание сохранённого результата поиска в текстовый файл UTF-8.

Запуск: python -I scripts/show_search.py <raw/NNN_...search....json> <out.txt>
Файл только читается как данные.
"""
import json
import sys
from pathlib import Path

data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
lines = [f"url: {data.get('url')}", f"title: {data.get('title')}", f"h1: {data.get('h1')}",
         f"consent: {data.get('consent')} sorry: {data.get('sorry')} has_feed: {data.get('has_feed')}",
         f"results: {len(data.get('results') or [])}"]
for item in data.get("results") or []:
    lines.append(f"- {item['name']} | {item['text']} | {item['href'][:160]}")
card = data.get("card")
if card:
    for key in ("name", "rating", "distribution", "hours", "tabs", "headings"):
        lines.append(f"card.{key}: {json.dumps(card.get(key), ensure_ascii=False)}")
    for item in card.get("items") or []:
        lines.append(f"card.item: {item['id']} | {item['label']} | {item.get('href')}")
    lines.append("card.text: " + (card.get("text") or ""))
if data.get("body_text"):
    lines.append("body: " + data["body_text"])
Path(sys.argv[2]).write_text("\n".join(lines) + "\n", encoding="utf-8")
print("ok")
