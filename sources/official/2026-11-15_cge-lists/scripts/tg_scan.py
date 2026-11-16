"""Листает открытый предпросмотр телеграм-канала назад в заданном диапазоне номеров записей.

Запуск из корня проекта:
    python -I -X utf8 sources/official/2026-11-15_cge-lists/scripts/tg_scan.py <канал> <от_номера> <до_номера> [папка_для_страниц]

Если задана папка_для_страниц (например, временная), страницы просмотра сохраняются в неё
(<папка>/raw/ и свой manifest.jsonl), а не в папку сбора: сплошной просмотр канала даёт сотни
страниц, в материалы идут только те, где нашлось объявление о списке (их загружают отдельно).

Идёт от большего номера к меньшему: запрашивает t.me/s/<канал>?before=N (GET, без входа),
каждую страницу сохраняет tools/fetch_raw.py, пауза между запросами 2 секунды.
Останавливается, когда самая ранняя запись на странице не больше <до_номера>.
Печатает только записи со ссылкой на mcge.by/archives/ либо со словами о сроках годности.
Уже пройденные диапазоны записываются в tg_scanned.jsonl, чтобы не ходить повторно.
"""
import html
import json
import re
import subprocess
import sys
import time
from pathlib import Path

FOLDER = Path("sources/official/2026-11-15_cge-lists")
SCANNED = FOLDER / "tg_scanned.jsonl"


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
        preview = " ".join(clean(part) for part in re.findall(
            r'(?is)<div class="link_preview_(?:title|description|site_name)[^"]*"[^>]*>(.*?)</div>', block))
        links = sorted(set(html.unescape(link) for link in re.findall(r'href="(https?://[^"]+)"', block)
                           if "t.me/" not in link and "telegram.org" not in link))
        posts.append({
            "post": post.group(1),
            "number": int(post.group(1).split("/")[1]),
            "time": when.group(1) if when else None,
            "links": links,
            "text": clean(body.group(1)) if body else "",
            "preview": preview,
        })
    return posts


def main():
    channel, start, stop = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
    store = Path(sys.argv[4]) if len(sys.argv) > 4 else FOLDER
    before = start
    pages = 0
    lowest = start
    while before > stop and pages < 600:
        url = f"https://t.me/s/{channel}?before={before}"
        result = subprocess.run(
            [sys.executable, "-I", "-X", "utf8", "tools/fetch_raw.py", str(store), url, f"tg-scan-{channel}-before-{before}"],
            capture_output=True, text=True, encoding="utf-8",
        )
        pages += 1
        try:
            record = json.loads(result.stdout.strip().splitlines()[-1])
        except (IndexError, json.JSONDecodeError):
            print("fetch failed:", result.stdout[:300], result.stderr[:300])
            break
        if not record["file"] or record["status"] != 200:
            print("bad answer:", record["status"], record.get("error"))
            break
        text = (store / record["file"]).read_text(encoding="utf-8", errors="replace")
        posts = parse(text)
        if not posts:
            print(f"before={before}: no posts")
            break
        numbers = [post["number"] for post in posts]
        print(f"before={before}: {len(posts)} posts {min(numbers)}..{max(numbers)} "
              f"{posts[0]['time'][:10] if posts[0]['time'] else '?'}..{posts[-1]['time'][:10] if posts[-1]['time'] else '?'} {record['file']}")
        for post in posts:
            mcge = [link for link in post["links"] if "mcge.by/archives/" in link]
            low = (post["text"] + " " + post["preview"]).lower()
            if mcge or "годност" in low or "истекш" in low or "просроч" in low:
                first = " / ".join(line.strip() for line in post["text"].splitlines() if line.strip())[:200]
                print(f"   {post['post']} {post['time'][:10] if post['time'] else '?'} {' '.join(mcge) or '-'} :: {first}")
        where = "project" if store == FOLDER else "temporary"
        with SCANNED.open("a", encoding="utf-8", newline="\n") as log:
            log.write(json.dumps({"channel": channel, "before": before, "min": min(numbers), "max": max(numbers),
                                  "first_time": posts[0]["time"], "last_time": posts[-1]["time"],
                                  "store": where, "file": record["file"], "fetched_at": record["fetched_at"],
                                  "sha256": record["sha256"]}, ensure_ascii=False) + "\n")
        # Все записи просмотренной страницы — в общий файл: по нему видно, что именно просмотрено.
        with (FOLDER / "tg_scan_posts.jsonl").open("a", encoding="utf-8", newline="\n") as output:
            for post in posts:
                output.write(json.dumps({"post": post["post"], "time": post["time"],
                                         "links": [link for link in post["links"] if "cdn" not in link and "telesco.pe" not in link],
                                         "text": post["text"][:6000], "preview": post["preview"][:300],
                                         "page": record["file"], "store": where}, ensure_ascii=False) + "\n")
        lowest = min(numbers)
        if lowest >= before:
            break
        before = lowest
        time.sleep(2)
    print(f"scanned down to {lowest}, pages {pages}")


if __name__ == "__main__":
    main()
