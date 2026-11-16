"""Собирает лист из нескольких фото крупными ячейками (для просмотра группами по 4–6).

Запуск из корня проекта:
    python -I sources/reviews/2026-11-15_media-yandex/scripts/quad.py <выходной.jpg> <cols> <cell> <файл> [<файл> ...]

Листы пишутся во временную папку. Исходные файлы только читаются. Подпись — путь к файлу.
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

LABEL = 22


def main():
    target = Path(sys.argv[1])
    cols = int(sys.argv[2])
    cell = int(sys.argv[3])
    files = [Path(name) for name in sys.argv[4:]]
    rows = (len(files) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cell, rows * (cell + LABEL)), "white")
    draw = ImageDraw.Draw(sheet)
    for position, path in enumerate(files):
        x = (position % cols) * cell
        y = (position // cols) * (cell + LABEL)
        with Image.open(path) as image:
            picture = ImageOps.exif_transpose(image).convert("RGB")
        picture.thumbnail((cell - 6, cell - 6), Image.LANCZOS)
        sheet.paste(picture, (x + (cell - picture.width) // 2, y + LABEL + (cell - picture.height) // 2))
        draw.text((x + 4, y + 5), f"{path.parent.name}/{path.name}", fill="black")
    target.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(target, quality=88)
    print(f"{target.as_posix()}\t{sheet.size[0]}x{sheet.size[1]}\t{len(files)} фото")


if __name__ == "__main__":
    main()
