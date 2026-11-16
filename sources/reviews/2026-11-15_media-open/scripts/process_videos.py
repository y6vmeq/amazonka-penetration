"""Кадры и обзорные листы для каждого скачанного видео, у которого их ещё нет.

Запуск из корня проекта:
    python -I -X utf8 sources/reviews/2026-11-15_media-open/scripts/process_videos.py [--max-frames 24]

Вызывает tools/video_frames.py: кадры в media/<группа>/frames/<имя видео>/, листы в media/<группа>/sheets/.
Собирает также один обзорный лист overview_<имя>.jpg (12 кадров) на видео.
Размер кадра, длительность и наличие звука пишет в work/video_info.json.
"""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw

BASE = Path(__file__).resolve().parent.parent
ROOT = BASE.parent.parent.parent
WORK = BASE / "work"


def overview(frames_dir, out_path, n_frames=12, cols=6, cell=240):
    files = sorted(frames_dir.glob("t*.jpg"))
    if not files:
        return
    step = max(1, len(files) / n_frames)
    picked = list(dict.fromkeys(files[min(len(files) - 1, int(i * step))] for i in range(min(n_frames, len(files)))))
    first = Image.open(picked[0])
    cell_h = int(first.height * cell / first.width)
    rows = (len(picked) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cell, rows * (cell_h + 16)), "white")
    draw = ImageDraw.Draw(sheet)
    for i, path in enumerate(picked):
        image = Image.open(path).convert("RGB").resize((cell, cell_h))
        x, y = (i % cols) * cell, (i // cols) * (cell_h + 16)
        sheet.paste(image, (x, y + 16))
        draw.text((x + 4, y + 2), path.stem, fill="black")
    sheet.save(out_path, quality=85)


def main():
    max_frames = sys.argv[sys.argv.index("--max-frames") + 1] if "--max-frames" in sys.argv else "24"
    info_path = WORK / "video_info.json"
    info = json.loads(info_path.read_text(encoding="utf-8")) if info_path.is_file() else {}
    for video in sorted((BASE / "media").glob("*/*.mp4")):
        folder = video.parent
        sheets = folder / "sheets"
        if list(sheets.glob(f"sheet_{video.stem}_*.jpg")):
            continue
        frames_dir = folder / "frames"
        result = subprocess.run(
            [sys.executable, "-I", str(ROOT / "tools" / "video_frames.py"), str(frames_dir), str(video),
             "--max-frames", max_frames, "--min-step", "0.5"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        line = (result.stdout.strip().splitlines() or [""])[0]
        if result.returncode != 0:
            print(f"FAILED {video.name}: {result.stderr.strip()[-300:]}")
            continue
        sheets.mkdir(exist_ok=True)
        for sheet in frames_dir.glob(f"sheet_{video.stem}_*.jpg"):
            shutil.move(str(sheet), str(sheets / sheet.name))
        overview(frames_dir / video.stem, sheets / f"overview_{video.stem}.jpg")
        match = re.search(r"(\d+)x(\d+), dur=([\d.]+)s, rotation=(-?\d+), audio=(yes|no), frames=(\d+)", line)
        if match:
            info[video.relative_to(BASE).as_posix()] = {
                "width": int(match.group(1)), "height": int(match.group(2)), "duration": float(match.group(3)),
                "rotation": int(match.group(4)), "audio": match.group(5) == "yes", "frames": int(match.group(6)),
                "sheets": sorted(p.relative_to(BASE).as_posix() for p in sheets.glob(f"*{video.stem}*.jpg")),
            }
        print(line, flush=True)
    info_path.write_text(json.dumps(info, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
