"""Проверяет, что цитаты из нормативных актов дословно есть в сохранённых текстах.

Запуск из корня проекта:
    python -I tools/quotes_check.py <папка> [<папка> ...]

В папке должен лежать quotes.jsonl: по одной записи JSON в строке с полями
    id        — метка цитаты, например "sanpin12-p4";
    act       — название и реквизиты акта;
    point     — статья, пункт, часть, абзац;
    text      — дословная цитата;
    raw_file  — путь к сохранённому тексту акта относительно этой папки
                (HTML, TXT или PDF, рядом с которым лежит <имя>.txt).

Сравнение — теми же правилами, что в tools/reviews_check.py: OK и LOOSE значит,
что цитата в тексте есть; PARTIAL, MISSING и NO-RAW нужно разбирать.
Итог пишется в <папка>/quotes_check_result.txt, в консоль — сводка латиницей.
Код возврата 1, если есть ошибки формата, MISSING или NO-RAW.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import reviews_check as check  # noqa: E402  (соседний файл проекта)

FIELDS = ("id", "act", "point", "text", "raw_file")
FAILING = ("MISSING", "NO-RAW", "EMPTY")


def check_folder(folder):
    counts = {key: 0 for key in ("quotes", "OK", "LOOSE", "PARTIAL", "MISSING", "NO-RAW", "IMAGE", "EMPTY", "format_errors")}
    lines, cache = [], {}
    jsonl = folder / "quotes.jsonl"
    if not jsonl.is_file():
        return counts, ["нет файла quotes.jsonl"], True
    for number, line in enumerate(jsonl.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not line.strip():
            continue
        counts["quotes"] += 1
        try:
            quote = json.loads(line)
        except json.JSONDecodeError as error:
            counts["format_errors"] += 1
            lines.append(f"строка {number}: не JSON ({error})")
            continue
        missing = [field for field in FIELDS if not isinstance(quote, dict) or not isinstance(quote.get(field), str)]
        if missing:
            counts["format_errors"] += 1
            lines.append(f"строка {number}: нет строковых полей {missing}")
            continue
        # check_quotes ждёт запись отзыва: подставляем недостающие поля.
        record = {"status": "verified-raw", "raw_file": quote["raw_file"], "text": quote["text"], "reply": None}
        verdict, _, note = check.check_quotes(record, folder, cache)
        counts[verdict] += 1
        lines.append(f"{quote['id']} | {quote['point']} | {verdict}" + (f" | {note}" if note else ""))
    failed = bool(counts["format_errors"] or any(counts[name] for name in FAILING))
    return counts, lines, failed


def main():
    if len(sys.argv) < 2:
        sys.exit("usage: python -I tools/quotes_check.py <folder> [...]")
    any_failed = False
    for argument in sys.argv[1:]:
        folder = Path(argument)
        counts, lines, failed = check_folder(folder)
        any_failed = any_failed or failed
        summary = " ".join(f"{key.lower()}={value}" for key, value in counts.items())
        if folder.is_dir():
            (folder / "quotes_check_result.txt").write_text(
                summary + "\n\n" + "\n".join(lines) + "\n", encoding="utf-8", newline="\n"
            )
        print(f"{ascii(str(folder))}: {summary} -> {'FAIL' if failed else 'PASS'}")
    sys.exit(1 if any_failed else 0)


if __name__ == "__main__":
    main()
