"""Обрезает снимок экрана, сохранённый браузерным расширением, и кладёт его в screenshots/.

Запуск: python -I -X utf8 scripts/shot.py <файл снимка> <имя без расширения> <left> <top> <right> <bottom> <ширина окна в CSS-пикселях> <адрес страницы> [пояснение]

Координаты — в CSS-пикселях страницы (как их вернул getBoundingClientRect). Снимок расширения
уменьшен до ширины кадра, поэтому координаты пересчитываются по отношению ширины файла к ширине окна.
Обрезка убирает панели сайта с данными вошедшего пользователя (меню, значок профиля, виджет сообщений,
строку ввода комментария). Исходный файл из временной папки удаляется.
В screenshots/index.jsonl дописывается строка: файл, адрес, время (UTC), SHA-256, область обрезки.
"""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent.parent


def main():
    src = Path(sys.argv[1])
    name = sys.argv[2]
    left, top, right, bottom, vw = (float(x) for x in sys.argv[3:8])
    url = sys.argv[8]
    note = sys.argv[9] if len(sys.argv) > 9 else ""
    image = Image.open(src)
    k = image.width / vw
    box = (
        max(0, int(left * k)),
        max(0, int(top * k)),
        min(image.width, int(right * k + 0.5)),
        min(image.height, int(bottom * k + 0.5)),
    )
    if box[2] - box[0] < 50 or box[3] - box[1] < 50:
        sys.exit(f"crop too small: {box} of {image.size}")
    out_dir = HERE / "screenshots"
    out_dir.mkdir(exist_ok=True)
    target = out_dir / f"{name}.png"
    image.crop(box).save(target)
    image.close()
    sha = hashlib.sha256(target.read_bytes()).hexdigest()
    taken = datetime.fromtimestamp(src.stat().st_mtime, timezone.utc).isoformat(timespec="seconds")
    line = {
        "file": f"screenshots/{target.name}",
        "url": url,
        "taken_at": taken,
        "sha256": sha,
        "size": [box[2] - box[0], box[3] - box[1]],
        "crop_css": [left, top, right, bottom],
        "note": note,
    }
    index = out_dir / "index.jsonl"
    old = index.read_text(encoding="utf-8").splitlines() if index.is_file() else []
    old = [l for l in old if l.strip() and json.loads(l).get("file") != line["file"]]
    old.append(json.dumps(line, ensure_ascii=False))
    index.write_text("\n".join(old) + "\n", encoding="utf-8", newline="\n")
    src.unlink()
    print("OK", target.name, line["size"], sha[:12])


if __name__ == "__main__":
    main()
