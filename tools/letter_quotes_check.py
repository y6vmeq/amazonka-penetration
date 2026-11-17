"""Сверяет цитаты «…» из проекта обращения с сохранёнными источниками.

Запуск из корня проекта:
    python -I -X utf8 tools/letter_quotes_check.py <письмо.md> [<доп. источник> ...]

Проверяется текст самого письма (между первой и второй строкой «---») и разделы «## Приложение …».
Каждая цитата ищется в записях sources/reviews/ALL.jsonl (поля text и reply) и в дополнительных файлах
(сырые копии страниц, тексты актов). Сравнение идёт без пробелов и переносов: при извлечении текста из PDF
в словах появляются лишние пробелы. Оценки:
    OK    — найдено дословно;
    Е/Ё   — найдено, если не различать «е» и «ё» (обычно это название органа или акта);
    ПЕР   — найдено, если не учитывать дефисы: в тексте, извлечённом из старых PDF (опубликования до 2012 г.),
            слова разорваны переносами на концах строк («разреши-тельной»); такую цитату просмотреть глазами;
    НЕТ   — не найдено: это название, надпись с изображения или ошибка. Каждую такую строку просмотреть.
Код возврата 1, если есть хотя бы одна оценка НЕТ.
"""
import html
import json
import re
import sys
from pathlib import Path

QUOTE = re.compile(r"«([^«»]+)»")
TAG = re.compile(r"<[^>]+>")


def squeeze(text):
    return re.sub(r"\s+", "", html.unescape(str(text or "")).replace(" ", " "))


def plain(text):
    return squeeze(text).replace("ё", "е").replace("Ё", "Е")


def bare(text):
    return re.sub("[-‐‑­]", "", plain(text))


def letter_part(path):
    lines = path.read_text(encoding="utf-8").split("\n")
    rules = [index for index, line in enumerate(lines) if line.strip() == "---"]
    if len(rules) < 2:
        sys.exit("в файле письма нет двух строк «---»")
    part = lines[rules[0] + 1:rules[1]]
    keep = False
    for line in lines[rules[1] + 1:]:
        if line.startswith("## "):
            keep = line.startswith("## Приложение")
        if keep:
            part.append(line)
    return "\n".join(part)


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    sources = []
    for line in Path("sources/reviews/ALL.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            record = json.loads(line)
            sources.append((record["id"], squeeze(record.get("text")) + "\u0000" + squeeze(record.get("reply"))))
    for name in sys.argv[2:]:
        raw = Path(name).read_text(encoding="utf-8", errors="replace")
        if name.endswith(".json"):
            raw = raw.replace("\\n", " ").replace('\\"', '"')
        sources.append((Path(name).name, squeeze(raw) + "\u0000" + squeeze(TAG.sub(" ", raw))))
    seen, missing, hyphen = [], 0, 0
    for quote in QUOTE.findall(letter_part(Path(sys.argv[1]))):
        quote = re.sub(r"\*\*", "", quote).strip()
        if quote in seen:
            continue
        seen.append(quote)
        exact = [name for name, text in sources if squeeze(quote) in text]
        loose = [] if exact else [name for name, text in sources if plain(quote) in text.replace("ё", "е").replace("Ё", "Е")]
        if not exact and not loose:
            loose = [name for name, text in sources if bare(quote) in bare(text)]
            mark = "ПЕР" if loose else "НЕТ"
        else:
            mark = "OK " if exact else "Е/Ё"
        missing += mark == "НЕТ"
        hyphen += mark == "ПЕР"
        where = ", ".join((exact or loose)[:3]) + (" …" if len(exact or loose) > 3 else "")
        print(f"{mark}  «{quote[:110]}{'…' if len(quote) > 110 else ''}»" + (f"  ← {where}" if where else ""))
    print(f"цитат: {len(seen)}, не найдено: {missing}" + (f", найдено без учёта переносов (ПЕР): {hyphen}" if hyphen else ""))
    sys.exit(1 if missing else 0)


if __name__ == "__main__":
    main()
