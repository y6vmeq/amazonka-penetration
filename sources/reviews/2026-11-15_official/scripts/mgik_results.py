"""Печатает результаты поиска mogilev.gov.by: ссылка | заголовок | фрагмент | дата изменения."""
import html, re, sys
from pathlib import Path
for f in sys.argv[1:]:
    p = Path(f)
    t = p.read_bytes().decode("utf-8", "replace")
    cnt = re.search(r"(\d+)\s*-\s*(\d+)\s*из\s*(\d+)", t)
    q = re.search(r'name="q" value="([^"]*)"', t)
    print(f"=== {p.name}: q={html.unescape(q.group(1)) if q else '?'} | {cnt.group(0) if cnt else 'счётчик не найден'}")
    for m in re.finditer(r'(?is)<a class="result-search-item" href="([^"]+)">(.*?)</a>\s*<p>(.*?)</p>\s*<small>(.*?)</small>', t):
        href = html.unescape(m.group(1))
        href = re.sub(r"\?sphrase_id=\d+$", "", href)
        title = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", m.group(2)))).strip()
        snippet = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", m.group(3)))).strip()
        date = re.sub(r"\s+", " ", m.group(4)).strip()
        print(f"- {href}\n    T: {title}\n    S: {snippet[:500]}\n    D: {date}")
