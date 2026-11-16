"""Переименовывает в media/manifest.jsonl поля width/height/duration в declared_*.

Запуск из корня проекта:
    python -I -X utf8 sources/reviews/2026-11-15_media-open/scripts/manifest_rename_fields.py

Причина: это размеры и длительность, заявленные площадкой в данных страницы, а не свойства
сохранённого файла (площадка отдаёт видео в меньшем разрешении). Фактический размер кадра и
длительность — в work/video_info.json и в media.md. Остальные поля и порядок строк не меняются.
"""
import json
from pathlib import Path

path = Path(__file__).resolve().parent.parent / "media" / "manifest.jsonl"
RENAME = {"width": "declared_width", "height": "declared_height", "duration": "declared_duration"}
lines = []
changed = 0
for line in path.read_text(encoding="utf-8").splitlines():
    if not line.strip():
        continue
    entry = json.loads(line)
    renamed = {}
    for key, value in entry.items():
        if key in RENAME:
            changed += 1
        renamed[RENAME.get(key, key)] = value
    lines.append(json.dumps(renamed, ensure_ascii=False))
path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
print(f"lines={len(lines)} renamed_fields={changed}")
