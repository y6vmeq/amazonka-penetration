"""Поиск по открытому предпросмотру телеграм-канала с сохранением сырых копий.

Запуск из корня проекта:
    python -I -X utf8 sources/official/2026-11-15_cge-lists/scripts/tg_search.py <канал> <краткое-имя> <запрос> [макс. страниц]

Каждую страницу выдачи сохраняет tools/fetch_raw.py (GET, без входа). Листает назад
по ссылке «before», пока есть записи. Печатает записи со ссылками на mcge.by и
первой строкой текста. Между запросами пауза 3 секунды.
"""
import html
import json
import re
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import quote

FOLDER = Path("sources/official/2026-11-15_cge-lists")


def clean(fragment):
    fragment = re.sub(r"(?is)<br\s*/?>", "\n", fragment)
    fragment = re.sub(r"(?s)<[^>]+>", "", fragment)
    return html.unescape(fragment).strip()


def parse(text):
    posts = []
    for block in re.split(r'(?=<div class="tgme_widget_message_wrap)', text):
        post = re.search(r'data-post="([^"]+)"', block)
        if not post:
            continue
        when = re.search(r'<time datetime="([^"]+)"', block)
        body = re.search(r'(?is)<div class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>', block)
        links = sorted(set(html.unescape(link) for link in re.findall(r'href="(https?://[^"]+)"', block)
                           if "t.me/" not in link and "telegram.org" not in link))
        posts.append({
            "post": post.group(1),
            "time": when.group(1) if when else None,
            "links": links,
            "text": clean(body.group(1)) if body else "",
        })
    return posts


def main():
    channel, name, query = sys.argv[1], sys.argv[2], sys.argv[3]
    max_pages = int(sys.argv[4]) if len(sys.argv) > 4 else 15
    before = None
    seen = set()
    for page in range(1, max_pages + 1):
        url = f"https://t.me/s/{channel}?q={quote(query)}" + (f"&before={before}" if before else "")
        label = f"tg-{name}" + (f"-before-{before}" if before else "")
        result = subprocess.run(
            [sys.executable, "-I", "-X", "utf8", "tools/fetch_raw.py", str(FOLDER), url, label],
            capture_output=True, text=True, encoding="utf-8",
        )
        try:
            record = json.loads(result.stdout.strip().splitlines()[-1])
        except (IndexError, json.JSONDecodeError):
            print("fetch failed:", result.stdout[:300], result.stderr[:300])
            break
        print(f"--- page {page}: status={record['status']} file={record['file']} bytes={record['bytes']}")
        if not record["file"] or record["status"] != 200:
            break
        text = (FOLDER / record["file"]).read_text(encoding="utf-8", errors="replace")
        posts = [post for post in parse(text) if post["post"] not in seen]
        if not posts:
            print("no (new) posts on this page")
            break
        for post in posts:
            seen.add(post["post"])
            mcge = [link for link in post["links"] if "mcge.by/archives/" in link]
            first_lines = " / ".join(line.strip() for line in post["text"].splitlines() if line.strip())[:330]
            print(f"{post['post']} | {post['time']} | {' '.join(mcge) or '-'}\n      {first_lines}")
        numbers = [int(post["post"].split("/")[1]) for post in posts]
        before = min(numbers)
        if not re.search(r'href="/s/[^"]*before=', text):
            print("no 'before' link: end of results")
            break
        time.sleep(3)
    print("total posts:", len(seen))


if __name__ == "__main__":
    main()
