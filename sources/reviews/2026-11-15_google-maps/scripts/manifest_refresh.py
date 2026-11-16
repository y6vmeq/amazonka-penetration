"""Обновляет raw/manifest.jsonl для файлов, сохранённых из браузера.

Запуск из корня проекта:
    python -I sources/reviews/2026-11-15_google-maps/scripts/manifest_refresh.py [<url для новых файлов>]

Для каждого файла в raw/ пересчитывает размер и SHA-256; fetched_at берёт из времени
изменения файла (UTC). У уже записанных файлов сохраняет url и note. Новым файлам
ставит url из аргумента. Файлы только читаются как данные.
"""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

RAW = Path(__file__).resolve().parent.parent / "raw"


def main():
    default_url = sys.argv[1] if len(sys.argv) > 1 else None
    manifest = RAW / "manifest.jsonl"
    old = {}
    if manifest.is_file():
        for line in manifest.read_text(encoding="utf-8").splitlines():
            if line.strip():
                record = json.loads(line)
                old[record["file"]] = record
    out = []
    added = changed = 0
    for path in sorted(RAW.iterdir()):
        if path.name == "manifest.jsonl" or path.name.startswith(".") or not path.is_file():
            continue
        data = path.read_bytes()
        rel = f"raw/{path.name}"
        digest = hashlib.sha256(data).hexdigest()
        record = dict(old.get(rel, {}))
        if not record:
            added += 1
            own_url = None
            if path.suffix == ".json":
                try:
                    content = json.loads(data.decode("utf-8"))
                    if isinstance(content, dict) and isinstance(content.get("url"), str):
                        own_url = content["url"]
                except (ValueError, UnicodeDecodeError):
                    own_url = None
            if own_url is None and default_url is None:
                sys.exit(f"new file {path.name}: pass the url as an argument")
            record["url"] = own_url or default_url
        elif record.get("sha256") != digest:
            changed += 1
        record.update({
            "file": rel,
            "fetched_at": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(timespec="seconds"),
            "bytes": len(data),
            "sha256": digest,
            "method": "browser",
        })
        ordered = {key: record[key] for key in ("file", "url", "fetched_at", "bytes", "sha256", "method")}
        for key, value in record.items():
            ordered.setdefault(key, value)
        out.append(ordered)
    manifest.write_text("".join(json.dumps(record, ensure_ascii=False) + "\n" for record in out),
                        encoding="utf-8", newline="\n")
    print(f"files={len(out)} added={added} changed={changed}")


if __name__ == "__main__":
    main()
