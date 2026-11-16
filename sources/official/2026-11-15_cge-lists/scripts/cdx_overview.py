"""Обзор справки CDX веб-архива по mcge.by/archives/* (сырая копия прежнего сбора, файл 345).

Запуск из корня проекта:
    python -I -X utf8 sources/official/2026-11-15_cge-lists/scripts/cdx_overview.py [путь к json]

Печатает: сколько адресов, диапазоны номеров записей, страницы архива по месяцам,
распределение меток времени. Ничего не скачивает.
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

DEFAULT = Path("sources/reviews/2026-11-15_official/raw/345_web-archive-org_wa-cdx-mcge-archives.json")


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT
    rows = json.loads(path.read_text(encoding="utf-8"))
    header, rows = rows[0], rows[1:]
    print("header:", header, "rows:", len(rows))
    posts, dates, other = [], [], []
    for original, timestamp, status, mime in rows:
        tail = original.split("/archives/", 1)[1] if "/archives/" in original else original
        if re.fullmatch(r"\d+/?", tail):
            posts.append((int(tail.strip("/")), timestamp, original))
        elif tail.startswith("date/"):
            dates.append((tail, timestamp, original))
        else:
            other.append((tail, timestamp, original))
    posts.sort()
    print("posts:", len(posts), "min id", posts[0][0], "max id", posts[-1][0])
    print("date pages:", len(dates))
    print("other:", len(other))
    print("--- capture years of posts:", sorted(Counter(t[:4] for _, t, _ in posts).items()))
    print("--- capture months of posts:", sorted(Counter(t[:6] for _, t, _ in posts).items()))
    print("--- date pages:")
    for tail, timestamp, original in sorted(dates):
        print(f"  {tail:40s} {timestamp} {original}")
    print("--- other (first 80):")
    for tail, timestamp, original in sorted(other)[:80]:
        print(f"  {tail[:90]:90s} {timestamp}")
    print("--- posts with id >= 1700:")
    for number, timestamp, original in posts:
        if number >= 1700:
            print(f"  {number:6d} {timestamp} {original}")


if __name__ == "__main__":
    main()
