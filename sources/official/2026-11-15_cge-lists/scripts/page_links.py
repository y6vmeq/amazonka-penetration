"""Печатает ссылки сохранённой страницы, адрес или подпись которых подходят под регулярное выражение.

Запуск из корня проекта:
    python -I -X utf8 sources/official/2026-11-15_cge-lists/scripts/page_links.py <файл.html> <регулярное выражение>

Используется для поиска адресов (выдача поиска по сайту, ленты, страницы архива).
"""
import html
import re
import sys
from pathlib import Path


def clean(fragment):
    fragment = re.sub(r"(?s)<[^>]+>", " ", fragment)
    return re.sub(r"\s+", " ", html.unescape(fragment)).strip()


def main():
    path = Path(sys.argv[1])
    pattern = re.compile(sys.argv[2], re.IGNORECASE)
    text = path.read_text(encoding="utf-8", errors="replace")
    seen = {}
    for match in re.finditer(r'(?is)<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', text):
        href, label = html.unescape(match.group(1)), clean(match.group(2))
        if not pattern.search(href + " " + label):
            continue
        if href not in seen or (label and not seen[href]):
            seen[href] = label
    for href, label in seen.items():
        print(href, "|", label[:200])
    print("links:", len(seen))


if __name__ == "__main__":
    main()
