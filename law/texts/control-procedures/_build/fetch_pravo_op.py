"""Скачивает PDF официального опубликования акта с pravo.by по регистрационному номеру.

Запуск из корня проекта:
    python -I -X utf8 law/texts/control-procedures/_build/fetch_pravo_op.py <рег. номер> [<рег. номер> ...]

Для каждого номера: загружает карточку акта (https://pravo.by/document/?guid=12551&p0=<номер>),
находит в ней ссылку на PDF (/upload/docs/op/…pdf), загружает PDF и извлекает текст
(tools/pdf_text.py). Всё сохраняется через tools/fetch_raw.py в law/texts/control-procedures/raw/
с записью в manifest.jsonl. Между запросами пауза 2 секунды.

Сделан по образцу law/texts/trade-ads-smoking/_build/fetch_pravo_op.py; отличается только папкой.
"""
import json
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
FOLDER = "law/texts/control-procedures"


def fetch(url, name):
    result = subprocess.run(
        [sys.executable, "-I", "-X", "utf8", "tools/fetch_raw.py", FOLDER, url, name],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=180,
    )
    line = [l for l in result.stdout.splitlines() if l.strip().startswith("{")]
    return json.loads(line[-1]) if line else {"status": None, "file": None, "error": result.stderr[-200:]}


sys.stdout.reconfigure(encoding="utf-8")
for regnum in sys.argv[1:]:
    card = fetch(f"https://pravo.by/document/?guid=12551&p0={regnum}", f"pravo-card-{regnum}")
    time.sleep(2)
    if card.get("status") != 200 or not card.get("file"):
        print(regnum, "карточка не получена:", card.get("status"), card.get("error"))
        continue
    html_text = (ROOT / FOLDER / card["file"]).read_bytes().decode("utf-8", errors="replace")
    title = re.search(r"<title>(.*?)</title>", html_text, re.S)
    links = sorted(set(re.findall(r'href="(/upload/docs/op/[^"]+\.pdf)"', html_text)))
    if not links:
        print(regnum, "в карточке нет ссылки на PDF")
        continue
    pdf = fetch("https://pravo.by" + links[0], f"pravo-op-{regnum}")
    time.sleep(2)
    if pdf.get("status") != 200 or not pdf.get("file"):
        print(regnum, "PDF не получен:", pdf.get("status"), pdf.get("error"))
        continue
    subprocess.run([sys.executable, "-I", "-X", "utf8", "tools/pdf_text.py", str(Path(FOLDER) / pdf["file"])],
                   cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=180)
    text_file = (ROOT / FOLDER / pdf["file"]).with_suffix(".txt")
    chars = len(text_file.read_text(encoding="utf-8")) if text_file.is_file() else 0
    head = re.sub(r"\s+", " ", title.group(1)).strip()[:150] if title else ""
    print(regnum, "|", pdf["file"], "| байт", pdf.get("bytes"), "| знаков", chars, "|", head)
