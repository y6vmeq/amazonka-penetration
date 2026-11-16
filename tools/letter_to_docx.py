"""Оформляет проект обращения из letters/<имя>.md как документ Word.

Запуск из корня проекта:
    python -I -X utf8 tools/letter_to_docx.py <письмо.md> <выход.docx>
        [--applicant "Иванов Иван Иванович" --applicant-gen "Иванова Ивана Ивановича" --signature "И. И. Иванов"]
        [--address "г. Могилёв, ул. …"] [--variant 1] [--appendix <приложение.md>] [--note "добавка к пометке о проекте"]

Из файла письма берётся только само письмо (между первой и второй строкой «---») и разделы «## Приложение …»
после него; внутренняя справка «Откуда каждый факт» в документ не идёт. Из таблиц приложений убираются
внутренние графы («Запись в базе», «Файл в проекте»).

Если задан заявитель, его данные подставляются в поля письма (мужской род), а всё подставленное и всё, что
осталось в квадратных скобках, выделяется жёлтым: это нужно заменить или проверить перед подачей.
"""
import re
import sys
from pathlib import Path

from docx import Document
from docx.enum.section import WD_ORIENT, WD_SECTION
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_COLOR_INDEX, WD_TAB_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

sys.path.insert(0, str(Path(__file__).resolve().parent))
import md_to_docx as base  # noqa: E402  (соседний файл проекта)

FONT = "Times New Roman"
OPEN, CLOSE = "⟦", "⟧"
INTERNAL_COLUMNS = ("запись в базе", "внутренняя графа", "файл в проекте")
FEMININE = re.compile(r"\((?:ей|ла|лась|а)\)")
BRACKETS = re.compile(r"\[[^\[\]]+\]")
VARIANT = re.compile(r"^\*\*Вариант (\d+)\.\*\*\s*(.*)$")
NUMBERED = re.compile(r"^(\d+)[.)]\s+(.*)$")


def options(argv):
    values, positional, index = {"appendix": []}, [], 0
    while index < len(argv):
        item = argv[index]
        if item.startswith("--"):
            key = item[2:]
            if key == "appendix":
                values["appendix"].append(argv[index + 1])
            else:
                values[key] = argv[index + 1]
            index += 2
        else:
            positional.append(item)
            index += 1
    return positional, values


def mark(text):
    return OPEN + text + CLOSE


def fill(text, opts):
    """Подставляет данные заявителя и помечает то, что осталось заменить."""
    text = base.strip_refs(text, whole_sentences=False)
    if opts.get("applicant"):
        text = text.replace("[фамилия, имя, отчество]", mark(opts.get("applicant-gen", opts["applicant"])))
        text = re.sub(r"\[почтовый индекс, населённый пункт, улица, дом, квартира\]", lambda _: mark(opts["address"]), text)
        text = FEMININE.sub("", text)
        if text.startswith("[Ранее по изложенным вопросам"):
            text = mark("Ранее по изложенным вопросам я в государственные органы не обращался.")
    text = text.replace("[__]", mark("___"))
    text = re.sub(r"(?<!\.)\.\.(?!\.)", ".", text)  # после удаления служебной ссылки остаются две точки
    return BRACKETS.sub(lambda match: mark(match.group(0)), text)


def add_text(paragraph, text, size=14, bold=False):
    for chunk in re.split(r"(\*\*[^*]+\*\*|" + OPEN + "[^" + CLOSE + "]*" + CLOSE + ")", text):
        if not chunk:
            continue
        run = paragraph.add_run()
        run.font.size = Pt(size)
        if chunk.startswith("**"):
            run.text, run.bold = chunk[2:-2].replace(OPEN, "").replace(CLOSE, ""), True
        elif chunk.startswith(OPEN):
            run.text, run.bold = chunk[1:-1], bold or None
            run.font.highlight_color = WD_COLOR_INDEX.YELLOW
        else:
            run.text, run.bold = chunk, bold or None
    return paragraph


def body_paragraph(document, text, indent=True, align=WD_ALIGN_PARAGRAPH.JUSTIFY, before=0, after=0, bold=False):
    paragraph = document.add_paragraph()
    paragraph.alignment = align
    paragraph.paragraph_format.space_before, paragraph.paragraph_format.space_after = Pt(before), Pt(after)
    if indent:
        paragraph.paragraph_format.first_line_indent = Cm(1.25)
    add_text(paragraph, text, bold=bold)
    return paragraph


def parse_table(lines):
    rows = []
    for line in lines:
        if base.TABLE_RULE.match(line):
            continue
        rows.append([cell.strip() for cell in line.strip().strip("|").split("|")])
    keep = [index for index, head in enumerate(rows[0]) if not any(word in head.lower() for word in INTERNAL_COLUMNS)]
    return [[base.strip_refs(row[index], whole_sentences=False) if index < len(row) else "" for index in keep] for row in rows]


def add_appendix(document, title, note, table_lines):
    section = document.add_section(WD_SECTION.NEW_PAGE)
    section.orientation = WD_ORIENT.LANDSCAPE
    section.page_width, section.page_height = Cm(29.7), Cm(21.0)
    section.left_margin = section.right_margin = Cm(1.5)
    section.top_margin, section.bottom_margin = Cm(1.5), Cm(1.5)
    heading = document.add_paragraph()
    heading.paragraph_format.space_after = Pt(6)
    add_text(heading, title, size=13, bold=True)
    if note:
        paragraph = document.add_paragraph()
        paragraph.paragraph_format.space_after = Pt(6)
        add_text(paragraph, note, size=11)
    if table_lines:
        base.add_table(document, parse_table(table_lines), 26.7)


def build(source, target, opts):
    lines = source.read_text(encoding="utf-8").split("\n")
    rules = [index for index, line in enumerate(lines) if line.strip() == "---"]
    if len(rules) < 2:
        sys.exit("в файле письма нет двух строк «---», ограничивающих текст обращения")
    letter, tail = lines[rules[0] + 1:rules[1]], lines[rules[1] + 1:]
    title_index = next(index for index, line in enumerate(letter) if line.startswith("## "))
    head, body = [line for line in letter[:title_index]], letter[title_index + 1:]

    # адресат и заявитель
    addressee, applicant, variant, current = [], [], int(opts.get("variant", 1)), None
    for line in head:
        text = line.strip()
        if not text:
            continue
        found = VARIANT.match(text)
        if found:
            current = int(found.group(1))
            text = found.group(2)
        if text.startswith(("от ", "проживающ")):
            applicant.append(text)
        elif current is None or current == variant:
            addressee.append(text)

    document = Document()
    section = document.sections[0]
    section.page_width, section.page_height = Cm(21.0), Cm(29.7)
    section.left_margin, section.right_margin = Cm(3.0), Cm(1.5)
    section.top_margin = section.bottom_margin = Cm(2.0)
    normal = document.styles["Normal"]
    normal.font.name, normal.font.size = FONT, Pt(14)
    base.set_fonts(normal.element, FONT)
    normal.paragraph_format.space_after = Pt(0)
    defaults = document.styles.element.find(qn("w:docDefaults"))
    if defaults is not None:
        run_pr = defaults.find(qn("w:rPrDefault")).find(qn("w:rPr"))
        language = run_pr.find(qn("w:lang"))
        if language is None:
            language = OxmlElement("w:lang")
            run_pr.append(language)
        language.set(qn("w:val"), "ru-RU")

    if opts.get("applicant"):
        banner = document.add_paragraph()
        banner.paragraph_format.space_after = Pt(14)
        base.shade(banner._p.get_or_add_pPr(), "FFF2CC")
        note = ("ПРОЕКТ, не для подачи. Заявитель указан условно (" + opts["applicant"] + "): перед подачей заменить фамилию, имя, отчество "
                "и адрес на настоящие, поставить дату и личную подпись. Жёлтым выделено всё, что нужно заменить или проверить.")
        if opts.get("note"):
            note += " " + opts["note"]
        add_text(banner, note, size=11)

    for group in (addressee, applicant):
        for text in group:
            paragraph = document.add_paragraph()
            paragraph.paragraph_format.left_indent = Cm(8.0)
            add_text(paragraph, fill(text, opts))
        spacer = document.add_paragraph()
        spacer.paragraph_format.left_indent = Cm(8.0)

    heading = document.add_paragraph()
    heading.alignment = WD_ALIGN_PARAGRAPH.CENTER
    heading.paragraph_format.space_before, heading.paragraph_format.space_after = Pt(6), Pt(12)
    add_text(heading, letter[title_index][3:].strip(), bold=True)

    tail_start = None  # с абзаца «Приложения:» текст держится вместе с подписью, чтобы она не осталась одна на странице
    for line in body:
        text = line.strip()
        if not text:
            continue
        if re.match(r"^\[дата\]\s+\[личная подпись\]$", text):
            paragraph = document.add_paragraph()
            paragraph.paragraph_format.space_before = Pt(28)
            paragraph.paragraph_format.tab_stops.add_tab_stop(Cm(16.5), WD_TAB_ALIGNMENT.RIGHT)
            signature = "____________ " + opts["signature"] if opts.get("signature") else "[личная подпись]"
            add_text(paragraph, mark("«___» ____________ 20__ г.") + "\t" + mark(signature))
            if tail_start is not None:
                for kept in document.paragraphs[tail_start:-1]:
                    kept.paragraph_format.keep_with_next = True
            continue
        numbered = NUMBERED.match(text)
        if text.startswith("- "):
            body_paragraph(document, "– " + fill(text[2:], opts))
        elif numbered:
            body_paragraph(document, numbered.group(1) + ". " + fill(numbered.group(2), opts))
        elif text.rstrip(":") in ("Приложения",):
            tail_start = len(document.paragraphs)
            body_paragraph(document, text, before=12)
        else:
            body_paragraph(document, fill(text, opts), before=6 if text.startswith(("На основании", "Также **прошу", OPEN, "[Ранее")) else 0)

    # приложения: сначала внешние файлы, затем разделы «## Приложение …» из файла письма
    for name in opts["appendix"]:
        appendix_lines = Path(name).read_text(encoding="utf-8").split("\n")
        title = next((line[2:].strip() for line in appendix_lines if line.startswith("# ")), "Приложение")
        note = next((line.strip() for line in appendix_lines if line.strip() and not line.startswith(("#", "|"))), "")
        add_appendix(document, base.strip_refs(title, whole_sentences=False), base.strip_refs(note), [line for line in appendix_lines if base.TABLE_ROW.match(line)])
    index = 0
    while index < len(tail):
        line = tail[index]
        if line.startswith("## Приложение"):
            title = re.sub(r"\s*\(проект\)", "", line[3:].strip())
            block = []
            index += 1
            while index < len(tail) and not tail[index].startswith("## "):
                block.append(tail[index])
                index += 1
            note = next((item.strip() for item in block if item.strip() and not base.TABLE_ROW.match(item)), "")
            add_appendix(document, title, base.strip_refs(note), [item for item in block if base.TABLE_ROW.match(item)])
            continue
        index += 1

    footer = document.sections[0].footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = footer.add_run("проект · стр. " if opts.get("applicant") else "стр. ")
    run.font.size = Pt(9)
    base.add_field(footer, "PAGE", size=9)
    document.core_properties.title = letter[title_index][3:].strip().capitalize()
    document.core_properties.author = ""
    document.core_properties.language = "ru-RU"
    document.save(target)


def main():
    positional, opts = options(sys.argv[1:])
    if len(positional) != 2:
        sys.exit(__doc__)
    if opts.get("applicant"):
        opts.setdefault("address", "г. Могилёв, ул. ____________, д. ___, кв. ___")
    build(Path(positional[0]), Path(positional[1]), opts)
    print("saved:", ascii(positional[1]))


if __name__ == "__main__":
    main()
