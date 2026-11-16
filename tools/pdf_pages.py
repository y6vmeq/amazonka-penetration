"""Рендерит страницы PDF в PNG: python -I pdf_pages.py <файл.pdf> <папка> [dpi]"""
import sys
from pathlib import Path
import pymupdf as fitz
pdf, out = Path(sys.argv[1]), Path(sys.argv[2])
dpi = int(sys.argv[3]) if len(sys.argv) > 3 else 110
out.mkdir(parents=True, exist_ok=True)
doc = fitz.open(pdf)
for i, page in enumerate(doc, 1):
    pix = page.get_pixmap(dpi=dpi)
    target = out / f"page_{i:02d}.png"
    pix.save(target)
    print(target.as_posix(), pix.width, pix.height)
