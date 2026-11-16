"""Сводка по просмотренным записям телеграм-канала (tg_scan_posts.jsonl и tg_posts.jsonl).

Запуск из корня проекта:
    python -I -X utf8 sources/official/2026-11-15_cge-lists/scripts/tg_scan_report.py [ids]

Без параметров: объявления о списках просроченных товаров (по словам в тексте) и охват просмотра.
С параметром ids: все пары «дата записи — номер страницы mcge.by/archives/N» (для оценки,
в каком диапазоне номеров лежит страница нужного месяца).
"""
import json
import re
import sys
from pathlib import Path

FOLDER = Path("sources/official/2026-11-15_cge-lists")


def load():
    posts = {}
    for name in ("tg_posts.jsonl", "tg_scan_posts.jsonl"):
        path = FOLDER / name
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                post = json.loads(line)
                posts.setdefault(post["post"], post)
    return sorted(posts.values(), key=lambda item: int(item["post"].split("/")[1]))


def main():
    posts = load()
    numbers = [int(post["post"].split("/")[1]) for post in posts]
    print("posts known:", len(posts), "range", min(numbers), "..", max(numbers))
    scanned = FOLDER / "tg_scanned.jsonl"
    if scanned.is_file():
        rows = [json.loads(line) for line in scanned.read_text(encoding="utf-8").splitlines() if line.strip()]
        print("scan pages:", len(rows), "lowest post reached:", min(row["min"] for row in rows),
              "highest:", max(row["max"] for row in rows))
    if len(sys.argv) > 1 and sys.argv[1] == "ids":
        for post in posts:
            ids = sorted({int(match) for link in post.get("links", [])
                          for match in re.findall(r"mcge\.by/archives/(\d+)", link)})
            if ids:
                first = " ".join(post.get("text", "").split())[:110]
                print(f"{post['time'][:10] if post.get('time') else '?'} {post['post'].split('/')[1]:>5} {ids} {first}")
        return
    for post in posts:
        text = (post.get("text", "") + " " + post.get("preview", "")).lower()
        if not (("истекш" in text or "просроч" in text or "годност" in text) and ("торгов" in text or "объект" in text)):
            continue
        ids = sorted({int(match) for link in post.get("links", []) for match in re.findall(r"mcge\.by/archives/(\d+)", link)})
        lines = [line.strip() for line in post.get("text", "").splitlines() if line.strip()]
        key = [line for line in lines if re.search(r"(?i)за\s+[а-я]+\s+(?:месяц\s+)?20\d\d|квартал|полугод", line)]
        print(f"{post['time'][:10] if post.get('time') else '?'} {post['post']:22s} ids={ids}")
        for line in (key or lines[:2]):
            print("      " + line[:230])


if __name__ == "__main__":
    main()
