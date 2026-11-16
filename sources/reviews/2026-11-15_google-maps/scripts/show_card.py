"""Печатает краткое содержание сохранённой карточки места (без HTML) в текстовый файл UTF-8.

Запуск: python -I scripts/show_card.py <raw/NNN_..._card.json> <out.txt>
Файл только читается как данные.
"""
import json
import sys
from pathlib import Path

data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
lines = []
for key in ("captured_at", "url", "name", "panel_label", "rating", "distribution", "hours", "tabs", "headings", "error"):
    if key in data:
        lines.append(f"{key}: {json.dumps(data.get(key), ensure_ascii=False)}")
for item in data.get("items") or []:
    lines.append(f"item: {item['id']} | {item['label']} | {item.get('href')}")
lines.append("text: " + (data.get("text") or ""))
lines.append(f"html length: {len(data.get('html') or '')}")
Path(sys.argv[2]).write_text("\n".join(lines) + "\n", encoding="utf-8")
print("ok")
