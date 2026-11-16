"""Показывает устройство сохранённой страницы mcge.by: заголовки, дату, ссылки, таблицы.

Запуск из корня проекта:
    python -I -X utf8 sources/official/2026-11-15_cge-lists/scripts/peek_html.py <файл.html> [links|rows|text]

Ничего не скачивает и не исполняет содержимое страницы.
"""
import html
import re
import sys
from pathlib import Path


def clean(fragment):
    fragment = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", fragment)
    fragment = re.sub(r"(?s)<[^>]+>", " ", fragment)
    return re.sub(r"\s+", " ", html.unescape(fragment)).strip()


def main():
    path = Path(sys.argv[1])
    mode = sys.argv[2] if len(sys.argv) > 2 else "summary"
    data = path.read_bytes()
    text = data.decode("utf-8", errors="replace")
    print("bytes:", len(data))
    for tag in ("title", "h1", "h2", "h3"):
        for match in re.finditer(rf"(?is)<{tag}\b[^>]*>(.*?)</{tag}>", text):
            print(f"<{tag}>", clean(match.group(1))[:300])
    for match in re.finditer(r"(?is)<time\b[^>]*>(.*?)</time>", text):
        print("<time>", match.group(0)[:300])
    for match in re.finditer(r'(?is)<meta\s+(?:property|name)="([^"]+)"\s+content="([^"]*)"', text):
        if any(key in match.group(1) for key in ("published", "modified", "og:title", "og:url", "description")):
            print("meta", match.group(1), "=", html.unescape(match.group(2))[:300])
    for match in re.finditer(r'(?is)<link\s+rel=["\']([^"\']+)["\'][^>]*href=["\']([^"\']+)["\']', text):
        if match.group(1) in ("canonical", "prev", "next", "shortlink", "alternate"):
            print("link", match.group(1), "=", match.group(2)[:300])
    tables = re.findall(r"(?is)<table\b.*?</table>", text)
    print("tables:", len(tables))
    for index, table in enumerate(tables):
        rows = re.findall(r"(?is)<tr\b.*?</tr>", table)
        print(f"  table {index}: rows={len(rows)}")
        if mode == "rows":
            for number, row in enumerate(rows):
                cells = [clean(cell) for cell in re.findall(r"(?is)<t[dh]\b[^>]*>(.*?)</t[dh]>", row)]
                print(f"    {number:3d} [{len(cells)}] " + " | ".join(cells)[:400])
    if mode == "links":
        seen = set()
        for match in re.finditer(r'(?is)<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', text):
            href, label = html.unescape(match.group(1)), clean(match.group(2))
            if (href, label) in seen:
                continue
            seen.add((href, label))
            print("a", href[:200], "|", label[:200])
    if mode == "text":
        body = re.search(r"(?is)<body\b.*", text)
        print(clean(body.group(0) if body else text)[:6000])


if __name__ == "__main__":
    main()
