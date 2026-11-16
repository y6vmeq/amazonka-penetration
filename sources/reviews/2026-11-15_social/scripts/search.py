"""Запросы к поисковику Brave Search через curl; выдача сохраняется во временной папке.

usage: python -I search.py <out_txt> <queries_file>
В файле запросов — по одному запросу в строке (UTF-8). Результаты дописываются в out_txt
после каждого запроса. Запросы, похожие на путь к файлу, отбрасываются.
"""
import hashlib
import html
import re
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import quote_plus

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36")
SERP_DIR = Path(__file__).resolve().parent.parent / "serp"
SERP_DIR.mkdir(exist_ok=True)
URL = "https://search.brave.com/search?q={q}&source=web"
PATH_LIKE = re.compile(r"[A-Za-z]:[\/]|\\|/Users/|AppData|scratchpad|^@", re.I)
PAUSE = 9
RETRY_PAUSE = 75


def strip(text):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", text))).strip()


def fetch(url, target):
    cmd = ["curl", "--silent", "--show-error", "--location", "--compressed",
           "--connect-timeout", "20", "--max-time", "60", "--user-agent", UA,
           "--header", "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
           "--header", "Accept-Language: ru,be;q=0.8,en;q=0.5",
           "--output", str(target), "--write-out", "%{http_code}", url]
    res = subprocess.run(cmd, capture_output=True)
    return res.stdout.decode("ascii", "replace"), res.stderr.decode("utf-8", "replace").strip()


def parse(text):
    items = []
    for block in re.split(r'<div class="snippet [^"]*" data-pos="\d+" data-type="web"', text)[1:]:
        link = re.search(r'<a href="([^"]+)"', block)
        if not link:
            continue
        title = re.search(r'search-snippet-title[^"]*"[^>]*title="([^"]*)"', block)
        content = re.search(r'<div class="content [^"]*"[^>]*>(.*?)</div>', block, re.S)
        items.append((html.unescape(link.group(1)), strip(title.group(1)) if title else "",
                      strip(content.group(1)) if content else ""))
    return items


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    out_txt = Path(sys.argv[1])
    queries = [q.strip() for q in Path(sys.argv[2]).read_text(encoding="utf-8").splitlines()
               if q.strip() and not q.startswith("#")]
    for query in queries:
        if PATH_LIKE.search(query):
            line = f"=== SKIPPED (looks like a path): {query!r}\n"
        else:
            url = URL.format(q=quote_plus(query))
            name = f"brave_{hashlib.sha1(query.encode('utf-8')).hexdigest()[:10]}.html"
            target = SERP_DIR / name
            status, error, text = "", "", ""
            for _ in range(4):
                status, error = fetch(url, target)
                text = target.read_bytes().decode("utf-8", "replace") if target.exists() else ""
                if status != "429":
                    break
                time.sleep(RETRY_PAUSE)
            items = parse(text)
            flags = []
            if status == "429":
                flags.append("RATE-LIMIT")
            elif not items and "captcha" in text.lower():
                flags.append("CAPTCHA?")
            lines = [f"=== {query} | http={status} bytes={len(text)} results={len(items)} {' '.join(flags)} {error} | serp={name}"]
            for href, title, snippet in items:
                lines.append(f"- {href}\n    T: {title}\n    S: {snippet}")
            line = "\n".join(lines) + "\n\n"
        with out_txt.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(line)
        time.sleep(PAUSE)
    print("finished")


if __name__ == "__main__":
    main()
