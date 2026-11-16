"""Достаёт из сохранённой страницы выдачи поисковика (Bing) заголовки и адреса результатов.

Запуск из корня проекта:
    python -I -X utf8 sources/official/2026-11-15_cge-lists/scripts/serp_links.py <файл.html> [фильтр-подстрока]

Выдача поисковика годится только для поиска адресов, не для цитат.
"""
import base64
import html
import re
import sys
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit


def clean(fragment):
    fragment = re.sub(r"(?s)<[^>]+>", "", fragment)
    return re.sub(r"\s+", " ", html.unescape(fragment)).strip()


def real_url(href):
    href = html.unescape(href)
    if "bing.com/ck/a" in href:
        target = parse_qs(urlsplit(href).query).get("u", [""])[0]
        if target.startswith("a1"):
            body = target[2:]
            body += "=" * (-len(body) % 4)
            try:
                return base64.urlsafe_b64decode(body).decode("utf-8", errors="replace")
            except ValueError:
                return href
    return href


def main():
    path = Path(sys.argv[1])
    needle = sys.argv[2].lower() if len(sys.argv) > 2 else ""
    text = path.read_text(encoding="utf-8", errors="replace")
    blocks = re.findall(r'(?is)<li class="b_algo".*?</li>', text)
    print("result blocks:", len(blocks))
    for block in blocks:
        link = re.search(r'(?is)<h2[^>]*>\s*<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', block)
        if not link:
            continue
        url = unquote(real_url(link.group(1)))
        title = clean(link.group(2))
        snippet = re.search(r'(?is)<p\b[^>]*>(.*?)</p>', block)
        line = f"{url}\n    {title}\n    {clean(snippet.group(1))[:300] if snippet else ''}"
        if needle and needle not in line.lower():
            continue
        print(line)
    if not blocks:
        marker = re.search(r"(?is)<title>(.*?)</title>", text)
        print("title:", clean(marker.group(1)) if marker else "-")
        print("captcha" if re.search(r"(?i)captcha|unusual traffic|are you a robot", text) else "no captcha marker")


if __name__ == "__main__":
    main()
