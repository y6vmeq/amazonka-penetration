"""Переводит рабочий файл Markdown (заголовки, абзацы, примечания «>», таблицы, списки) в документ Word.

Запуск из корня проекта:
    python -I -X utf8 tools/md_to_docx.py <файл.md> <файл.docx> [--landscape] [--strip-refs]

--landscape   альбомный лист A4 (удобно для широких таблиц);
--strip-refs  убрать служебные ссылки проекта: пути в обратных кавычках (`law/…`, `strategy/…`),
              номера записей сборов в скобках (logged-in-004 и т. п.). Предложение, которое состоит
              из одной такой ссылки («Разборы: `…`.»), убирается целиком.

Ширина столбцов таблиц подбирается по длине текста. Нужна библиотека python-docx.
"""
import re
import sys
from pathlib import Path

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

FONT = "Arial"
INK = RGBColor(0x1E, 0x2A, 0x32)
HEAD = RGBColor(0x12, 0x40, 0x3C)
HEADER_FILL = "DDE9E4"
NOTE_FILL = "F3F6F5"
RECORD_ID = re.compile(r"\s*\((?:[a-z]+(?:-[a-z]+)*-\d{3}[^()]*)\)")
REF_IN_BRACKETS = re.compile(r"\s*\([^()]*`[^()]*\)")
SENTENCE_END = re.compile(r"(?<=[.!?])\s+")
TABLE_ROW = re.compile(r"^\s*\|.*\|\s*$")
TABLE_RULE = re.compile(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$")
NUMBERED = re.compile(r"^\s*\d+[.)]\s+")


def strip_refs(text, whole_sentences=True):
    """Убирает служебные ссылки проекта из текста."""
    text = REF_IN_BRACKETS.sub("", text)
    text = RECORD_ID.sub("", text)
    if "`" not in text:
        return text
    if whole_sentences:
        kept = [part for part in SENTENCE_END.split(text) if "`" not in part]
        return " ".join(kept)
    text = re.sub(r"\s*[—–-]\s*`[^`]*`", "", text)
    return re.sub(r"`[^`]*`", "", text).strip(" ;,")


def set_fonts(run_or_style_element, name):
    rpr = run_or_style_element.get_or_add_rPr()
    fonts = rpr.find(qn("w:rFonts"))
    if fonts is None:
        fonts = OxmlElement("w:rFonts")
        rpr.append(fonts)
    for attribute in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        fonts.set(qn(attribute), name)
    # шрифт темы в стандартных стилях заголовков перебивает заданный: убираем ссылки на тему
    for attribute in ("w:asciiTheme", "w:hAnsiTheme", "w:cstheme", "w:eastAsiaTheme"):
        if fonts.get(qn(attribute)) is not None:
            del fonts.attrib[qn(attribute)]


def add_runs(paragraph, text, size=None, bold=False, italic=False, color=None):
    """Добавляет текст с разметкой **полужирный** и `код`."""
    for index, chunk in enumerate(re.split(r"(\*\*[^*]+\*\*|`[^`]+`)", text)):
        if not chunk:
            continue
        run = paragraph.add_run()
        if chunk.startswith("**") and chunk.endswith("**"):
            run.text, run.bold = chunk[2:-2], True
        elif chunk.startswith("`") and chunk.endswith("`"):
            run.text = chunk[1:-1]
            run.font.name = "Consolas"
        else:
            run.text = chunk
            run.bold = bold or None
        run.italic = italic or None
        if size:
            run.font.size = Pt(size)
        if color is not None:
            run.font.color.rgb = color
    return paragraph


def shade(element_pr, fill):
    shading = OxmlElement("w:shd")
    shading.set(qn("w:val"), "clear")
    shading.set(qn("w:color"), "auto")
    shading.set(qn("w:fill"), fill)
    element_pr.append(shading)


def add_field(paragraph, instruction, size=8):
    for kind, text in (("begin", None), (None, instruction), ("end", None)):
        run = paragraph.add_run()
        run.font.size = Pt(size)
        if kind:
            char = OxmlElement("w:fldChar")
            char.set(qn("w:fldCharType"), kind)
            run._r.append(char)
        else:
            instr = OxmlElement("w:instrText")
            instr.set(qn("xml:space"), "preserve")
            instr.text = text
            run._r.append(instr)


def column_widths(rows, usable_cm):
    """Ширина столбцов по длине текста: узкие столбцы (номера) не раздуваются."""
    count = len(rows[0])
    weights = []
    for column in range(count):
        lengths = [len(row[column]) for row in rows if column < len(row)]
        longest, average = max(lengths), sum(lengths) / len(lengths)
        weights.append(2.7 if longest <= 4 else max(6.0, average ** 0.62 + longest ** 0.35))
    total = sum(weights)
    return [usable_cm * weight / total for weight in weights]


def add_table(document, rows, usable_cm):
    widths = column_widths(rows, usable_cm)
    table = document.add_table(rows=len(rows), cols=len(rows[0]))
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    layout = OxmlElement("w:tblLayout")
    layout.set(qn("w:type"), "fixed")
    table._tbl.tblPr.append(layout)
    for row_index, row in enumerate(rows):
        table_row = table.rows[row_index]
        row_pr = table_row._tr.get_or_add_trPr()
        row_pr.append(OxmlElement("w:cantSplit"))
        if row_index == 0:
            row_pr.append(OxmlElement("w:tblHeader"))
        for column, width in enumerate(widths):
            cell = table_row.cells[column]
            cell.width = Cm(width)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.TOP
            text = row[column] if column < len(row) else ""
            paragraph = cell.paragraphs[0]
            paragraph.paragraph_format.space_after = Pt(2)
            paragraph.paragraph_format.space_before = Pt(2)
            if row_index == 0:
                shade(cell._tc.get_or_add_tcPr(), HEADER_FILL)
                add_runs(paragraph, text, size=9.5, bold=True, color=HEAD)
                paragraph.paragraph_format.keep_with_next = True  # шапка не остаётся одна внизу страницы
            else:
                established = column == len(row) - 1 and text.strip().lower().startswith("установлено")
                add_runs(paragraph, text, size=9.5, bold=established, color=HEAD if established else None)
            if len(text) <= 4:
                paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    document.add_paragraph().paragraph_format.space_after = Pt(2)


def build(source, target, landscape, clean):
    lines = source.read_text(encoding="utf-8").split("\n")
    document = Document()
    section = document.sections[0]
    if landscape:
        section.orientation = WD_ORIENT.LANDSCAPE
        section.page_width, section.page_height = Cm(29.7), Cm(21.0)
    else:
        section.page_width, section.page_height = Cm(21.0), Cm(29.7)
    section.left_margin = section.right_margin = Cm(1.6)
    section.top_margin, section.bottom_margin = Cm(1.5), Cm(1.6)
    usable_cm = (section.page_width - section.left_margin - section.right_margin) / 360000

    styles = document.styles
    normal = styles["Normal"]
    normal.font.name, normal.font.size, normal.font.color.rgb = FONT, Pt(10.5), INK
    set_fonts(normal.element, FONT)
    normal.paragraph_format.space_after = Pt(5)
    for name, size, before, after in (("Title", 20, 0, 6), ("Heading 1", 15, 16, 6), ("Heading 2", 12, 12, 4)):
        style = styles[name]
        style.font.name, style.font.size, style.font.bold = FONT, Pt(size), True
        style.font.color.rgb = HEAD
        set_fonts(style.element, FONT)
        style.paragraph_format.space_before, style.paragraph_format.space_after = Pt(before), Pt(after)
        style.paragraph_format.keep_with_next = True
    defaults = styles.element.find(qn("w:docDefaults"))
    if defaults is not None:
        run_pr = defaults.find(qn("w:rPrDefault")).find(qn("w:rPr"))
        language = run_pr.find(qn("w:lang"))
        if language is None:
            language = OxmlElement("w:lang")
            run_pr.append(language)
        language.set(qn("w:val"), "ru-RU")
        language.set(qn("w:eastAsia"), "ru-RU")

    title_text = ""
    index = 0
    while index < len(lines):
        line = lines[index]
        if not line.strip():
            index += 1
            continue
        heading = re.match(r"^(#{1,3})\s+(.*)$", line)
        if heading:
            level, text = len(heading.group(1)), heading.group(2).strip()
            if clean:
                text = strip_refs(text, whole_sentences=False)
            if level == 1:
                title_text = title_text or text
                paragraph = document.add_paragraph(style="Title")
                add_runs(paragraph, text)
                # у стандартного стиля «Название» есть нижняя линия — убираем её
                borders = paragraph._p.get_or_add_pPr().find(qn("w:pBdr"))
                style_borders = styles["Title"].element.get_or_add_pPr().find(qn("w:pBdr"))
                for item in (borders, style_borders):
                    if item is not None:
                        item.getparent().remove(item)
            else:
                document.add_heading(text, level=level - 1)
            index += 1
            continue
        if line.lstrip().startswith(">"):
            block = []
            while index < len(lines) and lines[index].lstrip().startswith(">"):
                block.append(lines[index].lstrip()[1:].strip())
                index += 1
            for text in _split_note(block):
                if clean:
                    text = strip_refs(text)
                if not text.strip():
                    continue
                paragraph = document.add_paragraph()
                paragraph.paragraph_format.left_indent = Cm(0.4)
                paragraph.paragraph_format.right_indent = Cm(0.4)
                shade(paragraph._p.get_or_add_pPr(), NOTE_FILL)
                add_runs(paragraph, text, size=10)
            continue
        if TABLE_ROW.match(line):
            rows = []
            while index < len(lines) and TABLE_ROW.match(lines[index]):
                if not TABLE_RULE.match(lines[index]):
                    cells = [cell.strip() for cell in lines[index].strip().strip("|").split("|")]
                    if clean:
                        cells = [strip_refs(cell, whole_sentences=False) or "—" for cell in cells]
                    rows.append(cells)
                index += 1
            if rows:
                width = max(len(row) for row in rows)
                rows = [row + [""] * (width - len(row)) for row in rows]
                # абзац перед таблицей (например, «Орган: …») не отрывается от неё
                if document.paragraphs and document.element.body[-2].tag == qn("w:p"):
                    document.paragraphs[-1].paragraph_format.keep_with_next = True
                add_table(document, rows, usable_cm)
            continue
        if NUMBERED.match(line) or line.lstrip().startswith(("- ", "* ")):
            numbered = bool(NUMBERED.match(line))
            text = NUMBERED.sub("", line) if numbered else line.lstrip()[2:]
            if clean:
                text = strip_refs(text)
            if text.strip():
                paragraph = document.add_paragraph(style="List Number" if numbered else "List Bullet")
                add_runs(paragraph, text.strip())
            index += 1
            continue
        text = line.strip()
        if clean:
            text = strip_refs(text)
        if text.strip():
            add_runs(document.add_paragraph(), text.strip())
        index += 1

    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = footer.add_run((title_text[:90] + " · стр. ") if title_text else "стр. ")
    run.font.size = Pt(8)
    add_field(footer, "PAGE")
    run = footer.add_run(" из ")
    run.font.size = Pt(8)
    add_field(footer, "NUMPAGES")
    document.core_properties.title = title_text
    document.core_properties.author = ""
    document.core_properties.language = "ru-RU"
    document.save(target)
    return title_text


def _split_note(block):
    """Примечание «>»: пустая строка внутри него разделяет абзацы."""
    parts, current = [], []
    for text in block:
        if text:
            current.append(text)
        elif current:
            parts.append(" ".join(current))
            current = []
    if current:
        parts.append(" ".join(current))
    return parts


def main():
    args = [arg for arg in sys.argv[1:] if not arg.startswith("--")]
    if len(args) != 2:
        sys.exit("usage: python -I -X utf8 tools/md_to_docx.py <in.md> <out.docx> [--landscape] [--strip-refs]")
    title = build(Path(args[0]), Path(args[1]), "--landscape" in sys.argv, "--strip-refs" in sys.argv)
    print("saved:", ascii(args[1]), "| title chars:", len(title))


if __name__ == "__main__":
    main()
