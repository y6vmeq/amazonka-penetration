"""Сжимает сценарий для browser_run_code_unsafe: убирает строки-комментарии и отступы.
Запуск: python -I -X utf8 minify.py <файл.js>  ->  <файл>.min.js рядом."""
import sys
from pathlib import Path

source = Path(sys.argv[1])
lines = [line.strip() for line in source.read_text(encoding="utf-8").splitlines()]
lines = [line for line in lines if line and not line.startswith("//")]
target = source.with_suffix(".min.js")
target.write_text(" ".join(lines) + "\n", encoding="utf-8", newline="\n")
print(target.name, target.stat().st_size)
