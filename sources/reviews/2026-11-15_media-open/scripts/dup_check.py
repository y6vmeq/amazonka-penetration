"""Ищет среди скачанных в этом проходе файлов побайтные дубли файлов, уже лежащих в проекте.

Запуск из корня проекта:
    python -I -X utf8 sources/reviews/2026-11-15_media-open/scripts/dup_check.py

Считает SHA-256 всех видео и изображений в sources/**/media/ (кроме папки этого прохода и
кадров/листов) и сравнивает с media/manifest.jsonl этого прохода. Результат — work/dup_check.json.
"""
import hashlib
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
ROOT = BASE.parent.parent.parent
SUFFIXES = {".mp4", ".jpg", ".jpeg", ".png", ".webp", ".mov", ".webm"}
SKIP_PARTS = {"frames", "sheets", "frames_hall", "sheets_hall", "_preview"}


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    mine = {}
    for line in (BASE / "media" / "manifest.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            entry = json.loads(line)
            mine[entry["sha256"]] = entry["file"]
    sizes = {(BASE / rel).stat().st_size for rel in mine.values()}
    found = {}
    checked = 0
    for media_dir in (ROOT / "sources").rglob("media"):
        if not media_dir.is_dir() or BASE in media_dir.parents or media_dir == BASE / "media":
            continue
        for path in media_dir.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in SUFFIXES:
                continue
            if SKIP_PARTS & set(path.relative_to(media_dir).parts[:-1]):
                continue
            if path.stat().st_size not in sizes:  # размер не совпал — дублем быть не может
                continue
            checked += 1
            value = digest(path)
            if value in mine:
                found.setdefault(mine[value], []).append(path.relative_to(ROOT).as_posix())
    (BASE / "work" / "dup_check.json").write_text(json.dumps(found, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"my files: {len(mine)}; candidates hashed: {checked}; duplicates: {len(found)}")
    for mine_file, others in sorted(found.items()):
        print(f"  {mine_file}\n    == {'; '.join(others)}")


if __name__ == "__main__":
    main()
