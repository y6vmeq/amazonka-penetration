"""Показывает по данным прежнего прохода, у каких постов Threads собрано меньше ответов, чем показывал счётчик."""
import json
import sys
from collections import defaultdict
from pathlib import Path

here = Path(__file__).resolve().parent.parent
prev = here.parent / "2026-11-15_threads-instagram"
posts = json.loads((prev / "work" / "threads_posts.json").read_text(encoding="utf-8"))
children = defaultdict(list)
for code, p in posts.items():
    if p.get("reply_to"):
        children[p["reply_to"]].append(code)

sample = posts["Dfu38mVjF4M"] if "Dfu38mVjF4M" in posts else next(iter(posts.values()))
print("sample reply_to:", sample.get("reply_to"), "level", sample.get("reply_level"))

def root_of(code, depth=0):
    p = posts.get(code)
    while p and p.get("reply_to") and p["reply_to"] in posts and depth < 50:
        code = p["reply_to"]
        p = posts[code]
        depth += 1
    return code

roots = ["DfuxGCzjKsE", "Dfq-YE2EWpt", "DfsDkxTESCq", "Dfmpin6Ctpv", "DfvGhOPCqXC", "DfrlrgOkbQO", "DfsF8sDiIBS"]
out = {}
for code, p in posts.items():
    r = root_of(code)
    if r not in roots:
        continue
    have = len(children.get(code, []))
    want = p.get("direct_reply_count") or 0
    out.setdefault(r, []).append((code, p["user"], p.get("reply_level"), want, have, p.get("iso")))
res = {}
for r in roots:
    rows = out.get(r, [])
    print("==", r, posts[r]["user"], "posts in branch:", len(rows), "root counter:", posts[r].get("direct_reply_count"))
    miss = [row for row in rows if row[3] != row[4]]
    for row in miss:
        print("   ", row)
    res[r] = {"n": len(rows), "codes": [row[0] for row in rows], "mismatch": miss}
(here / "work" / "prev_tree.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
