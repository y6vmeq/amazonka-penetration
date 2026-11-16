"""Бережная загрузка СУЩЕСТВУЮЩИХ копий из веб-архива через tools/fetch_raw.py.

Запуск из корня проекта:
    python -I -X utf8 sources/official/2026-11-15_cge-lists/scripts/wa_fetch.py <url> <имя> [<url> <имя> ...]
    python -I -X utf8 sources/official/2026-11-15_cge-lists/scripts/wa_fetch.py --status

Правила (заданы постановщиком задачи) зашиты в код:
  * один запрос за раз, между запросами к архиву не меньше 65 секунд;
  * после отказа HTTP 429 — пауза не меньше 15 минут (до неё скрипт запросов не делает
    и сразу завершается: ждать надо отдельной командой);
  * после трёх отказов 429 подряд работа с архивом прекращается совсем;
  * только адреса web.archive.org/web/<метка>id_/... и web.archive.org/cdx/...;
    новых копий скрипт не создаёт (адреса /save/ запрещены).
Состояние хранится в scripts/wa_state.json, журнал — в wa_log.jsonl.
Скрипт сам ждёт до разрешённого времени, но не дольше --max-wait секунд (по умолчанию 70).
"""
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

FOLDER = Path("sources/official/2026-11-15_cge-lists")
STATE = FOLDER / "scripts" / "wa_state.json"
LOG = FOLDER / "wa_log.jsonl"
GAP = 65
PENALTY = 15 * 60 + 20
ALLOWED = ("http://web.archive.org/web/", "https://web.archive.org/web/",
           "http://web.archive.org/cdx/", "https://web.archive.org/cdx/",
           "http://archive.org/wayback/available", "https://archive.org/wayback/available")


def load():
    if STATE.is_file():
        return json.loads(STATE.read_text(encoding="utf-8"))
    return {"last_request": 0, "blocked_until": 0, "consecutive_429": 0, "total_429": 0, "total_requests": 0, "stopped": False}


def save(state):
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")


def stamp(seconds):
    return datetime.fromtimestamp(seconds, timezone.utc).strftime("%H:%M:%S") if seconds else "-"


def others():
    """Последний запрос к архиву и последний отказ 429 по ВСЕМ журналам проекта.

    С этого компьютера к архиву могут обращаться и другие агенты: их запросы тоже
    учитываются, чтобы пауза выдерживалась относительно любого запроса.
    """
    latest, latest_429 = 0.0, 0.0
    for manifest in Path("sources").rglob("manifest.jsonl"):
        try:
            lines = manifest.read_text(encoding="utf-8", errors="replace").splitlines()[-600:]
        except OSError:
            continue
        for line in lines:
            if "archive.org" not in line:
                continue
            try:
                record = json.loads(line)
                moment = datetime.fromisoformat(record["fetched_at"]).timestamp()
            except (ValueError, KeyError, TypeError):
                continue
            if "web.archive.org" not in str(record.get("url", "")):
                continue
            latest = max(latest, moment)
            if record.get("status") == 429:
                latest_429 = max(latest_429, moment)
    return latest, latest_429


def allowed_time(state):
    latest, latest_429 = others()
    return max(state["last_request"] + GAP, state["blocked_until"], latest + GAP, latest_429 + PENALTY)


def main():
    arguments = sys.argv[1:]
    state = load()
    if arguments[:1] == ["--status"]:
        now = time.time()
        print(json.dumps(state, ensure_ascii=False))
        latest, latest_429 = others()
        print("now", stamp(now), "last", stamp(state["last_request"]), "blocked_until", stamp(state["blocked_until"]),
              "any-agent last", stamp(latest), "any-agent last 429", stamp(latest_429),
              "next allowed in", max(0, int(allowed_time(state) - now)), "s")
        return
    max_wait = 70
    global GAP
    while arguments[:1] in (["--max-wait"], ["--gap"]):
        if arguments[0] == "--max-wait":
            max_wait = int(arguments[1])
        else:
            GAP = max(65, int(arguments[1]))     # пауза между запросами: не меньше 65 секунд
        arguments = arguments[2:]
    if len(arguments) % 2 or not arguments:
        sys.exit("usage: wa_fetch.py [--max-wait N] <url> <name> [...]")
    pairs = list(zip(arguments[0::2], arguments[1::2]))
    for url, name in pairs:
        if not url.startswith(ALLOWED) or "/save/" in url:
            sys.exit(f"not an allowed archive url: {url}")
    for url, name in pairs:
        state = load()
        if state["stopped"]:
            print("STOPPED: no more archive requests:", state.get("stop_reason", "three 429 in a row"))
            sys.exit(3)
        allowed_at = allowed_time(state)
        wait = allowed_at - time.time()
        if wait > max_wait:
            print(f"WAIT: next archive request allowed at {stamp(allowed_at)} UTC (in {int(wait)} s); not fetching {name}")
            sys.exit(4)
        if wait > 0:
            time.sleep(wait)
        state["last_request"] = time.time()
        state["total_requests"] += 1
        save(state)
        result = subprocess.run(
            [sys.executable, "-I", "-X", "utf8", "tools/fetch_raw.py", str(FOLDER), url, name],
            capture_output=True, text=True, encoding="utf-8",
        )
        state["last_request"] = time.time()
        try:
            record = json.loads(result.stdout.strip().splitlines()[-1])
        except (IndexError, json.JSONDecodeError):
            record = {"file": None, "status": 0, "bytes": 0, "error": (result.stdout + result.stderr)[:300], "url": url}
        entry = {"at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "name": name, "url": url,
                 "status": record.get("status"), "file": record.get("file"), "bytes": record.get("bytes"),
                 "final_url": record.get("final_url"), "error": record.get("error")}
        if record.get("status") == 429:
            state["consecutive_429"] += 1
            state["total_429"] += 1
            state["blocked_until"] = time.time() + PENALTY
            if state["consecutive_429"] >= 3:
                state["stopped"] = True
        elif record.get("status") and "/web/" in url:
            # Счётчик отказов подряд сбрасывает только успешная выдача КОПИИ СТРАНИЦЫ.
            # Ответ справочного интерфейса CDX его не сбрасывает: отказывает именно выдача копий,
            # и удачный справочный запрос не должен «обнулять» три отказа подряд.
            state["consecutive_429"] = 0
        save(state)
        with LOG.open("a", encoding="utf-8", newline="\n") as log:
            log.write(json.dumps(entry, ensure_ascii=False) + "\n")
        print(json.dumps(entry, ensure_ascii=True))
        if record.get("status") == 429:
            print(f"429: pause until {stamp(state['blocked_until'])} UTC; consecutive={state['consecutive_429']} stopped={state['stopped']}")
            sys.exit(2)
    print("done")


if __name__ == "__main__":
    main()
