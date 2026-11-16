"""Verify Threads screenshots taken with scripts/shot_check.js.

Usage (from project root): python -I <scripts>/shots_verify.py

For each work/shots/NNN_*.json (result of shot_check.js saved right before the screenshot):
  * the page URL must contain the post code from the file name;
  * the screenshot screenshots/NNN_*.png must be written after the check and within 60 s
    (checked only while the file is not cropped yet: run this script before shots_crop.py);
  * posts rendered on the page are listed; the thread ends where the first vertical gap between post blocks appears
    (below it Threads shows suggested posts of unrelated authors).
Writes work/shots/_visible.json: post code -> screenshot path, for the opened post and the posts below it
up to the end of the thread. Cropping is done by shots_crop.py.
"""
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

sys.stdout.reconfigure(encoding="utf-8")
BASE = Path(__file__).resolve().parent.parent
SHOTS = BASE / "work" / "shots"
ITEM = re.compile(r"^(\S+) (\S+) y=(-?\d+) h=(\d+)$")


def main():
    db = json.loads((BASE / "work" / "threads_posts.json").read_text(encoding="utf-8"))
    visible = {}
    problems = []
    for path in sorted(SHOTS.glob("[0-9][0-9][0-9]_threads_*.json")):
        stem = path.stem
        data = json.loads(path.read_text(encoding="utf-8"))
        png = BASE / "screenshots" / (stem + ".png")
        code = data["url"].rstrip("/").split("/")[-1]
        ok_url = stem.endswith(code)
        t_check = datetime.fromisoformat(data["t"].replace("Z", "+00:00"))
        if not png.is_file():
            problems.append(f"{stem}: no screenshot")
            continue
        t_png = datetime.fromtimestamp(os.path.getmtime(png), timezone.utc)
        delta = (t_png - t_check).total_seconds()
        items = []
        for raw in data["items"]:
            m = ITEM.match(raw)
            if m:
                items.append({"user": m.group(1), "code": m.group(2), "y": int(m.group(3)), "h": int(m.group(4))})
        # a block that starts inside the previous one is a quoted post (preview), not a post of the thread
        cut = None
        bottom = 0
        for i, it in enumerate(items):
            if i and it["y"] > bottom + 10:
                cut = i
                break
            it["nested"] = bool(i) and it["y"] + it["h"] <= bottom
            bottom = max(bottom, it["y"] + it["h"])
        thread = items if cut is None else items[:cut]
        with Image.open(png) as im:
            size = im.size
        print(f"== {stem}  url_ok={ok_url}  shot-check={delta:.1f}s  png={size}  dialogs={data.get('dialogs')}  thread_bottom={bottom}")
        if not ok_url:
            problems.append(f"{stem}: page url {data['url']} does not match")
        # the time check makes sense only for a file that has not been cropped yet (cropping rewrites the file)
        if size[1] == data.get("ih") and not (0 <= delta <= 60):
            problems.append(f"{stem}: screenshot time differs from check by {delta:.1f}s")
        # Threads scrolls a reply page to the opened post: posts above it (ancestors) may be outside the screenshot
        focus = next((i for i, it in enumerate(thread) if it["code"] == code), 0)
        for n, it in enumerate(thread):
            it["above"] = n < focus
            known = it["code"] in db
            flag = "" if known else "  [not in collected data]"
            # compared with the height of the captured viewport, not of the file: the file may be cropped already
            beyond = "  [below the captured area]" if it["y"] + it["h"] > data.get("ih", size[1]) else ""
            nested = "  [quoted inside the previous post]" if it.get("nested") else ""
            print(f"   {it['user']} {it['code']} y={it['y']} h={it['h']}{flag}{beyond}{nested}")
            if not beyond and not it.get("nested") and not it["above"]:
                # the page of the post itself is preferred over pages where it is shown as an ancestor
                if it["code"] == code or it["code"] not in visible:
                    visible[it["code"]] = f"screenshots/{png.name}"
        if cut is not None:
            nxt = items[cut]
            print(f"   -- cut before: {nxt['user']} {nxt['code']} y={nxt['y']} (in collected data: {nxt['code'] in db}); {len(items) - cut} blocks below")
    (SHOTS / "_visible.json").write_text(json.dumps(visible, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"visible posts: {len(visible)}; problems: {len(problems)}")
    for p in problems:
        print("  !", p)


if __name__ == "__main__":
    main()
