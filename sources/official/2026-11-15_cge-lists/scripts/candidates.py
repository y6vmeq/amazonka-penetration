"""Для месяцев, по которым адрес списка не найден, оценивает диапазон номеров страниц mcge.by.

Запуск из корня проекта:
    python -I -X utf8 sources/official/2026-11-15_cge-lists/scripts/candidates.py

Логика (это ОЦЕНКА, а не установленный факт):
  * номера записей сайта растут со временем;
  * записи телеграм-канала со ссылкой на mcge.by/archives/N дают пары «дата — номер»;
  * список за месяц М публикуется обычно с 5-го по 28-е число месяца М+1;
  * значит, номер страницы списка лежит между номерами, привязанными к датам до и после этого окна.
В диапазоне печатаются номера, копии которых есть в веб-архиве (справка CDX), с пометкой,
о чём страница, если это известно из телеграм-канала. Результат пишется в candidates.json.
"""
import json
import re
from datetime import date
from pathlib import Path

FOLDER = Path("sources/official/2026-11-15_cge-lists")
CDX = Path("sources/reviews/2026-11-15_official/raw/345_web-archive-org_wa-cdx-mcge-archives.json")
KNOWN = {
    "2023-11": [1786], "2024-02": [2007], "2024-03": [2133], "2024-06": [2392], "2024-07": [2591],
    "2024-08": [2678], "2025-04": [3891], "2025-05": [4051], "2025-06": [4193], "2025-08": [4401],
    "2025-11": [4981], "2026-03": [5467, 5505], "2026-05": [5762], "2026-06": [5967], "2026-07": [6013],
    "2026-09": [6382], "2026-10": [6484],
}


def months():
    year, month = 2023, 11
    while (year, month) <= (2026, 10):
        yield f"{year:04d}-{month:02d}"
        month += 1
        if month == 13:
            year, month = year + 1, 1


def next_month(label):
    year, month = int(label[:4]), int(label[5:])
    return (year + 1, 1) if month == 12 else (year, month + 1)


def main():
    pairs = []          # (дата записи, номер страницы, начало текста)
    topics = {}
    for name in ("tg_posts.jsonl", "tg_scan_posts.jsonl"):
        path = FOLDER / name
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            post = json.loads(line)
            if not post.get("time"):
                continue
            when = date.fromisoformat(post["time"][:10])
            for link in post.get("links", []):
                for number in re.findall(r"mcge\.by/archives/(\d+)", link):
                    pairs.append((when, int(number)))
                    topics.setdefault(int(number), (when.isoformat(), " ".join(post.get("text", "").split())[:90]))
    # Запись телеграма может ссылаться на старую страницу: берём для каждого номера самую раннюю дату.
    first_seen = {}
    for when, number in pairs:
        if number not in first_seen or when < first_seen[number]:
            first_seen[number] = when
    ordered = sorted((when, number) for number, when in first_seen.items())
    # Убираем «возвраты» к старым страницам: оставляем только пары, где номер не меньше всех предыдущих.
    clean, highest = [], 0
    for when, number in ordered:
        if number >= highest:
            clean.append((when, number))
            highest = number
    rows = json.loads(CDX.read_text(encoding="utf-8"))[1:]
    archived = {}
    for original, timestamp, status, mime in rows:
        match = re.search(r"/archives/(\d+)/?$", original)
        if match:
            archived[int(match.group(1))] = timestamp
    result = {}
    for label in months():
        if label in KNOWN:
            continue
        year, month = next_month(label)
        start, end = date(year, month, 5), date(year, month, 28)
        low = max((number for when, number in clean if when < start), default=None)
        high = min((number for when, number in clean if when > end), default=None)
        inside = [(when, number) for when, number in clean if start <= when <= end]
        in_archive = sorted(number for number in archived if low is not None and high is not None and low < number < high)
        unknown = [number for number in in_archive if number not in topics]
        result[label] = {"window": [start.isoformat(), end.isoformat()], "id_low": low, "id_high": high,
                         "archived_in_range": in_archive, "archived_unknown_topic": unknown,
                         "first_capture": {str(number): archived[number] for number in unknown}}
        print(f"{label}: окно {start}..{end}; номера {low}..{high}; в архиве {len(in_archive)}, "
              f"из них без известной темы {len(unknown)}")
        print("    привязки внутри окна:", ", ".join(f"{when.isoformat()[5:]}={number}" for when, number in inside))
        print("    кандидаты (есть в архиве, тема неизвестна):", ", ".join(f"{number}@{archived[number][:8]}" for number in unknown))
    (FOLDER / "candidates.json").write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
