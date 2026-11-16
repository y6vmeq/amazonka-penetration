"""Уменьшенная копия снимка для просмотра (исходник не меняется).

Запуск: python -I scripts/preview.py <папка_сбора> <макс_сторона> <файл относительно media/> [...]
Копии пишутся в work/preview/<группа>__<имя>.jpg
"""
import sys
from pathlib import Path

from PIL import Image, ImageOps

collection = Path(sys.argv[1])
side = int(sys.argv[2])
out_dir = collection / "work" / "preview"
out_dir.mkdir(parents=True, exist_ok=True)
for relative in sys.argv[3:]:
    source = collection / "media" / relative
    with Image.open(source) as image:
        image = ImageOps.exif_transpose(image).convert("RGB")
        image.thumbnail((side, side))
        target = out_dir / (relative.replace("/", "__").rsplit(".", 1)[0] + ".jpg")
        image.save(target, quality=88)
        print(target.as_posix(), image.size)
