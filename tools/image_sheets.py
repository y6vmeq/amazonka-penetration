"""Собирает обзорные листы из изображений, чтобы быстро просмотреть много фото.

Запуск из корня проекта:
    python -I tools/image_sheets.py <папка_с_медиа> <папка_для_листов> [--cols 4] [--rows 3]

Берёт все изображения в <папка_с_медиа> и её подпапках, раскладывает по
--cols × --rows на лист. Под каждой миниатюрой — путь к файлу относительно
<папка_с_медиа>: по нему потом открывают нужное фото в полном размере.
Листы: <папка_для_листов>/sheet_NNN.jpg; рядом sheets_index.tsv (лист, файл).
"""
import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
CELL = 360
LABEL_HEIGHT = 30


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("media_dir")
    parser.add_argument("out_dir")
    parser.add_argument("--cols", type=int, default=4)
    parser.add_argument("--rows", type=int, default=3)
    args = parser.parse_args()

    media_dir, out_dir = Path(args.media_dir), Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    files = sorted(
        path for path in media_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES and out_dir not in path.parents
    )
    per_sheet = args.cols * args.rows
    index_lines = []
    for start in range(0, len(files), per_sheet):
        sheet_number = start // per_sheet + 1
        sheet = Image.new("RGB", (args.cols * CELL, args.rows * (CELL + LABEL_HEIGHT)), "white")
        draw = ImageDraw.Draw(sheet)
        for position, path in enumerate(files[start:start + per_sheet]):
            x = (position % args.cols) * CELL
            y = (position // args.cols) * (CELL + LABEL_HEIGHT)
            label = path.relative_to(media_dir).as_posix()
            try:
                with Image.open(path) as image:
                    thumbnail = ImageOps.exif_transpose(image).convert("RGB")
                    thumbnail.thumbnail((CELL - 8, CELL - 8))
                    sheet.paste(thumbnail, (x + (CELL - thumbnail.width) // 2, y + LABEL_HEIGHT + (CELL - thumbnail.height) // 2))
            except OSError:
                label += " (не открылось)"
            draw.text((x + 6, y + 8), label[-52:], fill="black")
            index_lines.append(f"sheet_{sheet_number:03d}.jpg\t{label}")
        sheet.save(out_dir / f"sheet_{sheet_number:03d}.jpg", quality=85)
    (out_dir / "sheets_index.tsv").write_text("\n".join(index_lines) + "\n", encoding="utf-8", newline="\n")
    print(f"images={len(files)} sheets={(len(files) + per_sheet - 1) // per_sheet}")


if __name__ == "__main__":
    main()
