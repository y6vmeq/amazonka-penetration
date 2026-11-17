"""Поиск грубых слов в публикациях, копии которых прикладываются к письму.

Зачем: пункт 5 статьи 12 Закона об обращениях не допускает в обращении нецензурных и оскорбительных
слов, а приложенные копии — часть обращения (стандарт писем, раздел 8, пункт 66). На глаз такие слова
пропускаются: на снимке виден весь отзыв, а в письме из него приведена одна фраза.

Что делает: берёт записи свода `sources/reviews/ALL.jsonl`, названные в описании приложения 1
(`letters/_src/<имя>_prilozhenie-1.json`) и в таблицах приложений самого письма, и ищет в полном тексте
каждой записи слова из двух списков:
  ГРУБО     — нецензурные и оскорбительные слова и их сокращения: на копии закрыть обязательно;
  ПРОСМОТР  — просторечные и резкие слова: посмотреть глазами и решить.

Запуск из корня проекта:
    python -I -X utf8 tools/letter_copies_scan.py                 # все письма набора
    python -I -X utf8 tools/letter_copies_scan.py letters/<имя>.md
Список слов заведомо неполон: пустой вывод не отменяет просмотра копий перед подачей.
"""
import json
import re
import sys
from pathlib import Path

B = r"(?<![а-яё])"  # начало слова
E = r"(?![а-яё])"   # конец слова
COARSE = [
    B + r"хз" + E, r"хрен", r"дерьм", r"говн", B + r"жоп", B + r"бл[яе]+" + E, r"бляд", r"пизд", B + r"хер" + E, r"херн", B + r"ху[йеёяю]",
    B + r"[её]б[аеиоуыюя][а-яё]+", r"(?:за|на|у|вы|до|разъ|объ)[её]б", r"мудак|мудил", B + r"сук[аиу]" + E, r"сучк|сучь", B + r"твар", B + r"урод",
    r"идиот", r"дебил", r"мраз", r"скотин", B + r"ссан|обосс|обоср|засран|" + B + r"срат|" + B + r"сран", r"придур|кретин", r"быдл", r"шалав|шлюх|проститут",
    B + r"лох" + E + r"|лохотрон", r"параш", B + r"гнид", B + r"падл", B + r"чмо" + E, r"ублюд", r"сволоч", r"подон",
]
LOOK = [
    r"нахрен|на хрен|нафиг|на фиг|пофиг|" + B + r"фиг" + E, r"охрен|офиг", r"пипец|капец|звездец|трындец", r"отстой", r"срач", r"блев|блюв", r"вонюч|воняет|вонь",
    r"задниц", B + r"свин(?:ь|ств|арн)", r"гадюшн|гадост", B + r"ч[её]рт" + E, r"туп(?:ые|ых|ой|ая|ость)", r"мерзк|мерзост", r"тошнотв", r"жулик|мошенник|" + B + r"ворь[её]|" + B + r"воры" + E,
]
COARSE_RX = re.compile("(?i)" + "|".join(f"(?:{p})" for p in COARSE))
LOOK_RX = re.compile("(?i)" + "|".join(f"(?:{p})" for p in LOOK))
RECORD_ID = re.compile(r"(?<![\w-])([a-z]+(?:-[a-z]+)*-\d{3})(?![\w-])")
SET = [
    "sanitarnaya-sluzhba_amazonka", "gorispolkom_amazonka_zdanie-fasad-reklama", "gorispolkom_amazonka_torgovlya", "prirodoohrana_amazonka_zhivotnye", "nalogovaya_amazonka",
    "sanitarnaya-sluzhba_smak-by", "gorispolkom_smak-by_raboty-okna-vhod", "gorispolkom_smak-by_torgovlya", "nalogovaya_smak-by",
]


def load_records():
    records = {}
    for line in Path("sources/reviews/ALL.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            record = json.loads(line)
            records[record.get("id")] = record
    return records


def rows_of(letter):
    """Записи свода, копии которых прикладываются: {идентификатор: где названа}."""
    rows = {}
    source = Path("letters/_src") / f"{letter.stem}_prilozhenie-1.json"
    if source.is_file():
        for number, item in enumerate(json.loads(source.read_text(encoding="utf-8")).get("items", []), 1):
            rows.setdefault(item.get("id"), f"приложение 1, строка {number}")
    parts = re.split(r"(?m)^---\s*$", letter.read_text(encoding="utf-8"))
    tail = "---".join(parts[2:]).split("## Откуда каждый факт")[0]
    title = ""
    for line in tail.split("\n"):
        heading = re.match(r"## (Приложение \d+)", line)
        if heading:
            title = heading.group(1).lower()
        cells = [cell.strip() for cell in line.split("|")]
        if len(cells) > 3 and cells[1].isdigit():
            for ident in RECORD_ID.findall(line):
                rows.setdefault(ident, f"{title or 'приложение'}, строка {cells[1]}")
    return rows


def scan(letter, records):
    rows = rows_of(letter)
    found = 0
    print(f"{letter.name}: записей свода в приложениях — {len(rows)}")
    for ident, where in rows.items():
        text = str((records.get(ident) or {}).get("text") or "")
        for mark, pattern in (("ГРУБО   ", COARSE_RX), ("ПРОСМОТР", LOOK_RX)):
            seen = set()
            for match in pattern.finditer(text):
                word = match.group(0).lower()
                if word in seen:
                    continue
                seen.add(word)
                found += mark.startswith("ГРУБО")
                first, last = match.start(), match.end()
                while first > 0 and re.match("[а-яёА-ЯЁ]", text[first - 1]):
                    first -= 1
                while last < len(text) and re.match("[а-яёА-ЯЁ]", text[last]):
                    last += 1
                start, end = max(0, first - 40), min(len(text), last + 40)
                context = text[start:first] + "[…]" + text[last:end] if mark.startswith("ГРУБО") else text[start:end]
                print(f"  {mark} {where} ({ident}): …{context}…".replace("\n", " "))
    return found


def main():
    letters = [Path(arg) for arg in sys.argv[1:]] or [Path("letters") / f"{name}.md" for name in SET]
    records = load_records()
    total = sum(scan(letter, records) for letter in letters)
    print(f"итого грубых слов, которые нужно закрыть на копиях: {total}")


if __name__ == "__main__":
    main()
