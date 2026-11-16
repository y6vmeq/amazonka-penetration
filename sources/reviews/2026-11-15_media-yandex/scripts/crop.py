"""Вырезает и увеличивает фрагмент фото (для чтения текста и мелких деталей).

Запуск из корня проекта:
    python -I sources/reviews/2026-11-15_media-yandex/scripts/crop.py <файл> <имя_вырезки> <x0> <y0> <x1> <y1> [--scale N] [--max N] [--contrast K] [--gray] [--rotate G] [--out ПАПКА]

Координаты — доли ширины и высоты (0..1) после исправления ориентации по EXIF.
По умолчанию вырезка сохраняется в crops/ своей папки. Исходный файл только читается.
--max ограничивает большую сторону результата (по умолчанию 1500), --scale — увеличение.
"""
import argparse
from pathlib import Path

from PIL import Image, ImageEnhance, ImageOps

OWN = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source")
    parser.add_argument("name")
    parser.add_argument("box", nargs=4, type=float)
    parser.add_argument("--scale", type=float, default=1.0)
    parser.add_argument("--max", type=int, default=1500)
    parser.add_argument("--contrast", type=float, default=1.0)
    parser.add_argument("--brightness", type=float, default=1.0)
    parser.add_argument("--gray", action="store_true")
    parser.add_argument("--autocontrast", action="store_true")
    parser.add_argument("--rotate", type=float, default=0.0)
    parser.add_argument("--out", default=str(OWN / "crops"))
    args = parser.parse_args()

    with Image.open(args.source) as image:
        picture = ImageOps.exif_transpose(image).convert("RGB")
    width, height = picture.size
    x0, y0, x1, y1 = args.box
    fragment = picture.crop((int(x0 * width), int(y0 * height), int(x1 * width), int(y1 * height)))
    if args.rotate:
        fragment = fragment.rotate(args.rotate, expand=True, resample=Image.BICUBIC)
    if args.scale != 1.0:
        fragment = fragment.resize((int(fragment.width * args.scale), int(fragment.height * args.scale)), Image.LANCZOS)
    if max(fragment.size) > args.max:
        fragment.thumbnail((args.max, args.max), Image.LANCZOS)
    if args.gray:
        fragment = ImageOps.grayscale(fragment).convert("RGB")
    if args.autocontrast:
        fragment = ImageOps.autocontrast(fragment, cutoff=1)
    if args.brightness != 1.0:
        fragment = ImageEnhance.Brightness(fragment).enhance(args.brightness)
    if args.contrast != 1.0:
        fragment = ImageEnhance.Contrast(fragment).enhance(args.contrast)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / f"{args.name}.jpg"
    fragment.save(target, quality=92)
    print(f"{target.as_posix()}\t{fragment.size[0]}x{fragment.size[1]} (источник {width}x{height})")


if __name__ == "__main__":
    main()
