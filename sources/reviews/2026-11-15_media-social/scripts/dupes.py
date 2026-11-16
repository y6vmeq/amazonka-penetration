"""Ищет одинаковые по содержанию снимки в разных группах (перцептивный хеш dHash 16x16).

Запуск: python -I scripts/dupes.py <папка_сбора> <выход.tsv> [порог]
Сравнивает только изображения верхнего уровня каждой группы media/<группа>/ (без кадров и листов).
Порог — число различающихся бит из 256 (по умолчанию 26). Результат — пары «файл — файл — расстояние».
"""
import sys
from pathlib import Path

from PIL import Image

collection = Path(sys.argv[1])
out = Path(sys.argv[2])
threshold = int(sys.argv[3]) if len(sys.argv) > 3 else 26
SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


def dhash(path, size=16):
    with Image.open(path) as image:
        gray = image.convert("L").resize((size + 1, size), Image.LANCZOS)
        pixels = list(gray.getdata())
    bits = 0
    for row in range(size):
        for col in range(size):
            bits = (bits << 1) | (pixels[row * (size + 1) + col] > pixels[row * (size + 1) + col + 1])
    return bits


items = []
for group in sorted(p for p in (collection / "media").iterdir() if p.is_dir()):
    for path in sorted(group.iterdir()):
        if path.is_file() and path.suffix.lower() in SUFFIXES and path.stem != "cover":
            try:
                items.append((group.name, path.name, dhash(path)))
            except OSError:
                pass
lines = []
for i, (group_a, name_a, hash_a) in enumerate(items):
    for group_b, name_b, hash_b in items[i + 1:]:
        if group_a == group_b:
            continue
        distance = bin(hash_a ^ hash_b).count("1")
        if distance <= threshold:
            lines.append(f"{group_a}/{name_a}\t{group_b}/{name_b}\t{distance}")
out.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("images", len(items), "pairs", len(lines))
