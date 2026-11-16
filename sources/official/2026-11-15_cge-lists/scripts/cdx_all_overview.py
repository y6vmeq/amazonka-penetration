"""Обзор полного перечня сохранённых в веб-архиве адресов сайта (ответ CDX в JSON).

Запуск из корня проекта:
    python -I -X utf8 sources/official/2026-11-15_cge-lists/scripts/cdx_all_overview.py <файл.json> [подстрока ...]

Без подстрок: число адресов по первому сегменту пути и типам содержимого.
С подстроками: все строки, где адрес содержит любую из них (без учёта регистра, адрес раскодирован).
"""
import json
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import unquote, urlsplit


def main():
    path = Path(sys.argv[1])
    needles = [needle.lower() for needle in sys.argv[2:]]
    rows = json.loads(path.read_text(encoding="utf-8"))
    header, rows = rows[0], rows[1:]
    print("header:", header, "rows:", len(rows))
    index = {name: position for position, name in enumerate(header)}
    if needles:
        for row in rows:
            original = unquote(row[index["original"]])
            if any(needle in original.lower() for needle in needles):
                print(row[index["timestamp"]], row[index["mimetype"]], row[index.get("length", 0)] if "length" in index else "", original[:230])
        return
    segments, mimes = Counter(), Counter()
    for row in rows:
        parts = urlsplit(row[index["original"]])
        first = parts.path.strip("/").split("/")[0] if parts.path.strip("/") else "(root)"
        if parts.query and first == "(root)":
            first = "(root)?" + parts.query.split("=")[0]
        segments[unquote(first)[:40]] += 1
        mimes[row[index["mimetype"]]] += 1
    print("mimetypes:", mimes.most_common(12))
    for name, count in segments.most_common(80):
        print(f"{count:6d} {name}")


if __name__ == "__main__":
    main()
