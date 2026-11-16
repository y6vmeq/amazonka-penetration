"""Разбирает официальный PDF акта на пункты и абзацы по отступам первой строки.

Запуск из корня проекта:
    python -I law/texts/sanitary-obshchepit/_build/extract_points.py <файл.pdf> <out.json>

Результат: {"<номер пункта>": {"paragraphs": [{"text", "pages", "breaks"}, ...]}}.
pages — страницы абзаца; breaks — позиции в тексте, где абзац переходит на новую страницу
(между ними в сырой копии стоит колонтитул, поэтому при сверке такой абзац делят на части).
Абзац начинается со строки с отступом (красная строка). Слово, перенесённое по дефису
(«санитарно-» / «гигиенического»), склеивается без пробела. Колонтитулы отбрасываются.
Заголовки глав в пункты не попадают.
"""
import json
import re
import sys
from pathlib import Path

import pymupdf

HEADER = re.compile(r"^Национальный правовой Интернет-портал Республики Беларусь, \d\d\.\d\d\.\d{4}, \d+/\d+$")
INDENT = 12  # пунктов правее левого поля — красная строка


def page_lines(page):
    """Строки страницы: (y, x0, текст), сверху вниз; куски одной строки склеены."""
    rows = {}
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            text = "".join(span["text"] for span in line["spans"])
            if not text.strip():
                continue
            key = round(line["bbox"][1] / 3)
            rows.setdefault(key, []).append((line["bbox"][0], text))
    result = []
    for key in sorted(rows):
        parts = sorted(rows[key])
        text = re.sub(r"\s+", " ", " ".join(part[1].strip() for part in parts)).strip()
        result.append((key * 3, parts[0][0], text))
    return result


def main():
    source, target = sys.argv[1], sys.argv[2]
    paragraphs = []  # {"text", "page", "centered"}
    with pymupdf.open(source) as document:
        for page_number, page in enumerate(document, 1):
            lines = page_lines(page)
            body = [line for line in lines if not HEADER.match(line[2]) and not re.fullmatch(r"\d+", line[2])]
            if not body:
                continue
            margin = min(x0 for _, x0, _ in body)
            for _, x0, text in body:
                starts = x0 > margin + INDENT
                if starts or not paragraphs:
                    paragraphs.append({"text": text, "pages": [page_number], "breaks": []})
                else:
                    last = paragraphs[-1]
                    if page_number not in last["pages"]:
                        # абзац продолжается на новой странице: запоминаем место разрыва
                        last["pages"].append(page_number)
                        last["breaks"].append(len(last["text"]))
                    if last["text"].endswith("-") and text[:1].islower():
                        last["text"] += text
                    else:
                        last["text"] += " " + text
    points, current, expected, started = {}, None, 1, False
    for paragraph in paragraphs:
        text = paragraph["text"]
        if text.startswith("ГЛАВА 1"):
            started = True
        if not started:
            continue
        if re.match(r"^ГЛАВА \d+", text) or (text.isupper() and len(text) > 8):
            current = None if re.match(r"^ГЛАВА \d+", text) else current
            if current is None:
                continue
        if re.match(rf"^{expected}\. ", text):
            current = expected
            points[str(current)] = {"paragraphs": []}
            expected += 1
        if current is not None:
            points[str(current)]["paragraphs"].append(
                {"text": text, "pages": paragraph["pages"], "breaks": paragraph["breaks"]}
            )
    Path(target).write_text(json.dumps(points, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    print(f"points={len(points)} paragraphs={sum(len(point['paragraphs']) for point in points.values())}")


if __name__ == "__main__":
    main()
