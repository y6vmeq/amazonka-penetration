"""Для каждой группы в media/ снимает кадры с лучшего по разрешению видео и готовит список для расшифровки.

Запуск из корня проекта:
    python -I <папка_сбора>/scripts/process_videos.py <папка_сбора> [шаблон группы ...]
Кадры: media/<группа>/frames/<имя видео>/tNNN.Ns.jpg, листы: media/<группа>/frames/sheet_*.jpg
(их делает tools/video_frames.py). Группы, где папка frames уже есть, пропускаются.
Печатает список видео для расшифровки (вариант h264, если он есть).
Видеофайлы только читаются библиотекой PyAV, не исполняются.
"""
import fnmatch
import math
import subprocess
import sys
from pathlib import Path

import av

collection = Path(sys.argv[1])
patterns = sys.argv[2:] or ["*"]
media = collection / "media"
tools = Path("tools")
to_transcribe = []
for group_dir in sorted(p for p in media.iterdir() if p.is_dir() and not p.name.startswith("_")):
    if not any(fnmatch.fnmatch(group_dir.name, pattern) for pattern in patterns):
        continue
    videos = sorted(p for p in group_dir.iterdir() if p.suffix.lower() in (".mp4", ".webm", ".mov", ".mkv"))
    if not videos:
        continue
    info = []
    for video in videos:
        with av.open(str(video)) as container:
            stream = container.streams.video[0]
            duration = float(container.duration / av.time_base) if container.duration else 0.0
            info.append((stream.width * stream.height, video, duration, stream.codec_context.name, bool(container.streams.audio)))
    info.sort(key=lambda item: item[0], reverse=True)
    best = info[0]
    h264 = next((item for item in info if item[3] == "h264"), best)
    if not (h264[1].with_suffix("").parent / (h264[1].stem + ".transcript.txt")).exists():
        to_transcribe.append(h264[1])
    frames_dir = group_dir / "frames"
    if frames_dir.exists():
        print(f"{group_dir.name}: frames есть, пропуск")
        continue
    duration = best[2]
    if duration <= 20:
        max_frames, min_step = max(8, math.ceil(duration * 2)), 0.5
    elif duration <= 48:
        max_frames, min_step = math.ceil(duration), 1.0
    elif duration <= 150:
        max_frames, min_step = 48, 1.0
    else:
        max_frames, min_step = 64, 1.0
    result = subprocess.run(
        [sys.executable, "-I", str(tools / "video_frames.py"), str(frames_dir), str(best[1]),
         "--max-frames", str(max_frames), "--min-step", str(min_step)],
        capture_output=True, text=True,
    )
    line = (result.stdout.strip().splitlines() or ["?"])[0]
    print(f"{group_dir.name}: {line}" + (f" ERR {result.stderr.strip()[-200:]}" if result.returncode else ""), flush=True)

list_path = collection / "work" / "to_transcribe.txt"
list_path.write_text("\n".join(p.as_posix() for p in to_transcribe) + "\n", encoding="utf-8")
print("to_transcribe", len(to_transcribe), "->", list_path.as_posix())
