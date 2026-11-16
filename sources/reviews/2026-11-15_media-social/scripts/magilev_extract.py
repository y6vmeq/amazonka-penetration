"""Из сохранённых статей magilev.by выписывает фото (полный размер) с подписями и встроенные видео.

Запуск: python -I scripts/magilev_extract.py <папка_сбора>
Пишет work/magilev_images.json и списки work/lists/magilev_<дата>_<имя>.json для tools/media_download.py.
Страницы читаются как текст, ничего не исполняется.
"""
import html
import json
import re
import sys
from pathlib import Path

collection = Path(sys.argv[1])
manifest = {}
for line in (collection / "raw" / "manifest.jsonl").read_text(encoding="utf-8").splitlines():
    record = json.loads(line)
    if record.get("file"):
        manifest[record["file"]] = record
lists_dir = collection / "work" / "lists"
lists_dir.mkdir(parents=True, exist_ok=True)
result = []
for path in sorted((collection / "raw").glob("*_magilev-by_*.html")):
    page = path.read_text(encoding="utf-8", errors="replace")
    url = manifest[f"raw/{path.name}"]["url"]
    m = re.search(r"/news/(\d{4})/(\d{2})/(\d{2})/", url)
    date = "-".join(m.groups()) if m else "0000-00-00"
    short = re.sub(r"^\d+_magilev-by_magilev-\d{4}-\d{2}-\d{2}-", "", path.stem)
    group = f"magilev_{date}_{short}"
    title = re.search(r"<title>(.*?)</title>", page, re.S)
    photos = []
    for figure in re.findall(r"<figure\b[^>]*>(.*?)</figure>", page, re.S):
        img = re.search(r"<img\b[^>]*>", figure)
        if not img:
            continue
        src = re.search(r"data-src=([^\s>\"]+|\"[^\"]+\")", img.group(0)) or re.search(r"\bsrc=([^\s>\"]+|\"[^\"]+\")", img.group(0))
        if not src:
            continue
        src_url = src.group(1).strip('"')
        id_match = re.search(r"media\.magilev\.by/([A-Za-z0-9_-]+)/", src_url)
        caption = re.search(r"<figcaption>(.*?)</figcaption>", figure, re.S)
        alt = re.search(r'alt="([^"]*)"', img.group(0))
        photos.append({
            "n": len(photos) + 1,
            "url": f"https://media.magilev.by/{id_match.group(1)}/full.webp" if id_match else src_url,
            "src": src_url,
            "caption": html.unescape(re.sub(r"<[^>]+>", "", caption.group(1))).strip() if caption else "",
            "alt": html.unescape(alt.group(1)) if alt else "",
        })
    embeds = sorted(set(re.findall(r"<iframe\b[^>]*src=\"?([^\s\">]+)", page)))
    videos = sorted(set(re.findall(r"<(?:video|source)\b[^>]*src=\"?([^\s\">]+)", page)))
    links = sorted(set(u for u in re.findall(r"href=\"?(https?://[^\s\">]+)", page)
                       if re.search(r"instagram\.com|tiktok\.com|youtube\.com|youtu\.be|t\.me/|vk\.com/(?:video|clip|wall)", u)))
    og = re.search(r"property=og:image content=([^\s>]+)", page)
    item = {"raw": f"raw/{path.name}", "url": url, "group": group,
            "title": html.unescape(title.group(1)).strip() if title else "", "og_image": og.group(1) if og else None,
            "photos": photos, "iframes": embeds, "videos": videos, "social_links": links}
    result.append(item)
    (lists_dir / f"{group}.json").write_text(json.dumps(photos, ensure_ascii=False, indent=1), encoding="utf-8")
    print(group, "photos", len(photos), "iframes", len(embeds), "videos", len(videos), "links", len(links))
(collection / "work" / "magilev_images.json").write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
