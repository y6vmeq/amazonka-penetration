"""Decode a JSON map {key: base64} (dumped from the browser) into files and print SHA-256.

Usage: python -P tools/b64map_to_files.py <dump.json> <out_dir> <file_prefix>
Each key's suffix after the first "_" becomes part of the name: <file_prefix>_<suffix>.<ext>,
the extension is chosen by the file signature (mp4 / jpg / png / webp / bin).
Compare the printed hashes with the ones computed in the page before trusting the files.
"""
import base64, hashlib, json, os, sys

src, out_dir, prefix = sys.argv[1], sys.argv[2], sys.argv[3]
raw = open(src, encoding="utf-8").read().strip()
obj = json.loads(raw)
if isinstance(obj, str):
    obj = json.loads(obj)
os.makedirs(out_dir, exist_ok=True)


def ext_of(data: bytes) -> str:
    if data[4:8] == b"ftyp":
        return "mp4"
    if data[:3] == b"\xff\xd8\xff":
        return "jpg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return "bin"


for key, b64 in obj.items():
    data = base64.b64decode(b64)
    suffix = key.split("_", 1)[1] if "_" in key else key
    name = f"{prefix}_{suffix}.{ext_of(data)}"
    with open(os.path.join(out_dir, name), "wb") as f:
        f.write(data)
    print(f"{name} {len(data)} sha256={hashlib.sha256(data).hexdigest()}")
