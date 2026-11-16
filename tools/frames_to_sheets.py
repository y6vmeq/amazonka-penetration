"""Split frame dumps (JSON with base64 JPEGs) into files and build labelled contact sheets.

Usage: python -I frames_to_sheets.py <out_dir> <dump1.json> [<dump2.json> ...]
A dump is either {"name","W","H","dur","frames":[{t,b64}]} or {"<name>": {"W","H","dur","frames":[...]}, ...}.
"""
import base64, io, json, os, sys
from PIL import Image, ImageDraw

out_dir = sys.argv[1]
videos = {}
for path in sys.argv[2:]:
    raw = open(path, encoding="utf-8").read().strip()
    obj = json.loads(raw)
    if isinstance(obj, str):
        obj = json.loads(obj)
    if "frames" in obj:
        videos[obj["name"]] = obj
    else:
        videos.update(obj)

COLS, ROWS, CELL_W = 4, 2, 360
for name, v in videos.items():
    vdir = os.path.join(out_dir, name)
    os.makedirs(vdir, exist_ok=True)
    imgs = []
    for fr in v["frames"]:
        data = base64.b64decode(fr["b64"])
        fname = os.path.join(vdir, f"t{fr['t']:05.1f}s.jpg")
        with open(fname, "wb") as f:
            f.write(data)
        imgs.append((fr["t"], Image.open(io.BytesIO(data)).convert("RGB")))
    w, h = imgs[0][1].size
    cell_h = int(h * CELL_W / w)
    per = COLS * ROWS
    for s in range(0, len(imgs), per):
        chunk = imgs[s:s + per]
        sheet = Image.new("RGB", (COLS * CELL_W, ROWS * (cell_h + 22)), "white")
        draw = ImageDraw.Draw(sheet)
        for i, (t, im) in enumerate(chunk):
            x, y = (i % COLS) * CELL_W, (i // COLS) * (cell_h + 22)
            sheet.paste(im.resize((CELL_W, cell_h)), (x, y + 22))
            draw.text((x + 6, y + 4), f"{name}  t={t:.1f}s", fill="black")
        sheet_path = os.path.join(out_dir, f"sheet_{name}_{s // per + 1:02d}.jpg")
        sheet.save(sheet_path, quality=85)
    print(f"{name}: {w}x{h}, dur={v['dur']:.1f}s, frames={len(imgs)}, sheets={(len(imgs) + per - 1) // per}")
