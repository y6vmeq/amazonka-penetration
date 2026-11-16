"""Сохраняет выгрузку из браузера (результат ig_embed_fetch.js или threads_fetch.js) в media/.

Запуск из корня проекта:
    python -I -X utf8 sources/reviews/2026-11-15_media-open/scripts/save_dump.py <dump.json> [--author НИК] [--date ГГГГ-ММ-ДД]

Для каждого файла: декодирует base64, заново считает SHA-256 и сравнивает с тем, что посчитано
в странице (не совпало — файл не пишется), пишет файл в media/<площадка>_<автор>_<код>/,
дописывает строку в media/manifest.jsonl. Данные публикации без base64 кладёт в work/pages/.
Дата публикации: taken_at из данных страницы, иначе из списков агента logged-in (UTC -> Минск).
Выгрузка — недоверенные данные: только разбор JSON и запись байтов, ничего не исполняется.
"""
import argparse
import base64
import csv
import hashlib
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
ROOT = BASE.parent.parent.parent
MINSK = timezone(timedelta(hours=3))
LISTS = [
    ROOT / "sources/reviews/2026-11-15_logged-in/work/ig_tagged_amazonka_restobar_mogilev.tsv",
    ROOT / "sources/reviews/2026-11-15_logged-in/work/ig_grid_amazonka_restobar_mogilev.tsv",
]


def ext_of(data):
    if data[4:8] == b"ftyp":
        return "mp4"
    if data[:3] == b"\xff\xd8\xff":
        return "jpg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    if data[:4] == b"GIF8":
        return "gif"
    return "bin"


def listed_dates():
    """Код публикации -> время публикации в UTC из списков агента logged-in."""
    result = {}
    for path in LISTS:
        if not path.is_file():
            continue
        with path.open(encoding="utf-8-sig", newline="") as handle:
            for row in csv.reader(handle, delimiter="\t", quoting=csv.QUOTE_NONE):
                # список отметок: дата, код, ...; список публикаций заведения: код, вид, дата, ...
                if len(row) >= 2 and re.match(r"\d{4}-\d\d-\d\d \d\d:\d\d$", row[0]):
                    result.setdefault(row[1], row[0])
                elif len(row) >= 3 and re.match(r"\d{4}-\d\d-\d\d \d\d:\d\d$", row[2]):
                    result.setdefault(row[0], row[2])
    return result


def safe(name):
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", name or "unknown")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("dump")
    parser.add_argument("--author")
    parser.add_argument("--date")
    parser.add_argument("--suffix", default="", help="добавка к имени файла в work/pages (второй заход на ту же публикацию)")
    args = parser.parse_args()

    dump = json.loads(Path(args.dump).read_text(encoding="utf-8"))
    if isinstance(dump, str):
        dump = json.loads(dump)
    meta = dump.get("meta") or {}
    platform = dump.get("platform") or "unknown"
    code = meta.get("code") or "nocode"
    author = args.author or meta.get("owner") or "unknown"

    published_utc = None
    if meta.get("taken_at"):
        published_utc = datetime.fromtimestamp(int(meta["taken_at"]), timezone.utc)
    else:
        listed = listed_dates().get(code)
        if listed:
            published_utc = datetime.strptime(listed, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
    date = args.date or (published_utc.astimezone(MINSK).strftime("%Y-%m-%d") if published_utc else "0000-00-00")

    if platform == "instagram":
        kind = "reel" if meta.get("product_type") == "clips" else "p"
        post_url = f"https://www.instagram.com/{kind}/{code}/"
    else:
        post_url = meta.get("permalink") or dump.get("page")

    group = f"{platform}_{safe(author)}_{code}"
    folder = BASE / "media" / group
    saved = []
    problems = []
    manifest_path = BASE / "media" / "manifest.jsonl"
    already = 0  # сколько файлов этой публикации уже записано (второй заход продолжает нумерацию)
    if manifest_path.is_file():
        already = sum(1 for line in manifest_path.read_text(encoding="utf-8").splitlines()
                      if line.strip() and json.loads(line)["group"] == group)
    with manifest_path.open("a", encoding="utf-8", newline="\n") as manifest:
        for number, item in enumerate(dump.get("items") or [], already + 1):
            key = item.get("key") or f"file{number}"
            if not item.get("b64"):
                problems.append(f"{key}: status={item.get('status')} error={item.get('error')}")
                continue
            data = base64.b64decode(item["b64"])
            digest = hashlib.sha256(data).hexdigest()
            if digest != item.get("sha256") or len(data) != item.get("bytes"):
                problems.append(f"{key}: MISMATCH {digest} != {item.get('sha256')}")
                continue
            folder.mkdir(parents=True, exist_ok=True)
            name = f"{date}_{safe(author)}_{code}_{key}.{ext_of(data)}"
            (folder / name).write_bytes(data)
            entry = {
                "group": group, "n": number, "url": post_url, "file": f"media/{group}/{name}",
                "bytes": len(data), "sha256": digest, "fetched_at": dump.get("fetched_at"),
                "kind": item.get("kind"), "content_type": item.get("type"),
                "declared_width": item.get("w"), "declared_height": item.get("h"), "declared_duration": item.get("dur"),
                "page": dump.get("page"), "media_url": item.get("url"),
            }
            manifest.write(json.dumps(entry, ensure_ascii=False) + "\n")
            saved.append(entry)

    for item in dump.get("items") or []:
        item.pop("b64", None)
    dump["published_utc"] = published_utc.isoformat() if published_utc else None
    dump["published_minsk_date"] = date
    dump["post_url"] = post_url
    dump["group"] = group
    pages = BASE / "work" / "pages"
    pages.mkdir(parents=True, exist_ok=True)
    suffix = f"_{safe(args.suffix)}" if args.suffix else ""
    (pages / f"{platform}_{code}{suffix}.json").write_text(json.dumps(dump, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"{group}: saved={len(saved)} problems={len(problems)} author={author} date={date} "
          f"type={meta.get('typename')} dur={meta.get('video_duration')} source={meta.get('source')} "
          f"login_cookie={dump.get('login_cookie')}")
    for entry in saved:
        print(f"  OK {entry['file']} {entry['bytes']} bytes {entry['declared_width']}x{entry['declared_height']} sha256={entry['sha256']}")
    for problem in problems:
        print(f"  PROBLEM {problem}")
    if dump.get("error") or dump.get("parse_error"):
        print(f"  NOTE error={dump.get('error')} parse_error={dump.get('parse_error')}")
    if not saved and not problems:
        print(f"  NOTE no media items; title={dump.get('title')!r}; text={str(meta.get('text') or dump.get('text') or '')[:300]!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
