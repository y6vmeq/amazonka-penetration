"""Комментарии к постам каналов Telegram через открытый виджет обсуждения
(https://t.me/<канал>/<id>?embed=1&discussion=1&comments_limit=100), без входа.

Каждая страница сохраняется как сырая копия (fetch() из tools/fetch_raw.py), сводка — в UTF-8.

usage: python -I tgcomments.py <collection_dir> <digest_txt> <posts_file>
posts_file: по одной ссылке https://t.me/<канал>/<id> в строке.
Модуль также импортируется сборщиком (функция comments()).
"""
import html
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, r"C:/Users/y6vme/OneDrive/myDocuments/belarus/tools")
import fetch_raw  # noqa: E402


def clean(fragment):
    fragment = re.sub(r"(?i)<br\s*/?>", "\n", fragment)
    fragment = re.sub(r"<[^>]+>", "", fragment)
    return html.unescape(fragment).strip()


def comments(text):
    """Комментарии со страницы виджета обсуждения."""
    result = []
    for part in re.split(r'(?=<div class="tgme_widget_message_wrap js-widget_message_wrap">)', text)[1:]:
        post_id = re.search(r'data-post-id="(\d+)"', part)
        if not post_id:
            continue
        author = re.search(r'class="tgme_widget_message_author_name"[^>]*>(.*?)</(?:a|span)>\s*</div>', part, re.S)
        body = re.search(r'<div class="tgme_widget_message_text js-message_text"[^>]*>(.*?)</div>\s*(?:<div class="tgme_widget_message_(?:reactions|footer)|<a class="tgme_widget_message_link_preview)', part, re.S)
        if not body:
            body = re.search(r'<div class="tgme_widget_message_text js-message_text"[^>]*>(.*?)</div>', part, re.S)
        when = re.search(r'<a class="tgme_widget_message_date" href="([^"]+)"><time datetime="([^"]+)">([^<]*)</time>', part)
        reply_to = re.search(r'class="tgme_widget_message_reply[^"]*"[^>]*href="([^"]+)"', part)
        media = []
        if "tgme_widget_message_photo_wrap" in part:
            media.append("photo")
        if "tgme_widget_message_video" in part:
            media.append("video")
        if "tgme_widget_message_sticker" in part:
            media.append("sticker")
        if "tgme_widget_message_voice" in part:
            media.append("voice")
        result.append({
            "comment_id": post_id.group(1),
            "author": clean(author.group(1)) if author else None,
            "text": clean(body.group(1)) if body else "",
            "url": html.unescape(when.group(1)) if when else None,
            "datetime": when.group(2) if when else None,
            "date_shown": when.group(3) if when else None,
            "reply_to": html.unescape(reply_to.group(1)) if reply_to else None,
            "media": media,
        })
    return result


def header(text):
    head = re.search(r'<h3 class="tgme_post_discussion_header">(.*?)</h3>', text, re.S)
    count = re.search(r'"comments_cnt":(\d+)', text)
    unavailable = "Discussion is not available" in text
    more = re.search(r'js-messages_more[^"]*"[^>]*data-(?:after|before)="(\d+)"', text)
    return (clean(head.group(1)) if head else None, int(count.group(1)) if count else None, unavailable,
            more.group(1) if more else None)


def main():
    collection = Path(sys.argv[1])
    digest = Path(sys.argv[2])
    posts = [line.strip() for line in Path(sys.argv[3]).read_text(encoding="utf-8").splitlines() if line.strip().startswith("https://t.me/")]
    for post in posts:
        channel, post_id = post.rstrip("/").split("/")[-2:]
        url = f"https://t.me/{channel}/{post_id}?embed=1&discussion=1&comments_limit=100"
        record = fetch_raw.fetch(collection, url, f"tg-{channel}-{post_id}-comments")
        lines = []
        if not record["file"]:
            lines.append(f"@@ {post} | ERROR {record['error']}")
        else:
            text = (collection / record["file"]).read_bytes().decode("utf-8", "replace")
            head, count, unavailable, more = header(text)
            items = comments(text)
            lines.append(f"@@ {post} | http={record['status']} | header={head!r} | comments_cnt={count} | parsed={len(items)} | unavailable={unavailable} | more={more} | {record['file']}")
            for item in items:
                lines.append(f"  - [{item['datetime']}] {item['author']!r} ({item['url']}) reply_to={item['reply_to']} media={item['media']}\n      {item['text']!r}")
        with digest.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write("\n".join(lines) + "\n")
        time.sleep(1.2)
    print("done")


if __name__ == "__main__":
    main()
