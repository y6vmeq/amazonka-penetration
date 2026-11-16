"""Проверки двух выписок перед сдачей: исключённые заведения, фамилии, служебные пометки, таблицы.

Запуск из корня проекта:
    python -I -X utf8 law/texts/control-procedures/_build/final_checks.py

Проверяет law/ukaz-510-2009_kontrol-nadzor.md и law/razresheniya_kto-razreshil.md:
  - фильтр tools/scope_filter.py не находит упоминаний заведений, исключённых из работы;
  - в тексте нет подписей под актами (фамилий должностных лиц);
  - не осталось пометок-заполнителей в двойных скобках;
  - в каждой строке таблицы число граф совпадает с числом граф в её заголовке;
  - в каждом абзаце сходится число открывающих и закрывающих кавычек-ёлочек.
Код возврата 1, если что-то найдено.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "tools"))
import scope_filter  # noqa: E402  (файл проекта)

FILES = ["law/ukaz-510-2009_kontrol-nadzor.md", "law/razresheniya_kto-razreshil.md"]
SIGNATURES = re.compile(r"[А-ЯЁ]\.\s?[А-ЯЁ][а-яё]+(?=\s*$)|[А-ЯЁ]\.[А-ЯЁ]\.\s?[А-ЯЁ][а-яё]+")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    problems = 0
    for rel in FILES:
        text = (ROOT / rel).read_text(encoding="utf-8")
        lines = text.split("\n")
        if scope_filter.mentions(text):
            problems += 1
            print(rel, ": фильтр нашёл упоминание исключённого заведения")
        for number, line in enumerate(lines, 1):
            if "⟦" in line or "⟧" in line:
                problems += 1
                print(f"{rel}:{number}: осталась пометка-заполнитель")
            found = SIGNATURES.findall(line)
            if found:
                problems += 1
                print(f"{rel}:{number}: похоже на фамилию с инициалами: {found[:3]}")
        header_cells = None
        for number, line in enumerate(lines, 1):
            if line.startswith("|"):
                cells = len(re.findall(r"(?<!\\)\|", line)) - 1
                if header_cells is None:
                    header_cells = cells
                elif cells != header_cells:
                    problems += 1
                    print(f"{rel}:{number}: граф {cells}, в заголовке {header_cells}")
            else:
                header_cells = None
        for index, paragraph in enumerate(re.split(r"\n[ \t]*\n", text), 1):
            if paragraph.count("«") != paragraph.count("»"):
                problems += 1
                print(f"{rel}: абзац {index}: кавычек « {paragraph.count('«')}, » {paragraph.count('»')}: {paragraph[:80]!r}")
        print(rel, "| строк", len(lines), "| знаков", len(text))
    print("problems:", problems)
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
