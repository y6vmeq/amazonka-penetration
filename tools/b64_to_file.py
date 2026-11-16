"""Decode a base64 dump (possibly JSON-quoted) into a binary file and verify SHA-256.

Usage: python -I b64_to_file.py <src.b64> <dst.bin> <expected_sha256>
"""
import base64, hashlib, json, sys

src, dst, expected = sys.argv[1], sys.argv[2], sys.argv[3].lower()
raw = open(src, encoding="utf-8").read().strip()
if raw.startswith('"'):
    raw = json.loads(raw)
data = base64.b64decode(raw)
digest = hashlib.sha256(data).hexdigest()
if digest != expected:
    print(f"MISMATCH {dst}: got {digest}")
    sys.exit(1)
with open(dst, "wb") as f:
    f.write(data)
print(f"OK {dst.split('/')[-1]} {len(data)} bytes sha256={digest}")
