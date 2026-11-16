"""Сводит записи телеграм-канала из всех сохранённых страниц предпросмотра (raw/*_t-me_*.html).

Запуск из корня проекта:
    python -I -X utf8 sources/official/2026-11-15_cge-lists/scripts/tg_collect.py [all]

Пишет tg_posts.jsonl (все записи без повторов: номер, время, ссылки, текст, файл) и
печатает записи, похожие на объявления о списке просроченных товаров
(есть «истекш» и «торговл» в тексте). С параметром all печатает все записи кратко.
"""
import html
import json
import re
import sys
from pathlib import Path

FOLDER = Path("sources/official/2026-11-15_cge-lists")


def clean(fragment):
    fragment = re.sub(r"(?is)<br\s*/?>", "\n", fragment)
    fragment = re.sub(r"(?s)<[^>]+>", "", fragment)
    return html.unescape(fragment).strip()


def parse(text):
    for block in re.split(r'(?=<div class="tgme_widget_message_wrap)', text):
        post = re.search(r'data-post="([^"]+)"', block)
        if not post:
            continue
        when = re.search(r'<time datetime="([^"]+)"', block)
        body = re.search(r'(?is)<div class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>', block)
        links = sorted(set(html.unescape(link) for link in re.findall(r'href="(https?://[^"]+)"', block)
                           if "t.me/" not in link and "telegram.org" not in link))
        yield {
            "post": post.group(1),
            "time": when.group(1) if when else None,
            "links": links,
            "text": clean(body.group(1)) if body else "",
        }


def main():
    show_all = len(sys.argv) > 1 and sys.argv[1] == "all"
    posts = {}
    for path in sorted((FOLDER / "raw").glob("*_t-me_*.html")):
        text = path.read_text(encoding="utf-8", errors="replace")
        for post in parse(text):
            post["raw_file"] = f"raw/{path.name}"
            posts.setdefault(post["post"], post)
    ordered = sorted(posts.values(), key=lambda item: int(item["post"].split("/")[1]))
    with (FOLDER / "tg_posts.jsonl").open("w", encoding="utf-8", newline="\n") as output:
        for post in ordered:
            output.write(json.dumps(post, ensure_ascii=False) + "\n")
    print("posts total:", len(ordered))
    for post in ordered:
        low = post["text"].lower()
        is_list = "истекш" in low and "торговл" in low
        if not (show_all or is_list):
            continue
        mcge = [link for link in post["links"] if "mcge.by/archives/" in link]
        lines = [line.strip() for line in post["text"].splitlines() if line.strip()]
        tail = [line for line in lines if re.search(r"(?i)за\s+[а-я]+\s+(?:месяц\s+)?20\d\d|квартал", line)]
        print(f"{post['post']:22s} {post['time'][:10] if post['time'] else '?':10s} {' '.join(mcge) or '-'}")
        if show_all:
            print("      " + (lines[0][:160] if lines else ""))
        else:
            for line in (tail or lines[:1]):
                print("      " + line[:240])


if __name__ == "__main__":
    main()
