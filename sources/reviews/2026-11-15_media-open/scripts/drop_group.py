"""Убирает ошибочно сохранённую группу: файлы media/<группа>/ и её строки в media/manifest.jsonl.

Запуск из корня проекта:
    python -I -X utf8 sources/reviews/2026-11-15_media-open/scripts/drop_group.py <группа>
Нужен, когда файл сохранён с неверным именем (например, без даты) и выгрузку сохраняют заново.
"""
import json
import shutil
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
group = sys.argv[1]
if "/" in group or "\\" in group or group in ("", ".", ".."):
    sys.exit("bad group name")
folder = BASE / "media" / group
if folder.is_dir():
    # OneDrive иногда держит саму папку: файлы удаляем, пустая папка может остаться
    shutil.rmtree(folder, ignore_errors=True)
manifest = BASE / "media" / "manifest.jsonl"
lines = [line for line in manifest.read_text(encoding="utf-8").splitlines() if line.strip()]
kept = [line for line in lines if json.loads(line)["group"] != group]
manifest.write_text("".join(line + "\n" for line in kept), encoding="utf-8", newline="\n")
print(f"dropped {len(lines) - len(kept)} manifest lines, folder removed: {group}")
