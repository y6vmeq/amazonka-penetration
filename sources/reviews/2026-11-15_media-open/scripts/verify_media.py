"""Проверка папки media/ перед сдачей.

Запуск из корня проекта:
    python -I -X utf8 sources/reviews/2026-11-15_media-open/scripts/verify_media.py

Проверяет: каждый файл из media/manifest.jsonl есть на диске, размер и SHA-256 совпадают;
у каждого видео есть расшифровка, кадры и листы; в media/ нет исходных файлов вне журнала;
каждый файл упомянут в media.md. Результат — work/verify_result.txt.
"""
import hashlib
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
SOURCE_SUFFIXES = {".mp4", ".jpg", ".jpeg", ".png", ".webp"}
DERIVED_PARTS = {"frames", "sheets", "frames_start", "frames_amazonka", "frames_staff"}


def main():
    lines, problems = [], 0
    entries = [json.loads(line) for line in (BASE / "media" / "manifest.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    media_md = (BASE / "media.md").read_text(encoding="utf-8")
    listed = set()
    videos = images = 0
    for entry in entries:
        path = BASE / entry["file"]
        listed.add(path.resolve())
        if not path.is_file():
            problems += 1
            lines.append(f"MISSING {entry['file']}")
            continue
        data = path.read_bytes()
        if len(data) != entry["bytes"] or hashlib.sha256(data).hexdigest() != entry["sha256"]:
            problems += 1
            lines.append(f"CHANGED {entry['file']}")
        if entry["file"] not in media_md or entry["sha256"] not in media_md:
            problems += 1
            lines.append(f"NOT-IN-MEDIA-MD {entry['file']}")
        for field in ("group", "n", "url", "file", "bytes", "sha256", "fetched_at"):
            if entry.get(field) in (None, ""):
                problems += 1
                lines.append(f"EMPTY-FIELD {field} {entry['file']}")
        if path.suffix == ".mp4":
            videos += 1
            stem = path.with_suffix("")
            if not Path(str(stem) + ".transcript.txt").is_file():
                problems += 1
                lines.append(f"NO-TRANSCRIPT {entry['file']}")
            if not list((path.parent / "frames" / path.stem).glob("t*.jpg")):
                problems += 1
                lines.append(f"NO-FRAMES {entry['file']}")
            if not list((path.parent / "sheets").glob(f"*{path.stem}*.jpg")):
                problems += 1
                lines.append(f"NO-SHEETS {entry['file']}")
        else:
            images += 1
    for path in (BASE / "media").rglob("*"):
        if not path.is_file() or path.suffix.lower() not in SOURCE_SUFFIXES:
            continue
        if DERIVED_PARTS & set(path.relative_to(BASE / "media").parts[:-1]):
            continue
        if path.resolve() not in listed:
            problems += 1
            lines.append(f"UNLISTED {path.relative_to(BASE).as_posix()}")
    summary = f"files={len(entries)} videos={videos} images={images} groups={len({e['group'] for e in entries})} problems={problems}"
    lines.append(summary + (" -> PASS" if not problems else " -> FAIL"))
    (BASE / "work" / "verify_result.txt").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(lines[-12:]))


if __name__ == "__main__":
    main()
