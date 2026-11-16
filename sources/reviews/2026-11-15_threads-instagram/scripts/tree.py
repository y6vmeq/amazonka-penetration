"""Print reply trees from work/threads_posts.json and list posts whose direct replies are not all collected.

Usage: python -I <scripts>/tree.py [--full] [--root CODE]
Writes work/tree.txt (UTF-8) and prints a summary.
"""
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
BASE = Path(__file__).resolve().parent.parent
db = json.loads((BASE / "work" / "threads_posts.json").read_text(encoding="utf-8"))

children = {}
for code, rec in db.items():
    parent = rec.get("parent")
    if parent:
        children.setdefault(parent, []).append(code)
for parent in children:
    children[parent].sort(key=lambda c: db[c].get("taken_at") or 0)

full = "--full" in sys.argv
only_root = sys.argv[sys.argv.index("--root") + 1] if "--root" in sys.argv else None
lines = []


def show(code, depth):
    rec = db[code]
    known = len(children.get(code, []))
    drc = rec.get("direct_reply_count")
    text = (rec.get("text") or "").replace("\n", " ⏎ ")
    if not full:
        text = text[:110]
    media = ",".join(m["kind"] for m in rec.get("media") or []) or ""
    flag = "" if drc is None or known >= drc else f"  <<< known {known} of {drc}"
    lines.append(f"{'    ' * depth}[{code}] {rec.get('user')} {(rec.get('iso') or '')[:16]} "
                 f"lk={rec.get('like_count')} drc={drc}{(' media=' + media) if media else ''}"
                 f"{' quotes=' + rec['quoted']['code'] if rec.get('quoted') else ''}{flag}")
    lines.append(f"{'    ' * depth}    {text}")
    for child in children.get(code, []):
        show(child, depth + 1)


roots = [c for c, r in db.items() if not r.get("parent")]
roots.sort(key=lambda c: db[c].get("taken_at") or 0)
for root in roots:
    if only_root and root != only_root:
        continue
    show(root, 0)
    lines.append("")


def count(code):
    return 1 + sum(count(c) for c in children.get(code, []))


lines.append("== summary ==")
for root in roots:
    rec = db[root]
    lines.append(f"{root} {rec.get('user')} drc={rec.get('direct_reply_count')} "
                 f"direct_known={len(children.get(root, []))} descendants_known={count(root) - 1} kinds={rec.get('ctx_kinds')}")
incomplete = [(c, r) for c, r in db.items()
              if (r.get("direct_reply_count") or 0) > len(children.get(c, []))]
lines.append("== incomplete (direct replies known < counter) ==")
for code, rec in incomplete:
    lines.append(f"{code} {rec.get('user')} known={len(children.get(code, []))} of {rec.get('direct_reply_count')} "
                 f"visited={'page_raw' in rec} {rec.get('permalink')}")
(BASE / "work" / "tree.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines[-(len(incomplete) + len(roots) + 3):]))
print(f"posts in db: {len(db)}")
