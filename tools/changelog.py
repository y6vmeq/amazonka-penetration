"""Журнал изменений проекта: запись в CHANGELOG.md и блок «Последние изменения» в README.md.

Запуск из корня проекта:
    python -I -X utf8 tools/changelog.py add "<что изменилось и в каких файлах>" [--date ДД.ММ.ГГГГ]
    python -I -X utf8 tools/changelog.py sync

add  — ставит запись первой под заголовком даты (по умолчанию сегодня по минскому времени;
       заголовок создаётся, если его нет) и обновляет блок в README.md;
sync — только обновляет блок в README.md по журналу (последние записи).

Правило проекта (CLAUDE.md, раздел «Журнал изменений и коммиты»): одно изменение — одна запись
в журнале и один коммит. Запись проверяется фильтром tools/scope_filter.py: названий заведений,
исключённых из работы, в журнале быть не должно. Имён людей и учётных записей тоже не писать.
"""
import argparse
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import scope_filter  # noqa: E402  (соседний файл проекта)

ROOT = Path(__file__).resolve().parent.parent
CHANGELOG = ROOT / "CHANGELOG.md"
README = ROOT / "README.md"
START, END = "<!-- changelog:start -->", "<!-- changelog:end -->"
LATEST = 8
DATE_HEADING = re.compile(r"^## (\d{2}\.\d{2}\.\d{4})\s*$")


def today() -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=3)).strftime("%d.%m.%Y")


def entries(text: str) -> list[tuple[str, str]]:
    """Записи журнала по порядку файла: (дата, текст записи без маркера списка)."""
    found, date = [], None
    for line in text.split("\n"):
        heading = DATE_HEADING.match(line)
        if heading:
            date = heading.group(1)
        elif date and line.startswith("- "):
            found.append((date, line[2:].strip()))
        elif date and found and line.startswith("  ") and line.strip():
            found[-1] = (found[-1][0], found[-1][1] + " " + line.strip())
    return found


def add(text: str, date: str) -> None:
    entry = " ".join(text.split())
    if not entry:
        sys.exit("пустая запись")
    if scope_filter.mentions(entry):
        sys.exit("в записи есть упоминание заведения, исключённого из работы: переформулируйте")
    lines = CHANGELOG.read_text(encoding="utf-8").split("\n")
    heading = f"## {date}"
    if heading in lines:
        index = lines.index(heading) + 1
        while index < len(lines) and not lines[index].strip():
            index += 1
        lines[index:index] = [f"- {entry}"]
    else:
        first = next((i for i, line in enumerate(lines) if DATE_HEADING.match(line)), len(lines))
        lines[first:first] = [heading, "", f"- {entry}", ""]
    CHANGELOG.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print(f"журнал: запись добавлена под {date}")


def sync() -> None:
    latest = entries(CHANGELOG.read_text(encoding="utf-8"))[:LATEST]
    block = "\n".join(f"- **{date}.** {text}" for date, text in latest)
    readme = README.read_text(encoding="utf-8")
    if START not in readme or END not in readme:
        sys.exit(f"в README.md нет меток {START} и {END}")
    head, rest = readme.split(START, 1)
    _, tail = rest.split(END, 1)
    README.write_text(f"{head}{START}\n{block}\n{END}{tail}", encoding="utf-8", newline="\n")
    print(f"README.md: в блоке «Последние изменения» записей — {len(latest)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Журнал изменений проекта")
    commands = parser.add_subparsers(dest="command", required=True)
    add_parser = commands.add_parser("add", help="добавить запись и обновить README.md")
    add_parser.add_argument("text")
    add_parser.add_argument("--date", default=today())
    commands.add_parser("sync", help="обновить блок в README.md по журналу")
    args = parser.parse_args()
    if args.command == "add":
        if not re.fullmatch(r"\d{2}\.\d{2}\.\d{4}", args.date):
            sys.exit("дата — в виде ДД.ММ.ГГГГ")
        add(args.text, args.date)
    sync()


if __name__ == "__main__":
    main()
