"""Сопоставляет скачанные публикации с записями прежних сборов (по коду публикации в url записи).

Запуск из корня проекта:
    python -I -X utf8 sources/reviews/2026-11-15_media-open/scripts/link_records.py
Читает sources/reviews/ALL.jsonl и reviews.jsonl сборов; пишет work/record_links.tsv:
код публикации, папка с медиа, номера записей. Ничего в чужих папках не меняет.
"""
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
REVIEWS = BASE.parent


def main():
    groups = {}
    for line in (BASE / "media" / "manifest.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            entry = json.loads(line)
            code = entry["url"].rstrip("/").split("/")[-1]
            groups[code] = entry["group"]
    records = {}
    sources = sorted(REVIEWS.glob("2026-11-15_*/reviews.jsonl"))
    for path in sources:
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            haystack = " ".join(str(record.get(field) or "") for field in ("url", "notes")) + " " + json.dumps(record.get("media") or [], ensure_ascii=False)
            for code in groups:
                if code in haystack:
                    records.setdefault(code, []).append(record["id"])
    rows = ["код\tпапка\tзаписи прежних сборов"]
    for code, group in groups.items():
        rows.append(f"{code}\tmedia/{group}\t{', '.join(sorted(set(records.get(code, [])))) or '—'}")
    (BASE / "work" / "record_links.tsv").write_text("\n".join(rows) + "\n", encoding="utf-8", newline="\n")
    linked = sum(1 for code in groups if records.get(code))
    print(f"publications={len(groups)} linked={linked} sources={len(sources)}")
    for row in rows[1:]:
        if not row.endswith("—"):
            print(row)


if __name__ == "__main__":
    main()
