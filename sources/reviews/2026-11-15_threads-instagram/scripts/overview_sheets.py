"""Make one compact overview sheet per video from already extracted frames.

Usage: python -I <scripts>/overview_sheets.py [--frames 12] [--cols 6] [--cell 240] [name-substring ...]
Reads media/*/frames/<video name>/t*.jpg, writes media/*/sheets/overview_<video name>.jpg
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw

BASE = Path(__file__).resolve().parent.parent


def opt(name, default):
    return int(sys.argv[sys.argv.index(name) + 1]) if name in sys.argv else default


def main():
    n_frames, cols, cell = opt("--frames", 12), opt("--cols", 6), opt("--cell", 240)
    filters = [a for a in sys.argv[1:] if not a.startswith("--") and not a.isdigit()]
    for frames_dir in sorted((BASE / "media").glob("*/frames/*")):
        if not frames_dir.is_dir():
            continue
        if filters and not any(f in frames_dir.as_posix() for f in filters):
            continue
        out = frames_dir.parent.parent / "sheets" / f"overview_{frames_dir.name}.jpg"
        if out.exists() and "--force" not in sys.argv:
            continue
        files = sorted(frames_dir.glob("t*.jpg"))
        if not files:
            continue
        step = max(1, len(files) / n_frames)
        picked = [files[min(len(files) - 1, int(i * step))] for i in range(min(n_frames, len(files)))]
        picked = list(dict.fromkeys(picked))
        first = Image.open(picked[0])
        cell_h = int(first.height * cell / first.width)
        rows = (len(picked) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * cell, rows * (cell_h + 16)), "white")
        draw = ImageDraw.Draw(sheet)
        for i, f in enumerate(picked):
            im = Image.open(f).convert("RGB").resize((cell, cell_h))
            x, y = (i % cols) * cell, (i // cols) * (cell_h + 16)
            sheet.paste(im, (x, y + 16))
            draw.text((x + 4, y + 2), f.stem, fill="black")
        out.parent.mkdir(exist_ok=True)
        sheet.save(out, quality=85)
        print(out.relative_to(BASE).as_posix(), len(picked))


if __name__ == "__main__":
    main()
