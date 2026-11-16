"""Скачивает фото и видео из открытых источников в папку сбора.

Запуск из корня проекта (три режима):

    python -I tools/media_download.py <папка_сбора>
        все прямые ссылки из полей media записей <папка_сбора>/reviews.jsonl;

    python -I tools/media_download.py <папка_сбора> --list <файл.json> --group <имя>
        ссылки из JSON-списка: [{"n": 1, "url": "..."}, ...] или {"photos": [...]};

    python -I tools/media_download.py <папка_сбора> --url <ссылка> --group <имя>
        одна прямая ссылка на файл.

Файлы попадают в <папка_сбора>/media/<группа>/NNN.<расширение>; группа для первого
режима — id записи. В <папка_сбора>/media/manifest.jsonl дописывается строка на каждую
ссылку: группа, номер, ссылка, файл, размер, SHA-256, тип содержимого, время.

Сохраняются только изображения и видео. Страницы (HTML) и плейлисты потокового видео
пропускаются с пометкой: их нужно получать браузером или другой программой.
Повторный запуск уже скачанное не трогает. Скачанное не исполняется и не разбирается.
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
)
MAX_BYTES = 300_000_000
PAUSE_SECONDS = 0.3
EXTENSIONS = {
    "image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "image/gif": ".gif",
    "image/avif": ".avif", "image/heic": ".heic",
    "video/mp4": ".mp4", "video/webm": ".webm", "video/quicktime": ".mov",
}
URL = re.compile(r"https?://[^\s\"'<>]+")
YANDEX_SIZE = re.compile(r"(avatars\.mds\.yandex\.net/get-[^/]+/\d+/[^/]+)/[A-Za-z0-9_]+$")
GOOGLE_SIZE = re.compile(r"(lh\d\.googleusercontent\.com/.+)=[a-z]\d+[^/]*$")


def best_size(url):
    """Яндекс и Google отдают миниатюру по умолчанию; просим исходный размер."""
    url = YANDEX_SIZE.sub(r"\1/orig", url)
    return GOOGLE_SIZE.sub(r"\1=s1600", url)


def from_reviews(collection_dir):
    tasks = []
    for line in (collection_dir / "reviews.jsonl").read_text(encoding="utf-8-sig").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        for number, entry in enumerate(record.get("media") or [], 1):
            text = entry if isinstance(entry, str) else json.dumps(entry, ensure_ascii=False)
            match = URL.search(text)
            if match:
                tasks.append((record["id"], number, match.group(0).rstrip(").,;")))
    return tasks


def from_list(path, group):
    data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if isinstance(data, str):
        data = json.loads(data)
    if isinstance(data, dict):
        data = next(value for value in data.values() if isinstance(value, list) and value and isinstance(value[0], dict))
    return [(group, item.get("n", number), item["url"]) for number, item in enumerate(data, 1) if item.get("url")]


def download(url, target_stem):
    """Возвращает (файл или None, тип содержимого, HTTP-статус, пояснение)."""
    temporary = target_stem.with_suffix(".part")
    command = [
        "curl", "--silent", "--show-error", "--location", "--compressed",
        "--proto", "=http,https", "--proto-redir", "=http,https",
        "--connect-timeout", "20", "--max-time", "600", "--max-filesize", str(MAX_BYTES),
        "--user-agent", USER_AGENT, "--output", str(temporary),
        "--write-out", r"%{http_code}\t%{content_type}", url,
    ]
    result = subprocess.run(command, capture_output=True)
    fields = result.stdout.decode("utf-8", errors="replace").split("\t")
    status = int(fields[0]) if fields and fields[0].isdigit() else 0
    content_type = (fields[1] if len(fields) > 1 else "").split(";")[0].strip().lower()
    if result.returncode != 0 or not temporary.exists():
        temporary.unlink(missing_ok=True)
        return None, content_type, status, result.stderr.decode("utf-8", errors="replace").strip()[:200]
    if status >= 400 or content_type not in EXTENSIONS:
        temporary.unlink()
        return None, content_type, status, "не изображение и не видео" if status < 400 else "ошибка HTTP"
    target = target_stem.with_suffix(EXTENSIONS[content_type])
    temporary.replace(target)
    return target, content_type, status, ""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("collection_dir")
    parser.add_argument("--list")
    parser.add_argument("--url")
    parser.add_argument("--group")
    args = parser.parse_args()
    collection_dir = Path(args.collection_dir)
    if (args.list or args.url) and not args.group:
        sys.exit("--group is required with --list and --url")

    if args.url:
        tasks = [(args.group, None, args.url)]
    elif args.list:
        tasks = from_list(args.list, args.group)
    else:
        tasks = from_reviews(collection_dir)

    media_dir = collection_dir / "media"
    media_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = media_dir / "manifest.jsonl"
    done = set()
    if manifest_path.is_file():
        for line in manifest_path.read_text(encoding="utf-8").splitlines():
            entry = json.loads(line)
            if entry.get("file"):
                done.add(entry["url"])

    saved = skipped = failed = 0
    with manifest_path.open("a", encoding="utf-8", newline="\n") as manifest:
        for group, number, url in tasks:
            url = best_size(url)
            if url in done:
                skipped += 1
                continue
            group_dir = media_dir / re.sub(r"[^A-Za-z0-9_.-]+", "_", str(group))
            group_dir.mkdir(exist_ok=True)
            if number is None:
                number = len([path for path in group_dir.iterdir() if path.is_file()]) + 1
            target, content_type, status, note = download(url, group_dir / f"{int(number):03d}")
            entry = {
                "group": str(group), "n": number, "url": url,
                "file": str(target.relative_to(collection_dir).as_posix()) if target else None,
                "bytes": target.stat().st_size if target else 0,
                "sha256": hashlib.sha256(target.read_bytes()).hexdigest() if target else None,
                "content_type": content_type, "status": status, "note": note,
                "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            }
            manifest.write(json.dumps(entry, ensure_ascii=False) + "\n")
            manifest.flush()
            saved += bool(target)
            failed += not target
            done.add(url)
            time.sleep(PAUSE_SECONDS)
    print(f"links={len(tasks)} saved={saved} already={skipped} not_saved={failed}")


if __name__ == "__main__":
    main()
