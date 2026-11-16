"""Дописывает строку в рабочую таблицу checked.jsonl (одна проверенная страница).

Запуск из корня проекта:
    python -I -X utf8 sources/reviews/2026-11-15_article-comments/scripts/checked.py \
        --n <номер сырой копии> --block yes|no|closed|none-visible --total N --collected N \
        --why "<почему не собрано>" [--shot screenshots/...] [--notes "..."] [--group "..."]
Адрес, заголовок и время берутся из work/info_NNN.json. Если сырой копии нет
(страница закрыта и не сохранялась), адрес задаётся через --url.
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

BASE = Path("sources/reviews/2026-11-15_article-comments")
BLOCK = {
    "yes": "есть",
    "no": "нет",
    "closed": "закрыт (вход, проверка или отключён)",
    "none-visible": "блок есть, комментариев нет",
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=0)
    parser.add_argument("--url", default="")
    parser.add_argument("--title", default="")
    parser.add_argument("--block", required=True, choices=sorted(BLOCK))
    parser.add_argument("--total", default="0", help="число или 'unknown'")
    parser.add_argument("--collected", type=int, default=0)
    parser.add_argument("--why", default="")
    parser.add_argument("--shot", default="")
    parser.add_argument("--notes", default="")
    parser.add_argument("--group", default="")
    parser.add_argument("--engine", default="")
    args = parser.parse_args()

    info = {}
    if args.n:
        info = json.loads((BASE / "work" / f"info_{args.n:03d}.json").read_text(encoding="utf-8"))
    total = None if args.total == "unknown" else int(args.total)
    record = {
        "url": args.url or info.get("url") or "",
        "title": args.title or info.get("title") or "",
        "group": args.group,
        "checked_at": info.get("at") or datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "comments_block": BLOCK[args.block],
        "comments_engine": args.engine,
        "comments_total": total,
        "comments_collected": args.collected,
        "not_collected_reason": args.why,
        "raw_file": info.get("html"),
        "screenshot": args.shot or None,
        "notes": args.notes,
    }
    with (BASE / "checked.jsonl").open("a", encoding="utf-8", newline="\n") as table:
        table.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(json.dumps(record, ensure_ascii=False))


if __name__ == "__main__":
    main()
