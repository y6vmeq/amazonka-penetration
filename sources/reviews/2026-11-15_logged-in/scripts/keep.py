"""Переносит снимок области экрана (действие zoom расширения) из временной папки в screenshots/ без обрезки.

Запуск: python -I -X utf8 scripts/keep.py <имя без расширения> <адрес страницы> <пояснение> <файл снимка> [<область: l,t,r,b в координатах кадра>]

Несколько снимков за один запуск: повторить тройку аргументов нельзя, поэтому есть второй режим —
python -I -X utf8 scripts/keep.py --list <файл.json>, где файл — список объектов
{"src": ..., "name": ..., "url": ..., "note": ..., "region": [l,t,r,b]}.
В screenshots/index.jsonl дописывается строка: файл, адрес, время (UTC), SHA-256, размер, область.
"""
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent.parent
TEMP = Path(r"C:\Users\y6vme\AppData\Local\Temp\claude-chrome-screenshots-Q7ZrXS")


def keep(src, name, url, note, region=None):
    src = Path(src)
    if not src.is_absolute():
        src = TEMP / src
    out_dir = HERE / "screenshots"
    out_dir.mkdir(exist_ok=True)
    target = out_dir / f"{name}{src.suffix.lower()}"
    taken = datetime.fromtimestamp(src.stat().st_mtime, timezone.utc).isoformat(timespec="seconds")
    shutil.move(str(src), str(target))
    with Image.open(target) as image:
        size = list(image.size)
    line = {
        "file": f"screenshots/{target.name}",
        "url": url,
        "taken_at": taken,
        "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
        "size": size,
        "region_frame": region,
        "note": note,
    }
    index = out_dir / "index.jsonl"
    old = index.read_text(encoding="utf-8").splitlines() if index.is_file() else []
    old = [l for l in old if l.strip() and json.loads(l).get("file") != line["file"]]
    old.append(json.dumps(line, ensure_ascii=False))
    index.write_text("\n".join(old) + "\n", encoding="utf-8", newline="\n")
    print("OK", target.name, size)


def main():
    if sys.argv[1] == "--list":
        for item in json.loads(Path(sys.argv[2]).read_text(encoding="utf-8")):
            keep(item["src"], item["name"], item["url"], item.get("note", ""), item.get("region"))
    else:
        region = [float(x) for x in sys.argv[5].split(",")] if len(sys.argv) > 5 else None
        keep(sys.argv[4], sys.argv[1], sys.argv[2], sys.argv[3], region)


if __name__ == "__main__":
    main()
