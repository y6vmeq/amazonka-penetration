"""Печатает таблицу «публикация → папка → файлы → длительность» по журналу файлов.

Запуск из корня проекта:
    python -I -X utf8 sources/reviews/2026-11-15_media-open/scripts/table_publications.py
Пишет ту же таблицу в work/table_publications.md.
"""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
MINSK = timezone(timedelta(hours=3))


def main():
    info = json.loads((BASE / "work" / "video_info.json").read_text(encoding="utf-8"))
    order = []
    for path in sorted((BASE / "work").glob("notes_*.json")):
        order += list(json.loads(path.read_text(encoding="utf-8")))
    pages = {}
    for path in (BASE / "work" / "pages").glob("*.json"):
        page = json.loads(path.read_text(encoding="utf-8"))
        meta = page.get("meta") or {}
        key = f"{page.get('platform')}:{meta.get('code')}"
        if path.stem.endswith(str(meta.get("code"))):
            pages[key] = page
    groups = {}
    for line in (BASE / "media" / "manifest.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            entry = json.loads(line)
            groups.setdefault(entry["group"], []).append(entry)
    rows = ["| № | Публикация | Автор, дата | Папка в `media/` | Файлы | Длительность |", "|---|---|---|---|---|---|"]
    total_seconds = 0.0
    for number, key in enumerate(order, 1):
        page = pages[key]
        meta = page["meta"]
        entries = groups[page["group"]]
        videos = [e for e in entries if e["file"].endswith(".mp4")]
        images = len(entries) - len(videos)
        durations = [info[e["file"]]["duration"] for e in videos]
        total_seconds += sum(durations)
        parts = []
        if videos:
            parts.append(f"{len(videos)} видео")
        if images:
            parts.append(f"{images} фото")
        stamp = meta.get("taken_at")
        if stamp:
            date = datetime.fromtimestamp(int(stamp), timezone.utc).astimezone(MINSK).strftime("%d.%m.%Y")
        else:
            date = datetime.fromisoformat(page["published_utc"]).astimezone(MINSK).strftime("%d.%m.%Y")
        platform = "Threads" if key.startswith("threads") else "Instagram"
        code = key.split(":", 1)[1]
        rows.append(f"| {number} | {platform} `{code}` | `{meta.get('owner')}`, {date} | `{page['group']}` | {', '.join(parts)} | "
                    f"{', '.join(str(d).replace('.', ',') + ' с' for d in durations) or '—'} |")
    rows.append("")
    rows.append(f"Всего видео: {sum(1 for g in groups.values() for e in g if e['file'].endswith('.mp4'))}, "
                f"общая длительность {total_seconds:.0f} с; фото: {sum(1 for g in groups.values() for e in g if not e['file'].endswith('.mp4'))}.")
    text = "\n".join(rows) + "\n"
    (BASE / "work" / "table_publications.md").write_text(text, encoding="utf-8", newline="\n")
    print(text)


if __name__ == "__main__":
    main()
