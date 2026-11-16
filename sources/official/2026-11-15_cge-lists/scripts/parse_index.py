"""Достаёт из сохранённой страницы архива сайта mcge.by (по месяцам, по рубрике) или из ленты RSS
перечень записей: номер, заголовок, дата.

Запуск из корня проекта:
    python -I -X utf8 sources/official/2026-11-15_cge-lists/scripts/parse_index.py <файл> [<файл> ...]

Заголовки со словами о товарах с истекшими сроками годности помечаются «>>». Результат по всем
файлам дописывается в index_titles.jsonl (номер записи, заголовок, дата, файл-источник).
"""
import html
import json
import re
import sys
from pathlib import Path

FOLDER = Path("sources/official/2026-11-15_cge-lists")
LIST_WORDS = re.compile(r"истекш|сроками годности|просроч", re.IGNORECASE)


def clean(fragment):
    fragment = re.sub(r"(?s)<!\[CDATA\[(.*?)\]\]>", r"\1", fragment)
    fragment = re.sub(r"(?s)<[^>]+>", " ", fragment)
    return re.sub(r"\s+", " ", html.unescape(fragment)).strip()


def from_feed(text):
    items = []
    for item in re.findall(r"(?is)<item\b.*?</item>", text):
        link = re.search(r"(?is)<link>(.*?)</link>", item)
        title = re.search(r"(?is)<title>(.*?)</title>", item)
        when = re.search(r"(?is)<pubDate>(.*?)</pubDate>", item)
        number = re.search(r"/archives/(\d+)", link.group(1)) if link else None
        if not number:
            guid = re.search(r"\?p=(\d+)", item)
            number = guid
        items.append({"id": int(number.group(1)) if number else None,
                      "title": clean(title.group(1)) if title else "",
                      "date": clean(when.group(1)) if when else None})
    return items


def from_html(text):
    """Записи на странице архива: ссылки вида /archives/<номер> с непустой подписью; дата — ближайший <time> после ссылки."""
    items, seen = [], set()
    body = text
    stop = re.search(r"Вы пропустили", body)
    if stop:
        body = body[:stop.start()]
    for match in re.finditer(r'(?is)<a\b[^>]*href="https?://mcge\.by/archives/(\d+)/?"[^>]*>(.*?)</a>', body):
        number, label = int(match.group(1)), clean(match.group(2))
        if not label or number in seen or len(label) < 8:
            continue
        seen.add(number)
        after = body[match.end():match.end() + 3000]
        when = re.search(r"(?is)<time\b[^>]*>(.*?)</time>", after)
        items.append({"id": number, "title": label, "date": clean(when.group(1)) if when else None})
    return items


def main():
    out = FOLDER / "index_titles.jsonl"
    for argument in sys.argv[1:]:
        path = Path(argument)
        text = path.read_text(encoding="utf-8", errors="replace")
        is_feed = "<rss" in text[:600] or "<item>" in text
        items = from_feed(text) if is_feed else from_html(text)
        heading = re.search(r"(?is)<h1\b[^>]*>(.*?)</h1>", text)
        pages = sorted({int(n) for n in re.findall(r"/page/(\d+)", text)})
        print("=" * 90)
        print(path.name, "| записей:", len(items), "| заголовок страницы:", clean(heading.group(1))[:80] if heading else "-",
              "| номера страниц в навигации:", pages[-6:] if pages else "-")
        with out.open("a", encoding="utf-8", newline="\n") as output:
            for item in items:
                mark = ">>" if LIST_WORDS.search(item["title"]) else "  "
                print(f"{mark} {item['id']} | {item['date']} | {item['title'][:170]}")
                output.write(json.dumps({**item, "source_file": f"raw/{path.name}"}, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
