"""Save media fetched in the browser (fetch_media.js dump) to media/<folder>/ and log them.

Usage: python -I <scripts>/save_media.py <dump.json>
For every item: decode base64, recompute SHA-256 and compare with the hash computed in the page,
write the file (extension by signature), append a line to work/media_log.jsonl.
"""
import base64
import hashlib
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
BASE = Path(__file__).resolve().parent.parent
WORK = BASE / "work"


def ext_of(data):
    if data[4:8] == b"ftyp":
        return "mp4"
    if data[:3] == b"\xff\xd8\xff":
        return "jpg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    if data[:4] == b"GIF8":
        return "gif"
    return "bin"


def main():
    dump = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    plan = {p["key"]: p for p in json.loads((WORK / "media_plan.json").read_text(encoding="utf-8"))}
    extra_plan = WORK / "media_plan_extra.json"
    if extra_plan.is_file():
        plan.update({p["key"]: p for p in json.loads(extra_plan.read_text(encoding="utf-8"))})
    ok = 0
    with open(WORK / "media_log.jsonl", "a", encoding="utf-8", newline="\n") as log:
        for item in dump["items"]:
            key = item["key"]
            p = plan.get(key)
            if not item.get("b64") or not p:
                print(f"FAILED {key}: status={item.get('status')} error={item.get('error')} planned={bool(p)}")
                continue
            data = base64.b64decode(item["b64"])
            digest = hashlib.sha256(data).hexdigest()
            if digest != item["sha256"] or len(data) != item["bytes"]:
                print(f"MISMATCH {key}: {digest} != {item['sha256']}")
                continue
            folder = BASE / p["folder"]
            folder.mkdir(parents=True, exist_ok=True)
            rel = f"{p['folder']}/{p['name']}.{ext_of(data)}"
            (BASE / rel).write_bytes(data)
            entry = {"key": key, "file": rel, "sha256": digest, "bytes": len(data), "content_type": item.get("type"),
                     "fetched_at": dump["fetched_at"], "post_url": p["post_url"], "author": p["author"], "code": p["code"],
                     "kind": p["kind"], "published": p.get("published"), "platform": key.split(":")[0]}
            log.write(json.dumps(entry, ensure_ascii=False) + "\n")
            ok += 1
            print(f"OK {rel} {len(data)} bytes sha256={digest}")
    print(f"saved {ok} of {len(dump['items'])}")


if __name__ == "__main__":
    main()
