"""Собирает презентацию «Как подавать обращения и жалобы» (python-pptx, значки — из системного шрифта эмодзи).

Запуск из корня проекта:
    python -I -X utf8 strategy/_build/build_presentation_obrashcheniya.py <выход.pptx>

Содержание опирается на выписки: law/zakon-300-z_obrashcheniya.md (Закон № 300-З), law/ukaz-498-2007_kuda-obrashchatsya.md,
authorities/README.md и strategy/2026-11-15_povody-kratko.md. Тексты слайдов править здесь, затем пересобрать.
"""
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

from lxml import etree
from PIL import Image, ImageDraw, ImageFont
from pptx import Presentation
from pptx.enum.dml import MSO_THEME_COLOR as T
from pptx.enum.lang import MSO_LANGUAGE_ID
from pptx.enum.shapes import MSO_SHAPE, PP_PLACEHOLDER
from pptx.enum.text import MSO_ANCHOR, MSO_AUTO_SIZE, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Inches as I
from pptx.util import Pt

THEME = {
    "name": "Обращения",
    "major": "Cambria",
    "minor": "Calibri",
    "colors": {
        "dk1": "1E2A32", "lt1": "FFFFFF", "dk2": "12403C", "lt2": "EEF3F1",
        "accent1": "1F7A6B", "accent2": "C9462C", "accent3": "E0A526",
        "accent4": "4A6FA5", "accent5": "7A5C99", "accent6": "5F6B73",
        "hlink": "1F7A6B", "folHlink": "5F6B73",
    },
}
INK, GREEN, WHITE, TINT = T.TEXT_1, T.TEXT_2, T.BACKGROUND_1, T.BACKGROUND_2
TEAL, RED, AMBER, SLATE = T.ACCENT_1, T.ACCENT_2, T.ACCENT_3, T.ACCENT_6
EMOJI_FONT = "C:/Windows/Fonts/seguiemj.ttf"
ICONS = {
    "envelope": "✉", "document": "📄", "pen": "🖊", "magnifier": "🔍", "people": "👥", "building": "🏛",
    "house": "🏠", "check": "✅", "cross": "❌", "warning": "⚠", "camera": "📷", "receipt": "🧾",
    "scales": "⚖", "laptop": "💻", "speech": "💬", "link": "🔗", "fire": "🔥", "bricks": "🧱", "soap": "🧼",
    "bags": "🛍", "moon": "🌙", "briefcase": "💼", "ruler": "📐", "lizard": "🦎", "postbox": "📮",
    "calendar": "🗓", "idcard": "🪪", "clip": "📎", "ban": "🚫", "memo": "📝", "up": "⬆", "clock": "🕒",
    "person": "👤", "question": "❓", "office": "🏢", "shield": "🛡", "handshake": "🤝",
}
ICON_NAMES = {
    "envelope": "конверт", "document": "документ", "pen": "ручка", "magnifier": "лупа", "people": "люди",
    "building": "здание органа", "house": "жилой дом", "check": "галочка", "cross": "крестик", "warning": "внимание",
    "camera": "фотоаппарат", "receipt": "чек", "scales": "весы", "laptop": "компьютер", "speech": "разговор",
    "link": "ссылка", "fire": "огонь", "bricks": "кирпичная стена", "soap": "мыло", "bags": "покупки", "moon": "ночь",
    "briefcase": "портфель", "ruler": "линейка", "lizard": "ящерица", "postbox": "почтовый ящик", "calendar": "календарь",
    "idcard": "удостоверение", "clip": "скрепка", "ban": "запрет", "memo": "записка", "up": "стрелка вверх",
    "clock": "часы", "person": "человек", "question": "вопрос", "office": "учреждение", "shield": "щит",
    "handshake": "рукопожатие",
}
PALE = {"envelope", "document", "speech", "link", "clip"}  # светлые значки: им нужен цветной круг
_icon_dir = Path(tempfile.mkdtemp(prefix="deck_icons_"))


def icon_file(name):
    """Рисует значок в PNG с прозрачным фоном и возвращает путь."""
    path = _icon_dir / f"{name}.png"
    if not path.exists():
        size = 256
        font = ImageFont.truetype(EMOJI_FONT, 200)
        image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        glyph = ICONS[name]
        left, top, right, bottom = draw.textbbox((0, 0), glyph, font=font, embedded_color=True)
        draw.text(((size - (right - left)) / 2 - left, (size - (bottom - top)) / 2 - top), glyph, font=font, embedded_color=True)
        image.save(path)
    return str(path)


def shape(slide, kind, x, y, w, h, fill=None, tint=0.0, line=None, radius=None, name=None):
    item = slide.shapes.add_shape(kind, I(x), I(y), I(w), I(h))
    item.shadow.inherit = False
    if fill is None:
        item.fill.background()
    else:
        item.fill.solid()
        item.fill.fore_color.theme_color = fill
        if tint:
            item.fill.fore_color.brightness = tint
    if line is None:
        item.line.fill.background()
    else:
        item.line.color.theme_color = line[0]
        item.line.width = Pt(line[1])
        if len(line) > 2:
            item.line.color.brightness = line[2]
    if radius is not None:
        item.adjustments[0] = radius
    if name:
        item.name = name
    return item


def text(slide, x, y, w, h, parts, size=16, color=INK, bold=False, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP,
         into=None, margin=0.0, after=0, italic=False, line_spacing=None):
    """parts — строка или список абзацев; абзац — строка или список пар (текст, свойства)."""
    item = into if into is not None else slide.shapes.add_textbox(I(x), I(y), I(w), I(h))
    frame = item.text_frame
    frame.word_wrap = True
    frame.auto_size = MSO_AUTO_SIZE.NONE
    frame.margin_left = frame.margin_right = frame.margin_top = frame.margin_bottom = I(margin)
    frame.vertical_anchor = anchor
    for index, paragraph in enumerate([parts] if isinstance(parts, str) else parts):
        target = frame.paragraphs[0] if index == 0 else frame.add_paragraph()
        target.alignment = align
        if after:
            target.space_after = Pt(after)
        if line_spacing:
            target.line_spacing = line_spacing
        for run_text, options in ([(paragraph, {})] if isinstance(paragraph, str) else paragraph):
            run = target.add_run()
            run.text = run_text
            run.font.size = Pt(options.get("size", size))
            run.font.bold = options.get("bold", bold)
            run.font.italic = options.get("italic", italic)
            run.font.color.theme_color = options.get("color", color)
            run.font.language_id = MSO_LANGUAGE_ID.RUSSIAN
    return item


def icon(slide, name, x, y, size, circle=TINT, tint=0.0, ring=None):
    """Значок в круге: круг — фигура, значок — картинка поверх."""
    if circle in (WHITE, TINT) and name in PALE:
        circle, tint = TEAL, 0.5
    if circle is not None:
        shape(slide, MSO_SHAPE.OVAL, x, y, size, size, fill=circle, tint=tint, line=ring, name=f"Круг: {ICON_NAMES[name]}")
    inset = size * 0.2
    picture = slide.shapes.add_picture(icon_file(name), I(x + inset), I(y + inset), I(size - 2 * inset), I(size - 2 * inset))
    picture._element.nvPicPr.cNvPr.set("descr", f"Значок: {ICON_NAMES[name]}")
    picture.name = f"Значок: {ICON_NAMES[name]}"
    return picture


def badge(slide, x, y, size, label, fill=TEAL, font=14, color=WHITE):
    item = shape(slide, MSO_SHAPE.OVAL, x, y, size, size, fill=fill, name=f"Номер {label}")
    text(slide, 0, 0, 0, 0, label, size=font, color=color, bold=True, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE, into=item)
    return item


def title(slide, value, dark=False, size=34):
    item = slide.shapes.title
    frame = item.text_frame
    frame.word_wrap = True
    frame.auto_size = MSO_AUTO_SIZE.NONE
    frame.vertical_anchor = MSO_ANCHOR.MIDDLE
    frame.margin_left = frame.margin_right = frame.margin_top = frame.margin_bottom = 0
    paragraph = frame.paragraphs[0]
    paragraph.alignment = PP_ALIGN.LEFT
    run = paragraph.add_run()
    run.text = value
    run.font.size, run.font.bold = Pt(size), True
    run.font.color.theme_color = WHITE if dark else GREEN
    run.font.language_id = MSO_LANGUAGE_ID.RUSSIAN
    return item


def slide_number(slide, dark=False):
    box = slide.shapes.add_textbox(I(12.03), I(6.93), I(0.7), I(0.3))
    box.name = "Номер слайда"
    frame = box.text_frame
    frame.margin_left = frame.margin_right = frame.margin_top = frame.margin_bottom = 0
    paragraph = frame.paragraphs[0]
    paragraph.alignment = PP_ALIGN.RIGHT
    field = etree.SubElement(paragraph._p, qn("a:fld"), {"id": "{B6F15528-21DE-4FAA-801E-634DDDAF4B2B}", "type": "slidenum"})
    properties = etree.SubElement(field, qn("a:rPr"), {"lang": "ru-RU", "sz": "1100"})
    fill = etree.SubElement(properties, qn("a:solidFill"))
    etree.SubElement(fill, qn("a:schemeClr"), {"val": "bg1" if dark else "accent6"})
    etree.SubElement(field, qn("a:t")).text = "‹#›"


def background(slide, color):
    slide.background.fill.solid()
    slide.background.fill.fore_color.theme_color = color


def notes(slide, value):
    slide.notes_slide.notes_text_frame.text = value


def content_slide(prs, heading, note):
    slide = prs.slides.add_slide(prs.slide_layouts[5])
    title(slide, heading)
    slide_number(slide)
    notes(slide, note)
    return slide


def build(target):
    prs = Presentation()
    prs.slide_width, prs.slide_height = I(13.333), I(7.5)
    for layout_index, boxes in ((5, {PP_PLACEHOLDER.TITLE: (0.6, 0.42, 12.13, 0.95)}),
                                (0, {PP_PLACEHOLDER.CENTER_TITLE: (0.8, 2.0, 7.3, 2.0), PP_PLACEHOLDER.SUBTITLE: (0.8, 4.15, 7.3, 1.3)})):
        for placeholder in prs.slide_layouts[layout_index].placeholders:
            geometry = boxes.get(placeholder.placeholder_format.type)
            if geometry:
                placeholder.left, placeholder.top, placeholder.width, placeholder.height = (I(v) for v in geometry)

    # ---------- 1. Титул ----------
    slide = prs.slides.add_slide(prs.slide_layouts[0])
    background(slide, GREEN)
    title(slide, "Как подавать обращения и жалобы", dark=True, size=44)
    subtitle = slide.placeholders[1]
    text(slide, 0, 0, 0, 0, "Порядок для нашего дела: рестобар «Амазонка» и «Смак.BY», г. Могилёв", size=20, color=WHITE, into=subtitle)
    text(slide, 0.8, 6.35, 8.5, 0.5,
         "По Закону Республики Беларусь «Об обращениях граждан и юридических лиц». Состояние на 15.11.2026",
         size=12, color=WHITE)
    shape(slide, MSO_SHAPE.OVAL, 8.75, 1.45, 3.9, 3.9, fill=TEAL, tint=0.35, name="Большой круг")
    icon(slide, "envelope", 9.35, 2.05, 2.7, circle=None)
    icon(slide, "magnifier", 11.1, 4.05, 1.6, circle=WHITE)
    icon(slide, "memo", 8.3, 4.35, 1.45, circle=AMBER, tint=0.5)
    notes(slide, "Презентация — памятка для всех, кто будет подписывать и подавать обращения. Нормы взяты из выписок в папке law проекта; "
                 "перед подачей сверить действующую редакцию Закона № 300-З.")

    # ---------- 2. Четыре правила ----------
    slide = content_slide(prs, "Четыре правила, на которых держится всё",
                          "Одно письмо — один орган: правило проекта и ст. 10, п. 2 Закона (обращения подаются по компетенции). "
                          "Анонимные обращения: ст. 23. Обжалование: ст. 20; запрет жалобы в тот же орган: ст. 10, п. 6.")
    cards = [
        ("building", "Одно письмо — один орган", "В каждом письме только вопросы, которые решает именно этот орган."),
        ("magnifier", "Только проверяемые факты", "Что, где, когда и откуда известно. Вместо обвинений — «прошу проверить»."),
        ("idcard", "Фамилия, адрес, подпись", "Анонимные обращения не рассматривают."),
        ("up", "Не согласны — выше", "Ответ обжалуют в вышестоящий орган, затем в суд. В тот же орган жаловаться нельзя."),
    ]
    for index, (name, head, body) in enumerate(cards):
        x, y = 0.6 + (index % 2) * 6.17, 1.7 + (index // 2) * 2.55
        shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE, x, y, 5.96, 2.3, fill=TINT, radius=0.08, name=f"Карточка {index + 1}")
        icon(slide, name, x + 0.3, y + 0.5, 1.3, circle=WHITE)
        text(slide, x + 1.9, y + 0.32, 3.8, 0.5, head, size=20, bold=True, color=GREEN)
        text(slide, x + 1.9, y + 0.88, 3.8, 1.3, body, size=16)

    # ---------- 3. Путь обращения ----------
    slide = content_slide(prs, "Путь обращения: от письма до ответа",
                          "Способы подачи: ст. 10, п. 1; электронные обращения: ст. 25. Сроки: ст. 17, п. 3. Пересылка по компетенции "
                          "за пять рабочих дней: ст. 10, п. 3. Обжалование: ст. 20.")
    steps = [
        ("memo", "Готовим", "факты, просьба, приложения, подпись"),
        ("postbox", "Подаём", "почтой, на приёме или через обращения.бел"),
        ("clock", "Рассмотрение", "15 дней; с проверкой — до месяца"),
        ("envelope", "Ответ", "сохраняем его: он нужен для жалобы"),
        ("up", "Не согласны", "вышестоящий орган, затем суд"),
    ]
    for index, (name, head, body) in enumerate(steps):
        x = 0.6 + index * 2.5
        icon(slide, name, x + 0.39, 1.75, 1.35, circle=TINT)
        badge(slide, x + 0.32, 1.68, 0.42, str(index + 1), fill=TEAL if index < 4 else RED)
        text(slide, x, 3.3, 2.13, 0.45, head, size=18, bold=True, color=GREEN, align=PP_ALIGN.CENTER)
        text(slide, x, 3.78, 2.13, 1.1, body, size=14, align=PP_ALIGN.CENTER)
        if index < 4:
            shape(slide, MSO_SHAPE.RIGHT_ARROW, x + 2.0, 2.27, 0.62, 0.32, fill=TEAL, tint=0.4, name=f"Стрелка {index + 1}")
    shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE, 0.6, 5.35, 12.13, 1.3, fill=AMBER, tint=0.8, radius=0.12, name="Плашка: не по адресу")
    icon(slide, "office", 0.85, 5.55, 0.9, circle=WHITE)
    text(slide, 2.0, 5.5, 10.5, 1.0,
         [[("Письмо попало не по адресу? ", {"bold": True}),
           ("За пять рабочих дней его перешлют в нужный орган либо оставят без рассмотрения и разъяснят, куда обращаться.", {})]],
         size=16, anchor=MSO_ANCHOR.MIDDLE)

    # ---------- 4. Что должно быть в обращении ----------
    slide = content_slide(prs, "Что обязательно должно быть в обращении",
                          "Ст. 12, п. 2: адресат; фамилия, собственное имя, отчество (либо инициалы) и адрес места жительства; изложение сути; "
                          "личная подпись. П. 1: язык — белорусский или русский. П. 7: сведения о результатах прежнего рассмотрения. "
                          "Просьба и перечень приложений — правило проекта.")
    page = shape(slide, MSO_SHAPE.RECTANGLE, 1.05, 1.62, 4.75, 5.35, fill=WHITE, line=(SLATE, 1, 0.5), name="Лист письма")
    page.shadow.inherit = True
    mock = [
        (1.75, 0.62, [[("Кому: ", {"bold": True}), ("Могилёвский зональный центр гигиены и эпидемиологии", {})]], PP_ALIGN.RIGHT),
        (2.48, 0.62, [[("От кого: ", {"bold": True}), ("Фамилия Имя Отчество, адрес места жительства", {})]], PP_ALIGN.RIGHT),
        (3.28, 1.25, [[("Обращение", {"bold": True})],
                      "На сайте областного центра гигиены опубликовано: 20.03.2024 и 21.04.2025 в баре выявлена продукция с истекшим сроком годности…"],
         PP_ALIGN.LEFT),
        (4.62, 0.62, [[("Прошу ", {"bold": True}), ("провести проверку и сообщить о результатах.", {})]], PP_ALIGN.LEFT),
        (5.38, 0.62, [[("Приложения: ", {"bold": True}), ("перечень публикаций с датами и выдержками.", {})]], PP_ALIGN.LEFT),
    ]
    for (y, h, parts, align) in mock:
        text(slide, 1.75 if align == PP_ALIGN.RIGHT else 1.45, y, 3.85 if align == PP_ALIGN.RIGHT else 4.15, h, parts, size=11, align=align)
    text(slide, 1.45, 6.25, 1.5, 0.4, "Дата", size=11)
    text(slide, 3.6, 6.25, 2.0, 0.4, "Подпись", size=11, italic=True, align=PP_ALIGN.RIGHT)
    for label, y in (("1", 1.8), ("2", 2.53), ("3", 3.3), ("4", 4.66), ("6", 5.42), ("5", 6.2)):
        badge(slide, 0.85, y, 0.42, label)
    legend = [
        ("1", "Кому", "название и (или) адрес органа", True),
        ("2", "От кого", "фамилия, имя, отчество и адрес места жительства", True),
        ("3", "Суть", "что произошло: факты с датами", True),
        ("4", "Просьба", "проверить и сообщить о результатах", False),
        ("5", "Личная подпись", "для письменного обращения", True),
        ("6", "Приложения", "публикации, фото, чеки", False),
    ]
    for index, (label, head, body, by_law) in enumerate(legend):
        y = 1.68 + index * 0.76
        badge(slide, 6.45, y + 0.04, 0.42, label)
        text(slide, 7.05, y, 4.2, 0.62, [[(head + " — ", {"bold": True, "color": GREEN}), (body, {})]], size=16, anchor=MSO_ANCHOR.MIDDLE)
        pill = shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE, 11.38, y + 0.08, 1.35, 0.36, fill=TEAL if by_law else AMBER,
                     tint=0.0 if by_law else 0.55, radius=0.5, name="Метка")
        text(slide, 0, 0, 0, 0, "по закону" if by_law else "наше правило", size=12, bold=True, color=WHITE if by_law else INK,
             align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE, into=pill)
    text(slide, 6.45, 6.38, 6.28, 0.55, "Язык — русский или белорусский. Если по вопросу уже обращались, это нужно указать.",
         size=14, color=SLATE)

    # ---------- 5. Три способа подать ----------
    slide = content_slide(prs, "Три способа подать",
                          "Ст. 10, п. 1: письменные обращения — нарочным (курьером), почтой, на личном приёме, записью в книге замечаний и "
                          "предложений; устные — на личном приёме; электронные — в порядке ст. 25, через систему учёта и обработки обращений. "
                          "Ст. 25, п. 2: суть электронного обращения не может излагаться ссылками на интернет-ресурсы.")
    ways = [
        ("envelope", "Письменно", ["Почтой, нарочным или на личном приёме. Нужна личная подпись.",
                                   "Запись в книге замечаний — тоже письменное обращение."]),
        ("speech", "Устно", ["На личном приёме в органе."]),
        ("laptop", "Электронно", ["Через систему обращения.бел.",
                                  "Суть нельзя излагать ссылками на сайты: факты пишем в самом тексте."]),
    ]
    for index, (name, head, body) in enumerate(ways):
        x = 0.6 + index * 4.11
        shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE, x, 1.7, 3.9, 3.55, fill=TINT, radius=0.06, name=f"Способ {index + 1}")
        icon(slide, name, x + 1.3, 1.95, 1.3, circle=WHITE)
        text(slide, x + 0.3, 3.38, 3.3, 0.45, head, size=20, bold=True, color=GREEN, align=PP_ALIGN.CENTER)
        text(slide, x + 0.3, 3.88, 3.3, 1.3, body, size=14, after=4)
    shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE, 0.6, 5.55, 12.13, 1.15, fill=TEAL, radius=0.12, name="Плашка: наш выбор")
    icon(slide, "check", 0.85, 5.68, 0.9, circle=WHITE)
    text(slide, 2.0, 5.62, 10.5, 1.0,
         [[("Для нас надёжнее письменно: ", {"bold": True}),
           ("с подписью, приложениями и отметкой о приёме либо почтовой квитанцией.", {})]],
         size=16, color=WHITE, anchor=MSO_ANCHOR.MIDDLE)

    # ---------- 6. Как писать о фактах ----------
    slide = content_slide(prs, "Как писать о фактах",
                          "Правило проекта: каждое утверждение опирается на источник; квалификацию не завышать. Ст. 12, п. 5: не допускаются "
                          "нецензурные и оскорбительные слова. Ст. 27: клевета и оскорбления влекут ответственность. Имена авторов публикаций "
                          "в письмах не называем без их согласия.")
    columns = [
        (0.6, "check", "Так", TEAL, 0.85, [
            "«На сайте областного центра гигиены опубликовано: 20.03.2024 и 21.04.2025 в баре выявлена продукция с истекшим сроком годности».",
            "«В публикации заведения от 18.09.2023 посетителей приглашают приходить с детьми и брать рептилий в руки».",
            "«Прошу провести проверку и сообщить о результатах».",
        ]),
        (6.77, "cross", "Не так", RED, 0.85, [
            "«Там антисанитария, это все знают».",
            "«Подробности смотрите по ссылке».",
            "«Заведение грубо нарушает закон».",
            "«Проверяющие их покрывают».",
        ]),
    ]
    for x, name, head, color, tint, lines in columns:
        shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE, x, 1.7, 5.96, 4.3, fill=color, tint=tint, radius=0.05, name=f"Колонка: {head}")
        icon(slide, name, x + 0.3, 1.9, 0.8, circle=WHITE)
        text(slide, x + 1.3, 1.95, 4.3, 0.7, head, size=24, bold=True, color=GREEN if color == TEAL else RED, anchor=MSO_ANCHOR.MIDDLE)
        text(slide, x + 0.35, 2.95, 5.3, 2.95, lines, size=17, after=12)
    text(slide, 0.6, 6.2, 12.13, 0.5,
         "Имён авторов отзывов в письмах не называем. Грубые слова из отзывов не переносим: пересказываем нейтрально.",
         size=14, color=SLATE)

    # ---------- 7. Чего делать нельзя ----------
    slide = content_slide(prs, "Чего делать нельзя",
                          "Анонимные обращения: ст. 23. Ссылки вместо сути: ст. 25, п. 2. Грубые слова: ст. 12, п. 5. Жалоба в тот же орган: "
                          "ст. 10, п. 6. Клевета и оскорбления: ст. 27. Расходы на рассмотрение обращений с заведомо ложными сведениями "
                          "могут быть взысканы с заявителя: ст. 19, п. 2.")
    bans = [
        ("person", "Анонимно", "Без фамилии или адреса обращение не рассмотрят."),
        ("link", "Ссылки вместо сути", "В электронном обращении суть ссылками излагать нельзя."),
        ("speech", "Грубые слова", "Оскорбительные выражения не допускаются."),
        ("question", "Слухи и догадки", "Пишем только то, что подтверждается источником."),
        ("building", "Жалоба в тот же орган", "На ответ органа жалуются выше, а не в него самого."),
        ("warning", "Ложные сведения", "За клевету отвечает заявитель; расходы могут взыскать."),
    ]
    for index, (name, head, body) in enumerate(bans):
        x, y = 0.6 + (index % 3) * 4.11, 1.7 + (index // 3) * 2.58
        shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE, x, y, 3.9, 2.35, fill=RED, tint=0.86, radius=0.08, name=f"Запрет {index + 1}")
        icon(slide, name, x + 0.25, y + 0.28, 0.95, circle=WHITE)
        icon(slide, "ban", x + 0.82, y + 0.82, 0.5, circle=None)
        text(slide, x + 1.45, y + 0.28, 2.3, 0.95, head, size=18, bold=True, color=RED, anchor=MSO_ANCHOR.MIDDLE)
        text(slide, x + 0.3, y + 1.38, 3.35, 0.9, body, size=14)

    # ---------- 8. Куда писать ----------
    slide = content_slide(prs, "Куда писать: вопрос → орган",
                          "Указ Президента № 498: обращение, куда бы оно ни поступило, первоначально рассматривает местный орган по месту, "
                          "где возник вопрос. Адреса сверены только у горисполкома (ул. Первомайская, 28а) и городского центра гигиены "
                          "(ул. Лазаренко, 66); остальные названия и адреса нужно сверить по официальным сайтам.")
    routes = [
        ("soap", "Чистота, продукты, насекомые", "центр гигиены и эпидемиологии"),
        ("bags", "Ночной режим, терраса, права потребителей", "горисполком: управление торговли и услуг"),
        ("ruler", "Вывеска, фасад, перепланировка", "горисполком: архитектура и градостроительство"),
        ("building", "Здание — историко-культурная ценность", "управление культуры, Министерство культуры"),
        ("bricks", "Стены, проёмы, реконструкция", "строительный надзор"),
        ("fire", "Выходы, угли кальяна, горючий декор", "МЧС, пожарный надзор"),
        ("receipt", "Чеки и приём оплаты", "налоговая инспекция"),
        ("lizard", "Рептилии и их содержание", "природоохранные органы, ветеринарная служба"),
        ("moon", "Шум ночью", "милиция — по обращениям жильцов"),
        ("briefcase", "Оформление работников", "инспекция труда"),
    ]
    for index, (name, question, body) in enumerate(routes):
        x, y = 0.6 + (index // 5) * 6.17, 1.62 + (index % 5) * 0.95
        shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE, x, y, 5.96, 0.83, fill=TINT, radius=0.2, name=f"Маршрут {index + 1}")
        icon(slide, name, x + 0.12, y + 0.09, 0.65, circle=WHITE)
        text(slide, x + 0.92, y + 0.04, 4.95, 0.75,
             [[(question, {"bold": True, "color": GREEN})], [("→ " + body, {})]], size=14, anchor=MSO_ANCHOR.MIDDLE)
    text(slide, 0.6, 6.42, 11.3, 0.5,
         "Куда бы ни пришло обращение, первым его рассматривает местный орган. Названия части органов ещё сверяем.",
         size=14, color=SLATE)

    # ---------- 9. Наш порядок ----------
    slide = content_slide(prs, "Наш порядок: с чего начинаем",
                          "Порядок из strategy/2026-11-15_povody-kratko.md. Проекты первых двух писем лежат в папке letters; поля заявителя "
                          "в них пустые. По «Смак.BY» писать о фасаде нужно до того, как прорежут вход.")
    shape(slide, MSO_SHAPE.RECTANGLE, 1.2, 2.13, 8.2, 0.06, fill=TEAL, tint=0.5, name="Линия порядка")
    plan = [
        ("soap", "Санитарная служба", "«Амазонка»: просроченные продукты и насекомые.", "проект готов"),
        ("building", "Горисполком и охрана наследия", "«Амазонка»: вывеска, фасад, терраса, согласования работ.", "проект готов"),
        ("fire", "МЧС", "Выходы, вместимость, кальяны, жилой дом.", ""),
        ("receipt", "Торговля и налоговая", "«Смак.BY» — после покупки с чеком.", ""),
    ]
    for index, (name, head, body, mark) in enumerate(plan):
        x = 0.6 + index * 2.28
        badge(slide, x + 0.74, 1.86, 0.6, str(index + 1), font=18)
        shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE, x, 2.7, 2.1, 3.9, fill=TINT, radius=0.07, name=f"Шаг {index + 1}")
        icon(slide, name, x + 0.62, 2.88, 0.86, circle=WHITE)
        text(slide, x + 0.15, 3.85, 1.8, 0.95, head, size=16, bold=True, color=GREEN, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
        text(slide, x + 0.15, 4.83, 1.8, 1.2, body, size=14, align=PP_ALIGN.CENTER)
        if mark:
            pill = shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE, x + 0.35, 6.1, 1.4, 0.36, fill=TEAL, radius=0.5, name="Метка: проект готов")
            text(slide, 0, 0, 0, 0, mark, size=12, bold=True, color=WHITE, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE, into=pill)
    shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE, 9.85, 1.7, 2.88, 2.6, fill=RED, tint=0.86, radius=0.08, name="Срочно")
    icon(slide, "warning", 10.02, 1.86, 0.7, circle=WHITE)
    text(slide, 10.85, 1.86, 1.75, 0.7, "Срочно", size=18, bold=True, color=RED, anchor=MSO_ANCHOR.MIDDLE)
    text(slide, 10.02, 2.7, 2.55, 1.5, "«Смак.BY»: письмо о работах на фасаде — пока вход не прорезан.", size=14)
    shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE, 9.85, 4.5, 2.88, 2.1, fill=AMBER, tint=0.8, radius=0.08, name="Параллельно")
    icon(slide, "house", 10.02, 4.66, 0.7, circle=WHITE)
    text(slide, 10.85, 4.66, 1.75, 0.7, "Параллельно", size=18, bold=True, color=GREEN, anchor=MSO_ANCHOR.MIDDLE)
    text(slide, 10.02, 5.5, 2.55, 1.0, "Жильцы домов подают свои обращения.", size=14)

    # ---------- 10. Сроки ----------
    slide = content_slide(prs, "Сроки, которые нужно знать",
                          "Ст. 17, п. 3: письменные обращения рассматриваются не позднее пятнадцати дней, а требующие дополнительного изучения и "
                          "проверки — не позднее одного месяца. Ст. 10, п. 3: пересылка по компетенции — пять рабочих дней. Ст. 19, п. 1: "
                          "обращения рассматриваются без взимания платы.")
    stats = [
        ("15", "дней", "обычный срок рассмотрения письменного обращения", TEAL),
        ("1", "месяц", "если нужны дополнительное изучение и проверка", GREEN),
        ("5", "рабочих дней", "на пересылку, если письмо пришло не по адресу", SLATE),
    ]
    for index, (figure, unit, body, color) in enumerate(stats):
        x = 0.6 + index * 4.11
        shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE, x, 1.7, 3.9, 3.05, fill=TINT, radius=0.07, name=f"Срок {index + 1}")
        text(slide, x + 0.2, 1.8, 3.5, 1.55, [[(figure, {"size": 60})], [(unit, {"size": 20})]], bold=True, color=color,
             align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
        text(slide, x + 0.35, 3.5, 3.2, 1.1, body, size=16, align=PP_ALIGN.CENTER)
    icon(slide, "calendar", 0.6, 5.15, 1.15, circle=TINT)
    text(slide, 2.0, 5.1, 10.7, 1.3,
         ["Записываем дату подачи. Храним второй экземпляр с отметкой о приёме или почтовую квитанцию.",
          "Обращения рассматривают бесплатно."],
         size=16, after=6, anchor=MSO_ANCHOR.MIDDLE)

    # ---------- 11. Если ответ не устроил ----------
    slide = content_slide(prs, "Если ответ не устроил",
                          "Ст. 20: ответ обжалуется в вышестоящую организацию, после этого — в суд. Ст. 10, п. 6: запрещено направлять жалобы "
                          "в организацию, действия которой обжалуются. Ст. 12, п. 7: в обращении должна быть информация о результатах прежнего "
                          "рассмотрения с подтверждающими документами. Примеры — из authorities/README.md.")
    stairs = [("Местный орган", 0.6, 5.35, TEAL, 0.6), ("Вышестоящий орган", 2.75, 4.2, TEAL, 0.0), ("Суд", 4.9, 3.05, GREEN, 0.0)]
    for index, (label, x, y, color, tint) in enumerate(stairs):
        step = shape(slide, MSO_SHAPE.RECTANGLE, x, y, 2.15, 6.65 - y, fill=color, tint=tint, name=f"Ступень: {label}")
        text(slide, 0, 0, 0, 0, label, size=16, bold=True, color=WHITE if index else INK, align=PP_ALIGN.CENTER,
             anchor=MSO_ANCHOR.TOP, into=step, margin=0.12)
    icon(slide, "scales", 5.4, 1.75, 1.15, circle=TINT)
    shape(slide, MSO_SHAPE.UP_ARROW, 1.4, 4.1, 0.5, 1.05, fill=AMBER, name="Стрелка вверх 1")
    shape(slide, MSO_SHAPE.UP_ARROW, 3.55, 2.95, 0.5, 1.05, fill=AMBER, name="Стрелка вверх 2")
    text(slide, 7.6, 1.7, 5.13, 0.45, "Примеры", size=20, bold=True, color=GREEN)
    for index, chain in enumerate(["Городской центр гигиены → областной центр гигиены → Министерство здравоохранения",
                                   "Горисполком → облисполком"]):
        card = shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE, 7.6, 2.25 + index * 1.25, 5.13, 1.05, fill=TINT, radius=0.12, name=f"Пример {index + 1}")
        text(slide, 0, 0, 0, 0, chain, size=15, anchor=MSO_ANCHOR.MIDDLE, into=card, margin=0.18)
    text(slide, 7.6, 4.85, 5.13, 1.8,
         [[("В жалобе пишем, ", {"bold": True}), ("что уже обращались, и прикладываем полученный ответ.", {})],
          [("Жалобу на орган ", {"bold": True}), ("подают не в него самого, а выше.", {})]],
         size=16, after=10)

    # ---------- 12. Коллективное обращение ----------
    slide = content_slide(prs, "Коллективное обращение и жильцы",
                          "Ст. 22: коллективные обращения тридцати и более заявителей рассматриваются с выездом на место; ответ направляется "
                          "заявителю, указанному для ответа, иначе первому в списке, указавшему адрес. Постановление Совета Министров № 319, п. 8: "
                          "три и более коллективных обращения за календарный год от жителей в радиусе 50 метров с обоснованными жалобами — "
                          "основание признать согласование ночного режима утратившим силу (сверить по действующей редакции).")
    shape(slide, MSO_SHAPE.OVAL, 0.75, 1.95, 3.6, 3.6, fill=TINT, name="Круг: жильцы")
    icon(slide, "house", 1.3, 2.25, 2.5, circle=None)
    icon(slide, "people", 2.95, 4.2, 1.5, circle=WHITE, ring=(TEAL, 2))
    text(slide, 0.6, 5.85, 3.9, 0.9, "Обращение жильцов весит больше обращения посетителя.", size=14, color=SLATE, align=PP_ALIGN.CENTER)
    facts = [
        ("pen", "Одно письмо — несколько подписей",
         "Ответ придёт тому, кто указан для ответа, иначе первому в списке с адресом."),
        ("office", "30 и более заявителей", "Обращение рассматривают с выездом на место."),
        ("moon", "Три коллективных обращения жильцов за год",
         "Основание отменить ночной режим: жители в радиусе 50 метров, обоснованные жалобы."),
    ]
    for index, (name, head, body) in enumerate(facts):
        y = 1.7 + index * 1.68
        shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE, 4.95, y, 7.78, 1.5, fill=TINT, radius=0.1, name=f"Факт {index + 1}")
        icon(slide, name, 5.15, y + 0.27, 0.95, circle=WHITE)
        text(slide, 6.35, y + 0.14, 6.2, 0.5, head, size=18, bold=True, color=GREEN, anchor=MSO_ANCHOR.MIDDLE)
        text(slide, 6.35, y + 0.68, 6.2, 0.75, body, size=14)

    # ---------- 13. Что подготовить ----------
    slide = content_slide(prs, "Что подготовить до подачи",
                          "Подробно: strategy/2026-11-15_pamyatka_osmotr-i-pokupka.md (осмотр и покупка) и strategy/2026-11-15_zhiltsam_obrazec.md "
                          "(жильцам). Книга замечаний предъявляется по первому требованию: ст. 24, п. 2; её непредъявление — ч. 2 ст. 10.10 КоАП.")
    todo = [
        ("idcard", "Заявитель", "фамилия, имя, отчество и адрес"),
        ("camera", "Осмотр на месте", "фото, размеры, число мест, выходы"),
        ("receipt", "Покупка с чеком", "чек покажет, кто продавец"),
        ("clip", "Исходные файлы", "фото и видео с датами съёмки"),
        ("document", "Приложения", "перечень публикаций с датами и выдержками"),
        ("memo", "Книга замечаний", "попросить и записать, когда её дали"),
    ]
    for index, (name, head, body) in enumerate(todo):
        x, y = 0.6 + (index % 2) * 6.17, 1.7 + (index // 2) * 1.68
        shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE, x, y, 5.96, 1.48, fill=TINT, radius=0.1, name=f"Пункт {index + 1}")
        icon(slide, name, x + 0.22, y + 0.24, 1.0, circle=WHITE)
        text(slide, x + 1.45, y + 0.2, 3.6, 0.5, head, size=18, bold=True, color=GREEN, anchor=MSO_ANCHOR.MIDDLE)
        text(slide, x + 1.45, y + 0.74, 3.6, 0.65, body, size=14)
        box = shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE, x + 5.2, y + 0.5, 0.48, 0.48, fill=WHITE, line=(TEAL, 2), radius=0.15, name="Клетка")
        box.name = "Клетка для отметки"

    # ---------- 14. Памятка ----------
    slide = prs.slides.add_slide(prs.slide_layouts[5])
    background(slide, GREEN)
    title(slide, "Памятка на одну страницу", dark=True)
    slide_number(slide, dark=True)
    rules = ["Один орган — одно письмо", "Факты с датой и источником", "«Прошу проверить», без обвинений",
             "Фамилия, адрес, подпись", "Не согласны — в вышестоящий орган"]
    for index, rule in enumerate(rules):
        y = 1.72 + index * 0.92
        badge(slide, 0.6, y, 0.64, str(index + 1), fill=AMBER, font=20, color=INK)
        text(slide, 1.5, y, 6.3, 0.64, rule, size=22, bold=True, color=WHITE, anchor=MSO_ANCHOR.MIDDLE)
    shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE, 8.2, 1.72, 4.53, 3.75, fill=WHITE, radius=0.06, name="Осталось решить")
    icon(slide, "question", 8.45, 1.95, 0.95, circle=TINT)
    text(slide, 9.6, 1.95, 2.95, 0.95, "Осталось решить", size=20, bold=True, color=GREEN, anchor=MSO_ANCHOR.MIDDLE)
    text(slide, 8.45, 3.1, 4.05, 2.2,
         ["Кто будет заявителем.", "В какой центр гигиены подавать первым: городской или областной.",
          "Давать ли органу адреса публикаций, где видны имена авторов."],
         size=16, after=10)
    notes(slide, "Открытые вопросы — из tasks.md: заявитель не определён; первый адресат санитарного письма не выбран; адреса публикаций "
                 "Threads содержат имена авторов.")

    prs.core_properties.title = "Как подавать обращения и жалобы"
    prs.core_properties.subject = "Порядок подачи обращений по делу «Амазонка» и «Смак.BY»"
    prs.core_properties.author = ""
    prs.core_properties.language = "ru-RU"
    prs.save(target)
    apply_theme(target)
    shutil.rmtree(_icon_dir, ignore_errors=True)


def apply_theme(target):
    """Записывает цвета и шрифты темы: python-pptx сам тему не меняет."""
    namespace = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main"}
    source = Path(target)
    temporary = source.with_suffix(".tmp")
    with zipfile.ZipFile(source) as archive, zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED) as output:
        for item in archive.infolist():
            data = archive.read(item.filename)
            if item.filename.startswith("ppt/theme/theme") and item.filename.endswith(".xml"):
                root = etree.fromstring(data)
                root.set("name", THEME["name"])
                scheme = root.find(".//a:clrScheme", namespace)
                scheme.set("name", THEME["name"])
                for child in scheme:
                    key = etree.QName(child).localname
                    if key in THEME["colors"]:
                        for old in list(child):
                            child.remove(old)
                        etree.SubElement(child, qn("a:srgbClr"), {"val": THEME["colors"][key]})
                fonts = root.find(".//a:fontScheme", namespace)
                fonts.set("name", THEME["name"])
                fonts.find("a:majorFont/a:latin", namespace).set("typeface", THEME["major"])
                fonts.find("a:minorFont/a:latin", namespace).set("typeface", THEME["minor"])
                data = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
            output.writestr(item, data)
    temporary.replace(source)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: python -I -X utf8 strategy/_build/build_presentation_obrashcheniya.py <out.pptx>")
    build(sys.argv[1])
    print("saved:", ascii(sys.argv[1]))
