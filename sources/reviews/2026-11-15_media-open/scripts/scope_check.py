"""Проверяет текстовые файлы прохода фильтром проекта tools/scope_filter.py (заведения вне рамок работы).

Запуск из корня проекта:
    python -I -X utf8 sources/reviews/2026-11-15_media-open/scripts/scope_check.py
Ничего не правит: только печатает файлы и строки, где фильтр видит упоминание.
"""
import importlib.util
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
ROOT = BASE.parent.parent.parent
spec = importlib.util.spec_from_file_location("scope_filter", ROOT / "tools" / "scope_filter.py")
scope_filter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scope_filter)

hits = 0
checked = 0
for path in sorted(BASE.rglob("*")):
    if not path.is_file() or path.suffix.lower() not in {".md", ".txt", ".json", ".jsonl", ".tsv", ".log"}:
        continue
    checked += 1
    for number, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        if scope_filter.mentions(line):
            hits += 1
            print(f"{path.relative_to(BASE).as_posix()}:{number}: {line[:160]}")
print(f"checked={checked} hits={hits}")
