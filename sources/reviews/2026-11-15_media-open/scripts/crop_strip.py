"""Вырезает один и тот же прямоугольник из нескольких кадров и ставит вырезки в ряд (для сравнения).

Запуск из корня проекта:
    python -I -X utf8 sources/reviews/2026-11-15_media-open/scripts/crop_strip.py <выход.jpg> <x1,y1,x2,y2> <масштаб> <кадр...>
Подпись над вырезкой — имя кадра (в нём время). Исходные кадры не меняются.
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw

out, box, scale = sys.argv[1], tuple(int(v) for v in sys.argv[2].split(",")), float(sys.argv[3])
frames = [Path(p) for p in sys.argv[4:]]
crops = []
for path in frames:
    with Image.open(path) as image:
        crop = image.convert("RGB").crop(box)
        crops.append(crop.resize((int(crop.width * scale), int(crop.height * scale)), Image.LANCZOS))
width = sum(c.width for c in crops) + 6 * (len(crops) - 1)
sheet = Image.new("RGB", (width, crops[0].height + 18), "white")
draw = ImageDraw.Draw(sheet)
x = 0
for path, crop in zip(frames, crops):
    sheet.paste(crop, (x, 18))
    draw.text((x + 4, 3), path.stem, fill="black")
    x += crop.width + 6
Path(out).parent.mkdir(parents=True, exist_ok=True)
sheet.save(out, quality=90)
print(out, sheet.size)
