"""Сохраняет сырую копию веб-страницы как доказательство.

Запуск из корня проекта:
    python -I tools/fetch_raw.py <папка_сбора> <url> [краткое-имя]

Файл попадает в <папка_сбора>/raw/NNN_<домен>_<имя>.<расширение>. В
<папка_сбора>/raw/manifest.jsonl добавляется строка: файл, URL, конечный URL,
HTTP-статус, тип содержимого, время загрузки (UTC), размер, SHA-256.

Содержимое не разбирается и не исполняется. Сохраняются только текстовые
страницы, JSON, XML, PDF и изображения; остальное отбрасывается.
В stdout печатается одна строка JSON в ASCII: её можно читать в любой консоли.

Код возврата: 0 — сохранено, 2 — сохранено, но HTTP-статус 400 и выше,
1 — не сохранено.
"""
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
)
MAX_BYTES = 40_000_000

# Порядок важен: первое совпадение по началу Content-Type.
EXTENSIONS = [
    ("text/html", ".html"),
    ("application/xhtml", ".html"),
    ("application/json", ".json"),
    ("application/ld+json", ".json"),
    ("text/json", ".json"),
    ("text/xml", ".xml"),
    ("application/xml", ".xml"),
    ("application/rss", ".xml"),
    ("application/atom", ".xml"),
    ("text/plain", ".txt"),
    ("text/csv", ".csv"),
    ("text/javascript", ".js.txt"),
    ("application/javascript", ".js.txt"),
    ("application/pdf", ".pdf"),
    ("image/jpeg", ".jpg"),
    ("image/png", ".png"),
    ("image/webp", ".webp"),
    ("image/gif", ".gif"),
]


def slug(text, limit):
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return text[:limit].strip("-") or "page"


def next_number(raw_dir):
    numbers = [
        int(match.group(1))
        for path in raw_dir.iterdir()
        if (match := re.match(r"(\d{3,})_", path.name))
    ]
    return max(numbers, default=0) + 1


def extension_for(content_type, head):
    """Расширение по Content-Type; если его нет — по первым байтам. None — не сохранять."""
    content_type = content_type.lower().strip()
    for prefix, extension in EXTENSIONS:
        if content_type.startswith(prefix):
            return extension
    if content_type and not content_type.startswith(("application/octet-stream", "binary/")):
        return None
    head = head.lstrip(b"\xef\xbb\xbf \t\r\n")
    if head.startswith(b"%PDF"):
        return ".pdf"
    if head.startswith(b"<"):
        return ".html"
    if head.startswith((b"{", b"[")):
        return ".json"
    return None


def fetch(collection_dir, url, name):
    raw_dir = collection_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    number = next_number(raw_dir)
    parts = urlsplit(url)
    stem = f"{number:03d}_{slug(parts.hostname or 'host', 40)}_{slug(name or parts.path or 'page', 60)}"
    temporary = raw_dir / f".tmp_{number:03d}"

    command = [
        "curl", "--silent", "--show-error", "--location", "--compressed",
        "--proto", "=http,https", "--proto-redir", "=http,https",
        "--connect-timeout", "20", "--max-time", "90",
        "--max-filesize", str(MAX_BYTES),
        "--user-agent", USER_AGENT,
        "--header", "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "--header", "Accept-Language: ru,be;q=0.8,en;q=0.5",
        "--output", str(temporary),
        "--write-out", r"%{http_code}\t%{url_effective}\t%{content_type}",
        url,
    ]
    result = subprocess.run(command, capture_output=True)
    fields = result.stdout.decode("utf-8", errors="replace").split("\t")
    status = int(fields[0]) if fields and fields[0].isdigit() else 0
    final_url = fields[1] if len(fields) > 1 else ""
    content_type = fields[2] if len(fields) > 2 else ""

    record = {
        "file": None,
        "url": url,
        "final_url": final_url,
        "status": status,
        "content_type": content_type,
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "bytes": 0,
        "sha256": None,
        "error": None,
    }

    if result.returncode != 0 or not temporary.exists():
        record["error"] = (
            result.stderr.decode("utf-8", errors="replace").strip()
            or f"curl exit code {result.returncode}"
        )
        temporary.unlink(missing_ok=True)
    else:
        data = temporary.read_bytes()
        extension = extension_for(content_type, data[:64])
        if extension is None:
            record["error"] = f"content type not saved: {content_type or 'unknown'}"
            temporary.unlink()
        else:
            target = raw_dir / (stem + extension)
            temporary.replace(target)
            record["file"] = f"raw/{target.name}"
            record["bytes"] = len(data)
            record["sha256"] = hashlib.sha256(data).hexdigest()

    with (raw_dir / "manifest.jsonl").open("a", encoding="utf-8", newline="\n") as manifest:
        manifest.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def main():
    if len(sys.argv) not in (3, 4) or not sys.argv[2].startswith(("http://", "https://")):
        sys.exit("usage: python -I tools/fetch_raw.py <collection_dir> <http(s) url> [short-name]")
    record = fetch(Path(sys.argv[1]), sys.argv[2], sys.argv[3] if len(sys.argv) == 4 else "")
    print(json.dumps(record, ensure_ascii=True))
    if record["file"] is None:
        sys.exit(1)
    if record["status"] >= 400:
        sys.exit(2)


if __name__ == "__main__":
    main()
