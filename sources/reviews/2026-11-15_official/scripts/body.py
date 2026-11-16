"""Печатает основной текст страницы mogilev.gov.by (между t4-main-body и «Быстрые ссылки») и ссылки в нём.
usage: python -I -X utf8 body.py [--links] [--max N] file...
"""
import html, re, sys
from pathlib import Path

def body_of(t):
    i = t.find("t4-main-body")
    if i < 0:
        i = t.find('class="page_body"')
    j = t.find("Быстрые ссылки", i)
    return t[i:j if j > 0 else len(t)]

def text_of(seg):
    seg = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", seg)
    seg = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</li>|</tr>|</h\d>", "\n", seg)
    seg = re.sub(r"(?i)</td>|</th>", " | ", seg)
    seg = re.sub(r"<[^>]*>", " ", seg)
    seg = html.unescape(seg).replace("\xa0", " ")
    lines = [re.sub(r"[ \t\r\f\v]+", " ", l).strip() for l in seg.split("\n")]
    return [l for l in lines if l and l != "|"]

args = sys.argv[1:]
links = "--links" in args
mx = 100000
if "--max" in args:
    mx = int(args[args.index("--max") + 1])
files = [a for i, a in enumerate(args) if not a.startswith("--") and (i == 0 or args[i-1] != "--max")]
for f in files:
    p = Path(f)
    t = p.read_bytes().decode("utf-8", "replace")
    seg = body_of(t)
    title = re.search(r"(?is)<title>(.*?)</title>", t)
    print(f"=== {p.name} | title: {html.unescape(title.group(1)).strip() if title else '?'}")
    out = "\n".join(text_of(seg))
    print(out[:mx])
    if links:
        seen = set()
        for m in re.finditer(r'(?is)<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', seg):
            href = html.unescape(m.group(1))
            label = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", m.group(2)))).strip()
            if href not in seen:
                seen.add(href)
                print("  LINK:", href, "|", label[:100])
