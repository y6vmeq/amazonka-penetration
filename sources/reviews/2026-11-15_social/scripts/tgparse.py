"""Разбор сохранённых страниц t.me/s/<канал>: сообщения в читаемый UTF-8.

usage: python -I tgparse.py <out_txt> [--grep=<regex>] <html> [<html> ...]
Модуль также импортируется сборщиком записей (функция messages()).
"""
import html
import re
import sys
from pathlib import Path


def clean(fragment):
    fragment = re.sub(r"(?i)<br\s*/?>", "\n", fragment)
    fragment = re.sub(r"<[^>]+>", "", fragment)
    return html.unescape(fragment).strip()


def messages(text):
    """Список словарей по сообщениям страницы предпросмотра канала."""
    result = []
    parts = re.split(r'(?=<div class="tgme_widget_message_wrap)', text)
    for part in parts[1:]:
        post = re.search(r'data-post="([^"]+)"', part)
        if not post:
            continue
        body = re.search(
            r'<div class="tgme_widget_message_text js-message_text"[^>]*>(.*?)</div>\s*(?:<div class="tgme_widget_message_(?:footer|reactions|link_preview)|<a class="tgme_widget_message_link_preview|</div>)',
            part, re.S)
        if not body:
            body = re.search(r'<div class="tgme_widget_message_text js-message_text"[^>]*>(.*?)</div>', part, re.S)
        when = re.search(r'<time datetime="([^"]+)" class="time"', part) or re.search(r'<time datetime="([^"]+)"', part)
        views = re.search(r'<span class="tgme_widget_message_views">([^<]*)</span>', part)
        fwd = re.search(r'class="tgme_widget_message_forwarded_from_name"[^>]*>(.*?)</(?:a|span)>', part, re.S)
        owner = re.search(r'class="tgme_widget_message_owner_name"[^>]*>(.*?)</a>', part, re.S)
        sign = re.search(r'class="tgme_widget_message_from_author"[^>]*>(.*?)</span>', part, re.S)
        media = []
        if "tgme_widget_message_photo_wrap" in part:
            media.append(f"photo x{part.count('tgme_widget_message_photo_wrap')}")
        if "tgme_widget_message_video" in part:
            media.append("video")
        if "tgme_widget_message_document" in part:
            media.append("document")
        if "tgme_widget_message_poll" in part:
            media.append("poll")
        links = re.findall(r'<a href="([^"]+)"[^>]*>', body.group(1)) if body else []
        preview = re.search(r'class="tgme_widget_message_link_preview"[^>]*href="([^"]+)"', part)
        poll_q = re.search(r'class="tgme_widget_message_poll_question"[^>]*>(.*?)</div>', part, re.S)
        poll_opts = re.findall(r'class="tgme_widget_message_poll_option_text"[^>]*>(.*?)</div>', part, re.S)
        poll_pct = re.findall(r'class="tgme_widget_message_poll_option_percent"[^>]*>(.*?)</div>', part, re.S)
        result.append({
            "post": post.group(1),
            "url": "https://t.me/" + post.group(1),
            "datetime": when.group(1) if when else None,
            "views": views.group(1) if views else None,
            "owner": clean(owner.group(1)) if owner else None,
            "forwarded_from": clean(fwd.group(1)) if fwd else None,
            "signature": clean(sign.group(1)) if sign else None,
            "text": clean(body.group(1)) if body else "",
            "text_html": body.group(1) if body else "",
            "media": media,
            "links": links,
            "preview": html.unescape(preview.group(1)) if preview else None,
            "poll": ({"question": clean(poll_q.group(1)), "options": [clean(o) for o in poll_opts], "percent": [clean(p) for p in poll_pct]} if poll_q else None),
        })
    return result


def channel_info(text):
    title = re.search(r'<div class="tgme_channel_info_header_title"[^>]*>(.*?)</div>', text, re.S)
    desc = re.search(r'<div class="tgme_channel_info_description"[^>]*>(.*?)</div>', text, re.S)
    counters = re.findall(r'<span class="counter_value">([^<]*)</span>\s*<span class="counter_type">([^<]*)</span>', text)
    return (clean(title.group(1)) if title else None, clean(desc.group(1)) if desc else None, counters)


def main():
    out_txt = Path(sys.argv[1])
    args = sys.argv[2:]
    pattern = None
    if args and args[0].startswith("--grep="):
        pattern = re.compile(args[0][7:], re.I)
        args = args[1:]
    lines = []
    for name in args:
        path = Path(name)
        text = path.read_bytes().decode("utf-8", errors="replace")
        title, desc, counters = channel_info(text)
        msgs = messages(text)
        shown = [m for m in msgs if not pattern or pattern.search(m["text"]) or (m["poll"] and pattern.search(str(m["poll"])))]
        lines.append(f"##### {path.name}\n# channel={title!r} counters={counters}\n# desc={desc!r}\n# messages={len(msgs)} shown={len(shown)}")
        for m in shown:
            lines.append(f"--- {m['url']} | {m['datetime']} | views={m['views']} | fwd={m['forwarded_from']!r} | sign={m['signature']!r} | media={m['media']} | preview={m['preview']}")
            lines.append(m["text"])
            if m["poll"]:
                lines.append("POLL: " + repr(m["poll"]))
            if m["links"]:
                lines.append("LINKS: " + " ".join(dict.fromkeys(m["links"])))
        lines.append("")
    with out_txt.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
