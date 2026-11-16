"""Раскладывает выгрузку страницы, сохранённую из браузера (Playwright MCP,
browser_evaluate + filename), по файлам сырой копии и дописывает manifest.jsonl.

Запуск из корня проекта:

  python -I sources/reviews/2026-11-15_browser-gaps/scripts/save_capture.py \
      <папка_сбора> <временный.json> <краткое-имя> [примечание]

Временный файл — JSON-объект, который вернула функция в браузере:
  url, captured_at, title — адрес страницы, время (ISO, UTC), заголовок;
  html, sha256_html       — outerHTML документа и его SHA-256, посчитанный в браузере (необязательно);
  text                    — видимый текст страницы (innerText) (необязательно);
  data                    — произвольные извлечённые данные (необязательно).

Создаются raw/NNN_<имя>.html, raw/NNN_<имя>.txt, raw/NNN_<имя>.json (что есть).
Для html сверяется SHA-256 с посчитанным в браузере. Содержимое не исполняется.
Временный файл удаляется. В stdout — одна строка JSON в ASCII.
"""
import base64
import hashlib
import json
import re
import sys
from pathlib import Path


def next_number(raw_dir):
    numbers = [
        int(match.group(1))
        for path in raw_dir.iterdir()
        if (match := re.match(r"(\d{3,})_", path.name))
    ]
    return max(numbers, default=0) + 1


def append_manifest(collection_dir, relative, url, fetched_at, note, extra=None):
    data = (collection_dir / relative).read_bytes()
    record = {
        "file": relative,
        "url": url,
        "fetched_at": fetched_at,
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "method": "browser",
        "note": note,
    }
    if extra:
        record.update(extra)
    with (collection_dir / "raw" / "manifest.jsonl").open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def load_capture(temporary):
    """Читает то, что записал Playwright: JSON-объект, JSON-строку с JSON внутри
    или строку base64 (в двойных или одинарных кавычках) с JSON в UTF-8.

    Base64 надёжнее всего: Playwright MCP иногда пишет результат не как JSON,
    а в виде литерала JavaScript (одинарные кавычки, склейка строк), и такой
    файл json.loads не читает. В base64 нет кавычек и переводов строк.
    """
    raw = temporary.read_text(encoding="utf-8").strip()
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        value = raw.strip("'\"")
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.startswith("{"):
            return json.loads(stripped)
        if re.fullmatch(r"[A-Za-z0-9+/=\s]+", stripped):
            return json.loads(base64.b64decode(stripped).decode("utf-8"))
        sys.exit("save_capture: cannot parse the temporary file (not JSON, not base64)")
    return value


def main():
    if len(sys.argv) not in (4, 5):
        sys.exit(__doc__)
    collection_dir = Path(sys.argv[1])
    temporary = Path(sys.argv[2])
    name = re.sub(r"[^a-zA-Z0-9_.-]+", "-", sys.argv[3]).strip("-")
    note = sys.argv[4] if len(sys.argv) == 5 else ""

    capture = load_capture(temporary)
    if not isinstance(capture, dict):
        sys.exit("save_capture: expected a JSON object")

    raw_dir = collection_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    number = next_number(raw_dir)
    stem = f"{number:03d}_{name}"
    url = capture.get("url", "")
    fetched_at = capture.get("captured_at", "")
    title = capture.get("title", "")
    written = []

    html = capture.get("html")
    if isinstance(html, str):
        data = html.encode("utf-8")
        digest = hashlib.sha256(data).hexdigest()
        expected = (capture.get("sha256_html") or "").lower()
        if expected and digest != expected:
            sys.exit(f"save_capture: SHA-256 mismatch for html, got {digest}, browser said {expected}")
        (raw_dir / f"{stem}.html").write_bytes(data)
        written.append(append_manifest(
            collection_dir, f"raw/{stem}.html", url, fetched_at,
            (note + " " if note else "") + "outerHTML документа из браузера; SHA-256 совпал с посчитанным в браузере"
            if expected else (note + " " if note else "") + "outerHTML документа из браузера",
            {"title": title},
        ))

    text = capture.get("text")
    if isinstance(text, str):
        (raw_dir / f"{stem}.txt").write_bytes(text.encode("utf-8"))
        written.append(append_manifest(
            collection_dir, f"raw/{stem}.txt", url, fetched_at,
            (note + " " if note else "") + "видимый текст страницы (innerText) из браузера",
            {"title": title},
        ))

    if "data" in capture and capture["data"] is not None:
        payload = {
            "url": url, "captured_at": fetched_at, "title": title, "data": capture["data"],
        }
        (raw_dir / f"{stem}.json").write_bytes(
            json.dumps(payload, ensure_ascii=False, indent=1).encode("utf-8")
        )
        written.append(append_manifest(
            collection_dir, f"raw/{stem}.json", url, fetched_at,
            (note + " " if note else "") + "данные, извлечённые из страницы в браузере",
            {"title": title},
        ))

    if not written:
        sys.exit("save_capture: nothing to write (no html, text or data)")
    temporary.unlink()
    print(json.dumps(
        [{"file": r["file"], "bytes": r["bytes"], "sha256": r["sha256"]} for r in written],
        ensure_ascii=True,
    ))


if __name__ == "__main__":
    main()
