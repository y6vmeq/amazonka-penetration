"""Собирает выписку общих требований пожарной безопасности (Декрет № 7) для объектов общественного питания.

Запуск из корня проекта:
    python -I law/texts/sanitary-obshchepit/_build/build_fire.py

Читает law/texts/animals-sanitary/raw/010_etalonline-by_dekret7-etalon.html,
пишет law/dekret-7-2017_pozharnye-trebovaniya.md. Цитаты переносятся программой.
Проверка: python -I tools/md_quotes_check.py law/dekret-7-2017_pozharnye-trebovaniya.md <та же страница>
"""
import html
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / "law/texts/animals-sanitary/raw/010_etalonline-by_dekret7-etalon.html"
TARGET = ROOT / "law/dekret-7-2017_pozharnye-trebovaniya.md"
START = "Общие требования пожарной безопасности к содержанию и эксплуатации"
END = "Общие санитарно-эпидемиологические требования к содержанию и эксплуатации"


def paragraphs(path):
    text = path.read_bytes().decode("utf-8-sig")
    text = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", text)
    text = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</tr>|</h\d>|</li>", "\n", text)
    text = html.unescape(re.sub(r"<[^>]*>", "", text)).replace("\xa0", " ")
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
    return [line for line in lines if line]


lines = paragraphs(SOURCE)
start = next(i for i, line in enumerate(lines) if line.startswith(START) and "(прилагается)" not in line)
end = next(i for i, line in enumerate(lines) if i > start and line.startswith(END))
section = lines[start + 1:end]

points, notes, current, expected, in_notes = {}, {}, None, 1, False
for line in section:
    if set(line) == {"_"}:
        in_notes = True
        continue
    if line.startswith("ГЛАВА ") or line.isupper():
        in_notes = False
        continue
    if re.match(rf"^{expected}\. ", line):
        current, in_notes = expected, False
        points[current] = [line]
        expected += 1
        continue
    if current is None:
        continue
    if in_notes and re.match(r"^\d+ ", line):
        notes.setdefault(current, []).append(line)
        continue
    in_notes = False
    points[current].append(line)


def quote(items):
    return "«" + "\n".join(items) + "»"


def p(number, first=None, last=None):
    return quote(points[number][first:last])


parts = [
    "# Общие требования пожарной безопасности (Декрет № 7) — выписки для объектов общественного питания",
    "",
    "> Эти требования утверждены Декретом Президента и обязательны для каждого объекта (подп. 3.5 п. 3 Декрета — см. `law/dekret-7-2017_sanitarnye-trebovaniya.md`, раздел 1). Требования к проектированию и планировке зданий — в строительных нормах: `law/sn-2.02.05-2020_fire.md`. Разбор по «Амазонке»: `law/_analysis_amazonka-capacity-exits-fire.md`.",
    "",
    "- **Акт:** Декрет Президента Республики Беларусь от 23 ноября 2017 г. № 7 «О развитии предпринимательства». Им утверждены «Общие требования пожарной безопасности к содержанию и эксплуатации капитальных строений (зданий, сооружений), изолированных помещений и иных объектов, принадлежащих субъектам хозяйствования».",
    "- **Источник текста:** ЭТАЛОН-ONLINE, https://etalonline.by/document/?regnum=Pd1700007.",
    "- **Копия:** `law/texts/animals-sanitary/raw/010_etalonline-by_dekret7-etalon.html`, SHA-256 `eb909e33070f914d9d2679227f3bab2cf783213359f8c7493d41cf9588848c47`, загружено 15.11.2026 10:22 UTC.",
    "- **Редакция:** действующая на 15.11.2026 (с изменениями, внесёнными Законом от 15.04.2026 № 139-З); с 01.01.2027 вступают в силу новые изменения — тогда текст сверить заново.",
    "- **Проверка цитат:** `python -I tools/md_quotes_check.py law/dekret-7-2017_pozharnye-trebovaniya.md law/texts/animals-sanitary/raw/010_etalonline-by_dekret7-etalon.html`. Файл собран скриптом `law/texts/sanitary-obshchepit/_build/build_fire.py`; цитаты перенесены программой.",
    "- Цифра сразу после слова в цитате — знак сноски в тексте акта.",
    "",
    "## 1. Обязанности руководителя, инструкции",
    "",
    "**п. 3** (начало и подп. 3.1). " + p(3, 0, 4),
    "",
    "**п. 7.** " + p(7),
    "",
    "**п. 9.** " + p(9),
    "",
    "## 2. Курение, угли, открытый огонь",
    "",
    "**п. 11.** " + p(11),
    "",
    "**п. 12.** " + p(12),
    "",
    "**п. 17.** " + p(17),
    "",
    "**п. 21.** " + p(21),
    "",
    "**Сноска 2 к п. 21.** " + quote(notes[21]),
    "",
    "- Кальян: режим курения в зале общепита должен быть определён общеобъектовой инструкцией по пожарной безопасности, а места для курения — оборудованы и обозначены (пп. 11, 12). Разрешено ли курение кальяна в зале вообще, решают другие акты; они не выписаны.",
    "- Угли: п. 17 говорит о приспособлениях для горящего угля на территории объектов общепита и требует тушить остатки «до полного прекращения тления». К углям кальяна, выброшенным в пластиковую урну (отзыв google-maps-024), его можно применить только по смыслу: в письме это вопрос к органу.",
    "- Открытый огонь в зале разрешён только как свечи при оформлении столов, подаче блюд и изделий (сноска 2).",
    "",
    "## 3. Шторы, декор, вентиляция",
    "",
    "**п. 25.** " + p(25),
    "",
    "**п. 28.** " + p(28),
    "",
    "## 4. Электрооборудование",
    "",
    "**п. 30** (начало и абзац третий). " + quote([points[30][0]]) + " … " + quote([points[30][2]]),
    "",
    "## 5. Эвакуация",
    "",
    "**п. 44.** " + p(44),
    "",
    "**п. 45.** " + p(45),
    "",
    "**п. 48.** " + p(48),
    "",
    "**п. 50** (начало и абзац второй). " + p(50, 0, 2),
    "",
    "## 6. Огнетушители",
    "",
    "**п. 53.** " + p(53),
    "",
    "**п. 54.** " + p(54),
    "",
    "## 7. Чего здесь нет",
    "",
    "- Числа эвакуационных выходов, ширины проходов, требований к отделке: это строительные нормы (`law/sn-2.02.05-2020_fire.md`).",
    "- Норм о предельном числе людей в зале в этом акте нет.",
    "- Ответственность — ст. 24.36 КоАП: `law/koap_pomeshchenie-pozhar-nasledie-fasad.md`, раздел 1. Порядок надзора органов МЧС не выписан.",
    "",
]
TARGET.write_text("\n".join(parts), encoding="utf-8", newline="\n")
print("written", TARGET.relative_to(ROOT).as_posix(), "points parsed:", len(points))
