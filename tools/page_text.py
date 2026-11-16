"""Печатает содержательную часть сохранённой страницы: строки текста и ссылки,
которых нет на странице-образце того же сайта (общий шаблон отбрасывается).

    python -I -X utf8 page_text.py <образец.html> <страница.html> [макс_знаков_в_строке]
"""
import html
import re
import sys
from pathlib import Path


def lines_of(path):
    text = Path(path).read_bytes().decode("utf-8", "replace")
    text = re.sub(r"(?is)<(script|style|noscript)\b.*?</\1>", " ", text)
    links = re.findall(r'(?is)<a\b[^>]*href="([^"#]+)"[^>]*>(.*?)</a>', text)
    links = [(h, re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]*>", " ", t))).strip()) for h, t in links]
    text = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</tr>|</h\d>|</li>|</td>|</th>", "\n", text)
    text = html.unescape(re.sub(r"<[^>]*>", " ", text)).replace("\xa0", " ")
    rows = [re.sub(r"[ \t]+", " ", row).strip() for row in text.splitlines()]
    return [row for row in rows if row], links


base_lines, base_links = lines_of(sys.argv[1])
page_lines, page_links = lines_of(sys.argv[2])
limit = int(sys.argv[3]) if len(sys.argv) > 3 else 400
seen = set(base_lines)
print("== ТЕКСТ")
for row in page_lines:
    if row not in seen:
        print(row[:limit])
print("== ССЫЛКИ")
known = set(base_links)
for href, label in page_links:
    if (href, label) not in known and not href.startswith("javascript"):
        print(f"{label[:110]} -> {href[:200]}")
