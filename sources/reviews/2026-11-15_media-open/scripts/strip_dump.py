"""Кладёт данные выгрузки без base64 в work/pages/ и ничего больше не делает.

Запуск из корня проекта:
    python -I -X utf8 sources/reviews/2026-11-15_media-open/scripts/strip_dump.py <dump.json> <суффикс>
Нужен для проверочных заходов на обычную страницу публикации, когда файл совпал с уже
сохранённым (тот же SHA-256) и повторно его писать не нужно.
"""
import json
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
dump = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
suffix = re.sub(r"[^A-Za-z0-9_.-]+", "_", sys.argv[2])
for item in dump.get("items") or []:
    item.pop("b64", None)
code = (dump.get("meta") or {}).get("code") or "nocode"
target = BASE / "work" / "pages" / f"{dump.get('platform')}_{code}_{suffix}.json"
target.write_text(json.dumps(dump, ensure_ascii=False, indent=1), encoding="utf-8")
print(target.name)
