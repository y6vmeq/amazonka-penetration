"""Сводит записи всех папок сбора отзывов в общий перечень.

Запуск из корня проекта:
    python -I tools/reviews_merge.py [sources/reviews]

Читает <корень>/<дата>_<слаг>/reviews.jsonl, сверяет тексты с сырыми копиями
(теми же правилами, что reviews_check.py), склеивает повторы и пишет:
  <корень>/ALL.jsonl  — все уникальные записи с полями source_dir, verdict, also_at;
  <корень>/INDEX.md   — сводные таблицы и перечень по заведениям.

Повтором считается запись с тем же текстом (сравниваются только буквы и
цифры). Для коротких текстов дополнительно должны совпасть автор, площадка
и дата: иначе склеились бы разные отзывы вроде «Ужасно».
Из повторов главной остаётся запись с лучшей сверкой, со скриншотом и с
площадки-первоисточника; остальные перечисляются в also_at.
"""
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import reviews_check as check  # noqa: E402  (соседний файл проекта)

COLLECTION_DIR = re.compile(r"\d{4}-\d{2}-\d{2}_.+")
SHORT_TEXT = 40
PREVIEW = 140
VERDICT_RANK = {"OK": 0, "LOOSE": 0, "PARTIAL": 1, "IMAGE": 2, "SNIPPET": 3}
# Площадки, где отзыв публикуется автором; остальные обычно его перепечатывают.
ORIGINAL_PLATFORMS = ["yandex-maps", "google-maps", "threads", "instagram", "telegram", "vk"]
VENUE_NAMES = {
    "amazonka-mogilev": "«Амазонка», Могилёв",
    "smak-by": "«Смак.BY»",
    "amazonka-minsk": "«Амазонка», Минск",
    "legal-entity": "ООО «АмазонкаГрупп»",
    "unclear": "не ясно, к чему относится",
}


def load_records(root):
    """Возвращает (записи с полями source_dir и verdict, список сообщений о проблемах)."""
    records, problems = [], []
    for collection_dir in sorted(path for path in root.iterdir() if path.is_dir()):
        jsonl = collection_dir / "reviews.jsonl"
        if not COLLECTION_DIR.fullmatch(collection_dir.name) or not jsonl.is_file():
            continue
        seen_ids, cache = set(), {}
        for number, line in enumerate(jsonl.read_text(encoding="utf-8-sig").splitlines(), 1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                problems.append(f"{collection_dir.name}, строка {number}: не JSON")
                continue
            if not isinstance(record, dict):
                problems.append(f"{collection_dir.name}, строка {number}: не объект JSON")
                continue
            found = check.format_problems(record, seen_ids)
            if found:
                problems.append(
                    f"{collection_dir.name}, строка {number} ({record.get('id', '?')}): " + "; ".join(found)
                )
                continue
            verdict, _, _ = check.check_quotes(record, collection_dir, cache)
            record["source_dir"] = collection_dir.name
            record["verdict"] = verdict
            records.append(record)
    return records, problems


def duplicate_key(record):
    text_key = check.letters_only(check.normalize(record["text"]))
    if len(text_key) >= SHORT_TEXT:
        return text_key
    return (text_key, record["author"], record["platform"], record["date_iso"] or record["date_published"])


def preference(record):
    platform = record["platform"]
    return (
        VERDICT_RANK.get(record["verdict"], 4),
        0 if record["screenshot"] else 1,
        ORIGINAL_PLATFORMS.index(platform) if platform in ORIGINAL_PLATFORMS else len(ORIGINAL_PLATFORMS),
        record["id"],
    )


def merge(records):
    groups = defaultdict(list)
    for record in records:
        groups[duplicate_key(record)].append(record)
    unique = []
    for group in groups.values():
        group.sort(key=preference)
        primary = group[0]
        primary["also_at"] = [
            {"id": other["id"], "platform": other["platform"], "url": other["url"]} for other in group[1:]
        ]
        unique.append(primary)
    unique.sort(key=lambda record: (record["venue"], record["date_iso"] or "", record["id"]), reverse=True)
    return unique


def cell(value):
    return str(value).replace("|", "/").replace("\r", " ").replace("\n", " ")


def preview(text):
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= PREVIEW else text[:PREVIEW].rstrip() + "…"


def count_table(header, counter):
    lines = [f"| {header[0]} | {header[1]} | Записей |", "|---|---|---|"]
    for (first, second), count in sorted(counter.items(), key=lambda item: (item[0][0], -item[1], item[0][1])):
        lines.append(f"| {cell(first)} | {cell(second)} | {count} |")
    return lines


def build_index(unique, total, problems):
    by_platform = Counter((VENUE_NAMES[record["venue"]], record["platform"]) for record in unique)
    by_topic = Counter(
        (VENUE_NAMES[record["venue"]], topic) for record in unique for topic in record["topics"]
    )
    verdicts = Counter(record["verdict"] for record in unique)

    lines = [
        "# Сводный перечень отзывов из открытых источников",
        "",
        f"Сформирован {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC скриптом `tools/reviews_merge.py`. "
        "Руками не править: при следующем запуске файл перезаписывается.",
        "",
        f"- Собрано записей: {total}. После склейки повторов: {len(unique)}.",
        "- Сверка с сырыми копиями: "
        + ", ".join(f"{name} — {count}" for name, count in sorted(verdicts.items()))
        + ". Значения описаны в `tools/reviews_check.py`.",
        "- Все записи — сведения из открытых источников, **не проверенные** по существу. "
        "Это повод для проверки, а не доказательство.",
        "- Полные тексты: `ALL.jsonl` и файлы `reviews.jsonl` в папках сбора.",
        "",
        "## По заведениям и площадкам",
        "",
        *count_table(("Заведение", "Площадка"), by_platform),
        "",
        "## По темам",
        "",
        "Один отзыв может относиться к нескольким темам.",
        "",
        *count_table(("Заведение", "Тема"), by_topic),
        "",
    ]
    if problems:
        lines += ["## Записи, не попавшие в перечень из-за ошибок формата", ""]
        lines += [f"- {problem}" for problem in problems]
        lines.append("")

    lines += ["## Перечень", ""]
    for venue, name in VENUE_NAMES.items():
        rows = [record for record in unique if record["venue"] == venue]
        if not rows:
            continue
        lines += [
            f"### {name} — {len(rows)}",
            "",
            "| id | Дата | Площадка | Оценка | Автор | Темы | Сверка | Начало текста |",
            "|---|---|---|---|---|---|---|---|",
        ]
        for record in rows:
            rating = "" if record["rating"] is None else record["rating"]
            lines.append(
                f"| [{record['id']}]({record['url']}) | {cell(record['date_iso'] or record['date_published'] or '')} "
                f"| {cell(record['platform'])} | {rating} | {cell(record['author'] or '')} "
                f"| {cell(', '.join(record['topics']))} | {record['verdict']} | {cell(preview(record['text']))} |"
            )
        lines.append("")
    return "\n".join(lines)


def main():
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "sources/reviews")
    if not root.is_dir():
        sys.exit(f"no such directory: {root}")
    records, problems = load_records(root)
    unique = merge(records)
    with (root / "ALL.jsonl").open("w", encoding="utf-8", newline="\n") as output:
        for record in unique:
            output.write(json.dumps(record, ensure_ascii=False) + "\n")
    (root / "INDEX.md").write_text(build_index(unique, len(records), problems), encoding="utf-8", newline="\n")
    print(f"collected={len(records)} unique={len(unique)} format_errors={len(problems)}")


if __name__ == "__main__":
    main()
