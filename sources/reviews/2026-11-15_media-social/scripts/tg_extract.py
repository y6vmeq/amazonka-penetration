"""Достаёт из сохранённых страниц Telegram (embed) адреса фото и видео, дату и текст поста.

Запуск: python -I scripts/tg_extract.py <папка_сбора> <выход.json>
Читает raw/*t-me_tg-embed-*.html как данные (регулярными выражениями), ничего не исполняет.
"""
import html, json, re, sys
from pathlib import Path

collection = Path(sys.argv[1])
out = Path(sys.argv[2])
result = []
for path in sorted((collection / "raw").glob("*_t-me_tg-embed-*.html")):
    page = path.read_text(encoding="utf-8", errors="replace")
    item = {"raw": f"raw/{path.name}", "bytes": len(page)}
    m = re.search(r'data-post="([^"]+)"', page)
    item["post"] = m.group(1) if m else None
    item["datetime"] = re.findall(r'<time[^>]+datetime="([^"]+)"', page)
    item["photos"] = [html.unescape(u) for u in re.findall(r"tgme_widget_message_photo_wrap[^>]*background-image:url\('([^']+)'\)", page)]
    item["photo_links"] = re.findall(r'class="tgme_widget_message_photo_wrap[^"]*"[^>]*href="([^"]+)"', page)
    item["videos"] = [html.unescape(u) for u in re.findall(r'<video[^>]+src="([^"]+)"', page)]
    item["video_thumbs"] = [html.unescape(u) for u in re.findall(r"tgme_widget_message_video_thumb\"[^>]*background-image:url\('([^']+)'\)", page)]
    item["video_duration"] = re.findall(r'message_video_duration[^>]*>([^<]+)<', page)
    item["link_preview_image"] = [html.unescape(u) for u in re.findall(r"link_preview_(?:right_)?image\"[^>]*background-image:url\('([^']+)'\)", page)]
    item["not_supported"] = "message_media_not_supported" in page
    item["views"] = re.findall(r'tgme_widget_message_views">([^<]+)<', page)
    m = re.search(r'<div class="tgme_widget_message_text js-message_text"[^>]*>(.*?)</div>\s*(?:<div class="tgme_widget_message_(?:footer|reactions|link_preview)|<a class="tgme_widget_message_link_preview)', page, re.S)
    text = m.group(1) if m else ""
    text = re.sub(r"<br\s*/?>", "\n", text)
    text = html.unescape(re.sub(r"<[^>]+>", "", text))
    item["text"] = text
    item["error"] = re.findall(r'tgme_widget_message_error">([^<]+)<', page)
    result.append(item)
out.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
for item in result:
    print(item["raw"], "post=", item["post"], "photos=", len(item["photos"]), "videos=", len(item["videos"]), "thumbs=", len(item["video_thumbs"]), "dur=", item["video_duration"], "unsupported=", item["not_supported"], "err=", len(item["error"]))
