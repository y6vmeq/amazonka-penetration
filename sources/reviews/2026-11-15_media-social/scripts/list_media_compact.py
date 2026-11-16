"""Компактная таблица: записи чужих агентов, их ссылки и поля media."""
import json, sys
from pathlib import Path

root = Path(sys.argv[1])
out = Path(sys.argv[2])
agents = sys.argv[3:]
lines = []
for agent in agents:
    path = root / f"2026-11-15_{agent}" / "reviews.jsonl"
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        media = r.get("media") or []
        lines.append(f"## {r['id']} | {r['venue']} | {r['platform']} | {r['kind']} | {r.get('date_iso')} | {r.get('author')} | {r.get('sentiment')} | raw={r.get('raw_file')}")
        lines.append(f"   URL: {r['url']}")
        for m in media:
            s = m if isinstance(m, str) else json.dumps(m, ensure_ascii=False)
            lines.append("   M: " + s[:300])
        lines.append("   N: " + (r.get("notes") or "")[:260].replace("\n", " "))
out.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("lines", len(lines))
