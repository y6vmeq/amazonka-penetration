"""Служебный скрипт для файлов, сохранённых из браузера (Playwright, browser_evaluate + filename).

Запуск из корня проекта:

  python -I <папка_сбора>/scripts/browser_file.py decode <src.json> <dst> <sha256>
      src.json — строка, которую вернул браузер (Playwright пишет её как JSON-литерал).
      Скрипт разэкранирует её, сверяет SHA-256 (UTF-8) с посчитанным в браузере
      и пишет байты в dst. Исходный временный файл удаляется.

  python -I <папка_сбора>/scripts/browser_file.py manifest <папка_сбора> <raw/файл> <url> <fetched_at> [note]
      Дописывает строку в raw/manifest.jsonl: file, url, fetched_at, bytes, sha256, method=browser.

Содержимое файлов не исполняется и не разбирается (кроме json.loads для строки-литерала).
"""
import hashlib
import json
import sys
from pathlib import Path


def decode(src, dst, expected):
    src, dst = Path(src), Path(dst)
    text = json.loads(src.read_text(encoding="utf-8"))
    if not isinstance(text, str):
        sys.exit("decode: expected a JSON string literal")
    data = text.encode("utf-8")
    digest = hashlib.sha256(data).hexdigest()
    if digest != expected.lower():
        sys.exit(f"decode: SHA-256 mismatch, got {digest}")
    dst.write_bytes(data)
    src.unlink()
    print(f"OK {dst.name} bytes={len(data)} sha256={digest}")


def manifest(collection_dir, relative, url, fetched_at, note=""):
    collection_dir = Path(collection_dir)
    data = (collection_dir / relative).read_bytes()
    record = {
        "file": relative.replace("\\", "/"),
        "url": url,
        "fetched_at": fetched_at,
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "method": "browser",
        "note": note,
    }
    with (collection_dir / "raw" / "manifest.jsonl").open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(json.dumps(record, ensure_ascii=True))


def main():
    if len(sys.argv) == 5 and sys.argv[1] == "decode":
        decode(sys.argv[2], sys.argv[3], sys.argv[4])
    elif len(sys.argv) in (6, 7) and sys.argv[1] == "manifest":
        manifest(*sys.argv[2:])
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
