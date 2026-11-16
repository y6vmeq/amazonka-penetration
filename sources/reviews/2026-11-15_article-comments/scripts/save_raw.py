"""Превращает снимок страницы из браузера в сырую копию и записывает её в manifest.

Снимок делает функция window.__ac.dump() (scripts/init_helpers.js): Playwright
сохраняет её результат как JSON в файл work/dump.json (одна страница) или
work/dumps.json (список страниц после пакетного обхода scripts/batch_pages.js).
Для каждой страницы скрипт:
  - пишет raw/NNN_<домен>_<имя>.html — разметку после работы скриптов
    (document.documentElement.outerHTML), байт в байт в UTF-8;
  - пишет raw/NNN_<домен>_<имя>.txt — видимый текст страницы (innerText);
  - сверяет SHA-256 разметки с посчитанным в браузере;
  - дописывает две строки в raw/manifest.jsonl;
  - кладёт признаки блока комментариев в work/info_NNN.json;
  - печатает короткую сводку.

Запуск из корня проекта:
    python -I -X utf8 sources/reviews/2026-11-15_article-comments/scripts/save_raw.py [имя] [--dump файл] [--note текст]
Имя обязательно для одиночного снимка; в пакетном берётся из extra.name.
"""
import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

BASE = Path("sources/reviews/2026-11-15_article-comments")
RAW = BASE / "raw"
WORK = BASE / "work"


def slug(text, limit):
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return text[:limit].strip("-") or "page"


def next_number():
    numbers = [
        int(match.group(1))
        for path in RAW.iterdir()
        if (match := re.match(r"(\d{3,})_", path.name))
    ]
    return max(numbers, default=0) + 1


def utf8(text):
    """Как TextEncoder в браузере: одиночные суррогаты заменяются на U+FFFD."""
    return text.encode("utf-8", errors="surrogatepass").decode("utf-8", errors="replace").encode("utf-8")


def save_one(dump, name, note):
    number = next_number()
    host = urlsplit(dump.get("url") or "").hostname or "host"
    host = re.sub(r"^www\.", "", host)
    stem = f"{number:03d}_{slug(host, 30)}_{slug(name, 70)}"
    fetched_at = dump.get("at") or datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")

    html_bytes = utf8(dump["html"])
    html_sha = hashlib.sha256(html_bytes).hexdigest()
    html_path = RAW / f"{stem}.html"
    if html_path.exists():
        sys.exit(f"file exists: {html_path}")
    html_path.write_bytes(html_bytes)

    text_bytes = utf8(dump.get("text") or "")
    text_path = RAW / f"{stem}.txt"
    text_path.write_bytes(text_bytes)

    browser_sha = dump.get("sha256")
    sha_note = (
        "SHA-256 совпал с посчитанным в браузере" if browser_sha == html_sha
        else ("в браузере SHA-256 не считался" if not browser_sha else f"SHA-256 в браузере другой: {browser_sha}")
    )
    extra = dump.get("extra") if isinstance(dump.get("extra"), dict) else {}
    common = {
        "url": dump.get("url") or "",
        "fetched_at": fetched_at,
        "method": "browser",
        "title": dump.get("title") or "",
    }
    if extra.get("status") is not None:
        common["status"] = extra["status"]
    if extra.get("requested") and extra["requested"] != dump.get("url"):
        common["requested_url"] = extra["requested"]
    lines = [
        {"file": f"raw/{html_path.name}", **common, "bytes": len(html_bytes), "sha256": html_sha, "kind": "dom",
         "note": ("outerHTML документа после работы скриптов (Playwright); " + sha_note + ("; " + note if note else ""))},
        {"file": f"raw/{text_path.name}", **common, "bytes": len(text_bytes), "sha256": hashlib.sha256(text_bytes).hexdigest(), "kind": "text",
         "note": "видимый текст страницы (innerText) из браузера" + ("; " + note if note else "")},
    ]
    with (RAW / "manifest.jsonl").open("a", encoding="utf-8", newline="\n") as manifest:
        for line in lines:
            manifest.write(json.dumps(line, ensure_ascii=False) + "\n")

    info = {"number": number, "url": dump.get("url"), "title": dump.get("title"), "at": fetched_at,
            "html": f"raw/{html_path.name}", "txt": f"raw/{text_path.name}", "sha256": html_sha,
            "sha_match": browser_sha == html_sha, "info": dump.get("info"), "extra": dump.get("extra")}
    (WORK / f"info_{number:03d}.json").write_text(json.dumps(info, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")

    detected = dump.get("info") or {}
    print(json.dumps({
        "n": number, "html": f"raw/{html_path.name}", "bytes": len(html_bytes), "sha_match": browser_sha == html_sha,
        "url": dump.get("url"), "title": dump.get("title"), "at": fetched_at,
        "comment_elements": detected.get("commentElementCount"), "iframes": len(detected.get("iframes") or []),
        "widget_scripts": detected.get("widgetScripts"), "textareas": detected.get("textareas"),
        "mentions": len(detected.get("mentions") or []), "text_len": detected.get("bodyTextLength"),
    }, ensure_ascii=False))
    return number


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("name", nargs="?", default="")
    parser.add_argument("--dump", default="")
    parser.add_argument("--note", default="")
    parser.add_argument("--keep-dump", action="store_true")
    args = parser.parse_args()

    RAW.mkdir(parents=True, exist_ok=True)
    WORK.mkdir(parents=True, exist_ok=True)
    dump_path = Path(args.dump) if args.dump else None
    if dump_path is None:
        single, batch = WORK / "dump.json", WORK / "dumps.json"
        dump_path = single if single.exists() else batch
    data = json.loads(dump_path.read_text(encoding="utf-8-sig"))
    if isinstance(data, str):
        data = {"html": data, "url": "", "title": "", "at": None, "sha256": None, "info": None, "text": "", "extra": None}

    if isinstance(data, list):
        for dump in data:
            extra = dump.get("extra") if isinstance(dump.get("extra"), dict) else {}
            save_one(dump, extra.get("name") or args.name or "page", args.note)
    else:
        if not args.name:
            sys.exit("name is required for a single dump")
        save_one(data, args.name, args.note)
    if not args.keep_dump:
        dump_path.unlink()


if __name__ == "__main__":
    main()
