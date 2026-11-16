"""Frames and contact sheets for every downloaded video that has none yet.

Usage (from project root): python -I <scripts>/process_videos.py [--max-frames 24]
Uses tools/video_frames.py; frames go to <media folder>/frames/<video name>/, sheets to <media folder>/sheets/.
Prints one line per video: size, duration, audio, frames. Appends the facts to work/video_info.json.
"""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
BASE = Path(__file__).resolve().parent.parent
ROOT = BASE.parent.parent.parent
WORK = BASE / "work"


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
        m = re.search(r"(\d+)x(\d+), dur=([\d.]+)s, rotation=(-?\d+), audio=(yes|no), frames=(\d+)", line)
        if m:
            info[video.relative_to(BASE).as_posix()] = {
                "width": int(m.group(1)), "height": int(m.group(2)), "duration": float(m.group(3)),
                "audio": m.group(5) == "yes", "frames": int(m.group(6)),
                "sheets": sorted(p.relative_to(BASE).as_posix() for p in sheets.glob(f"sheet_{video.stem}_*.jpg")),
            }
        print(line)
    info_path.write_text(json.dumps(info, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
