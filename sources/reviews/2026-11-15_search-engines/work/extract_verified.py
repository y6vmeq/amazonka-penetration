"""Достаёт отзывы и фрагменты из сырых копий (raw/) и пишет work/verified.jsonl.

Запуск из корня проекта:
    python -I sources/reviews/2026-11-15_search-engines/work/extract_verified.py list   # таблица всех отзывов -> work/peek.txt
    python -I sources/reviews/2026-11-15_search-engines/work/extract_verified.py build  # work/verified.jsonl

Тексты берутся из сырых копий программно (без ручного набора). Какие отзывы включать и с какими
метками — задаётся в work/verified_meta.py (словарь META и список SPECS).
"""
import html
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
COLLECTION = HERE.parent
RAW = COLLECTION / "raw"

MONTHS = {
    "января": 1, "февраля": 2, "марта": 3, "апреля": 4, "мая": 5, "июня": 6,
    "июля": 7, "августа": 8, "сентября": 9, "октября": 10, "ноября": 11, "декабря": 12,
}


def read(path):
    data = path.read_bytes()
    for encoding in ("utf-8", "cp1251"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", "replace")


def clean(fragment):
    """HTML-фрагмент -> текст: <br> и </p> дают перенос строки, остальные теги убираются."""
    fragment = re.sub(r"(?is)<script.*?</script>|<style.*?</style>", " ", fragment)
    fragment = re.sub(r"(?i)<br\s*/?>|</p>|</div>", "\n", fragment)
    fragment = html.unescape(re.sub(r"<[^>]+>", " ", fragment))
    lines = [re.sub(r"[ \t\r\f\v ]+", " ", line).strip() for line in fragment.split("\n")]
    return "\n".join(line for line in lines if line)


def flat_text(source):
    text = re.sub(r"(?is)<script.*?</script>|<style.*?</style>", " ", source)
    text = html.unescape(re.sub(r"<[^>]+>", " ", text))
    return re.sub(r"\s+", " ", text)


def iso_dmy(text):
    match = re.search(r"(\d{2})\.(\d{2})\.(\d{4})", text)
    return f"{match.group(3)}-{match.group(2)}-{match.group(1)}" if match else None


def iso_words(text):
    match = re.search(r"(\d{1,2}) ([а-яё]+) (\d{4})", text.lower())
    if match and match.group(2) in MONTHS:
        return f"{match.group(3)}-{MONTHS[match.group(2)]:02d}-{int(match.group(1)):02d}"
    return None


def raw_files(pattern):
    return sorted(RAW.glob(pattern))


def parse_justeat(pattern, base_url):
    items = []
    for path in raw_files(pattern):
        source = read(path)
        for match in re.finditer(
            r'<a name="r(\d+)"></a>\s*<div class="item">\s*<div class="head"><span class="author">(.*?)</span>\s*'
            r'<span class="date">(.*?)</span></div>\s*<div class="rating"><img src="/image/rating/star-(\d)\.png"[^>]*></div>\s*'
            r'<div class="text">(.*?)</div>', source, flags=re.S):
            rid, author, date, rating, body = match.groups()
            items.append({
                "site": "just-eat.by", "rid": f"justeat-{rid}", "url": f"{base_url}#r{rid}",
                "author": clean(author), "date_published": clean(date), "date_iso": iso_dmy(date),
                "rating": int(rating), "text": clean(body), "reply": None, "raw_file": f"raw/{path.name}",
            })
    return items


def parse_mogilev_in(pattern):
    items = []
    for path in raw_files(pattern):
        source = read(path)
        for match in re.finditer(
            r'<div class="res-rvw-item\s*">\s*<i class="stars stars(\d)"></i>\s*<span class="res-rvw-date">(.*?)</span>\s*'
            r'<a href="(https://mogilev\.in/[^"]+/rev(\d+)/)" class="res-rvw-link\s*">(.*?)</a>', source, flags=re.S):
            rating, date, url, rid, body = match.groups()
            items.append({
                "site": "mogilev.in", "rid": f"mogilevin-{rid}", "url": url, "author": None,
                "date_published": clean(date), "date_iso": iso_dmy(date), "rating": int(rating),
                "text": clean(body), "reply": None, "raw_file": f"raw/{path.name}",
            })
    return items


def parse_firmi(pattern, base_url):
    items = []
    seen = set()
    for path in raw_files(pattern):
        source = read(path)
        for match in re.finditer(
            r'<div class="review">\s*<div class="review-name"><span>(.*?)</span>.*?</div>\s*<div class="review-date">(.*?)</div>\s*'
            r'<p class="review-text">(.*?)</p>\s*<div id="like(\d+)"', source, flags=re.S):
            author, date, body, rid = match.groups()
            if rid in seen:
                continue
            seen.add(rid)
            rating = len(re.findall(r'class="a-star"', body))
            items.append({
                "site": "firmi.by", "rid": f"firmi-{rid}", "url": base_url, "author": clean(author),
                "date_published": clean(date), "date_iso": iso_words(date), "rating": rating or None,
                "text": clean(body), "reply": None, "raw_file": f"raw/{path.name}",
            })
    return items


def parse_gorodwiki(pattern, base_url):
    items = []
    seen = set()
    for path in raw_files(pattern):
        source = read(path)
        for match in re.finditer(
            r'<div id="c(\d+)" class="review">(.*?)<div class="review-data">(.*?)</div>', source, flags=re.S):
            rid, head, body = match.groups()
            if rid in seen:
                continue
            seen.add(rid)
            author = re.search(r'<span class="user"></span>\s*<span>(.*?)</span>', head, flags=re.S)
            date = re.search(r'<div class="reviewdate">(.*?)</div>', head, flags=re.S)
            rating = len(re.findall(r'class="fa-star"', head))
            items.append({
                "site": "gorodwiki.ru", "rid": f"gorodwiki-{rid}", "url": f"{base_url}#c{rid}",
                "author": clean(author.group(1)) if author else None,
                "date_published": clean(date.group(1)) if date else None,
                "date_iso": iso_words(date.group(1)) if date else None,
                "rating": rating or None, "text": clean(body), "reply": None, "raw_file": f"raw/{path.name}",
            })
    return items


def parse_clever(pattern, base_url):
    items = []
    for path in raw_files(pattern):
        source = read(path)
        blocks = re.split(r'(?=<div class="comm__item\s[^>]*data-id=")', source)
        last = None
        for block in blocks:
            head = re.match(r'<div class="comm__item\s*(comm__item--reply)?\s*"\s*data-id="(\d+)"', block)
            if not head:
                continue
            is_reply, rid = head.groups()
            name = re.search(r'class="comm__name">(.*?)</a>', block, flags=re.S)
            date = re.search(r'<div class="comm__date">(.*?)</div>', block, flags=re.S)
            body = re.search(r'<div class="comm__text">(.*?)</div>', block, flags=re.S)
            text = clean(body.group(1)) if body else ""
            if is_reply:
                if last is not None and text:
                    last["reply"] = text
                    last["reply_meta"] = f"{clean(name.group(1)) if name else ''}, {clean(date.group(1)) if date else ''}"
                continue
            marks = dict(re.findall(r'comm__rating-pos">([^:<]+):\s*<div class="comm__rating-value">(\d)</div>', block))
            total = re.search(r'comm__rating-mark comm__rating-mark--(\d)', block)
            dishes = []
            for dish in re.finditer(
                r'<div class="comm__dish-name">(.*?)</div>\s*<i class="comm__dish-mark[^"]*comm__dish-mark--(\d)"></i>\s*'
                r'<div class="comm__dish-text[^"]*">(.*?)</div>', block, flags=re.S):
                dishes.append(f"{clean(dish.group(1))} — оценка {dish.group(2)}: {clean(dish.group(3))}")
            last = {
                "site": "clever.by", "rid": f"clever-{rid}", "url": f"{base_url}#rev{rid}",
                "author": clean(name.group(1)) if name else None,
                "date_published": clean(date.group(1)) if date else None,
                "date_iso": iso_dmy(date.group(1)) if date else None,
                "rating": int(total.group(1)) if total else None, "text": text, "reply": None,
                "raw_file": f"raw/{path.name}", "marks": marks, "dishes": dishes,
            }
            if text:
                items.append(last)
    return items


def vacancy_text(fragment):
    """HTML описания вакансии -> текст: абзацы и пункты списка — с новой строки."""
    fragment = re.sub(r"(?i)<br\s*/?>|</p>|</li>|<ul>|</ul>|</div>", "\n", fragment)
    fragment = html.unescape(re.sub(r"<[^>]+>", " ", fragment))
    lines = [re.sub(r"\s+", " ", line).strip() for line in fragment.split("\n")]
    return "\n".join(line for line in lines if line)


def parse_vacancy(pattern):
    """Вакансия на hh.ru / rabota.by: описание — из разметки JobPosting, шапка — из видимого текста страницы."""
    for path in raw_files(pattern):
        source = read(path)
        for match in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', source, flags=re.S):
            try:
                data = json.loads(match.group(1))
            except json.JSONDecodeError:
                continue
            if data.get("@type") != "JobPosting":
                continue
            flat = flat_text(source)
            title = data.get("title", "")
            header = None
            begin = flat.find(f"{title} В архиве с")
            if begin >= 0:
                finish = flat.find("ООО АмазонкаГрупп", begin)
                if 0 <= finish - begin < 600:
                    header = flat[begin:finish + len("ООО АмазонкаГрупп")].strip()
            address = (data.get("jobLocation") or {}).get("address") or {}
            place = ", ".join(part for part in (address.get("addressLocality"), address.get("streetAddress")) if part)
            return {
                "title": title, "text": vacancy_text(data.get("description", "")),
                "posted": data.get("datePosted"), "valid": data.get("validThrough"),
                "employer": (data.get("hiringOrganization") or {}).get("name"),
                "place": place, "header": header, "raw_file": f"raw/{path.name}",
            }
    return None


def all_reviews():
    items = []
    items += parse_justeat("008_*", "https://just-eat.by/shopreviews/amazonka-mogilev.html")
    items += parse_mogilev_in("009_*")
    items += parse_firmi("01[45]_firmi*", "https://firmi.by/mogilev/amazonka-restobar-92979")
    items += parse_firmi("027_firmi*", "https://firmi.by/mogilev/amazonka-restobar-92979")
    items += parse_gorodwiki("007_*", "https://by.gorodwiki.ru/mogilev/amazonka-restobar-1021111-otzyvy")
    items += parse_gorodwiki("028_*", "https://by.gorodwiki.ru/mogilev/amazonka-restobar-1021111-otzyvy")
    items += parse_clever("011_*", "https://clever.by/mogilev/amazonka-delivery/")
    unique = {}
    for item in items:
        unique.setdefault(item["rid"], item)
    return list(unique.values())


def captured_at(raw_file):
    """Время загрузки сырой копии из raw/manifest.jsonl."""
    manifest = RAW / "manifest.jsonl"
    result = None
    for line in manifest.read_text(encoding="utf-8").splitlines():
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if record.get("file") == raw_file:
            result = record["fetched_at"]
    return result


def spec_text(raw_pattern, start, end):
    """Фрагмент плоского текста сырой копии от start до end включительно."""
    for path in raw_files(raw_pattern):
        text = flat_text(read(path))
        begin = text.find(start)
        if begin < 0:
            continue
        finish = text.find(end, begin)
        if finish < 0:
            continue
        return text[begin:finish + len(end)].strip(), f"raw/{path.name}"
    return None, None


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "list"
    reviews = all_reviews()
    if mode == "list":
        lines = []
        for item in reviews:
            extra = ""
            if item.get("marks"):
                extra = " | " + ", ".join(f"{k}={v}" for k, v in item["marks"].items())
            lines.append(f"{item['rid']} | {item['date_published']} | {item['author']} | оценка {item['rating']}{extra}")
            lines.append("    " + item["text"].replace("\n", " / "))
            for dish in item.get("dishes", []):
                lines.append("    блюдо: " + dish)
            if item.get("reply"):
                lines.append("    ОТВЕТ (" + item.get("reply_meta", "") + "): " + item["reply"].replace("\n", " / "))
        (HERE / "peek.txt").write_text("\n".join(lines), encoding="utf-8")
        print(f"reviews={len(reviews)}")
        return

    sys.path.insert(0, str(HERE))
    import verified_meta  # noqa: E402

    by_id = {item["rid"]: item for item in reviews}
    out = []
    problems = []
    for rid, meta in verified_meta.META.items():
        item = by_id.get(rid)
        if item is None:
            problems.append(f"нет отзыва {rid}")
            continue
        notes = meta.get("notes", "")
        if item.get("marks"):
            marks = ", ".join(f"{k.strip().lower()} {v}" for k, v in item["marks"].items())
            notes = (notes + " " if notes else "") + f"Оценки на странице: {marks}; общая {item['rating']}."
        if item.get("dishes"):
            notes = (notes + " " if notes else "") + "Оценки блюд на странице: " + "; ".join(item["dishes"]) + "."
        if item.get("reply_meta"):
            notes = (notes + " " if notes else "") + f"Ответ подписан: {item['reply_meta']}."
        out.append({
            "venue": meta.get("venue", "amazonka-mogilev"), "platform": item["site"], "kind": "review",
            "url": item["url"], "author": item["author"], "date_published": item["date_published"],
            "date_iso": item["date_iso"], "rating": item["rating"], "text": item["text"], "reply": item["reply"],
            "sentiment": meta["sentiment"], "topics": meta["topics"], "media": [],
            "captured_at": captured_at(item["raw_file"]), "raw_file": item["raw_file"], "screenshot": None,
            "access": "public", "status": "verified-raw", "notes": notes,
        })
    for spec in verified_meta.SPECS:
        text, raw_file = spec_text(spec["raw"], spec["start"], spec["end"])
        if text is None:
            problems.append(f"не найден фрагмент: {spec['raw']} / {spec['start'][:40]}")
            continue
        reply = None
        if spec.get("reply_start"):
            reply, _ = spec_text(spec["raw"], spec["reply_start"], spec["reply_end"])
            if reply is None:
                problems.append(f"не найден ответ: {spec['raw']} / {spec['reply_start'][:40]}")
        out.append({
            "venue": spec["venue"], "platform": spec["platform"], "kind": spec["kind"], "url": spec["url"],
            "author": spec.get("author"), "date_published": spec.get("date_published"), "date_iso": spec.get("date_iso"),
            "rating": spec.get("rating"), "text": text, "reply": reply, "sentiment": spec["sentiment"],
            "topics": spec["topics"], "media": [], "captured_at": captured_at(raw_file), "raw_file": raw_file,
            "screenshot": None, "access": "public", "status": "verified-raw", "notes": spec.get("notes", ""),
        })
    for spec in getattr(verified_meta, "VACANCIES", []):
        item = parse_vacancy(spec["raw"])
        if item is None or not item["text"]:
            problems.append(f"не разобрана вакансия: {spec['raw']}")
            continue
        archived = re.search(r"В архиве с \d{1,2} [а-яё]+ \d{4}", item["header"] or "")
        parts = []
        if item["header"]:
            parts.append(f"Шапка вакансии на странице: «{item['header']}».")
        else:
            problems.append(f"не найдена шапка вакансии: {spec['raw']}")
        parts.append(
            f"По разметке страницы (JobPosting): должность «{item['title']}», опубликована {item['posted']}, "
            f"действовала до {item['valid']}, место работы: {item['place']}. "
            "В поле date_iso — дата публикации по этой разметке."
        )
        if spec.get("notes"):
            parts.append(spec["notes"])
        out.append({
            "venue": spec["venue"], "platform": spec["platform"], "kind": "vacancy", "url": spec["url"],
            "author": item["employer"], "date_published": archived.group(0) if archived else None,
            "date_iso": (item["posted"] or "")[:10] or None, "rating": None, "text": item["text"], "reply": None,
            "sentiment": "neutral", "topics": spec.get("topics", ["staff-labor"]), "media": [],
            "captured_at": captured_at(item["raw_file"]), "raw_file": item["raw_file"], "screenshot": None,
            "access": "public", "status": "verified-raw", "notes": " ".join(parts),
        })
    (HERE / "verified.jsonl").write_text(
        "\n".join(json.dumps(record, ensure_ascii=False) for record in out) + ("\n" if out else ""),
        encoding="utf-8", newline="\n")
    print(f"verified={len(out)} problems={len(problems)}")
    problems_path = HERE / "verified_problems.txt"
    if problems:
        problems_path.write_text("\n".join(problems), encoding="utf-8")
    elif problems_path.is_file():
        problems_path.unlink()


if __name__ == "__main__":
    main()
