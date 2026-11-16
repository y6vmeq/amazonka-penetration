"""Сводит, что именно проверено в этом сборе: по записям raw/manifest.jsonl и журналам.

Запуск из корня проекта:
    python -I -X utf8 sources/official/2026-11-15_cge-lists/scripts/build_checked.py

Пишет checked_summary.txt: счётчики по сайтам и ответам, прямые попытки, обращения к веб-архиву
(по времени), просмотр телеграм-каналов. Ничего не скачивает.
"""
import json
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import unquote, urlsplit

FOLDER = Path("sources/official/2026-11-15_cge-lists")


def read_jsonl(path):
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main():
    manifest = read_jsonl(FOLDER / "raw" / "manifest.jsonl")
    lines = []
    by_host = defaultdict(Counter)
    for record in manifest:
        host = urlsplit(record["url"]).hostname or "?"
        status = record["status"] if record["status"] else ("нет ответа: " + (record.get("error") or "")[:60])
        by_host[host][status] += 1
    lines.append(f"Всего запросов через tools/fetch_raw.py: {len(manifest)}")
    for host in sorted(by_host):
        lines.append(f"  {host}: " + "; ".join(f"{status} × {count}" for status, count in by_host[host].most_common()))
    lines.append("")
    lines.append("Прямые попытки открыть сайты санитарной службы (по одной на адрес):")
    for record in manifest:
        host = urlsplit(record["url"]).hostname or ""
        if host.endswith("cge.by") or host == "mcge.by":
            lines.append(f"  {record['fetched_at'][11:19]} UTC  {unquote(record['url'])[:110]}  ->  "
                         f"{record['status'] or (record.get('error') or '')[:70]}")
    lines.append("")
    lines.append("Обращения к веб-архиву (по времени):")
    for entry in read_jsonl(FOLDER / "wa_log.jsonl"):
        kind = "справка CDX" if "/cdx/" in entry["url"] else "копия страницы"
        lines.append(f"  {entry['at'][11:19]} UTC  {kind:15s} {entry['status']}  {entry['name']}  ({entry['bytes']} байт)")
    wa = read_jsonl(FOLDER / "wa_log.jsonl")
    pages = [entry for entry in wa if "/cdx/" not in entry["url"]]
    lines.append(f"  Итого: запросов копий страниц {len(pages)}, из них отказов 429 — {sum(1 for e in pages if e['status'] == 429)}, "
                 f"успешных — {sum(1 for e in pages if e['status'] == 200)}; справочных запросов CDX {len(wa) - len(pages)}, "
                 f"из них 200 — {sum(1 for e in wa if '/cdx/' in e['url'] and e['status'] == 200)}, "
                 f"503 — {sum(1 for e in wa if '/cdx/' in e['url'] and e['status'] == 503)}, "
                 f"429 — {sum(1 for e in wa if '/cdx/' in e['url'] and e['status'] == 429)}")
    lines.append("")
    scanned = read_jsonl(FOLDER / "tg_scanned.jsonl")
    for channel in sorted({row.get("channel", "mogilevoblcge") for row in scanned}):
        part = [row for row in scanned if row.get("channel", "mogilevoblcge") == channel]
        times = [row[key] for row in part for key in ("first_time", "last_time") if row.get(key)]
        lines.append(f"Сплошной просмотр t.me/s/{channel}: страниц {len(part)}, записи "
                     f"{min(row['min'] for row in part)}–{max(row['max'] for row in part)}; "
                     f"самая ранняя запись {min(times)[:10]}, самая поздняя {max(times)[:10]}")
    keywords = read_jsonl(FOLDER / "tg_keywords.jsonl")
    if keywords:
        lines.append("Поиск названий в предпросмотре телеграм-каналов (канал: слово = число записей в выдаче):")
        grouped = defaultdict(list)
        for row in keywords:
            grouped[row["channel"]].append(f"{row['word']} = {len(row['posts'])}")
        for channel, items in grouped.items():
            lines.append(f"  {channel}: " + "; ".join(items))
    (FOLDER / "checked_summary.txt").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
