"""Делает читаемый текстовый список отзывов из полной выгрузки и подбирает уникальные слова для поиска.

Запуск: python -I scripts/readable.py <raw/NNN_..._all-reviews.json> <out.txt>
Файл выгрузки только читается как данные.
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path


def tokens(text):
    return {word for word in re.split("[^a-zа-яё0-9]+", (text or "").lower())
            if 2 <= len(word) <= 20 and re.fullmatch("[a-zа-я]+", word)}


def main():
    dump = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    reviews = dump["reviews"]
    frequency = Counter()
    for review in reviews:
        frequency.update(tokens(review["text"]))
    lines = [f"place: {dump.get('place_name')} | unique: {dump.get('unique_reviews')} | summary: "
             + json.dumps(dump.get("summary"), ensure_ascii=False)]
    order = sorted(range(len(reviews)), key=lambda index: (reviews[index]["rating"] or 9, index))
    for index in order:
        review = reviews[index]
        unique = sorted((word for word in tokens(review["text"]) if frequency[word] == 1 and len(word) >= 5),
                        key=lambda word: (-len(word), word))[:2]
        lines.append(f"### [{index:03d}] {review['rating']}* | {review['author']} | {review['date_shown']} | "
                     f"photos={review['photo_count']} | tokens={unique}")
        lines.append("TEXT: " + (review["text"] or "(нет текста)"))
        if review["structured"]:
            lines.append("ATTR: " + "; ".join(" — ".join(block) for block in review["structured"]))
        if review["reply"]:
            lines.append(f"REPLY ({review['reply']['date_shown']}): {review['reply']['text']}")
        captions = [photo["aria"] for photo in review["photos"]
                    if photo["aria"] and not re.match("^(Фото \\d|Видео$|Ещё \\d)", photo["aria"])]
        if captions:
            lines.append("PHOTO CAPTIONS: " + "; ".join(captions))
        lines.append("")
    Path(sys.argv[2]).write_text("\n".join(lines), encoding="utf-8")
    print("ok", len(reviews))


if __name__ == "__main__":
    main()
