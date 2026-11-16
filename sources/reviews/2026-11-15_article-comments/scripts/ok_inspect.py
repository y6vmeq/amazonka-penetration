"""Осмотр сохранённых страниц ok.ru (сырой HTML с сервера): есть ли в разметке комментарии.

Запуск: python -I -X utf8 .../scripts/ok_inspect.py <файл.html> [...]
Печатает заголовок, счётчики и найденные блоки комментариев (классы comments_*, d_comment_*).
"""
import html
import json
import re
import sys
from pathlib import Path

TAG = re.compile(r"(?s)<[^>]*>")


def text_of(fragment):
    fragment = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", fragment)
    return re.sub(r"\s+", " ", html.unescape(TAG.sub(" ", fragment))).strip()


for name in sys.argv[1:]:
    data = Path(name).read_text(encoding="utf-8", errors="replace")
    print("==", name, len(data))
    title = re.search(r"(?is)<title>(.*?)</title>", data)
    print("title:", text_of(title.group(1)) if title else None)
    for key in ("og:title", "og:description", "ya:ovs:comments", "ya:ovs:views_total", "ya:ovs:upload_date", "ya:ovs:likes", "video:duration"):
        match = re.search(r'<meta[^>]+(?:property|name)="%s"[^>]+content="([^"]*)"' % re.escape(key), data)
        if match:
            print(f"  {key}: {html.unescape(match.group(1))[:300]}")
    classes = {}
    for match in re.finditer(r'class="([^"]*)"', data):
        for cls in match.group(1).split():
            if re.search(r"comment|discuss|d_comment|cmnt", cls, re.I):
                classes[cls] = classes.get(cls, 0) + 1
    print("  classes:", dict(sorted(classes.items(), key=lambda item: -item[1])[:25]))
    for pattern in (r"commentsCount\D{0,5}(\d+)", r'"comments"\s*:\s*(\d+)', r"data-count=\"(\d+)\"[^>]*comment", r"Комментари\w*\s*(\d+)", r"(\d+)\s*комментар"):
        found = re.findall(pattern, data)[:8]
        if found:
            print(f"  {pattern}: {found}")
    blocks = re.findall(r'(?is)<div[^>]+class="[^"]*\b(?:comments_text|d_comment_text|comments_body|cmnt-text|d_comment_w)[^"]*"[^>]*>(.*?)</div>', data)
    print("  comment text blocks:", len(blocks))
    for block in blocks[:40]:
        print("   -", text_of(block)[:300])
    plain = text_of(data)
    for match in list(re.finditer(r"амазонк|Амазонк|рестобар|змеи|сырник", plain))[:6]:
        print("   ctx:", plain[max(0, match.start() - 100): match.start() + 200])
