"""Дописывает в media/manifest.jsonl файлы, полученные не через tools/media_download.py (например, yt-dlp).

Запуск: python -I scripts/manifest_add.py <папка_сбора> <группа> <ссылка на публикацию> <пояснение> <файл> [<файл> ...]
Для каждого файла считает размер и SHA-256. Уже записанные файлы пропускает.
"""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

collection = Path(sys.argv[1])
group, url, via = sys.argv[2], sys.argv[3], sys.argv[4]
files = [Path(p) for p in sys.argv[5:]]
manifest = collection / "media" / "manifest.jsonl"
known = set()
if manifest.is_file():
    for line in manifest.read_text(encoding="utf-8").splitlines():
        entry = json.loads(line)
        if entry.get("file"):
            known.add(entry["file"])
with manifest.open("a", encoding="utf-8", newline="\n") as out:
    for number, path in enumerate(files, 1):
        relative = path.resolve().relative_to(collection.resolve()).as_posix()
        if relative in known:
            print("already", relative)
            continue
        data = path.read_bytes()
        entry = {
            "group": group, "n": number, "url": url, "file": relative, "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(), "content_type": None, "status": 200, "note": "",
            "fetched_at": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(timespec="seconds"),
            "via": via,
        }
        out.write(json.dumps(entry, ensure_ascii=False) + "\n")
        print("added", relative, len(data), entry["sha256"])
