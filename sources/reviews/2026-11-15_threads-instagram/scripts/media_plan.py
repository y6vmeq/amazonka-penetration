"""Plan media downloads: write browser configs (work/mcfg_NN.js) for fetch_media.js and a plan file.

Usage: python -I <scripts>/media_plan.py threads
Reads work/threads_posts.json and work/classify_threads.json (+ EXTRA codes below).
Each planned item: key, url (CDN link taken from the page data), folder, name, post url, author, code, kind.
Items already present on disk (work/media_log.jsonl) are skipped.
"""
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
BASE = Path(__file__).resolve().parent.parent
WORK = BASE / "work"
MINSK = timezone(timedelta(hours=3))

# posts whose media are needed although the post itself is not a separate record
EXTRA = ["DfrmeALEf45", "DUkoavPjvVZ", "DVVxFFsDATm", "DVVxibdjCpK", "DVxx6DZDEUK", "DWQozuVFSTR", "DaUqoo5kXbv"]
# media collected on 14.11.2026 into sources/threads/media/ (not downloaded again)
ALREADY = {("DfsDkxTESCq", "video", 1), ("DfsDkxTESCq", "video", 2), ("DfsH9uSDGQm", "video", 1)}
# posts whose media show another place and are not downloaded
SKIP = {"DfsF8sDiIBS"}


def main():
    db = json.loads((WORK / "threads_posts.json").read_text(encoding="utf-8"))
    classify = json.loads((WORK / "classify_threads.json").read_text(encoding="utf-8"))
    classify.pop("_comment", None)
    done = set()
    log = WORK / "media_log.jsonl"
    if log.is_file():
        for line in log.read_text(encoding="utf-8").splitlines():
            if line.strip():
                done.add(json.loads(line)["key"])
    items = []
    for code in list(classify) + EXTRA:
        rec = db.get(code)
        if not rec or code in SKIP:
            continue
        date = datetime.fromtimestamp(rec["taken_at"], timezone.utc).astimezone(MINSK).strftime("%Y-%m-%d")
        counters = {}
        for m in rec.get("media") or []:
            if m["kind"] not in ("image", "video"):
                continue
            counters[m["kind"]] = counters.get(m["kind"], 0) + 1
            n = counters[m["kind"]]
            if (code, m["kind"], n) in ALREADY:
                continue
            key = f"threads:{code}:{m['kind']}{n}"
            if key in done:
                continue
            folder = f"media/threads_{rec['user']}_{code}"
            name = f"{date}_{rec['user']}_{code}_{'img' if m['kind'] == 'image' else 'video'}{n}"
            items.append({"key": key, "url": m["url"], "folder": folder, "name": name, "post_url": rec.get("permalink"),
                          "author": rec["user"], "code": code, "kind": m["kind"], "idx": m.get("idx"),
                          "published": rec["iso"], "w": m.get("w"), "h": m.get("h"), "has_audio": m.get("has_audio")})
    images = [i for i in items if i["kind"] == "image"]
    videos = [i for i in items if i["kind"] == "video"]
    batches = [images[i:i + 12] for i in range(0, len(images), 12)] + [videos[i:i + 2] for i in range(0, len(videos), 2)]
    for old in WORK.glob("mcfg_*.js"):
        old.unlink()
    for n, batch in enumerate(batches, 1):
        cfg = {"items": [{"key": b["key"], "url": b["url"]} for b in batch]}
        (WORK / f"mcfg_{n:02d}.js").write_text("() => { window.__mcfg = " + json.dumps(cfg) + "; return window.__mcfg.items.length; }", encoding="utf-8")
    (WORK / "media_plan.json").write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"planned: {len(images)} images, {len(videos)} videos, {len(batches)} batches")
    for n, batch in enumerate(batches, 1):
        print(f"  batch {n:02d}: " + ", ".join(b["key"].split(":", 1)[1] for b in batch))


if __name__ == "__main__":
    main()
