"""Ищет акт в Национальном реестре правовых актов на pravo.by и печатает найденные карточки.

Запуск из корня проекта:
    python -I -X utf8 law/texts/control-procedures/_build/reestr_search.py <имя> [p0=<слова названия>] [num_pr=<номер>] [date_pr=<дд.мм.гггг>] [date_pr_start=…] [date_pr_end=…] [r_sect=<раздел>]

Страница результатов сохраняется через tools/fetch_raw.py в law/texts/control-procedures/raw/
(с записью в manifest.jsonl). Печатаются регистрационные номера и названия из результатов.
Нужен только для того, чтобы узнать регистрационный номер акта; тексты берутся отдельно.
"""
import html
import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[4]
FOLDER = "law/texts/control-procedures"


def main():
    if len(sys.argv) < 3:
        sys.exit("usage: reestr_search.py <name> key=value [key=value ...]")
    name = sys.argv[1]
    params = dict(item.split("=", 1) for item in sys.argv[2:])
    url = "https://pravo.by/natsionalnyy-reestr/poisk-v-reestre/?" + urlencode(params)
    result = subprocess.run(
        [sys.executable, "-I", "-X", "utf8", "tools/fetch_raw.py", FOLDER, url, "reestr-poisk-" + name],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=180,
    )
    lines = [line for line in result.stdout.splitlines() if line.strip().startswith("{")]
    if not lines:
        sys.exit("fetch failed: " + result.stderr[-300:])
    record = json.loads(lines[-1])
    sys.stdout.reconfigure(encoding="utf-8")
    print("saved", record.get("file"), "status", record.get("status"))
    if not record.get("file"):
        return
    page = (ROOT / FOLDER / record["file"]).read_bytes().decode("utf-8", errors="replace")
    found = re.findall(r'(?is)<a[^>]+href="(/document/\?guid=3961&(?:amp;)?p0=([^"&]+))"[^>]*>(.*?)</a>', page)
    seen = set()
    for _, regnum, title in found:
        text = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]*>", " ", title))).strip()
        if (regnum, text) in seen or not text:
            continue
        seen.add((regnum, text))
        print(regnum, "|", text[:260])
    print("results:", len(seen))


if __name__ == "__main__":
    main()
