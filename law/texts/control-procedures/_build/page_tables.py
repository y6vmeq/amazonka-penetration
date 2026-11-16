"""Печатает строки таблиц сохранённой страницы ЭТАЛОН-ONLINE: одна строка таблицы — одна строка вывода.

Запуск из корня проекта:
    python -I -X utf8 law/texts/control-procedures/_build/page_tables.py <страница.html> [<файл_вывода.txt>]

Ячейки разделяются знаком « | », абзацы внутри ячейки — знаком « ¶ ». Нужен, чтобы найти
в едином перечне административных процедур и в перечнях Указа № 227 нужные строки.
Страница не исполняется: читается как текст.
"""
import html
import re
import sys
from pathlib import Path

SUPERSCRIPT = "⁰¹²³⁴⁵⁶⁷⁸⁹"


def cell_text(raw):
    raw = re.sub(
        r"(?is)<sup>\s*(\d+)\s*</sup>",
        lambda match: "".join(SUPERSCRIPT[int(digit)] for digit in match.group(1)),
        raw,
    )
    raw = re.sub(r"(?i)<br\s*/?>|</p>", " ¶ ", raw)
    raw = html.unescape(re.sub(r"<[^>]*>", " ", raw)).replace("\xa0", " ")
    raw = re.sub(r"\s+", " ", raw).strip()
    raw = re.sub(r"^(?:¶ ?)+|(?: ?¶)+$", "", raw).strip()
    return re.sub(r"\s*¶\s*", " ¶ ", raw)


def table_rows(page):
    page = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", page)
    rows = []
    for row in re.findall(r"(?is)<tr\b[^>]*>(.*?)</tr>", page):
        cells = [cell_text(cell) for cell in re.findall(r"(?is)<td\b[^>]*>(.*?)</td>", row)]
        if any(cells):
            rows.append(cells)
    return rows


def main():
    if len(sys.argv) not in (2, 3):
        sys.exit("usage: page_tables.py <page.html> [<out.txt>]")
    page = Path(sys.argv[1]).read_bytes().decode("utf-8-sig", errors="replace")
    rows = table_rows(page)
    out = "\n".join(f"{number:05d}\t" + " | ".join(cells) for number, cells in enumerate(rows))
    if len(sys.argv) == 3:
        Path(sys.argv[2]).write_text(out, encoding="utf-8", newline="\n")
        print("rows", len(rows), "->", sys.argv[2])
    else:
        sys.stdout.reconfigure(encoding="utf-8")
        print(out)


if __name__ == "__main__":
    main()
