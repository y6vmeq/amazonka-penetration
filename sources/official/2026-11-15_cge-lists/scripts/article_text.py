"""Печатает текст статьи из сохранённой страницы СМИ (masheka.by, mogilev.online, olo.by и т. п.).

Запуск из корня проекта:
    python -I -X utf8 sources/official/2026-11-15_cge-lists/scripts/article_text.py <файл.html> [links]

Печатает заголовок, дату, текст статьи абзацами. С параметром links — ещё и ссылки страницы,
в адресе или подписи которых есть слова о просроченных товарах или санитарной службе.
Статьи СМИ — пересказ; дословной копией списка они не являются.
"""
import html
import re
import sys
from pathlib import Path

BODY_MARKERS = (
    r'<div class="full-text"[^>]*>',                 # masheka.by (DLE)
    r'<div[^>]+class="[^"]*entry-content[^"]*"[^>]*>',  # WordPress
    r'<div[^>]+itemprop="articleBody"[^>]*>',
    r'<article\b[^>]*>',
)
END_MARKERS = (r'class="blog-post-share-box', r'class="[^"]*post-navigation', r"<footer\b", r'class="[^"]*sharedaddy',
               r'class="[^"]*related', r"</article>")


def clean(fragment):
    fragment = re.sub(r"(?is)<(script|style|noscript)\b.*?</\1>", " ", fragment)
    fragment = re.sub(r"(?is)</(p|div|li|h\d|tr)>|<br\s*/?>", "\n", fragment)
    fragment = re.sub(r"(?s)<[^>]+>", "", fragment)
    text = html.unescape(fragment).replace("\xa0", " ")
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def main():
    path = Path(sys.argv[1])
    text = path.read_text(encoding="utf-8", errors="replace")
    for tag in ("title", "h1"):
        for match in re.finditer(rf"(?is)<{tag}\b[^>]*>(.*?)</{tag}>", text):
            print(f"<{tag}>", clean(match.group(1))[:300])
    for pattern in (r'(?is)<meta\s+property="article:published_time"\s+content="([^"]+)"',
                    r'(?is)"datePublished"\s*:\s*"([^"]+)"',
                    r'(?is)<time\b[^>]*datetime="([^"]+)"',
                    r'(?is)fa-calendar-days"></i>\s*([^<]+)<'):
        match = re.search(pattern, text)
        if match:
            print("date:", clean(match.group(1)))
    body = None
    for marker in BODY_MARKERS:
        match = re.search("(?is)" + marker, text)
        if match:
            rest = text[match.end():]
            end = len(rest)
            for stop in END_MARKERS:
                found = re.search("(?is)" + stop, rest)
                if found:
                    end = min(end, found.start())
            body = clean(rest[:end])
            if len(body) > 200:
                break
    print("--- body ---")
    print(body or "(тело статьи не найдено)")
    if len(sys.argv) > 2 and sys.argv[2] == "links":
        print("--- links ---")
        seen = set()
        for match in re.finditer(r'(?is)<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', text):
            href, label = html.unescape(match.group(1)), re.sub(r"\s+", " ", clean(match.group(2)))
            if href in seen:
                continue
            if re.search(r"(?i)prosroch|srok|sanstanc|sanepid|просроч|истекш|санстанц|срок", href + " " + label):
                seen.add(href)
                print(href, "|", label[:160])


if __name__ == "__main__":
    main()
