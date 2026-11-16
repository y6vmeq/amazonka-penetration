"""Собирает reviews.jsonl из сырых копий (raw/*.json) и разметки work/classify.json.

Запуск из корня проекта: python -I -X utf8 sources/reviews/2026-11-15_logged-in/scripts/build_reviews.py

Тексты берутся только из сырых копий: скрипт находит пост по коду (Threads) или комментарий
по номеру (Instagram) и переносит текст как есть. Вручную в разметке задаются только
заведение, вид, тон, темы и пояснения.
"""
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
MINSK = timezone(timedelta(hours=3))
UI_TAILS = ("\nОтветов пока нет", "  Перевести", "\nПеревести")


def load_raw(name, cache={}):
    if name not in cache:
        cache[name] = json.loads((HERE / name).read_text(encoding="utf-8"))
    return cache[name]


def find_threads(raw, code):
    for key in ("fresh", "rel_new", "picked"):
        for item in raw.get(key) or []:
            if item.get("code") == code:
                return dict(item)
    for item in raw.get("items") or []:
        if item[1] == code:
            return {"code": item[1], "user": item[0], "dt": item[2], "likes": item[3], "replies": item[4],
                    "text": item[5], "img": [], "nvid": 0, "hdr": [], "links": []}
    return None


def find_instagram(raw, key):
    for item in raw.get("comments") or []:
        if str(item.get("pk")) == str(key) or item.get("k") == key:
            return dict(item)
    post = raw.get("post")
    if post and (post.get("code") == key or key == "post"):
        return dict(post)
    return None


def clean(text):
    for tail in UI_TAILS:
        if text.endswith(tail):
            text = text[: -len(tail)]
    return text.rstrip()


def minsk(dt):
    """Возвращает (дата ГГГГ-ММ-ДД по Минску, строка 'ДД.ММ.ГГГГ ЧЧ:ММ') или (None, None)."""
    if not dt:
        return None, None
    try:
        value = dt.replace("Z", "+00:00")
        if len(value) == 16:
            value += ":00+00:00"
        local = datetime.fromisoformat(value).astimezone(MINSK)
    except ValueError:
        return None, None
    return local.strftime("%Y-%m-%d"), local.strftime("%d.%m.%Y %H:%M")


def media_of(item, extra):
    out = []
    imgs = [a for a in (item.get("img") or [])]
    nvid = item.get("nvid") or 0
    if imgs or nvid:
        parts = []
        if imgs:
            parts.append(f"изображений: {len(imgs)}")
        if nvid:
            parts.append(f"видео: {nvid}")
        line = "не скачано (" + ", ".join(parts) + ")"
        alts = [a for a in imgs if a]
        if alts:
            line += "; автоматические подписи площадки: " + " | ".join(alts)
        out.append(line)
    out.extend(extra or [])
    return out


def load_stories(cache={}):
    """Строки stories.jsonl по ключу (аккаунт, адрес подборки или показа, номер элемента)."""
    if not cache:
        for line in (HERE / "stories.jsonl").read_text(encoding="utf-8").splitlines():
            if line.strip():
                item = json.loads(line)
                cache[(item["account"], item["hl_url"], item["i"])] = item
    return cache


def story_record(number, entry, problems):
    """Запись об элементе истории или подборки историй.

    Сырая копия здесь — снимок кадра: надписи выписаны с него глазами, программа их
    с источником сверить не может (проверка даёт оценку IMAGE).
    """
    key = tuple(entry["story"])
    item = load_stories().get(key)
    if item is None:
        problems.append(f"история {key}: нет в stories.jsonl")
        return None
    shots = [s.strip() for s in (item.get("shot") or "").split(";") if s.strip()]
    for shot in shots:
        if not (HERE / shot).is_file():
            problems.append(f"история {key}: нет файла {shot}")
    date_iso, local = minsk(item.get("dt"))
    notes = entry["notes"].strip()
    tail = [f"Элемент {item['i']} из {item['n']}: {item['highlight']}; вид: {item['kind']}."]
    if local:
        tail.append(f"Время публикации элемента по Минску: {local}.")
    tail.append("Истории и подборки открываются только после входа в аккаунт; надписи выписаны со снимка кадра "
                "(не из текста страницы), исходный файл не скачивался.")
    media = [f"снимок кадра: {shot}" for shot in shots]
    if item.get("seen"):
        media.append("что видно: " + item["seen"])
    if item.get("match"):
        media.append("тот же материал в файлах пользователя: " + item["match"])
    taken = ""
    index = HERE / "screenshots" / "index.jsonl"
    if shots and index.is_file():
        for line in index.read_text(encoding="utf-8").splitlines():
            if line.strip() and json.loads(line).get("file") == shots[0]:
                taken = json.loads(line).get("taken_at", "")
    return {
        "id": f"logged-in-{number:03d}",
        "venue": entry["venue"],
        "platform": "instagram",
        "kind": entry.get("kind", "post"),
        "url": item["hl_url"],
        "author": item["account"],
        "date_published": item.get("dt"),
        "date_iso": date_iso,
        "rating": None,
        "text": item.get("text") or "[надписей на кадре нет]",
        "reply": None,
        "sentiment": entry["sentiment"],
        "topics": entry["topics"],
        "media": media,
        "captured_at": taken,
        "raw_file": shots[0] if shots else None,
        "screenshot": shots[0] if shots else None,
        "access": "login-required",
        "status": "verified-raw",
        "notes": (notes + " " + " ".join(tail)).strip(),
    }


def main():
    spec = json.loads((HERE / "work" / "classify.json").read_text(encoding="utf-8"))
    records = []
    problems = []
    last = max((entry["id"] for entry in spec if "id" in entry), default=0)
    seen_ids = set()
    for entry in spec:
        number = entry.get("id")
        if number is None:
            last += 1
            number = last
        if number in seen_ids:
            problems.append(f"номер {number} повторяется")
        seen_ids.add(number)
        if entry.get("story"):
            record = story_record(number, entry, problems)
            if record:
                records.append(record)
            continue
        raw_name = entry["raw"]
        raw = load_raw(raw_name)
        platform = entry.get("platform", "threads")
        if platform == "threads":
            item = find_threads(raw, entry["code"])
            if item is None:
                problems.append(f"{entry['code']}: нет в {raw_name}")
                continue
            url = f"https://www.threads.com/@{item['user']}/post/{item['code']}"
            author = item["user"]
            dt = item.get("dt")
            counters = f"отметок «нравится» {item.get('likes')}, ответов {item.get('replies')}"
        else:
            item = find_instagram(raw, entry["code"])
            if item is None:
                problems.append(f"{entry['code']}: нет в {raw_name}")
                continue
            url = entry.get("url") or item.get("url") or raw.get("url")
            author = item.get("user")
            dt = item.get("dt")
            likes = item.get("likes")
            if isinstance(likes, str) and likes.strip():
                counters = likes.strip()
            elif item.get("bar"):
                counters = "панель публикации: " + item["bar"]
            else:
                counters = ""
        text = clean(item.get("text") or "")
        for old, new in entry.get("redact") or []:
            if old not in text:
                problems.append(f"{entry['code']}: нет фрагмента для замены")
            text = text.replace(old, new)
        date_iso, local = minsk(dt)
        notes = entry["notes"].strip()
        tail = []
        if local:
            tail.append(f"Время публикации по Минску: {local}.")
        if counters:
            tail.append(f"На момент фиксации: {counters}.")
        if entry.get("screenshot"):
            tail.append("Получено после входа в аккаунт (браузер пользователя).")
        else:
            tail.append("Получено после входа в аккаунт (браузер пользователя); снимка экрана нет.")
        record = {
            "id": f"logged-in-{number:03d}",
            "venue": entry["venue"],
            "platform": platform,
            "kind": entry["kind"],
            "url": url,
            "author": author,
            "date_published": dt,
            "date_iso": date_iso,
            "rating": None,
            "text": text,
            "reply": entry.get("reply"),
            "sentiment": entry["sentiment"],
            "topics": entry["topics"],
            "media": media_of(item, entry.get("media")),
            "captured_at": (raw.get("at") or "").replace("Z", "+00:00"),
            "raw_file": raw_name,
            "screenshot": entry.get("screenshot"),
            "access": entry.get("access", "login-required"),
            "status": "verified-raw",
            "notes": (notes + " " + " ".join(tail)).strip(),
        }
        records.append(record)
    records.sort(key=lambda r: r["id"])
    out = HERE / "reviews.jsonl"
    out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records), encoding="utf-8", newline="\n")
    print("records:", len(records), "problems:", len(problems))
    for line in problems:
        print("  ", line)
    if problems:
        sys.exit(1)


if __name__ == "__main__":
    main()
