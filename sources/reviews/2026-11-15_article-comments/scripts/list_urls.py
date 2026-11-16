"""Выписывает из свода ALL.jsonl адреса по площадкам для прохода article-comments.

Запуск из корня проекта:
    python -I -X utf8 sources/reviews/2026-11-15_article-comments/scripts/list_urls.py
Пишет work/urls_from_all.json и work/urls_from_all.txt в папке сбора.
"""
import json
from collections import OrderedDict, Counter
from pathlib import Path

ROOT = Path("sources/reviews")
OUT = ROOT / "2026-11-15_article-comments" / "work"
PLATFORMS = ["magilev.by", "komkur.info", "vk", "telegram", "youtube", "ok"]

records = [json.loads(line) for line in (ROOT / "ALL.jsonl").read_text(encoding="utf-8-sig").splitlines() if line.strip()]
platform_counts = Counter(record.get("platform") for record in records)

result = OrderedDict()
for platform in PLATFORMS:
    urls = OrderedDict()
    for record in records:
        if record.get("platform") != platform:
            continue
        entry = urls.setdefault(record["url"], [])
        entry.append({
            "id": record.get("id"),
            "kind": record.get("kind"),
            "venue": record.get("venue"),
            "author": record.get("author"),
            "date_published": record.get("date_published"),
            "text_head": (record.get("text") or "")[:160],
        })
    result[platform] = urls

OUT.mkdir(parents=True, exist_ok=True)
(OUT / "urls_from_all.json").write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")

lines = ["ВСЕ ПЛОЩАДКИ СВОДА:"]
for platform, count in platform_counts.most_common():
    lines.append(f"  {platform}: {count}")
lines.append("")
for platform, urls in result.items():
    lines.append(f"== {platform}: адресов {len(urls)}")
    for url, entries in urls.items():
        lines.append(url)
        for entry in entries:
            lines.append(f"    {entry['id']} | {entry['kind']} | {entry['venue']} | {entry['author']} | {entry['date_published']} | {entry['text_head']!r}")
    lines.append("")
(OUT / "urls_from_all.txt").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
print("ok", {platform: len(urls) for platform, urls in result.items()})
