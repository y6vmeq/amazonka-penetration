"""Сохраняет сырые копии страниц по списку work/fetch_list.txt через tools/fetch_raw.py.

Запуск из корня проекта:
    python -I sources/reviews/2026-11-15_search-engines/work/fetch_many.py

Строка списка: <краткое-имя><TAB><адрес>. Адрес может содержать кириллицу —
она кодируется в проценты (curl получает только ASCII). Уже загруженные адреса
(по raw/manifest.jsonl) пропускаются. Между запросами пауза 3 с.
"""
import json
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import quote, urlsplit, urlunsplit

HERE = Path(__file__).resolve().parent
COLLECTION = HERE.parent
ROOT = COLLECTION.parents[2]


def encode(url):
    parts = urlsplit(url)
    host = parts.hostname.encode("idna").decode("ascii") if parts.hostname else ""
    netloc = host + (f":{parts.port}" if parts.port else "")
    path = quote(parts.path, safe="/%:@!$&'()*+,;=~-._")
    query = quote(parts.query, safe="=&%:@!$'()*+,;/?~-._")
    return urlunsplit((parts.scheme, netloc, path, query, ""))


def already_fetched():
    done = set()
    manifest = COLLECTION / "raw" / "manifest.jsonl"
    if manifest.is_file():
        for line in manifest.read_text(encoding="utf-8").splitlines():
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            done.add(record["url"])  # уже пробовали (успешно или нет) — повторно не запрашиваем
    return done


def main():
    done = already_fetched()
    lines = (HERE / "fetch_list.txt").read_text(encoding="utf-8").splitlines()
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or "\t" not in line:
            continue
        name, url = (part.strip() for part in line.split("\t", 1))
        encoded = encode(url)
        if encoded in done:
            continue
        result = subprocess.run(
            [sys.executable, "-I", str(ROOT / "tools" / "fetch_raw.py"),
             str(COLLECTION.relative_to(ROOT)).replace("\\", "/"), encoded, name],
            capture_output=True, cwd=ROOT,
        )
        out = result.stdout.decode("utf-8", errors="replace").strip()
        try:
            record = json.loads(out)
            print(f"{name}: status={record['status']} bytes={record['bytes']} file={record['file']} error={ascii(record['error'])}")
        except json.JSONDecodeError:
            print(f"{name}: no json; rc={result.returncode}; {out[:200]!a}; {result.stderr[:200]!a}")
        done.add(encoded)
        time.sleep(3)


if __name__ == "__main__":
    main()
