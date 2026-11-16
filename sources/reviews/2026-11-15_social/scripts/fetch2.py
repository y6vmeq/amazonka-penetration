"""Обёртка над tools/fetch_raw.py: та же функция fetch() и тот же manifest.jsonl.

Отличия от прямого запуска fetch_raw.py:
  - можно задать несколько URL подряд с паузой;
  - режим vk: запрос без заголовка Accept (с ним vk.com отдаёт пустую оболочку
    без данных), остальные параметры curl те же.

usage: python -I fetch2.py <collection_dir> <pause_sec> <mode: std|vk> <url>|<name> [...]
Печатает по строке JSON (ASCII) на каждый URL.
"""
import json
import subprocess
import sys
import time
from pathlib import Path

PROJECT_TOOLS = Path(r"C:/Users/y6vme/OneDrive/myDocuments/belarus/tools")
sys.path.insert(0, str(PROJECT_TOOLS))
import fetch_raw  # noqa: E402

collection = Path(sys.argv[1])
pause = float(sys.argv[2])
mode = sys.argv[3]
items = sys.argv[4:]

if mode == "vk":
    original_run = subprocess.run

    def run_without_accept(command, *args, **kwargs):
        cleaned = []
        skip = False
        for index, part in enumerate(command):
            if skip:
                skip = False
                continue
            if part == "--header" and index + 1 < len(command) and command[index + 1].startswith("Accept:"):
                skip = True
                continue
            cleaned.append(part)
        return original_run(cleaned, *args, **kwargs)

    fetch_raw.subprocess.run = run_without_accept
elif mode != "std":
    sys.exit("mode must be std or vk")

for index, item in enumerate(items):
    url, _, name = item.partition("|")
    record = fetch_raw.fetch(collection, url, name)
    print(json.dumps(record, ensure_ascii=True))
    if index < len(items) - 1:
        time.sleep(pause)
