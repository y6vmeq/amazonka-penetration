"""Выписывает из сохранённых страниц (raw/*.html) адреса изображений и видео: <img>, srcset, data-src,
ссылки на файлы картинок в <a href>, og:image, <video>/<source>, <iframe> (встроенные плееры).

Запуск: python -I scripts/page_images.py <папка_сбора> <выход.json> <шаблон имени файла> [...]
Страницы читаются как текст (регулярные выражения), ничего не исполняется.
"""
import fnmatch
import html
import json
import re
import sys
from pathlib import Path
from urllib.parse import urljoin

collection = Path(sys.argv[1])
out = Path(sys.argv[2])
patterns = sys.argv[3:]
manifest = {}
for line in (collection / "raw" / "manifest.jsonl").read_text(encoding="utf-8").splitlines():
    record = json.loads(line)
    if record.get("file"):
        manifest[record["file"]] = record

IMAGE_EXT = re.compile(r"\.(?:jpe?g|png|webp|gif|avif)(?:[?#]|$)", re.I)
result = []
for path in sorted((collection / "raw").glob("*.html")):
    if not any(fnmatch.fnmatch(path.name, pattern) for pattern in patterns):
        continue
    base = manifest.get(f"raw/{path.name}", {}).get("final_url") or manifest.get(f"raw/{path.name}", {}).get("url") or ""
    page = path.read_text(encoding="utf-8", errors="replace")
    found = []

    def add(kind, url, extra=None):
        url = html.unescape(url.strip())
        if not url or url.startswith("data:"):
            return
        found.append({"kind": kind, "url": urljoin(base, url), **(extra or {})})

    for tag in re.findall(r"<img\b[^>]*>", page, re.I):
        attrs = dict((k.lower(), v) for k, v in re.findall(r'([\w:-]+)\s*=\s*"([^"]*)"', tag))
        attrs.update((k.lower(), v) for k, v in re.findall(r"([\w:-]+)\s*=\s*'([^']*)'", tag))
        extra = {"alt": html.unescape(attrs.get("alt", ""))[:200], "w": attrs.get("width"), "h": attrs.get("height"), "cls": attrs.get("class", "")[:80]}
        for key in ("src", "data-src", "data-original", "data-lazy-src", "data-full", "data-large_image", "data-zoom"):
            if attrs.get(key):
                add("img:" + key, attrs[key], extra)
        for key in ("srcset", "data-srcset"):
            for part in (attrs.get(key) or "").split(","):
                if part.strip():
                    add("img:" + key, part.strip().split()[0], extra)
    for url in re.findall(r'<a\b[^>]*href\s*=\s*"([^"]+)"', page, re.I):
        if IMAGE_EXT.search(url):
            add("a:href", url)
    for url in re.findall(r'<meta[^>]+property="og:image"[^>]+content="([^"]+)"', page, re.I):
        add("og:image", url)
    for url in re.findall(r'<meta[^>]+content="([^"]+)"[^>]+property="og:image"', page, re.I):
        add("og:image", url)
    for url in re.findall(r'<(?:video|source)\b[^>]*src\s*=\s*"([^"]+)"', page, re.I):
        add("video", url)
    for url in re.findall(r'<iframe\b[^>]*src\s*=\s*"([^"]+)"', page, re.I):
        add("iframe", url)
    for url in re.findall(r"background(?:-image)?\s*:\s*url\(['\"]?([^'\")]+)['\"]?\)", page, re.I):
        add("css:background", url)
    seen, unique = set(), []
    for item in found:
        if item["url"] not in seen:
            seen.add(item["url"])
            unique.append(item)
    result.append({"raw": f"raw/{path.name}", "page_url": base, "items": unique})
    print(path.name, "items", len(unique))
out.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
