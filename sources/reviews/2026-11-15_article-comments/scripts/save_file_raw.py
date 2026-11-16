"""Кладёт уже скачанный файл (например, страницу, полученную curl с другим User-Agent) в raw/ и в manifest.

Запуск из корня проекта:
    python -I -X utf8 .../scripts/save_file_raw.py <исходный файл> <адрес> <имя> <пояснение> [расширение]
"""
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

BASE = Path("sources/reviews/2026-11-15_article-comments")
RAW = BASE / "raw"

source, url, name, note = Path(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4]
extension = sys.argv[5] if len(sys.argv) > 5 else ".html"
numbers = [int(match.group(1)) for path in RAW.iterdir() if (match := re.match(r"(\d{3,})_", path.name))]
number = max(numbers, default=0) + 1
host = re.sub(r"[^a-z0-9]+", "-", (urlsplit(url).hostname or "host").lower()).strip("-")
target = RAW / f"{number:03d}_{host}_{re.sub(r'[^a-zA-Z0-9]+', '-', name).strip('-').lower()[:70]}{extension}"
data = source.read_bytes()
target.write_bytes(data)
with (RAW / "manifest.jsonl").open("a", encoding="utf-8", newline="\n") as manifest:
    manifest.write(json.dumps({"file": f"raw/{target.name}", "url": url, "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                               "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), "method": "curl", "kind": "server-html", "note": note}, ensure_ascii=False) + "\n")
print(json.dumps({"n": number, "file": f"raw/{target.name}", "bytes": len(data)}))
