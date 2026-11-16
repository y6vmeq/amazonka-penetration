"""Плотные обзорные листы из уже снятых кадров (для быстрого просмотра многих видео).

Запуск: python -I scripts/dense_sheets.py <папка_с_кадрами tNNN.Ns.jpg> <выходной_файл.jpg> [--cols 6] [--cell 240] [--every 1] [--max 24]
Кадры берутся по порядку времени, каждый --every-й; на лист попадает не больше --max кадров
(если кадров больше, пишутся файлы <имя>_2.jpg, <имя>_3.jpg ...). Подпись — время кадра.
"""
import argparse
from pathlib import Path

from PIL import Image, ImageDraw

parser = argparse.ArgumentParser()
parser.add_argument("frames_dir")
parser.add_argument("out_file")
parser.add_argument("--cols", type=int, default=6)
parser.add_argument("--cell", type=int, default=240)
parser.add_argument("--every", type=int, default=1)
parser.add_argument("--max", type=int, default=24)
parser.add_argument("--title", default="")
args = parser.parse_args()

frames = sorted(Path(args.frames_dir).glob("t*.jpg"))[:: args.every]
out = Path(args.out_file)
out.parent.mkdir(parents=True, exist_ok=True)
LABEL = 16
for part, start in enumerate(range(0, len(frames), args.max), 1):
    chunk = frames[start:start + args.max]
    with Image.open(chunk[0]) as first:
        cell_h = int(first.height * args.cell / first.width)
    rows = (len(chunk) + args.cols - 1) // args.cols
    sheet = Image.new("RGB", (args.cols * args.cell, rows * (cell_h + LABEL)), "white")
    draw = ImageDraw.Draw(sheet)
    for index, path in enumerate(chunk):
        x, y = (index % args.cols) * args.cell, (index // args.cols) * (cell_h + LABEL)
        with Image.open(path) as image:
            sheet.paste(image.convert("RGB").resize((args.cell, cell_h)), (x, y + LABEL))
        draw.text((x + 4, y + 2), f"{args.title} {path.stem}", fill="black")
    target = out if part == 1 else out.with_name(f"{out.stem}_{part}{out.suffix}")
    sheet.save(target, quality=85)
    print(target.as_posix(), len(chunk))
