"""Снимает кадры из видеофайлов без браузера и ffmpeg (через PyAV) и собирает обзорные листы.

Запуск из корня проекта:
    python -I tools/video_frames.py <папка_вывода> <видео...> [--max-frames 16] [--min-step 1.0]
                                    [--start 42 --end 47]

Кадры берутся равномерно: шаг = max(min-step, длительность / max-frames).
С --start и --end кадры берутся только из этого отрезка (в секундах): так можно
плотно снять короткий фрагмент.
Раскладку по файлам и листы делает tools/frames_to_sheets.py: кадры попадают в
<папка_вывода>/<имя видео>/tNNN.Ns.jpg, листы — в <папка_вывода>/sheet_<имя>_NN.jpg.
Для каждого видео печатается размер кадра, длительность, поворот и наличие звука.
"""
import argparse
import base64
import io
import json
import subprocess
import sys
from pathlib import Path

import av

JPEG_QUALITY = 88


def grab_frames(path, max_frames, min_step, start, end):
    """Возвращает (выгрузка в формате frames_to_sheets.py, есть ли звук, поворот в градусах)."""
    with av.open(str(path)) as container:
        stream = container.streams.video[0]
        has_audio = bool(container.streams.audio)
        duration = float(container.duration / av.time_base) if container.duration else 0.0
        span = max((min(end, duration) if end else duration) - start, 0.0)
        step = max(min_step, span / max_frames) if span else min_step
        frames, next_time, rotation = [], start, 0
        for frame in container.decode(stream):
            time = frame.time or 0.0
            if end and time > end:
                break
            if time + 1e-6 < next_time:
                continue
            image = frame.to_image()
            rotation = getattr(frame, "rotation", 0) or 0
            if rotation:
                image = image.rotate(rotation, expand=True)
            buffer = io.BytesIO()
            image.save(buffer, "JPEG", quality=JPEG_QUALITY)
            frames.append({"t": round(time, 1), "b64": base64.b64encode(buffer.getvalue()).decode("ascii")})
            next_time = time + step
        dump = {"name": path.stem, "W": stream.width, "H": stream.height, "dur": duration, "frames": frames}
        return dump, has_audio, rotation


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("out_dir")
    parser.add_argument("videos", nargs="+")
    parser.add_argument("--max-frames", type=int, default=16)
    parser.add_argument("--min-step", type=float, default=1.0)
    parser.add_argument("--start", type=float, default=0.0, help="с какой секунды брать кадры")
    parser.add_argument("--end", type=float, default=0.0, help="по какую секунду; 0 — до конца")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    dumps = {}
    for video in args.videos:
        dump, has_audio, rotation = grab_frames(
            Path(video), args.max_frames, args.min_step, args.start, args.end
        )
        dumps[dump["name"]] = dump
        print(
            f"{dump['name']}: {dump['W']}x{dump['H']}, dur={dump['dur']:.1f}s, "
            f"rotation={rotation}, audio={'yes' if has_audio else 'no'}, frames={len(dump['frames'])}",
            flush=True,
        )

    dump_path = out_dir / "_frames_dump.json"
    dump_path.write_text(json.dumps(dumps), encoding="utf-8")
    try:
        subprocess.run(
            [sys.executable, "-I", str(Path(__file__).with_name("frames_to_sheets.py")), str(out_dir), str(dump_path)],
            check=True,
        )
    finally:
        dump_path.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
