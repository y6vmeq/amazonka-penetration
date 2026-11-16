"""Печатает сохранённую страницу ЭТАЛОН-ONLINE по абзацам с номерами строк.

Запуск из корня проекта:
    python -I -X utf8 law/texts/control-procedures/_build/page_paragraphs.py <страница.html> [<файл_вывода.txt>]

Нужен, чтобы найти в тексте акта нужные пункты перед сборкой выписки. Теги убираются,
надстрочные цифры превращаются в знаки ¹²³, ячейки таблицы разделяются знаком « | ».
Страница не исполняется: читается как текст.
"""
import html
import re
import sys
from pathlib import Path

SUPERSCRIPT = "⁰¹²³⁴⁵⁶⁷⁸⁹"


def paragraphs(text):
    text = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", text)
    text = re.sub(
        r"(?is)<sup>\s*(\d+)\s*</sup>",
        lambda match: "".join(SUPERSCRIPT[int(digit)] for digit in match.group(1)),
        text,
    )
    text = re.sub(r"(?i)</td>", " | ", text)
    text = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</tr>|</h\d>|</li>", "\n", text)
    text = html.unescape(re.sub(r"<[^>]*>", "", text)).replace("\xa0", " ")
    rows = [re.sub(r"[ \t]+", " ", row).strip() for row in text.splitlines()]
    return [row for row in rows if row and row != "|"]


def main():
    if len(sys.argv) not in (2, 3):
        sys.exit("usage: page_paragraphs.py <page.html> [<out.txt>]")
    page = Path(sys.argv[1]).read_bytes().decode("utf-8-sig", errors="replace")
    rows = paragraphs(page)
    out = "\n".join(f"{number:05d}\t{row}" for number, row in enumerate(rows))
    if len(sys.argv) == 3:
        Path(sys.argv[2]).write_text(out, encoding="utf-8", newline="\n")
        print("rows", len(rows), "->", sys.argv[2])
    else:
        sys.stdout.reconfigure(encoding="utf-8")
        print(out)


if __name__ == "__main__":
    main()
