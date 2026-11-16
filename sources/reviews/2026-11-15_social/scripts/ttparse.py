"""Разбор сохранённых страниц TikTok: встраиваемые страницы тегов и профилей (/embed/tag/<тег>,
/embed/@<имя>), обычные страницы профиля и видео (JSON в __UNIVERSAL_DATA_FOR_REHYDRATION__).

usage: python -I ttparse.py <out_txt> <html> [...]
Модуль также импортируется сборщиком записей.
"""
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


def iso(timestamp):
    try:
        return datetime.fromtimestamp(int(timestamp), timezone.utc).isoformat(timespec="seconds")
    except (TypeError, ValueError):
        return None


def id_time(video_id):
    """Время создания из идентификатора видео TikTok (старшие 32 бита — секунды Unix)."""
    try:
        return iso(int(video_id) >> 32)
    except (TypeError, ValueError):
        return None


def frontity(text):
    match = re.search(r'<script id="__FRONTITY_CONNECT_STATE__" type="application/json">(.*?)</script>', text, re.S)
    if not match:
        return None
    try:
        return json.loads(match.group(1))
    except ValueError:
        return None


def universal(text):
    match = re.search(r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__" type="application/json">(.*?)</script>', text, re.S)
    if not match:
        return None
    try:
        return json.loads(match.group(1)).get("__DEFAULT_SCOPE__", {})
    except ValueError:
        return None


def embed_pages(text):
    """Список (маршрут, данные страницы) из встраиваемой страницы."""
    state = frontity(text)
    if not state:
        return []
    data = (state.get("source") or {}).get("data") or {}
    return [(key, value) for key, value in data.items() if key.startswith("/embed/") and isinstance(value, dict)]


def embed_videos(text):
    result = []
    for route, page in embed_pages(text):
        info = page.get("embedInfo") or {}
        for video in page.get("videoList") or []:
            author = video.get("authorUniqueId") or (info.get("uniqueId") if isinstance(info, dict) else None)
            result.append({
                "route": route,
                "id": video.get("id"),
                "url": f"https://www.tiktok.com/@{author}/video/{video.get('id')}" if author else f"https://www.tiktok.com/video/{video.get('id')}",
                "author": author,
                "desc": video.get("desc") or "",
                "plays": video.get("playCount"),
                "created": id_time(video.get("id")),
            })
    return result


def describe(text):
    lines = []
    for route, page in embed_pages(text):
        info = page.get("embedInfo") or {}
        short = {k: v for k, v in info.items() if k not in ("coverUrl", "avatarThumbUrl", "avatarUrl")} if isinstance(info, dict) else info
        lines.append(f"EMBED {route} | type={page.get('playlistType') or page.get('pageName')} | isError={page.get('isError')} | info={short}")
    for video in embed_videos(text):
        lines.append(f"  - {video['created']} {video['url']} plays={video['plays']}\n      {video['desc']!r}")
    scope = universal(text)
    if scope:
        user = scope.get("webapp.user-detail")
        if user is not None:
            info = (user.get("userInfo") or {})
            person = info.get("user") or {}
            stats = info.get("stats") or {}
            lines.append(f"USER statusCode={user.get('statusCode')} uniqueId={person.get('uniqueId')!r} nickname={person.get('nickname')!r} "
                         f"signature={person.get('signature')!r} bioLink={(person.get('bioLink') or {}).get('link')!r} "
                         f"followers={stats.get('followerCount')} videos={stats.get('videoCount')} hearts={stats.get('heartCount')} "
                         f"verified={person.get('verified')} private={person.get('privateAccount')}")
        video = scope.get("webapp.video-detail")
        if video is not None:
            item = ((video.get("itemInfo") or {}).get("itemStruct")) or {}
            author = item.get("author") or {}
            stats = item.get("stats") or {}
            lines.append(f"VIDEO statusCode={video.get('statusCode')} id={item.get('id')} author={author.get('uniqueId')!r} ({author.get('nickname')!r}) "
                         f"created={iso(item.get('createTime'))} stats={ {k: stats.get(k) for k in ('playCount', 'diggCount', 'commentCount', 'shareCount', 'collectCount')} }\n"
                         f"      desc={item.get('desc')!r}\n      location={(item.get('poi') or {}).get('name')!r} address={(item.get('poi') or {}).get('address')!r}")
    return lines


def main():
    out = Path(sys.argv[1])
    lines = []
    for name in sys.argv[2:]:
        path = Path(name)
        text = path.read_bytes().decode("utf-8", "replace")
        lines.append(f"##### {path.name} ({len(text)} символов)")
        lines.extend(describe(text) or ["  (данных нет)"])
        lines.append("")
    with out.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
