"""Раскодирует данные постов из сохранённой страницы vk.com в отдельный JSON рядом с ней.

Зачем: vk.com отдаёт посты внутри HTML-атрибута data-exec="{&quot;PostContentContainer/init&quot;:...}".
Текст там экранирован дважды (&lt;br&gt;, &amp;#127860;), поэтому tools/reviews_check.py не может
сопоставить его с записью. Этот скрипт делает одно механическое действие — html.unescape значения
атрибута — и сохраняет получившийся JSON как есть: raw/<имя>.decoded.json. Исходная страница не меняется.
В raw/derived.jsonl пишется, из какого файла (с его SHA-256) и когда получена производная копия.

Запуск из корня проекта:
    python -I sources/reviews/2026-11-15_social/scripts/vk_decode.py raw/250_....html [raw/...html ...]
Пути — относительно папки сбора. Функция decode_file() используется сборщиком build_reviews.py.
"""
import hashlib
import html
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
COLLECTION = HERE.parent
sys.path.insert(0, str(HERE))
import vkparse  # noqa: E402

METHOD = ("html.unescape значения каждого атрибута data-exec с ключом PostContentContainer/init; "
          "JSON сохранён без изменений содержимого (ensure_ascii=False)")


def decoded_name(raw_file):
    return re.sub(r"\.html$", "", raw_file) + ".decoded.json"


def decode_file(raw_file):
    """Создаёт (если ещё нет) raw/<имя>.decoded.json и возвращает его путь относительно папки сбора."""
    target_name = decoded_name(raw_file)
    target = COLLECTION / target_name
    if target.is_file():
        return target_name
    source = COLLECTION / raw_file
    data = source.read_bytes()
    text = vkparse.decode(data)
    containers = []
    for match in re.finditer(r'data-exec="(\{&quot;PostContentContainer[^"]*)"', text):
        try:
            containers.append(json.loads(html.unescape(match.group(1))))
        except ValueError:
            continue
    target.write_text(json.dumps(containers, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    record = {
        "file": target_name,
        "source": raw_file,
        "source_sha256": hashlib.sha256(data).hexdigest(),
        "method": METHOD,
        "containers": len(containers),
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
    }
    with (COLLECTION / "raw" / "derived.jsonl").open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return target_name


def main():
    for raw_file in sys.argv[1:]:
        print(decode_file(raw_file))


if __name__ == "__main__":
    main()
