"""Проверяет папку сбора отзывов: формат reviews.jsonl и дословность цитат.

Запуск из корня проекта:
    python -I tools/reviews_check.py <папка_сбора> [<папка_сбора> ...]

Для каждой записи проверяется:
  - обязательные поля и допустимые значения;
  - существует ли raw_file;
  - есть ли текст отзыва и ответ заведения в сырой копии.

Сравнение идёт после нормализации: пробелы, регистр, HTML-сущности,
JSON-экранирование. Итог пишется в <папка_сбора>/check_result.txt (UTF-8),
в консоль выводится короткая сводка латиницей.

Оценки дословности:
  OK       — текст найден в сырой копии целиком;
  LOOSE    — найден, если сравнивать только буквы и цифры (расходятся
             пунктуация, эмодзи или пробелы);
  PARTIAL  — найдено не меньше 80 % текста по фрагментам;
  MISSING  — в сырой копии текста нет: запись нельзя считать дословной;
  NO-RAW   — файл сырой копии не указан или не существует;
  IMAGE    — сырая копия — картинка или PDF без текста, сверять глазами;
  SNIPPET  — запись помечена как сниппет поисковика, сверка не делалась.

Код возврата: 0 — ошибок нет; 1 — есть ошибки формата, MISSING или NO-RAW.
"""
import html
import json
import re
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

VENUES = {
    "amazonka-mogilev", "smak-by",
    "amazonka-minsk", "legal-entity", "unclear",
}
KINDS = {
    "review", "comment", "post", "reply", "article", "video",
    "vacancy", "official", "other",
}
SENTIMENTS = {"negative", "mixed", "neutral", "positive"}
ACCESS = {"public", "login-required"}
STATUSES = {"verified-raw", "unverified-snippet"}
TOPICS = {
    "sanitary", "food-quality", "food-poisoning", "service", "billing",
    "receipt", "alcohol", "minors", "hookah-smoking", "security-conflict",
    "noise-night", "delivery", "booking-events", "staff-labor",
    "money-debts", "premises-building", "fire-safety", "ads-unlicensed",
    "discrimination", "management-response", "other",
}
# Поле -> допустимые типы значения.
FIELDS = {
    "id": (str,),
    "venue": (str,),
    "platform": (str,),
    "kind": (str,),
    "url": (str,),
    "author": (str, type(None)),
    "date_published": (str, type(None)),
    "date_iso": (str, type(None)),
    "rating": (int, float, type(None)),
    "text": (str,),
    "reply": (str, type(None)),
    "sentiment": (str,),
    "topics": (list,),
    "media": (list,),
    "captured_at": (str,),
    "raw_file": (str, type(None)),
    "screenshot": (str, type(None)),
    "access": (str,),
    "status": (str,),
    "notes": (str,),
}
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
MIN_CHUNK = 15
PARTIAL_SHARE = 0.8

ZERO_WIDTH = re.compile("[​-‏⁠﻿­]")
TAG = re.compile(r"<[^>]*>")
UNICODE_ESCAPE = re.compile(r"\\u([0-9a-fA-F]{4})")
SENTENCE_BREAK = re.compile(r"[.!?…\n]+")


def normalize(text):
    text = html.unescape(text)
    text = unicodedata.normalize("NFKC", text)
    text = ZERO_WIDTH.sub("", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def letters_only(text):
    return "".join(char for char in text if char.isalnum())


def decode(data):
    if data[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return data.decode("utf-16", errors="replace")
    for encoding in ("utf-8-sig", "cp1251"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def json_unescape(text):
    text = UNICODE_ESCAPE.sub(lambda match: chr(int(match.group(1), 16)), text)
    # 😀 после замены даёт два суррогата — склеиваем их в один символ.
    text = text.encode("utf-16", "surrogatepass").decode("utf-16", "replace")
    for escaped in ("\\n", "\\r", "\\t"):
        text = text.replace(escaped, " ")
    return text.replace('\\"', '"').replace("\\/", "/").replace("\\\\", "\\")


def load_variants(path):
    """Нормализованные варианты сырого текста: как есть, без тегов, после JSON-разэкранирования."""
    text = decode(path.read_bytes())
    unescaped = json_unescape(text)
    variants = {
        normalize(candidate)
        for candidate in (text, TAG.sub(" ", text), unescaped, TAG.sub(" ", unescaped))
    }
    return list(variants), [letters_only(variant) for variant in variants]


def verdict(quote, variants, loose_variants):
    needle = normalize(quote)
    if not needle:
        return "EMPTY", 0.0
    if any(needle in variant for variant in variants):
        return "OK", 1.0
    loose_needle = letters_only(needle)
    if loose_needle and any(loose_needle in variant for variant in loose_variants):
        return "LOOSE", 1.0
    chunks = [chunk.strip() for chunk in SENTENCE_BREAK.split(needle)]
    chunks = [chunk for chunk in chunks if len(chunk) >= MIN_CHUNK]
    if not chunks:
        return "MISSING", 0.0
    total = sum(len(chunk) for chunk in chunks)
    found = sum(
        len(chunk) for chunk in chunks
        if any(chunk in variant for variant in variants)
        or any(letters_only(chunk) in variant for variant in loose_variants)
    )
    share = found / total
    return ("PARTIAL" if share >= PARTIAL_SHARE else "MISSING"), share


def format_problems(record, seen_ids):
    problems = []
    for field, types in FIELDS.items():
        if field not in record:
            problems.append(f"нет поля {field}")
        elif not isinstance(record[field], types) or isinstance(record[field], bool):
            problems.append(f"поле {field}: неверный тип")
    if problems:
        return problems

    for field, allowed in (
        ("venue", VENUES), ("kind", KINDS), ("sentiment", SENTIMENTS),
        ("access", ACCESS), ("status", STATUSES),
    ):
        if record[field] not in allowed:
            problems.append(f"поле {field}: недопустимое значение {record[field]!r}")
    unknown_topics = [topic for topic in record["topics"] if topic not in TOPICS]
    if unknown_topics:
        problems.append(f"неизвестные темы: {unknown_topics}")
    if not record["url"].startswith(("http://", "https://")):
        problems.append("url не начинается с http")
    if not record["text"].strip():
        problems.append("пустой text")
    if record["id"] in seen_ids:
        problems.append("повтор id")
    seen_ids.add(record["id"])
    try:
        if datetime.fromisoformat(record["captured_at"]).tzinfo is None:
            problems.append("captured_at без часового пояса")
    except ValueError:
        problems.append("captured_at не в формате ISO 8601")
    if record["date_iso"] and not re.fullmatch(r"\d{4}(-\d{2}(-\d{2})?)?", record["date_iso"]):
        problems.append("date_iso не в формате ГГГГ, ГГГГ-ММ или ГГГГ-ММ-ДД")
    if record["status"] == "verified-raw" and not record["raw_file"]:
        problems.append("status verified-raw, но raw_file не указан")
    return problems


def check_quotes(record, collection_dir, cache):
    """Возвращает (оценка текста, оценка ответа, пояснение)."""
    if record["status"] == "unverified-snippet":
        return "SNIPPET", "-", ""
    raw_file = record["raw_file"]
    path = collection_dir / raw_file if raw_file else None
    if path is None or not path.is_file():
        return "NO-RAW", "-", f"нет файла {raw_file}"
    if path.suffix.lower() in IMAGE_SUFFIXES:
        return "IMAGE", "-", "сырая копия — изображение"
    if path.suffix.lower() == ".pdf":
        text_copy = path.with_suffix(".txt")
        if not text_copy.is_file():
            return "IMAGE", "-", "PDF без извлечённого текста рядом (<имя>.txt)"
        path = text_copy
    if path not in cache:
        cache[path] = load_variants(path)
    variants, loose_variants = cache[path]

    text_verdict, text_share = verdict(record["text"], variants, loose_variants)
    note = f"текст найден на {text_share:.0%}" if text_verdict in ("PARTIAL", "MISSING") else ""
    reply_verdict = "-"
    if record["reply"]:
        reply_verdict, reply_share = verdict(record["reply"], variants, loose_variants)
        if reply_verdict in ("PARTIAL", "MISSING"):
            note = f"{note}; ответ найден на {reply_share:.0%}".strip("; ")
    return text_verdict, reply_verdict, note


def check_collection(collection_dir):
    counts = {key: 0 for key in (
        "records", "OK", "LOOSE", "PARTIAL", "MISSING", "NO-RAW", "IMAGE",
        "SNIPPET", "EMPTY", "format_errors", "reply_problems",
    )}
    lines = []
    jsonl = collection_dir / "reviews.jsonl"
    if not jsonl.is_file():
        return counts, ["нет файла reviews.jsonl"], True

    seen_ids = set()
    cache = {}
    for number, line in enumerate(jsonl.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not line.strip():
            continue
        counts["records"] += 1
        try:
            record = json.loads(line)
        except json.JSONDecodeError as error:
            counts["format_errors"] += 1
            lines.append(f"строка {number}: не JSON ({error})")
            continue
        if not isinstance(record, dict):
            counts["format_errors"] += 1
            lines.append(f"строка {number}: ожидался объект JSON")
            continue
        problems = format_problems(record, seen_ids)
        if problems:
            counts["format_errors"] += 1
            lines.append(f"строка {number} ({record.get('id', '?')}): " + "; ".join(problems))
            continue
        text_verdict, reply_verdict, note = check_quotes(record, collection_dir, cache)
        counts[text_verdict] += 1
        if reply_verdict in ("PARTIAL", "MISSING", "EMPTY"):
            counts["reply_problems"] += 1
        lines.append(
            f"{record['id']} | текст: {text_verdict} | ответ: {reply_verdict}"
            + (f" | {note}" if note else "")
        )
    failed = bool(counts["format_errors"] or counts["MISSING"] or counts["NO-RAW"] or counts["EMPTY"])
    return counts, lines, failed


def main():
    if len(sys.argv) < 2:
        sys.exit("usage: python -I tools/reviews_check.py <collection_dir> [...]")
    any_failed = False
    for argument in sys.argv[1:]:
        collection_dir = Path(argument)
        counts, lines, failed = check_collection(collection_dir)
        any_failed = any_failed or failed
        summary = " ".join(f"{key.lower()}={value}" for key, value in counts.items())
        if collection_dir.is_dir():
            (collection_dir / "check_result.txt").write_text(
                summary + "\n\n" + "\n".join(lines) + "\n", encoding="utf-8", newline="\n"
            )
        print(f"{ascii(str(collection_dir))}: {summary} -> {'FAIL' if failed else 'PASS'}")
    sys.exit(1 if any_failed else 0)


if __name__ == "__main__":
    main()
