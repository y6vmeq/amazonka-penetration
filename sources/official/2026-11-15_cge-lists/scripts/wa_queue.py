"""Проходит очередь копий из веб-архива по одной, с паузами, и сразу разбирает полученное.

Запуск из корня проекта:
    python -I -X utf8 sources/official/2026-11-15_cge-lists/scripts/wa_queue.py <файл очереди> [--gap N] [--limit K]

Файл очереди: строки «<адрес копии> <имя>»; строки с # пропускаются. Уже полученные (ответ 200 в
wa_log.jsonl) повторно не запрашиваются. Каждый запрос делает wa_fetch.py (в нём зашиты правила:
один запрос за раз, пауза, остановка на отказе 429). При первом же отказе или ошибке очередь
останавливается. Полученные страницы списков сразу разбирает parse_list.py, страницы архива сайта
и ленты — parse_index.py.
"""
import json
import subprocess
import sys
from pathlib import Path

FOLDER = Path("sources/official/2026-11-15_cge-lists")
SCRIPTS = FOLDER / "scripts"


def done_names():
    log = FOLDER / "wa_log.jsonl"
    if not log.is_file():
        return set()
    return {json.loads(line)["name"] for line in log.read_text(encoding="utf-8").splitlines()
            if line.strip() and json.loads(line)["status"] == 200}


def main():
    arguments = sys.argv[1:]
    queue_file = Path(arguments[0])
    gap, limit = "100", 999
    if "--gap" in arguments:
        gap = arguments[arguments.index("--gap") + 1]
    if "--limit" in arguments:
        limit = int(arguments[arguments.index("--limit") + 1])
    pairs = []
    for line in queue_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        url, name = line.split()[:2]
        pairs.append((url, name))
    finished = done_names()
    made = 0
    for url, name in pairs:
        if name in finished:
            continue
        if made >= limit:
            print("limit reached")
            break
        result = subprocess.run(
            [sys.executable, "-I", "-X", "utf8", str(SCRIPTS / "wa_fetch.py"), "--gap", gap, "--max-wait", "400", url, name],
            capture_output=True, text=True, encoding="utf-8",
        )
        made += 1
        entry = None
        for out_line in result.stdout.splitlines():
            if out_line.startswith("{"):
                entry = json.loads(out_line)
        print(f"[{name}] exit={result.returncode} status={entry['status'] if entry else '?'} "
              f"bytes={entry['bytes'] if entry else '?'} file={entry['file'] if entry else '?'}", flush=True)
        if result.returncode != 0 or not entry or entry["status"] != 200 or not entry["file"]:
            print(result.stdout.strip().splitlines()[-1] if result.stdout.strip() else result.stderr[:300], flush=True)
            print("queue stopped", flush=True)
            sys.exit(2)
        path = FOLDER / entry["file"]
        parser = "parse_index.py" if ("date-" in name or "feed" in name or "category" in name or "author" in name) else "parse_list.py"
        parsed = subprocess.run([sys.executable, "-I", "-X", "utf8", str(SCRIPTS / parser), str(path)],
                                capture_output=True, text=True, encoding="utf-8")
        for out_line in parsed.stdout.splitlines():
            if parser == "parse_index.py" or out_line.startswith(("title:", "canonical:", "blocks:", "city blocks:", "   M:", "hits:", "   HIT", "hits outside")):
                print("    " + out_line[:330], flush=True)
        if parser == "parse_list.py":
            rebuild()
    print("queue pass finished", flush=True)


def rebuild():
    """После каждого полученного списка — сразу пересобрать months.jsonl и quotes.jsonl и сверить цитаты."""
    built = subprocess.run([sys.executable, "-I", "-X", "utf8", str(SCRIPTS / "build_months.py")],
                           capture_output=True, text=True, encoding="utf-8")
    tail = built.stdout.strip().splitlines()[-1] if built.stdout.strip() else built.stderr[-300:]
    check = subprocess.run([sys.executable, "-I", "-X", "utf8", "tools/quotes_check.py", str(FOLDER)],
                           capture_output=True, text=True, encoding="utf-8")
    print("    rebuilt:", tail, "|", check.stdout.strip()[-160:], flush=True)


if __name__ == "__main__":
    main()
