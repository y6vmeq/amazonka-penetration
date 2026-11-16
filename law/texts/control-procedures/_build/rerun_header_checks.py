"""Запускает команду проверки цитат, записанную в шапке каждой из двух выписок, и печатает её итог.

Запуск из корня проекта:
    python -I -X utf8 law/texts/control-procedures/_build/rerun_header_checks.py

Нужен, чтобы убедиться: команда из шапки выполняется как написана и даёт тот же итог,
который в шапке указан.
"""
import re
import shlex
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
FILES = ["law/ukaz-510-2009_kontrol-nadzor.md", "law/razresheniya_kto-razreshil.md"]


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    failed = False
    for rel in FILES:
        text = (ROOT / rel).read_text(encoding="utf-8")
        match = re.search(r"\*\*Проверка цитат:\*\* `(python [^`]+)`\. Итог: `([^`]+)`", text)
        if not match:
            print(rel, ": в шапке не найдена команда проверки")
            failed = True
            continue
        command, stated = match.group(1), match.group(2)
        arguments = shlex.split(command)
        arguments[0] = sys.executable
        result = subprocess.run(arguments, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=900)
        first = result.stdout.splitlines()[0] if result.stdout else result.stderr[-300:]
        actual = first.split(": ", 1)[1] if ": " in first else first
        print(rel)
        print("  в шапке:", stated)
        print("  сейчас: ", actual, "| код возврата", result.returncode)
        if actual != stated or result.returncode != 0:
            failed = True
            for line in result.stdout.splitlines()[1:20]:
                print("   ", line[:300])
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
