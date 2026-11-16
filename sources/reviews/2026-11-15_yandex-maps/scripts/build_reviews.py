"""Формирует reviews.jsonl из выгрузок Яндекс Карт (raw/*.json) и файлов разметки.

Запуск из корня проекта:
    python -I sources/reviews/2026-11-15_yandex-maps/scripts/build_reviews.py

Текст отзыва и ответ организации копируются из выгрузки без изменений. Из файла
разметки (scripts/classification_<venue>.tsv, ключ — reviewId) берутся только
sentiment, topics и пояснения для notes. Цитаты в «ёлочках» внутри пояснений сверяются с текстом
отзыва или ответа: если цитаты там нет, сборка останавливается.

Выгрузки читаются только как данные (json.loads), ничего из них не исполняется.
Результат: reviews.jsonl и scripts/id_map.json (id записи -> отзыв, нужен ли скриншот).
"""
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
SLUG = "yandex-maps"
MINSK = timezone(timedelta(hours=3))
LLC_REGISTERED = "2023-10-05"

TOPICS = {
    "sanitary", "food-quality", "food-poisoning", "service", "billing",
    "receipt", "alcohol", "minors", "hookah-smoking", "security-conflict",
    "noise-night", "delivery", "booking-events", "staff-labor",
    "money-debts", "premises-building", "fire-safety", "ads-unlicensed",
    "discrimination", "management-response", "other",
}
SENTIMENTS = {"negative", "mixed", "neutral", "positive"}
# Темы, по которым скриншот нужен при любой оценке.
SCREENSHOT_TOPICS = {
    "sanitary", "food-poisoning", "receipt", "billing", "minors",
    "security-conflict", "staff-labor",
}
MONTHS = {
    "января": 1, "февраля": 2, "марта": 3, "апреля": 4, "мая": 5, "июня": 6,
    "июля": 7, "августа": 8, "сентября": 9, "октября": 10, "ноября": 11, "декабря": 12,
}

# Порядок источников задаёт порядок номеров id. Новые карточки добавлять в конец.
SOURCES = [
    {
        "venue": "amazonka-mogilev",
        "raw": "raw/001_yandex-maps_amazonka_all-reviews.json",
        "classification": "scripts/classification_amazonka.tsv",
        "fallback_url": "https://yandex.by/maps/org/amazonka_restobar/172475261635/reviews/",
        "extra": "scripts/extra_amazonka.tsv",
        "animals": "scripts/animals_amazonka.tsv",
    },
]
# Дополнительные источники (другие карточки) подключаются файлом scripts/sources_extra.json.
EXTRA_SOURCES = BASE / "scripts" / "sources_extra.json"


def load_redactions():
    """review_id -> (исходный фрагмент, замена, пояснение). См. scripts/redactions.tsv."""
    table = {}
    for number, parts in read_tsv(BASE / "scripts" / "redactions.tsv", min_columns=4):
        table[parts[0]] = (parts[1], parts[2], parts[3])
    return table


def squash(text):
    return re.sub(r"\s+", " ", text).strip()


def parse_time(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def read_tsv(path, min_columns=3):
    rows = []
    if not path.is_file():
        return rows
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < min_columns:
            sys.exit(f"{path.name}:{number}: expected at least {min_columns} tab-separated columns")
        rows.append((number, [part.strip() for part in parts]))
    return rows


def shown_date_matches(shown, local_date):
    """Сверяет дату, показанную на странице («14 ноября», «3 июня 2025»), с датой по Минску."""
    match = re.fullmatch(r"(\d{1,2})\s+([а-яё]+)(?:\s+(\d{4}))?", shown.strip().lower())
    if not match or match.group(2) not in MONTHS:
        return None
    day, month = int(match.group(1)), MONTHS[match.group(2)]
    if (day, month) != (local_date.day, local_date.month):
        return False
    return match.group(3) is None or int(match.group(3)) == local_date.year


def check_quotes(notes, haystacks, where, problems):
    for quote in re.findall(r"«([^«»]+)»", notes):
        needle = squash(quote)
        if not any(needle in squash(hay) for hay in haystacks if hay):
            problems.append(f"{where}: quote not found in text/reply: {needle!r}")


def media_of(review):
    media = [url.replace("{size}", "orig") for url in review.get("photos", [])]
    media += [video["video_url"] for video in review.get("videos", []) if video.get("video_url")]
    return media


def base_notes(review, source, with_reply=True):
    notes = [f"reviewId в данных страницы: {review['review_id']}."]
    notes.append(f"Точное время отзыва (meta datePublished, UTC): {review['date_published']}.")
    if not review.get("review_url"):
        notes.append(
            "У автора нет публичного профиля, отдельной ссылки на отзыв страница не даёт: "
            "в url указана вкладка отзывов карточки."
        )
    reply = review.get("org_reply")
    if reply and with_reply:
        notes.append(
            f"Ответ организации («{squash(reply['header_shown'] or '')}»): дата на странице — "
            f"{reply['date_shown']} (UTC: {reply['model_updated_time']})."
        )
        if parse_time(reply["model_updated_time"]) < parse_time(review["date_published"]):
            notes.append(
                "Дата ответа раньше даты отзыва: в данных страницы дата отзыва хранится в поле "
                "updatedTime (время последнего изменения отзыва)."
            )
    if review["date_published"][:10] < LLC_REGISTERED and source["venue"] == "amazonka-mogilev":
        notes.append(
            "Отзыв датирован раньше 05.10.2023 — даты регистрации ООО «АмазонкаГрупп»; "
            "25.09.2023 организация в ответах на этой карточке писала о переезде «на новое место»."
        )
    reactions = review.get("model_reactions") or {}
    if reactions.get("likes") or reactions.get("dislikes"):
        notes.append(f"Реакции на странице: лайков {reactions.get('likes', 0)}, дизлайков {reactions.get('dislikes', 0)}.")
    return notes


def build_source(source, problems, warnings):
    raw_path = BASE / source["raw"]
    export = json.loads(raw_path.read_text(encoding="utf-8"))
    captured = parse_time(export["captured_at_browser"]).replace(microsecond=0).isoformat()
    by_id = {review["review_id"]: review for review in export["reviews"]}
    drafts = []
    seen = set()

    for number, parts in read_tsv(BASE / source["classification"]):
        where = f"{Path(source['classification']).name}:{number}"
        review_id, sentiment, topics = parts[0], parts[1], [t for t in parts[2].split(",") if t]
        manual = parts[3] if len(parts) > 3 else ""
        review = by_id.get(review_id)
        if review is None:
            problems.append(f"{where}: no review with id {review_id}")
            continue
        position = review["position"]
        if review_id in seen:
            problems.append(f"{where}: review {review_id} listed twice")
        seen.add(review_id)
        if sentiment not in SENTIMENTS:
            problems.append(f"{where}: bad sentiment {sentiment!r}")
        if not topics or any(topic not in TOPICS for topic in topics):
            problems.append(f"{where}: bad topics {topics!r}")
        if review["text"] != review["model_text"]:
            warnings.append(f"{where}: DOM text differs from page data text")
        reply = review.get("org_reply")
        reply_text = reply["text"] if reply else None
        check_quotes(manual, [review["text"], reply_text], where, problems)

        local_date = parse_time(review["date_published"]).astimezone(MINSK).date()
        if shown_date_matches(review["date_shown"], local_date) is not True:
            warnings.append(f"{where}: shown date {review['date_shown']!r} vs Minsk date {local_date}")

        notes = ([manual] if manual else []) + base_notes(review, source)
        text = review["text"]
        if review_id in REDACTIONS:
            fragment, replacement, explanation = REDACTIONS[review_id]
            if text.count(fragment) != 1:
                problems.append(f"{where}: redaction fragment not found exactly once")
            text = text.replace(fragment, replacement)
            notes.append(explanation)
        drafts.append({
            "sort_key": (review["date_published"], -position),
            "position": position,
            "review_id": review["review_id"],
            "record": {
                "id": None,
                "venue": source["venue"],
                "platform": "yandex-maps",
                "kind": "review",
                "url": review.get("review_url") or source["fallback_url"],
                "author": review["author_name"],
                "date_published": review["date_shown"],
                "date_iso": local_date.isoformat(),
                "rating": int(float(review["rating"])),
                "text": text,
                "reply": reply_text,
                "sentiment": sentiment,
                "topics": topics,
                "media": media_of(review),
                "captured_at": captured,
                "raw_file": source["raw"],
                "screenshot": None,
                "access": "public",
                "status": "verified-raw",
                "notes": " ".join(notes),
            },
        })

    for review in export["reviews"]:
        if float(review["rating"]) <= 3 and review["review_id"] not in seen:
            problems.append(f"{source['raw']}: rating {review['rating']} at position {review['position']} is not classified")

    drafts.sort(key=lambda draft: draft["sort_key"], reverse=True)

    # Отдельные записи об ответах организации на отзывы, которые сами в базу не входят.
    extras = []
    for number, parts in read_tsv(BASE / source.get("extra", "__none__")):
        where = f"{Path(source['extra']).name}:{number}"
        if len(parts) < 5:
            problems.append(f"{where}: expected at least 5 columns")
            continue
        review_id, venue, sentiment, topics, manual = parts[0], parts[1], parts[2], parts[3].split(","), parts[4]
        review = by_id.get(review_id)
        if review is None or not review.get("org_reply"):
            problems.append(f"{where}: no org reply for review {review_id}")
            continue
        position = review["position"]
        reply = review["org_reply"]
        check_quotes(manual, [reply["text"], review["text"]], where, problems)
        local_date = parse_time(reply["model_updated_time"]).astimezone(MINSK).date()
        notes = [manual] + [
            f"Это ответ организации на карточке «{export['org']['name_h1']}» на отзыв автора «{review['author_name']}» "
            f"(оценка {int(float(review['rating']))}, дата отзыва на странице: {review['date_shown']}); сам отзыв положительный и в базу не внесён.",
            f"reviewId отзыва в данных страницы: {review['review_id']}.",
            f"Точное время ответа по данным страницы (UTC): {reply['model_updated_time']}.",
        ]
        extras.append({
            "sort_key": None,
            "position": position,
            "review_id": review["review_id"],
            "record": {
                "id": None,
                "venue": venue,
                "platform": "yandex-maps",
                "kind": "reply",
                "url": review.get("review_url") or source["fallback_url"],
                "author": squash(reply["header_shown"] or "") or None,
                "date_published": reply["date_shown"],
                "date_iso": local_date.isoformat(),
                "rating": None,
                "text": reply["text"],
                "reply": None,
                "sentiment": sentiment,
                "topics": topics,
                "media": [],
                "captured_at": captured,
                "raw_file": source["raw"],
                "screenshot": None,
                "access": "public",
                "status": "verified-raw",
                "notes": " ".join(notes),
            },
        })
    # Упоминания животных (доп. задание): уже внесённым записям дописывается пометка,
    # остальные отзывы вносятся отдельным блоком после основных записей (номера прежних id не меняются).
    by_review = {draft["review_id"]: draft for draft in drafts}
    animal_drafts = []
    for number, parts in read_tsv(BASE / source.get("animals", "__none__"), min_columns=1):
        where = f"{Path(source['animals']).name}:{number}"
        review_id = parts[0]
        manual = parts[1] if len(parts) > 1 else ""
        review = by_id.get(review_id)
        if review is None:
            problems.append(f"{where}: no review with id {review_id}")
            continue
        reply = review.get("org_reply")
        reply_text = reply["text"] if reply else None
        check_quotes(manual, [review["text"], reply_text], where, problems)
        mark = source.get("animals_mark", "Тема: животные в зале.") + (" " + manual if manual else "")
        if review_id in by_review:
            record = by_review[review_id]["record"]
            if "other" not in record["topics"]:
                record["topics"].append("other")
            record["notes"] = mark + " " + record["notes"]
            continue
        if source.get("animals_annotate_only"):
            continue
        local_date = parse_time(review["date_published"]).astimezone(MINSK).date()
        rating = int(float(review["rating"]))
        animal_drafts.append({
            "sort_key": (review["date_published"], -review["position"]),
            "position": review["position"],
            "review_id": review_id,
            "record": {
                "id": None,
                "venue": source["venue"],
                "platform": "yandex-maps",
                "kind": "review",
                "url": review.get("review_url") or source["fallback_url"],
                "author": review["author_name"],
                "date_published": review["date_shown"],
                "date_iso": local_date.isoformat(),
                "rating": rating,
                "text": review["text"],
                "reply": reply_text,
                "sentiment": "positive" if rating == 5 else ("mixed" if rating == 4 else "negative"),
                "topics": ["other"],
                "media": media_of(review),
                "captured_at": captured,
                "raw_file": source["raw"],
                "screenshot": None,
                "access": "public",
                "status": "verified-raw",
                "notes": " ".join([mark, "Отзыв внесён только из-за упоминания животных (оценка 4–5, иных претензий по правилам отбора нет)."] + base_notes(review, source)),
            },
        })
    animal_drafts.sort(key=lambda draft: draft["sort_key"], reverse=True)
    return drafts + extras, animal_drafts


REDACTIONS = {}


def main():
    REDACTIONS.update(load_redactions())
    sources = list(SOURCES)
    if EXTRA_SOURCES.is_file():
        sources += json.loads(EXTRA_SOURCES.read_text(encoding="utf-8"))
    problems, warnings = [], []
    drafts, tail = [], []
    for source in sources:
        if source.get("late"):
            continue
        main_part, animal_part = build_source(source, problems, warnings)
        drafts += main_part
        tail += animal_part
    # Блок «животные» идёт после основных записей первой карточки; карточки с пометкой late — после него.
    drafts += tail
    for source in sources:
        if source.get("late"):
            main_part, animal_part = build_source(source, problems, warnings)
            drafts += main_part + animal_part
    for warning in warnings:
        print("WARNING", ascii(warning))
    if problems:
        for problem in problems:
            print("PROBLEM", ascii(problem))
        sys.exit(1)

    id_map = []
    lines = []
    for number, draft in enumerate(drafts, 1):
        record = draft["record"]
        record["id"] = f"{SLUG}-{number:03d}"
        shot = f"screenshots/{record['id']}.png"
        if (BASE / shot).is_file():
            record["screenshot"] = shot
        by_topic = bool(SCREENSHOT_TOPICS & set(record["topics"]))
        by_rating = record["rating"] is not None and record["rating"] <= 2
        id_map.append({
            "id": record["id"],
            "venue": record["venue"],
            "raw": record["raw_file"],
            "position": draft["position"],
            "review_id": draft["review_id"],
            "kind": record["kind"],
            "rating": record["rating"],
            "needs_screenshot": by_topic or by_rating,
            "priority_topic": by_topic,
            "has_screenshot": record["screenshot"] is not None,
        })
        lines.append(json.dumps(record, ensure_ascii=False))

    (BASE / "reviews.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    (BASE / "scripts" / "id_map.json").write_text(
        json.dumps(id_map, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n"
    )
    need = [item for item in id_map if item["needs_screenshot"]]
    print(
        f"records={len(id_map)} need_screenshot={len(need)} "
        f"priority={sum(1 for item in need if item['priority_topic'])} "
        f"have_screenshot={sum(1 for item in id_map if item['has_screenshot'])} "
        f"missing_screenshot={sum(1 for item in need if not item['has_screenshot'])}"
    )


if __name__ == "__main__":
    main()
