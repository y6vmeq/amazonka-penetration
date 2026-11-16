"""Из work/tg_extract.json делает списки ссылок для tools/media_download.py (--list)."""
import json, sys
from pathlib import Path

collection = Path(sys.argv[1])
data = json.loads((collection / "work" / "tg_extract.json").read_text(encoding="utf-8"))
lists_dir = collection / "work" / "lists"
lists_dir.mkdir(exist_ok=True)
for item in data:
    channel, number = item["post"].split("/")
    group = f"telegram_{channel}_{number}"
    urls = []
    seen = set()
    for key in ("videos", "photos", "video_thumbs", "link_preview_image"):
        for url in item[key]:
            if url not in seen:
                seen.add(url)
                urls.append({"n": len(urls) + 1, "url": url, "kind": key})
    (lists_dir / f"{group}.json").write_text(json.dumps(urls, ensure_ascii=False, indent=1), encoding="utf-8")
    print(group, len(urls))
