"""Запросы к поисковику Yahoo Search через curl; выдача сохраняется во временной папке (не в проекте).

usage: python -I ysearch.py <out_txt> <queries_file> [pages]
В файле запросов — по одному запросу в строке (UTF-8), строки с # пропускаются.
Результаты дописываются в out_txt после каждого запроса. Запросы, похожие на путь к файлу, отбрасываются.
"""
import hashlib
import html
import re
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import quote_plus, unquote

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36")
SERP_DIR = Path(__file__).resolve().parent.parent / "serp2"
SERP_DIR.mkdir(exist_ok=True)
PATH_LIKE = re.compile(r"[A-Za-z]:[\\/]|\\\\|/Users/|AppData|scratchpad|^@", re.I)
PAUSE = 4


def strip(text):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", text))).strip()


def fetch(url, target):
    cmd = ["curl", "--silent", "--show-error", "--location", "--compressed",
           "--connect-timeout", "20", "--max-time", "60", "--user-agent", UA,
           "--header", "Accept-Language: ru,be;q=0.8,en;q=0.5",
           "--output", str(target), "--write-out", "%{http_code}", url]
    res = subprocess.run(cmd, capture_output=True)
    return res.stdout.decode("ascii", "replace"), res.stderr.decode("utf-8", "replace").strip()


def parse(text):
    items = []
    for block in re.split(r'<div class="dd [^"]*\balgo\b[^"]*"', text)[1:]:
        link = re.search(r'<a [^>]*href="([^"]+)"', block)
        if not link:
            continue
        href = html.unescape(link.group(1))
        real = re.search(r"/RU=([^/]+)/", href)
        if real:
            href = unquote(real.group(1))
        title = re.search(r'<h3[^>]*class="title[^"]*"[^>]*>(.*?)</h3>', block, re.S)
        snippet = re.search(r'<div class="compText[^"]*"[^>]*>(.*?)</div>', block, re.S)
        items.append((href, strip(title.group(1)) if title else "", strip(snippet.group(1)) if snippet else ""))
    return items


def main():
    out_txt = Path(sys.argv[1])
    queries = [q.strip() for q in Path(sys.argv[2]).read_text(encoding="utf-8").splitlines()
               if q.strip() and not q.startswith("#")]
    pages = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    for query in queries:
        if PATH_LIKE.search(query):
            with out_txt.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(f"=== SKIPPED (looks like a path): {query!r}\n")
            continue
        seen = set()
        for page in range(pages):
            start = 1 + page * 7
            url = f"https://search.yahoo.com/search?p={quote_plus(query)}" + (f"&b={start}" if page else "")
            name = f"yahoo_{hashlib.sha1(query.encode('utf-8')).hexdigest()[:10]}_p{page + 1}.html"
            target = SERP_DIR / name
            status, error = fetch(url, target)
            text = target.read_bytes().decode("utf-8", "replace") if target.exists() else ""
            items = [item for item in parse(text) if item[0] not in seen]
            seen.update(item[0] for item in items)
            flag = "CAPTCHA?" if (not items and "captcha" in text.lower()) else ""
            lines = [f"=== {query} | p{page + 1} | http={status} bytes={len(text)} new_results={len(items)} {flag} {error} | serp={name}"]
            for href, title, snippet in items:
                lines.append(f"- {href}\n    T: {title}\n    S: {snippet}")
            with out_txt.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write("\n".join(lines) + "\n\n")
            time.sleep(PAUSE)
            if not items:
                break
    print("finished")


if __name__ == "__main__":
    main()
