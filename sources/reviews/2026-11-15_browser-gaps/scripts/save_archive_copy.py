"""Сохраняет выгрузку копии Wayback Machine (через save_capture.py) и печатает ключевые поля.

Запуск из корня проекта:
  python -I sources/reviews/2026-11-15_browser-gaps/scripts/save_archive_copy.py <метка_времени_копии>
"""
import io
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
COLLECTION = HERE.parent
stamp = sys.argv[1]
pretty = f"{stamp[6:8]}.{stamp[4:6]}.{stamp[0:4]} {stamp[8:10]}:{stamp[10:12]}:{stamp[12:14]} UTC"
result = subprocess.run(
    [sys.executable, "-I", str(HERE / "save_capture.py"), str(COLLECTION), str(COLLECTION / "raw" / "_tmp_capture.json"),
     f"web-archive_b4y-21181_{stamp}", f"Копия Wayback Machine от {pretty} объявления b4y.by/product/21181."],
    capture_output=True, text=True,
)
if result.returncode != 0:
    sys.exit(result.stderr or result.stdout)
files = json.loads(result.stdout)
out = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
out.write(", ".join(item["file"] for item in files) + "\n")
data_file = next(item["file"] for item in files if item["file"].endswith(".json"))
data = json.loads((COLLECTION / data_file).read_text(encoding="utf-8"))["data"]
if data.get("archive_timestamp") != stamp:
    out.write(f"WARNING: page timestamp {data.get('archive_timestamp')} differs from requested {stamp}\n")
for key, value in data.items():
    text = json.dumps(value, ensure_ascii=False)
    out.write(f"{key} = {text[:700]}\n")
out.flush()
