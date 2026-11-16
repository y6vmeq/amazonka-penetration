"""Cut the part of a screenshot that lies below the publication itself (suggested posts of unrelated authors).

Usage (from project root): python -I <scripts>/shots_crop.py [--apply]

Threads post pages: below the replies the page shows the section «Связанные ветки» with posts of unrelated
accounts. Its header is the only text that starts left of the avatar column, so it is found by pixels
(bright pixels in the band x = 326..333). The image is cut 22 px above the header.
Instagram post pages (files *_comments-expanded.png): below the post card the page shows «Ещё публикации от …».
The image is cut below the card; the card position is taken from work/shots/<name>_expand.json.
Nothing is redrawn: only the bottom of the image is removed. Without --apply the script only prints the plan.
"""
import json
import os
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.stdout.reconfigure(encoding="utf-8")
BASE = Path(__file__).resolve().parent.parent
SHOTS = BASE / "screenshots"
WORK = BASE / "work" / "shots"


def header_row(path):
    with Image.open(path) as im:
        a = np.asarray(im.convert("L"))
    rows = (a[:, 326:334] > 170).sum(axis=1) > 0
    runs = []
    y, h = 0, a.shape[0]
    while y < h:
        if rows[y]:
            s = y
            while y < h and rows[y]:
                y += 1
            runs.append((s, y - s))
        else:
            y += 1
    return runs, a.shape


def crop(path, height, apply):
    with Image.open(path) as im:
        w, h = im.size
        if height >= h - 5:
            return f"keep ({h})"
        if apply:
            im.crop((0, 0, w, height)).save(path.with_suffix(".tmp.png"))
    if apply:
        os.replace(path.with_suffix(".tmp.png"), path)
    return f"{h} -> {height}"


def main():
    apply = "--apply" in sys.argv
    for path in sorted(SHOTS.glob("*_threads_*.png")):
        if "_profile_" in path.name:
            print(f"{path.name}: profile page, kept as is")
            continue
        runs, shape = header_row(path)
        if len(runs) != 1 or runs[0][0] < 150:
            print(f"{path.name}: header not found unambiguously {runs[:5]} - kept as is ({shape[0]})")
            continue
        print(f"{path.name}: header at y={runs[0][0]}; {crop(path, runs[0][0] - 22, apply)}")
    for path in sorted(SHOTS.glob("*_instagram_*_comments-expanded.png")):
        meta = WORK / (path.name.replace("_comments-expanded.png", "_expand.json"))
        data = json.loads(meta.read_text(encoding="utf-8")) if meta.is_file() else {}
        if data.get("expanded") and data.get("pane"):
            bottom = data["pane"][1] + data["pane"][3] + 175
        else:
            bottom = 760
        print(f"{path.name}: card bottom {bottom}; {crop(path, bottom, apply)}")


if __name__ == "__main__":
    main()
