"""Разбор сохранённых страниц vk.com (стена, пост, поиск по стене): посты и комментарии.

Посты лежат в атрибуте data-exec="{&quot;PostContentContainer/init&quot;:...}" (JSON, экранированный
как HTML-атрибут), комментарии отрисованы в HTML (div.reply).

usage: python -I vkparse.py <out_txt> [--grep=<regex>] <html> [...]
Модуль также импортируется сборщиком записей.
"""
import html
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


def decode(data):
    head = data[:4000].lower()
    if b"windows-1251" in head:
        return data.decode("cp1251", errors="replace")
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("cp1251", errors="replace")


def vk_text(value):
    """Текст поста из JSON: <br> -> перевод строки, HTML-сущности -> символы."""
    value = re.sub(r"(?i)<br\s*/?>", "\n", value or "")
    value = re.sub(r"<[^>]+>", "", value)
    return html.unescape(value)


def iso(timestamp):
    return datetime.fromtimestamp(int(timestamp), timezone.utc).isoformat(timespec="seconds") if timestamp else None


def attachment_summary(item):
    result = []
    for attachment in item.get("attachments") or []:
        kind = attachment.get("type")
        body = attachment.get(kind) or {}
        if kind == "photo":
            result.append(f"photo https://vk.com/photo{body.get('owner_id')}_{body.get('id')}")
        elif kind == "video":
            result.append(f"video https://vk.com/video{body.get('owner_id')}_{body.get('id')} «{body.get('title', '')}»")
        elif kind == "link":
            result.append(f"link {body.get('url')} «{body.get('title', '')}»")
        elif kind == "poll":
            answers = "; ".join(f"{a.get('text')} — {a.get('votes')}" for a in body.get("answers") or [])
            result.append(f"poll «{body.get('question')}»: {answers}")
        elif kind == "doc":
            result.append(f"doc {body.get('title')}")
        else:
            result.append(str(kind))
    return result


def posts(text):
    result = []
    for match in re.finditer(r'data-exec="(\{&quot;PostContentContainer[^"]*)"', text):
        try:
            data = json.loads(html.unescape(match.group(1)))["PostContentContainer/init"]
        except (ValueError, KeyError):
            continue
        item = data.get("item") or {}
        groups = {g.get("id"): g for g in data.get("groups") or []}
        profiles = {p.get("id"): p for p in data.get("profiles") or []}
        owner_id = item.get("owner_id")
        from_id = item.get("from_id")
        if from_id and from_id < 0:
            author = (groups.get(-from_id) or {}).get("name")
        elif from_id:
            profile = profiles.get(from_id) or {}
            author = (profile.get("first_name", "") + " " + profile.get("last_name", "")).strip() or None
        else:
            author = None
        copies = []
        for copy in item.get("copy_history") or []:
            copies.append({
                "url": f"https://vk.com/wall{copy.get('owner_id')}_{copy.get('id')}",
                "date": iso(copy.get("date")),
                "text": vk_text(copy.get("text")),
                "attachments": attachment_summary(copy),
                "owner": (groups.get(-(copy.get("owner_id") or 0)) or {}).get("name"),
            })
        result.append({
            "post": f"{owner_id}_{item.get('id')}",
            "url": f"https://vk.com/wall{owner_id}_{item.get('id')}",
            "date": iso(item.get("date")),
            "author": author,
            "owner": (groups.get(-(owner_id or 0)) or {}).get("name") if owner_id and owner_id < 0 else None,
            "signer_id": item.get("signer_id"),
            "post_type": item.get("post_type"),
            "text": vk_text(item.get("text")),
            "text_raw": item.get("text") or "",
            "comments": (item.get("comments") or {}).get("count"),
            "likes": (item.get("likes") or {}).get("count"),
            "reposts": (item.get("reposts") or {}).get("count"),
            "views": (item.get("views") or {}).get("count"),
            "attachments": attachment_summary(item),
            "copy_history": copies,
        })
    return result


def reply_text(fragment):
    fragment = re.sub(r'<img[^>]*class="emoji"[^>]*alt="([^"]*)"[^>]*>', r"\1", fragment)
    fragment = re.sub(r'<img[^>]*alt="([^"]*)"[^>]*class="emoji"[^>]*>', r"\1", fragment)
    fragment = re.sub(r"(?i)<br\s*/?>", "\n", fragment)
    fragment = re.sub(r"<[^>]+>", "", fragment)
    return html.unescape(fragment).strip()


def replies(text):
    result = []
    for part in re.split(r'(?=<div id="post-?\d+_\d+" class="reply )', text)[1:]:
        head = re.match(r'<div id="post(-?\d+)_(\d+)" class="reply ', part)
        if not head:
            continue
        author = re.search(r'<a class="author[^"]*"[^>]*href="([^"]*)"[^>]*>(.*?)</a>', part, re.S)
        body = re.search(r'<div class="wall_reply_text"[^>]*>(.*?)</div>\s*</div>\s*</div>', part, re.S)
        if not body:
            body = re.search(r'<div class="wall_reply_text"[^>]*>(.*?)</div>', part, re.S)
        date = re.search(r'<a class="wd_lnk"[^>]*href="([^"]+)"[^>]*>\s*<span class="rel_date"\s*(?:data-date="(\d+)")?[^>]*>([^<]*)</span>', part, re.S)
        parent = re.search(r"wall(-?\d+_\d+)\?reply=", date.group(1)) if date else None
        reply_to = re.search(r'class="reply_to"[^>]*>(.*?)</a>', part, re.S)
        media = []
        if 'class="page_post_sized_thumbs' in part or "page_post_thumb_wrap" in part:
            media.append("photo/video")
        if "sticker" in part[:6000] and "sticker_img" in part:
            media.append("sticker")
        result.append({
            "reply": f"{head.group(1)}_{head.group(2)}",
            "parent_post": parent.group(1) if parent else None,
            "url": html.unescape(date.group(1)) if date else None,
            "date": iso(date.group(2)) if date and date.group(2) else None,
            "date_shown": date.group(3).strip() if date else None,
            "author": reply_text(author.group(2)) if author else None,
            "author_href": author.group(1) if author else None,
            "text": reply_text(body.group(1)) if body else "",
            "reply_to": reply_text(reply_to.group(1)) if reply_to else None,
            "media": media,
        })
    return result


def page_info(text):
    title = re.search(r"<title>(.*?)</title>", text, re.S)
    count = re.search(r'page_block_header_count[^>]*>\s*([^<]*?)\s*<', text)
    more = re.search(r'id="fw_load_more"[^>]*style="([^"]*)"', text)
    return (html.unescape(title.group(1)).strip() if title else None,
            count.group(1) if count else None,
            (more is not None and "display: none" not in more.group(1)))


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
        text = decode(path.read_bytes())
        title, count, more = page_info(text)
        all_posts = posts(text)
        all_replies = replies(text)
        lines.append(f"##### {path.name}\n# title={title!r} count={count} more={more} posts={len(all_posts)} replies={len(all_replies)}")
        for post in all_posts:
            blob = post["text"] + " ".join(c["text"] for c in post["copy_history"])
            if pattern and not pattern.search(blob):
                continue
            lines.append(f"--- {post['url']} | {post['date']} | author={post['author']!r} | comments={post['comments']} likes={post['likes']} views={post['views']} | att={post['attachments'][:6]}")
            lines.append(post["text"])
            for copy in post["copy_history"]:
                lines.append(f"   >>> РЕПОСТ {copy['url']} | {copy['date']} | owner={copy['owner']!r} | att={copy['attachments'][:6]}")
                lines.append(copy["text"])
        for reply in all_replies:
            lines.append(f"  * REPLY {reply['url']} | {reply['date']} ({reply['date_shown']}) | {reply['author']!r} | to={reply['reply_to']!r} | media={reply['media']}")
            lines.append(f"      {reply['text']!r}")
        lines.append("")
    with out_txt.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
