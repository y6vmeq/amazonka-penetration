"""Проверяет цитаты в кавычках-ёлочках из файла .md по сохранённым текстам актов.

Запуск из корня проекта:
    python -I tools/md_quotes_check.py <файл.md> <текст_акта> [<текст_акта> ...] [--min 25] [--all]

Нужен для выписок и разборов, где цитаты стоят прямо в тексте, без quotes.jsonl.
Берётся каждый фрагмент «…» (внешние кавычки, вложенные учитываются) длиной не меньше
--min букв; звёздочки выделения убираются; фрагмент с многоточием проверяется по частям.
Текст акта — .txt, .html или .pdf (для PDF берётся <имя>.txt рядом, его делает
tools/pdf_text.py). Колонтитулы страниц pravo.by при сверке пропускаются, поэтому пункт,
который переходит на другую страницу, находится целиком.

Оценки:
  OK       — фрагмент есть в тексте дословно (без учёта переносов строк и регистра);
  LOOSE    — совпадают только буквы и цифры; ниже показано, чем отличается.
             Отличие в пробелах внутри слова может менять смысл: проверить глазами;
  MISSING  — такого текста в актах нет. Это либо не цитата из этих актов (слова
             заведения, отзыв, другой акт), либо ошибка в цитате.
По умолчанию печатаются LOOSE и MISSING; с --all — все фрагменты.
Код возврата 1, если есть LOOSE или MISSING.
"""
import argparse
import difflib
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import reviews_check as check  # noqa: E402  (соседний файл проекта)

ELLIPSIS = re.compile(r"\s*(?:…|\.\.\.)\s*")
LINE_HYPHEN = re.compile(r"(?<=\w)- (?=\w)")
SPACE_BEFORE_MARK = re.compile(r" ([,.;:)])")
# Метка страницы из tools/pdf_text.py и колонтитул официального опубликования на pravo.by.
PAGE_BREAK = re.compile(
    r"\s*===== стр\. \d+ =====\s*"
    r"(?:Национальный правовой Интернет-портал Республики Беларусь, \d\d\.\d\d\.\d{4}, [\d/-]+[ \t]*\n[ \t]*\d+[ \t]*\n)?"
)


def outer_quotes(text):
    """Фрагменты во внешних кавычках «…»; вложенные кавычки остаются внутри фрагмента.

    Разбор идёт по абзацам (их разделяет пустая строка). В актах две открывающие кавычки
    часто закрыты одной («учреждением «Администрация … «Великий камень», другими…»):
    тогда счёт кавычек в абзаце не сходится, и фрагментом считается всё от первой
    незакрытой кавычки до последней закрывающей в этом абзаце.
    """
    fragments, offset = [], 0
    for paragraph in re.split(r"(\n[ \t]*\n)", text):
        depth, start, found = 0, None, []
        for index, char in enumerate(paragraph):
            if char == "«":
                if depth == 0:
                    start = index + 1
                depth += 1
            elif char == "»" and depth:
                depth -= 1
                if depth == 0:
                    found.append((start, index))
        if depth and start is not None:
            last = paragraph.rfind("»")
            if last > start:
                found.append((start, last))
        for begin, end in found:
            fragments.append((text[:offset + begin].count("\n") + 1, paragraph[begin:end]))
        offset += len(paragraph)
    return fragments


def load_texts(paths):
    variants, loose_variants = [], []
    for raw in paths:
        path = Path(raw)
        if path.suffix.lower() == ".pdf":
            path = path.with_suffix(".txt")
        if not path.is_file():
            sys.exit(f"no such text: {raw}")
        found, _ = check.load_variants(path)
        # Пункт может переходить на другую страницу: добавляем вариант без колонтитулов.
        joined = PAGE_BREAK.sub(" ", check.decode(path.read_bytes()))
        found = list(found) + [check.normalize(joined)]
        for variant in found:
            # перенос составного слова на новую строку и перенос по слогам
            # пробел перед знаком препинания появляется на месте ссылки или сноски в разметке страницы
            tight = SPACE_BEFORE_MARK.sub(lambda match: match.group(1), variant)
            for candidate in {variant, tight, LINE_HYPHEN.sub("-", variant), LINE_HYPHEN.sub("", variant)}:
                variants.append(candidate)
                loose_variants.append(check.letters_only(candidate))
    return variants, loose_variants


def locate(loose_needle, variant, loose):
    """Находит в тексте участок, совпадающий с цитатой по буквам, и возвращает его."""
    position = loose.find(loose_needle)
    if position < 0:
        return None
    count, start = 0, None
    for index, char in enumerate(variant):
        if char.isalnum():
            if count == position:
                start = index
            count += 1
            if count == position + len(loose_needle):
                return variant[start:index + 1]
    return None


def differences(raw_span, needle):
    lines = []
    matcher = difflib.SequenceMatcher(None, raw_span, needle, autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        left, right = raw_span[i1:i2], needle[j1:j2]
        if left.strip() == "" and right.strip() == "":
            kind = "пробел"
        else:
            kind = "знаки"
        context_raw = raw_span[max(0, i1 - 22):i2 + 22]
        context_quote = needle[max(0, j1 - 22):j2 + 22]
        lines.append(f"      {kind}: в акте «…{context_raw}…» — в файле «…{context_quote}…»")
    return lines


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("markdown")
    parser.add_argument("texts", nargs="+")
    parser.add_argument("--min", type=int, default=25)
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()

    variants, loose_variants = load_texts(args.texts)
    source = Path(args.markdown).read_text(encoding="utf-8-sig")
    counts = {"OK": 0, "LOOSE": 0, "MISSING": 0}
    report = []
    for line_number, fragment in outer_quotes(source):
        fragment = fragment.replace("**", "")
        for part in ELLIPSIS.split(fragment):
            needle = check.normalize(part)
            loose_needle = check.letters_only(needle)
            if len(loose_needle) < args.min:
                continue
            if any(needle in variant for variant in variants):
                counts["OK"] += 1
                if args.all:
                    report.append(f"OK      стр. {line_number}: {part[:90]}")
                continue
            # сначала быстрый поиск по заранее подготовленным «только буквам»
            hit = next((index for index, loose in enumerate(loose_variants) if loose_needle in loose), None)
            span = locate(loose_needle, variants[hit], loose_variants[hit]) if hit is not None else None
            if span is None:
                counts["MISSING"] += 1
                report.append(f"MISSING стр. {line_number}: {part[:160]}")
                continue
            # расхождение только в знаках на краях цитаты (точка, запятая) значения не имеет
            details = differences(span, needle.strip(" .,;:!?"))
            if not details:
                counts["OK"] += 1
                continue
            counts["LOOSE"] += 1
            report.append(f"LOOSE   стр. {line_number}: {part[:90]}")
            report.extend(details)
    summary = " ".join(f"{key.lower()}={value}" for key, value in counts.items())
    sys.stdout.reconfigure(encoding="utf-8")
    print(f"{args.markdown}: {summary}")
    for line in report:
        print(line)
    sys.exit(1 if counts["LOOSE"] or counts["MISSING"] else 0)


if __name__ == "__main__":
    main()
