"""Выписывает из EXIF каждого фото дату съёмки, модель камеры и признак наличия GPS (без координат).

Запуск из корня проекта:
    python -I sources/reviews/2026-11-15_media-yandex/scripts/exif_dates.py

Читает photo_index.json, исходные файлы только читает, пишет exif_dates.tsv в свою папку.
Координаты GPS не выписываются: только отметка, есть ли они в файле.
"""
import json
from pathlib import Path

from PIL import Image

OWN = Path(__file__).resolve().parents[1]
ROOT = Path(__file__).resolve().parents[4]


def main():
    rows = json.loads((OWN / "photo_index.json").read_text(encoding="utf-8"))
    lines = ["file\tsource_record\tdate\texif_datetime_original\texif_datetime\tmake\tmodel\tsoftware\thas_gps"]
    with_date = 0
    for row in rows:
        if not row.get("file"):
            continue
        try:
            with Image.open(ROOT / row["file"]) as image:
                exif = image.getexif()
                sub = exif.get_ifd(0x8769) if exif else {}
                original = sub.get(36867) or sub.get(36868) or ""
                stamp = exif.get(306, "") if exif else ""
                make = str(exif.get(271, "") or "").strip() if exif else ""
                model = str(exif.get(272, "") or "").strip() if exif else ""
                software = str(exif.get(305, "") or "").strip() if exif else ""
                has_gps = bool(exif.get_ifd(0x8825)) if exif else False
        except Exception as error:  # файл не читается как изображение с EXIF
            original, stamp, make, model, software, has_gps = "", "", "", "", f"ERR {error}", False
        if original or stamp:
            with_date += 1
        lines.append("\t".join([row["file"], row.get("source_record") or "", row.get("date") or "",
                                str(original), str(stamp), make, model, software, "да" if has_gps else ""]))
    (OWN / "exif_dates.tsv").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("files", len(lines) - 1, "with exif date", with_date)


if __name__ == "__main__":
    main()
