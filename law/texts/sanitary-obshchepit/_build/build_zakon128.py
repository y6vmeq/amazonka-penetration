"""Собирает выписку Закона «О государственном регулировании торговли и общественного питания» (№ 128-З).

Запуск из корня проекта:
    python -I law/texts/sanitary-obshchepit/_build/build_zakon128.py

Читает law/texts/animals-sanitary/raw/069_etalonline-by_etalon-zakon128-torgovlya.html,
пишет law/zakon-128-z_torgovlya-obshchepit.md. Цитаты переносятся программой.
Проверка: python -I tools/md_quotes_check.py law/zakon-128-z_torgovlya-obshchepit.md <та же страница>
"""
import html
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / "law/texts/animals-sanitary/raw/069_etalonline-by_etalon-zakon128-torgovlya.html"
TARGET = ROOT / "law/zakon-128-z_torgovlya-obshchepit.md"


def paragraphs(path):
    text = path.read_bytes().decode("utf-8-sig")
    text = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", text)
    text = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</tr>|</h\d>|</li>", "\n", text)
    text = html.unescape(re.sub(r"<[^>]*>", "", text)).replace("\xa0", " ")
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
    return [line for line in lines if line]


lines = paragraphs(SOURCE)


def article(number):
    starts = [i for i, line in enumerate(lines) if line.startswith(f"Статья {number}. ")]
    body = [lines[starts[-1]]]
    for line in lines[starts[-1] + 1:]:
        if line.startswith(("Статья ", "ГЛАВА ", "Президент Республики Беларусь")):
            break
        body.append(line)
    return body


def points(body, wanted):
    out, keep = [], False
    for line in body[1:]:
        match = re.match(r"^(\d+)\. ", line)
        if match:
            keep = int(match.group(1)) in wanted
        if keep:
            out.append(line)
    return out


def quote(items):
    return "«" + "\n".join(items) + "»"


a1, a11, a12, a17, a20, a27, a28 = (article(n) for n in (1, 11, 12, 17, 20, 27, 28))
definition = {key: next(line for line in a1 if line.startswith(key + " ")) for key in ("1.8.", "1.13.")}
edition = next(line for line in lines if line.startswith("с изменениями (дополнениями), внесенными Законом от 30.12.2025"))
p12 = points(a12, {1})

parts = [
    "# Закон о торговле и общественном питании (№ 128-З) — выписки: режим работы, Торговый реестр, летние площадки",
    "",
    "> Нужна для вопросов о ночном режиме «Амазонки», о числе мест в Торговом реестре, о летней террасе и о работе «Смак.BY» до открытия. Разборы: `law/_analysis_amazonka-capacity-exits-fire.md`, `law/_analysis_amazonka-building-facade.md`.",
    "",
    "- **Акт:** Закон Республики Беларусь от 8 января 2014 г. № 128-З «О государственном регулировании торговли и общественного питания».",
    "- **Источник текста:** ЭТАЛОН-ONLINE, https://etalonline.by/document/?regnum=H11400128.",
    "- **Копия:** `law/texts/animals-sanitary/raw/069_etalonline-by_etalon-zakon128-torgovlya.html`, загружена 15.11.2026 (SHA-256 — в `law/texts/animals-sanitary/raw/manifest.jsonl`).",
    f"- **Редакция.** Первая строка перечня редакций на странице: «{edition}».",
    "- **Проверка цитат:** `python -I tools/md_quotes_check.py law/zakon-128-z_torgovlya-obshchepit.md law/texts/animals-sanitary/raw/069_etalonline-by_etalon-zakon128-torgovlya.html`. Файл собран скриптом `law/texts/sanitary-obshchepit/_build/build_zakon128.py`.",
    "",
    "## 1. Режим работы ночью",
    "",
    "**ст. 17, п. 1** (части первая и вторая). " + quote(points(a17, {1})[:2]),
    "",
    "**ст. 17, п. 2.** " + quote(points(a17, {2})),
    "",
    "- Заведение, которое после 23:00 продаёт алкоголь или пиво, обязано согласовать ночной режим с районным или городским исполкомом. В едином перечне это процедура 8.8.1 (`law/kodeks-o-kulture_ohrana-naslediya.md`, раздел 6).",
    "- Порядок и условия согласования определяет Совет Министров; это постановление не выписано.",
    "",
    "## 2. Торговый реестр",
    "",
    "**ст. 20, п. 1.** " + quote(points(a20, {1})),
    "",
    "**ст. 20, пп. 4 и 5** (без части третьей п. 5). " + quote(points(a20, {4}) + points(a20, {5})[:2]),
    "",
    "- Осуществлять общественное питание в объекте можно «со дня включения сведений» о нём в Торговый реестр.",
    "- Сведения вносятся и меняются по заявлениям самого субъекта. Какие именно сведения (в том числе число мест) и в какой срок нужно менять, определяет Совет Министров; это постановление не выписано.",
    "",
    "## 3. Тип объекта и правила общественного питания",
    "",
    "**ст. 11, пп. 2 и 3.** " + quote(points(a11, {2, 3})),
    "",
    "**ст. 1, подп. 1.13.** " + quote([definition["1.13."]]),
    "",
    "## 4. Летние площадки",
    "",
    "**ст. 1, подп. 1.8.** " + quote([definition["1.8."]]),
    "",
    "**ст. 12, п. 1** (часть первая). " + quote(p12[:1]),
    "",
    "**ст. 12, п. 2.** " + quote(points(a12, {2})),
    "",
    "**ст. 12, п. 4.** " + quote(points(a12, {4})),
    "",
    "- Летняя площадка на земле общего пользования допускается только в месте, которое включено в перечень, определённый городским исполкомом. Перечни размещаются на сайте исполкома.",
    "- Исполком вправе установить требования к внешнему виду и размерам летних площадок.",
    "",
    "## 5. Контроль и ответственность",
    "",
    "**ст. 27.** " + quote(a27[1:]),
    "",
    "**ст. 28.** " + quote(a28[1:]),
    "",
    "Статьи КоАП — в `law/koap-13_torgovlya-raschety-alkogol.md` (ст. 13.11, ч. 1: нарушение законодательства о торговле и общественном питании).",
    "",
]
TARGET.write_text("\n".join(parts), encoding="utf-8", newline="\n")
print("written", TARGET.relative_to(ROOT).as_posix())
