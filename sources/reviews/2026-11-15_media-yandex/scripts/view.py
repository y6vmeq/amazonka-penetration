"""Делает уменьшенные копии фото для просмотра (во временной папке, не в проекте).

Запуск из корня проекта:
    python -I sources/reviews/2026-11-15_media-yandex/scripts/view.py <временная_папка> <макс_сторона> <файл> [<файл> ...]

Исходные файлы только читаются. Ориентация исправляется по EXIF.
Имя копии: <папка-источник>_<имя>.jpg.
"""
import sys
from pathlib import Path

from PIL import Image, ImageOps


def main():
    out_dir = Path(sys.argv[1])
    max_side = int(sys.argv[2])
    out_dir.mkdir(parents=True, exist_ok=True)
    for name in sys.argv[3:]:
        source = Path(name)
        with Image.open(source) as image:
            picture = ImageOps.exif_transpose(image).convert("RGB")
            original = picture.size
            picture.thumbnail((max_side, max_side), Image.LANCZOS)
            target = out_dir / f"{source.parent.name}_{source.stem}.jpg"
            picture.save(target, quality=88)
            print(f"{target.as_posix()}\t{original[0]}x{original[1]} -> {picture.size[0]}x{picture.size[1]}")


if __name__ == "__main__":
    main()
