"""Plan Instagram media downloads for the post codes listed in work/ig_media_codes.json.

Usage: python -I <scripts>/media_plan_ig.py
Writes work/media_plan_extra.json (read by save_media.py) and work/mcfg_all.js (batches for fetch_media_next.js).
Media URLs are the ones present in the page data (work/ig_posts.json). Items already in work/media_log.jsonl are skipped.
"""
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
BASE = Path(__file__).resolve().parent.parent
WORK = BASE / "work"
MINSK = timezone(timedelta(hours=3))


def main():
    db = json.loads((WORK / "ig_posts.json").read_text(encoding="utf-8"))
    codes = json.loads((WORK / "ig_media_codes.json").read_text(encoding="utf-8"))
    done = set()
    log = WORK / "media_log.jsonl"
    if log.is_file():
        done = {json.loads(l)["key"] for l in log.read_text(encoding="utf-8").splitlines() if l.strip()}
    extra_path = WORK / "media_plan_extra.json"
    plan = {p["key"]: p for p in json.loads(extra_path.read_text(encoding="utf-8"))} if extra_path.is_file() else {}
    items = []
    for code in codes:
        rec = db.get(code)
        if not rec or not rec.get("media"):
            print("no media data for", code)
            continue
        date = datetime.fromtimestamp(rec["taken_at"], timezone.utc).astimezone(MINSK).strftime("%Y-%m-%d") if rec.get("taken_at") else "0000-00-00"
        url = f"https://www.instagram.com/{'reel' if rec.get('product_type') == 'clips' else 'p'}/{code}/"
        counters = {}
        for m in rec["media"]:
            counters[m["kind"]] = counters.get(m["kind"], 0) + 1
            n = counters[m["kind"]]
            key = f"instagram:{code}:{m['kind']}{n}"
            if key in done:
                continue
            item = {"key": key, "url": m["url"], "folder": f"media/instagram_{rec.get('user')}_{code}",
                    "name": f"{date}_{rec.get('user')}_{code}_{'img' if m['kind'] == 'image' else 'video'}{n}",
                    "post_url": url, "author": rec.get("user"), "code": code, "kind": m["kind"], "idx": m.get("idx"),
                    "published": rec.get("iso"), "w": m.get("w"), "h": m.get("h")}
            plan[key] = item
            items.append(item)
    extra_path.write_text(json.dumps(list(plan.values()), ensure_ascii=False, indent=1), encoding="utf-8")
    images = [i for i in items if i["kind"] == "image"]
    videos = [i for i in items if i["kind"] == "video"]
    batches = [images[i:i + 10] for i in range(0, len(images), 10)] + [videos[i:i + 2] for i in range(0, len(videos), 2)]
    cfg = [[{"key": b["key"], "url": b["url"]} for b in batch] for batch in batches]
    (WORK / "mcfg_all.js").write_text("() => { window.__mbatches = " + json.dumps(cfg) + "; window.__mb = 0; return window.__mbatches.length; }", encoding="utf-8")
    print(f"planned: {len(images)} images, {len(videos)} videos, {len(batches)} batches")
    for n, batch in enumerate(batches, 1):
        print(f"  batch {n:02d}: " + ", ".join(b["key"].split(":", 1)[1] for b in batch))


if __name__ == "__main__":
    main()
