"""Раскладывает выгрузку поиска по сайту (scripts/magilev_search.js и ему подобные) в сырые копии.

Для каждого запроса пишет raw/NNN_<сайт>_search-<имя>.json: запрос, адрес, время,
карточки выдачи и разметку блока выдачи по страницам — как вернул браузер.
Дописывает строку в raw/manifest.jsonl. Сводный список адресов с пометкой
«есть в своде ALL.jsonl / нет» пишет в work/search_<сайт>.json и .txt.

Запуск из корня проекта:
    python -I -X utf8 sources/reviews/2026-11-15_article-comments/scripts/save_search.py <файл выгрузки> <сайт>
"""
import hashlib
import json
import re
import sys
from collections import OrderedDict
from pathlib import Path

BASE = Path("sources/reviews/2026-11-15_article-comments")
RAW = BASE / "raw"
WORK = BASE / "work"

TRANSLIT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e", "ж": "zh", "з": "z", "и": "i", "й": "j",
    "к": "k", "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f",
    "х": "h", "ц": "c", "ч": "ch", "ш": "sh", "щ": "sch", "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
}


def slug(text):
    text = "".join(TRANSLIT.get(char, char) for char in text.lower())
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-") or "query"


def next_number():
    numbers = [int(match.group(1)) for path in RAW.iterdir() if (match := re.match(r"(\d{3,})_", path.name))]
    return max(numbers, default=0) + 1


def norm_url(url):
    return re.sub(r"[?#].*$", "", url or "").rstrip("/")


def main():
    dump_path, site = Path(sys.argv[1]), sys.argv[2]
    dumps = json.loads(dump_path.read_text(encoding="utf-8-sig"))
    known = set()
    for line in Path("sources/reviews/ALL.jsonl").read_text(encoding="utf-8-sig").splitlines():
        if line.strip():
            known.add(norm_url(json.loads(line).get("url")))

    urls = OrderedDict()
    summary = []
    for dump in dumps:
        number = next_number()
        name = f"{number:03d}_{slug(site)}_search-{slug(dump['query'])}.json"
        data = json.dumps(dump, ensure_ascii=False, indent=1).encode("utf-8")
        (RAW / name).write_bytes(data)
        first_at = dump["pages"][0]["at"] if dump.get("pages") else None
        items = sum(len(page.get("items") or []) for page in dump.get("pages") or [])
        with (RAW / "manifest.jsonl").open("a", encoding="utf-8", newline="\n") as manifest:
            manifest.write(json.dumps({
                "file": f"raw/{name}", "url": dump.get("pages", [{}])[0].get("url") or dump.get("finalUrl"),
                "fetched_at": first_at, "method": "browser", "kind": "search-results",
                "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
                "note": f"Поиск по сайту {site}, запрос «{dump['query']}»: страниц выдачи {len(dump.get('pages') or [])}, карточек {items}; "
                        f"листание кнопкой сайта, остановка: {dump.get('stop')}. Разметка блока выдачи каждой страницы — в поле html.",
            }, ensure_ascii=False) + "\n")
        summary.append({"query": dump["query"], "file": f"raw/{name}", "pages": len(dump.get("pages") or []), "items": items, "stop": dump.get("stop")})
        for page in dump.get("pages") or []:
            for item in page.get("items") or []:
                key = norm_url(item.get("href"))
                if not key:
                    continue
                entry = urls.setdefault(key, {"url": key, "text": item.get("text"), "queries": [], "in_all": key in known})
                if dump["query"] not in entry["queries"]:
                    entry["queries"].append(dump["query"])

    result = {"site": site, "queries": summary, "urls": list(urls.values())}
    (WORK / f"search_{slug(site)}.json").write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    lines = [f"{item['query']}: страниц {item['pages']}, карточек {item['items']}, {item['stop']} -> {item['file']}" for item in summary]
    lines.append("")
    lines.append(f"Уникальных адресов: {len(urls)}; из них есть в своде: {sum(1 for entry in urls.values() if entry['in_all'])}")
    for entry in urls.values():
        lines.append(f"{'+' if entry['in_all'] else '-'} {entry['url']}\n      {entry['text']}\n      запросы: {', '.join(entry['queries'])}")
    (WORK / f"search_{slug(site)}.txt").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    dump_path.unlink()
    print(json.dumps({"queries": len(summary), "unique_urls": len(urls), "in_all": sum(1 for entry in urls.values() if entry["in_all"])}))


if __name__ == "__main__":
    main()
