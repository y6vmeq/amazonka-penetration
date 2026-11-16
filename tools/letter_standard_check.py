"""Проверяет проект обращения на соответствие стандарту letters/STANDART.md (форма и обязательные блоки).

Запуск из корня проекта:
    python -I -X utf8 tools/letter_standard_check.py letters/<имя>.md [letters/<имя2>.md ...]

Проверяется то, что можно проверить программой: части файла, разделы I–VII, обязательные формулировки
из Закона об обращениях, сквозная нумерация вопросов В1…Вn, перечень приложений, поля заявителя,
строка даты и подписи, внутренние справки, отсутствие пометок ⟦…⟧, фамилий физических лиц, учётных
записей и упоминаний заведений, исключённых из работы. Существо (верна ли норма, точен ли факт)
программа не оценивает: это делают tools/letter_quotes_check.py и проверяющие.

Оценки: OK, ОШИБКА (код возврата 1), ВНИМАНИЕ (просмотреть глазами; код возврата не меняет).
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import scope_filter  # noqa: E402  (соседний файл проекта)

ROOT = Path(__file__).resolve().parent.parent
SECTIONS = ["I", "II", "III", "IV", "V", "VI", "VII"]
LAW_QUOTES = [
    "если рассмотрены все изложенные в них вопросы, приняты надлежащие меры по защите, обеспечению реализации, восстановлению прав, свобод и (или) законных интересов заявителей и им направлены письменные ответы",
    "должны быть обоснованными и мотивированными (при необходимости – со ссылками на нормы актов законодательства), содержать конкретные формулировки, опровергающие или подтверждающие доводы заявителей",
    "принимать меры для полного, объективного, всестороннего и своевременного рассмотрения обращений",
]
SOURCES_PHRASE = "Выводов о том, что нарушения совершены, я не делаю"
SOURCES_PHRASE_OLD = "Утверждений о том, что нарушения совершены, заявление не содержит"
INTERNAL = ["Откуда каждый факт", "Проверка норм", "Что в письмо не включено", "Возможные возражения"]
# Фамилии из выписки ЕГР и карточек: в письмах их быть не должно (стандарт, раздел 4, пункт 7).
SURNAMES = ["Борохов", "Лукьянов", "Устинов", "Гончаренко", "Савицк", "Кравцов", "Максимчик", "Дук "]
RISKY = re.compile(r"незаконн|нарушил|нарушает|нарушают|виновн|преступ|мошенн|обман|антисанитар|самовольн", re.I)


def squeeze(text):
    return re.sub(r"\s+", " ", text)


def authors():
    names = set()
    path = ROOT / "sources" / "reviews" / "ALL.jsonl"
    if not path.is_file():
        return names
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            author = str(json.loads(line).get("author") or "").strip()
            if len(author) >= 6 and not re.search(r"амазонк|amazonka|смак|smak|gastrofest|могил|mogilev", author, re.I):
                names.add(author)
    return names


AUTHORS = authors()


def check(path):
    text = path.read_text(encoding="utf-8")
    parts = re.split(r"(?m)^---\s*$", text)
    results = []

    def add(level, name, detail=""):
        results.append((level, name, detail))

    if len(parts) < 3:
        add("ОШИБКА", "три части файла, разделённые строками ---", f"найдено частей: {len(parts)}")
        return results
    head, body, tail = parts[0], parts[1], "---".join(parts[2:])
    flat = squeeze(body)

    add("OK" if re.search(r"(?m)^# ПРОЕКТ\.", head) else "ОШИБКА", "шапка: заголовок «# ПРОЕКТ. …»")
    for word in ("До подачи", "Как подать", "Статус адресата"):
        add("OK" if word in head else "ОШИБКА", f"шапка: блок «{word}»")

    add("OK" if re.search(r"(?m)^## ЗАЯВЛЕНИЕ\s*$", body) else "ОШИБКА", "название «## ЗАЯВЛЕНИЕ»")
    add("OK" if "от [фамилия, имя, отчество]," in body else "ОШИБКА", "поле заявителя: «от [фамилия, имя, отчество],»")
    add("OK" if "проживающего(ей) по адресу: [" in body else "ОШИБКА", "поле адреса заявителя")

    add("OK" if re.search(r"(?m)^\*\*Кратко\.\*\*", body) else "ОШИБКА", "абзац «Кратко.» под названием (стандарт, раздел 8, пункт 2)")
    size = len(body)
    level = "OK" if size <= 30000 else ("ВНИМАНИЕ" if size <= 36000 else "ОШИБКА")
    add(level, "объём текста письма — до 30 тысяч знаков (стандарт, раздел 8, пункт 1)", f"знаков: {size}")
    add("OK" if "не могли быть проверены" not in flat else "ОШИБКА", "в абзаце об источниках нет слов «не могли быть проверены» (заменено на «мной на месте не проверялись»)")
    add("OK" if "в таком порядке" not in flat else "ВНИМАНИЕ", "в просьбах нет слов «в таком порядке» (стандарт, раздел 8, пункт 11)")
    add("OK" if re.search(r"(?m)^## Приложение \d+ \(проект\): [Нн]ормы", tail) else "ВНИМАНИЕ", "есть приложение с полными текстами норм (стандарт, раздел 2, пункт 6)")

    found = re.findall(r"(?m)^\*\*(I{1,3}|IV|V|VI{0,2})\. [^*]+\*\*\s*$", body)
    add("OK" if found == SECTIONS else "ОШИБКА", "разделы I–VII по порядку", "найдено: " + ", ".join(found))

    for quote in LAW_QUOTES:
        add("OK" if squeeze(quote) in flat else "ОШИБКА", "обязательная цитата Закона об обращениях", quote[:60] + "…")
    if SOURCES_PHRASE in flat:
        add("OK", "абзац об источниках сведений (раздел VII)")
    elif SOURCES_PHRASE_OLD in flat:
        add("ОШИБКА", "абзац об источниках сведений — в прежней редакции", "заменить на редакцию раздела 3.3 стандарта: «Выводов о том, что нарушения совершены, я не делаю…»")
    else:
        add("ОШИБКА", "абзац об источниках сведений (раздел VII)")

    numbers = [int(n) for n in re.findall(r"(?m)^(?:\*\*)?В(\d+)\.", body)]
    expected = list(range(1, len(numbers) + 1))
    add("OK" if numbers and numbers == expected else "ОШИБКА", "вопросы В1…Вn: сквозная нумерация", f"найдено {len(numbers)}: {numbers[:40]}")
    if numbers:
        ranges = {int(n) for n in re.findall(r"В1\s*[–—-]\s*В(\d+)", body)}
        add("OK" if ranges == {len(numbers)} else "ОШИБКА", "ссылка «В1–Вn» совпадает с числом вопросов", f"в тексте: {sorted(ranges)}, вопросов: {len(numbers)}")
        cited = {int(n) for n in re.findall(r"В(\d+)", body)}
        extra = sorted(n for n in cited if n > len(numbers))
        add("OK" if not extra else "ОШИБКА", "нет ссылок на несуществующие вопросы", f"лишние: {extra}")
        add("OK" if 8 <= len(numbers) <= 22 else "ВНИМАНИЕ", "вопросов от 8 до 22 (стандарт, раздел 8, пункт 1)", f"вопросов: {len(numbers)}")

    add("OK" if re.search(r"(?m)^\*{0,2}Приложения:\*{0,2}\s*$", body) else "ОШИБКА", "перечень «Приложения:»")
    add("OK" if "[дата]" in body and "[личная подпись]" in body else "ОШИБКА", "строка даты и подписи")
    listed = len(re.findall(r"(?m)^\d+\. .+", body.split("Приложения:")[-1])) if "Приложения:" in body else 0
    sections = len(re.findall(r"(?m)^## Приложение \d+", tail))
    add("OK" if listed and listed <= sections + 5 else "ВНИМАНИЕ", "приложения перечислены", f"в перечне: {listed}, разделов «## Приложение N» в файле: {sections}")

    add("OK" if "⟦" not in text else "ОШИБКА", "нет пометок ⟦…⟧", f"осталось: {text.count('⟦')}")
    add("OK" if not re.search(r"№\s*510", body) else "ОШИБКА", "нет ссылок на Указ № 510 (утратил силу с 01.01.2026; действует Указ № 227)")
    mentions = [m.group(0) for m in scope_filter.MENTION.finditer(text)]
    add("OK" if not mentions else "ОШИБКА", "нет упоминаний заведений, исключённых из работы", f"совпадений: {len(mentions)}")

    public = body + "\n" + "\n".join(re.findall(r"(?ms)^## Приложение \d+.*?(?=^## |\Z)", tail))
    names = sorted({name.strip() for name in SURNAMES if name in public})
    add("OK" if not names else "ОШИБКА", "нет фамилий физических лиц", ", ".join(names))
    handles = sorted(set(re.findall(r"(?<![\w.])@[A-Za-z0-9_.]{3,}", public)))
    add("OK" if not handles else "ОШИБКА", "нет учётных записей вида @имя", ", ".join(handles[:8]))
    writers = sorted(name for name in AUTHORS if name in public)
    add("OK" if not writers else "ОШИБКА", "нет имён авторов отзывов", ", ".join(writers[:8]))
    mails = sorted(set(re.findall(r"[\w.+-]+@[\w-]+\.[\w.]+", public)))
    add("OK" if not mails else "ВНИМАНИЕ", "адреса электронной почты в тексте письма", ", ".join(mails[:6]))

    risky = sorted({m.group(0).lower() for m in RISKY.finditer(body)})
    add("OK" if not risky else "ВНИМАНИЕ", "слова, требующие осторожности (допустимы только для установленного государственным органом и в цитатах норм)", ", ".join(risky))
    urls = re.findall(r"https?://\S+", body)
    add("OK" if not urls else "ОШИБКА", "в тексте письма нет адресов интернет-страниц (они только в приложениях)", f"найдено: {len(urls)}")

    for name in INTERNAL:
        add("OK" if re.search(rf"(?m)^## {re.escape(name)}", tail) else "ОШИБКА", f"внутренняя справка «{name}…»")
    return results


def main():
    paths = [Path(arg) for arg in sys.argv[1:]]
    if not paths:
        sys.exit("укажите файлы писем")
    failed = 0
    for path in paths:
        results = check(path)
        errors = [r for r in results if r[0] == "ОШИБКА"]
        warnings = [r for r in results if r[0] == "ВНИМАНИЕ"]
        failed += len(errors)
        print(f"{path.as_posix()}: проверок {len(results)}, ошибок {len(errors)}, на просмотр {len(warnings)}")
        for level, name, detail in results:
            if level != "OK":
                print(f"  {level}: {name}" + (f" — {detail}" if detail else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
