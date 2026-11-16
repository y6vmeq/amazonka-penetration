"""Обрезает уже сохранённый снимок в screenshots/ и обновляет его строку в index.jsonl.

Запуск: python -I -X utf8 scripts/crop_inplace.py <имя файла в screenshots/> <left> <top> <right> <bottom> [пояснение к обрезке]

Координаты — в пикселях самого файла. Нужен, когда в сохранённый снимок области попало лишнее
(например, кнопка с состоянием подписки вошедшего пользователя на затемнённом фоне).
"""
import hashlib
import json
import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent.parent


def main():
    name = sys.argv[1]
    box = tuple(int(x) for x in sys.argv[2:6])
    why = sys.argv[6] if len(sys.argv) > 6 else ""
    target = HERE / "screenshots" / name
    with Image.open(target) as image:
        cropped = image.crop(box)
        cropped.load()
    cropped.save(target)
    index = HERE / "screenshots" / "index.jsonl"
    rows = [json.loads(l) for l in index.read_text(encoding="utf-8").splitlines() if l.strip()]
    found = False
    for row in rows:
        if row.get("file") == f"screenshots/{name}":
            row["sha256"] = hashlib.sha256(target.read_bytes()).hexdigest()
            row["size"] = list(cropped.size)
            row["cropped_px"] = list(box)
            if why:
                row["note"] = (row.get("note", "") + " " + why).strip()
            found = True
    if not found:
        raise SystemExit("нет строки в index.jsonl")
    index.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8", newline="\n")
    print("OK", name, list(cropped.size))


if __name__ == "__main__":
    main()
