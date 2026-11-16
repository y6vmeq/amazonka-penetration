"""Находит прямые адреса фото ВКонтакте для записей агента social.

Запуск: python -I scripts/vk_lists.py <папка_сбора> <папка агента social>
Читает reviews.jsonl агента social (поля media вида «photo https://vk.com/photo-<owner>_<id>») и его
raw/*.decoded.json (данные постов), для каждого фото берёт самый большой размер.
Пишет work/lists/vk_<owner>_<post>.json и work/vk_photos.json. Ничего не исполняет.
"""
import json
import re
import sys
from pathlib import Path

collection, social = Path(sys.argv[1]), Path(sys.argv[2])
photos = {}


def walk(node):
    if isinstance(node, dict):
        if isinstance(node.get("sizes"), list) and "owner_id" in node and "id" in node:
            sizes = [s for s in node["sizes"] if isinstance(s, dict) and s.get("url")]
            if sizes:
                best = max(sizes, key=lambda s: (s.get("width") or 0) * (s.get("height") or 0))
                key = f"{node['owner_id']}_{node['id']}"
                old = photos.get(key)
                if not old or (best.get("width") or 0) > old["w"]:
                    photos[key] = {"url": best["url"], "w": best.get("width") or 0, "h": best.get("height") or 0,
                                   "date": node.get("date"), "text": node.get("text") or ""}
        for value in node.values():
            walk(value)
    elif isinstance(node, list):
        for value in node:
            walk(value)


for path in sorted((social / "raw").glob("*.decoded.json")):
    walk(json.loads(path.read_text(encoding="utf-8")))
print("photos in decoded copies:", len(photos))

lists_dir = collection / "work" / "lists"
lists_dir.mkdir(parents=True, exist_ok=True)
summary = []
for line in (social / "reviews.jsonl").read_text(encoding="utf-8-sig").splitlines():
    if not line.strip():
        continue
    record = json.loads(line)
    if record["platform"] != "vk":
        continue
    wanted = []
    for entry in record.get("media") or []:
        m = re.search(r"vk\.com/photo(-?\d+_\d+)", entry if isinstance(entry, str) else "")
        if m:
            wanted.append(m.group(1))
    if not wanted:
        continue
    post = re.search(r"wall(-?\d+)_(\d+)", record["url"])
    group = f"vk_{post.group(1).lstrip('-')}_{post.group(2)}"
    urls, missing = [], []
    for number, key in enumerate(wanted, 1):
        if key in photos:
            urls.append({"n": number, "url": photos[key]["url"], "photo": f"https://vk.com/photo{key}",
                         "w": photos[key]["w"], "h": photos[key]["h"], "date": photos[key]["date"], "text": photos[key]["text"]})
        else:
            missing.append(key)
    (lists_dir / f"{group}.json").write_text(json.dumps(urls, ensure_ascii=False, indent=1), encoding="utf-8")
    summary.append({"id": record["id"], "url": record["url"], "group": group, "found": len(urls), "missing": missing, "photos": urls})
    print(record["id"], group, "found", len(urls), "missing", missing)
(collection / "work" / "vk_photos.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
