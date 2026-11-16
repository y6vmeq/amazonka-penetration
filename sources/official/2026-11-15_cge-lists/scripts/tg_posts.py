"""Разбирает сохранённую страницу предпросмотра телеграм-канала (t.me/s/<канал>).

Запуск из корня проекта:
    python -I -X utf8 sources/official/2026-11-15_cge-lists/scripts/tg_posts.py <файл.html> [слово ...]

Печатает по каждой записи: номер, дату, ссылки и начало текста. Если заданы слова,
показывает только записи, где встретилось хотя бы одно (без учёта регистра).
В конце — адрес «раньше» (before=...), если он есть на странице.
"""
import html
import re
import sys
from pathlib import Path


def clean(fragment):
    fragment = re.sub(r"(?is)<br\s*/?>", "\n", fragment)
    fragment = re.sub(r"(?s)<[^>]+>", "", fragment)
    return html.unescape(fragment).strip()


def main():
    path = Path(sys.argv[1])
    words = [word.lower() for word in sys.argv[2:]]
    text = path.read_text(encoding="utf-8", errors="replace")
    blocks = re.split(r'(?=<div class="tgme_widget_message_wrap)', text)
    shown = 0
    total = 0
    for block in blocks:
        post = re.search(r'data-post="([^"]+)"', block)
        if not post:
            continue
        total += 1
        when = re.search(r'<time datetime="([^"]+)"', block)
        body = re.search(r'(?is)<div class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>\s*(?:<div class="tgme_widget_message_(?:footer|reply_markup|link_preview)|<a class="tgme_widget_message_link_preview|</div>)', block)
        body_text = clean(body.group(1)) if body else ""
        links = sorted(set(html.unescape(link) for link in re.findall(r'href="(https?://[^"]+)"', block)
                           if "t.me/" not in link and "telegram.org" not in link))
        haystack = (body_text + " " + " ".join(links)).lower()
        if words and not any(word in haystack for word in words):
            continue
        shown += 1
        print("=" * 80)
        print(post.group(1), "|", when.group(1) if when else "?")
        for link in links:
            print("   link:", link)
        print(body_text[:1500])
    print("=" * 80)
    print("posts on page:", total, "shown:", shown)
    for match in re.finditer(r'href="(/s/[^"]*(?:before|after)=[^"]*)"', text):
        print("nav:", html.unescape(match.group(1)))
    if "tgme_widget_message_wrap" not in text:
        marker = re.search(r'(?is)<div class="tgme_channel_history[^>]*>(.{0,600})', text)
        print("no posts; fragment:", clean(marker.group(1))[:300] if marker else "-")


if __name__ == "__main__":
    main()
