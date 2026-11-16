"""Разбор сохранённых страниц YouTube: выдача поиска (ytInitialData) и страница видео
(ytInitialPlayerResponse, ytInitialData).

usage: python -I ytparse.py <out_txt> [--grep=<regex>] <html> [...]
Модуль также импортируется сборщиком записей.
"""
import json
import re
import sys
from pathlib import Path


def extract_json(text, marker):
    """JSON-объект, который идёт сразу после marker (например 'var ytInitialData = ')."""
    start = text.find(marker)
    if start < 0:
        return None
    start = text.find("{", start)
    if start < 0:
        return None
    try:
        return json.JSONDecoder().raw_decode(text[start:])[0]
    except ValueError:
        return None


def runs(node):
    if not node:
        return ""
    if isinstance(node, str):
        return node
    if "simpleText" in node:
        return node["simpleText"]
    if "content" in node and isinstance(node["content"], str):
        return node["content"]
    return "".join(part.get("text", "") for part in node.get("runs") or [])


def walk(node, key, found):
    if isinstance(node, dict):
        for name, value in node.items():
            if name == key:
                found.append(value)
            walk(value, key, found)
    elif isinstance(node, list):
        for value in node:
            walk(value, key, found)
    return found


def search_results(text):
    data = extract_json(text, "var ytInitialData = ")
    if not data:
        return [], None
    estimated = data.get("estimatedResults")
    result = []
    for video in walk(data, "videoRenderer", []):
        snippets = video.get("detailedMetadataSnippets") or []
        result.append({
            "kind": "video",
            "id": video.get("videoId"),
            "url": f"https://www.youtube.com/watch?v={video.get('videoId')}",
            "title": runs(video.get("title")),
            "channel": runs(video.get("ownerText") or video.get("longBylineText")),
            "published": runs(video.get("publishedTimeText")),
            "views": runs(video.get("viewCountText")),
            "length": runs(video.get("lengthText")),
            "snippet": " | ".join(runs(s.get("snippetText")) for s in snippets) or runs(video.get("descriptionSnippet")),
        })
    for short in walk(data, "shortsLockupViewModel", []):
        video_id = (((short.get("onTap") or {}).get("innertubeCommand") or {}).get("reelWatchEndpoint") or {}).get("videoId")
        overlay = short.get("overlayMetadata") or {}
        result.append({
            "kind": "short",
            "id": video_id,
            "url": f"https://www.youtube.com/shorts/{video_id}",
            "title": runs(overlay.get("primaryText")),
            "channel": "",
            "published": "",
            "views": runs(overlay.get("secondaryText")),
            "length": "",
            "snippet": short.get("accessibilityText") or "",
        })
    for reel in walk(data, "reelItemRenderer", []):
        result.append({
            "kind": "short",
            "id": reel.get("videoId"),
            "url": f"https://www.youtube.com/shorts/{reel.get('videoId')}",
            "title": runs(reel.get("headline")),
            "channel": "",
            "published": "",
            "views": runs(reel.get("viewCountText")),
            "length": "",
            "snippet": "",
        })
    for channel in walk(data, "channelRenderer", []):
        result.append({
            "kind": "channel",
            "id": channel.get("channelId"),
            "url": f"https://www.youtube.com/channel/{channel.get('channelId')}",
            "title": runs(channel.get("title")),
            "channel": runs(channel.get("subscriberCountText")),
            "published": "",
            "views": runs(channel.get("videoCountText")),
            "length": "",
            "snippet": runs(channel.get("descriptionSnippet")),
        })
    return result, estimated


def video_details(text):
    player = extract_json(text, "var ytInitialPlayerResponse = ")
    if not player:
        return None
    details = player.get("videoDetails") or {}
    micro = (player.get("microformat") or {}).get("playerMicroformatRenderer") or {}
    status = player.get("playabilityStatus") or {}
    return {
        "id": details.get("videoId"),
        "title": details.get("title"),
        "channel": details.get("author"),
        "channel_id": details.get("channelId"),
        "description": details.get("shortDescription"),
        "length_seconds": details.get("lengthSeconds"),
        "views": details.get("viewCount"),
        "keywords": details.get("keywords"),
        "publish_date": micro.get("publishDate"),
        "upload_date": micro.get("uploadDate"),
        "category": micro.get("category"),
        "playability": status.get("status"),
        "reason": status.get("reason"),
    }


def main():
    out = Path(sys.argv[1])
    args = sys.argv[2:]
    pattern = None
    if args and args[0].startswith("--grep="):
        pattern = re.compile(args[0][7:], re.I)
        args = args[1:]
    lines = []
    for name in args:
        path = Path(name)
        text = path.read_bytes().decode("utf-8", "replace")
        items, estimated = search_results(text)
        details = video_details(text)
        lines.append(f"##### {path.name} | results={len(items)} estimated={estimated}")
        if details and details.get("id"):
            lines.append(f"VIDEO {details}")
        for item in items:
            blob = f"{item['title']} {item['snippet']} {item['channel']}"
            if pattern and not pattern.search(blob):
                continue
            lines.append(f"  - [{item['kind']}] {item['url']} | {item['published']} | {item['views']} | {item['length']} | {item['channel']!r}\n      T: {item['title']!r}\n      S: {item['snippet']!r}")
        lines.append("")
    with out.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
