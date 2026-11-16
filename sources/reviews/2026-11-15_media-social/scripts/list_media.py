"""Выписывает из reviews.jsonl чужих агентов записи с медиа и ссылками (рабочая таблица)."""
import json, sys
from pathlib import Path

root = Path(sys.argv[1])
out = Path(sys.argv[2])
agents = ["social", "crosslinks", "media-forums", "employer", "official"]
lines = []
for agent in agents:
    path = root / f"2026-11-15_{agent}" / "reviews.jsonl"
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        lines.append("=" * 100)
        lines.append(f"{r['id']} | {r['venue']} | {r['platform']} | {r['kind']} | {r.get('date_published')} | {r.get('date_iso')} | {r.get('author')}")
        lines.append(f"URL: {r['url']}")
        lines.append(f"RAW: {r.get('raw_file')}")
        lines.append(f"SENT: {r.get('sentiment')} TOPICS: {r.get('topics')}")
        media = r.get("media") or []
        lines.append(f"MEDIA ({len(media)}):")
        for m in media:
            lines.append("   - " + (m if isinstance(m, str) else json.dumps(m, ensure_ascii=False)))
        lines.append("NOTES: " + (r.get("notes") or ""))
        text = r.get("text") or ""
        lines.append("TEXT[0:400]: " + text[:400].replace("\n", " / "))
out.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("records", sum(1 for l in lines if l.startswith("URL: ")))
