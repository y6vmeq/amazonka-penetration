"""Извлекает текст из PDF в <имя>.txt рядом (для reviews_check). Только чтение PDF.
usage: python -I -X utf8 pdf2txt.py file.pdf ...
"""
import sys
from pathlib import Path
import pymupdf

for f in sys.argv[1:]:
    p = Path(f)
    out = p.with_suffix(".txt")
    try:
        doc = pymupdf.open(p)
    except Exception as e:
        print(f"{p.name}: ERROR {e}")
        continue
    parts = []
    images = 0
    for i, page in enumerate(doc):
        parts.append(f"[стр. {i+1}]\n" + page.get_text("text"))
        images += len(page.get_images())
    text = "\n".join(parts)
    chars = sum(1 for c in text if c.isalnum())
    out.write_text(text, encoding="utf-8", newline="\n")
    print(f"{p.name}: pages={len(doc)} alnum_chars={chars} images={images} -> {out.name}")
