"""Дописывает в raw/manifest.jsonl строки о файлах, сохранённых из браузера.

Запуск: python -I manifest_add.py <папка_сбора> <url> <файл в raw/> [<файл> ...] [--note "текст"]
fetched_at берётся из времени изменения файла (UTC). Файлы не разбираются и не исполняются.
"""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def main():
    args = sys.argv[1:]
    note = None
    if "--note" in args:
        index = args.index("--note")
        note = args[index + 1]
        del args[index:index + 2]
    collection = Path(args[0])
    url = args[1]
    raw_dir = collection / "raw"
    manifest = raw_dir / "manifest.jsonl"
    known = set()
    if manifest.is_file():
        for line in manifest.read_text(encoding="utf-8").splitlines():
            if line.strip():
                known.add(json.loads(line).get("file"))
    with manifest.open("a", encoding="utf-8", newline="\n") as out:
        for name in args[2:]:
            path = raw_dir / name
            data = path.read_bytes()
            rel = f"raw/{path.name}"
            if rel in known:
                print(f"skip (already in manifest): {path.name}")
                continue
            record = {
                "file": rel,
                "url": url,
                "fetched_at": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(timespec="seconds"),
                "bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
                "method": "browser",
            }
            if note:
                record["note"] = note
            out.write(json.dumps(record, ensure_ascii=False) + "\n")
            print(f"added: {path.name} {len(data)} bytes")


if __name__ == "__main__":
    main()
