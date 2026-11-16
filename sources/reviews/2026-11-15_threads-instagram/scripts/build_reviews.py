"""Build reviews.jsonl from collected data and hand-made classification files.

Usage (from project root): python -I sources/reviews/2026-11-15_threads-instagram/scripts/build_reviews.py

Inputs (all inside the collection folder):
  work/threads_posts.json     merged Threads posts (verbatim texts come from here)
  work/classify_threads.json  code -> [venue, kind, sentiment, topics, notes]
  work/ig_records.json        optional: ready-made records for Instagram (list of dicts without id)
  work/media_index.json       optional: key (post code) -> list of media entries (local path + source)
  work/ids.json               persistent key -> id map (created/extended here)
  raw/manifest.jsonl
Output: reviews.jsonl
"""
import html
import json
import re
import sys
import unicodedata
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
BASE = Path(__file__).resolve().parent.parent
WORK = BASE / "work"
SLUG = "threads-instagram"
MINSK = timezone(timedelta(hours=3))

# Personal details that must not be copied (protocol, section 5): code -> (verbatim fragment, replacement)
REDACT = {
    "Dfmpiq3CjWu": ("Сама живет, не в чем себе не отказывая, ездит на хорошей машине, за сумму гораздо больше, чем долги.",
                    "[личные сведения опущены]"),
    "DfsubhgDG0B": ("все отмывает машину свою", "[личные сведения опущены]"),
}

ZERO_WIDTH = re.compile("[​-‏⁠﻿­]")
TAG = re.compile(r"<[^>]*>")
UNICODE_ESCAPE = re.compile(r"\\u([0-9a-fA-F]{4})")


def normalize(text):
    text = html.unescape(text)
    text = unicodedata.normalize("NFKC", text)
    text = ZERO_WIDTH.sub("", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def letters_only(text):
    return "".join(ch for ch in text if ch.isalnum())


def json_unescape(text):
    text = UNICODE_ESCAPE.sub(lambda m: chr(int(m.group(1), 16)), text)
    text = text.encode("utf-16", "surrogatepass").decode("utf-16", "replace")
    for esc in ("\\n", "\\r", "\\t"):
        text = text.replace(esc, " ")
    return text.replace('\\"', '"').replace("\\/", "/").replace("\\\\", "\\")


_cache = {}


def raw_has(raw_rel, quote):
    """True if the quote is found in the raw copy (same normalisation as tools/reviews_check.py, strict or letters-only)."""
    path = BASE / raw_rel
    if not path.is_file():
        return False
    if raw_rel not in _cache:
        text = path.read_bytes().decode("utf-8", errors="replace")
        un = json_unescape(text)
        variants = {normalize(c) for c in (text, TAG.sub(" ", text), un, TAG.sub(" ", un))}
        _cache[raw_rel] = (variants, [letters_only(v) for v in variants])
    variants, loose = _cache[raw_rel]
    needle = normalize(quote)
    if any(needle in v for v in variants):
        return True
    ln = letters_only(needle)
    return bool(ln) and any(ln in v for v in loose)


def load_manifest():
    entries = {}
    for line in (BASE / "raw" / "manifest.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            e = json.loads(line)
            entries[e["file"]] = e
    return entries


def iso_tz(ts):
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(timezone.utc).isoformat(timespec="seconds")


def main():
    db = json.loads((WORK / "threads_posts.json").read_text(encoding="utf-8"))
    classify = json.loads((WORK / "classify_threads.json").read_text(encoding="utf-8"))
    classify.pop("_comment", None)
    manifest = load_manifest()
    media_index = json.loads((WORK / "media_index.json").read_text(encoding="utf-8")) if (WORK / "media_index.json").is_file() else {}
    ids_path = WORK / "ids.json"
    ids = json.loads(ids_path.read_text(encoding="utf-8")) if ids_path.is_file() else {}
    screenshots = {p.name[:3]: f"screenshots/{p.name}" for p in (BASE / "screenshots").glob("*.png")}

    def new_id(key):
        if key not in ids:
            ids[key] = f"{SLUG}-{len(ids) + 1:03d}"
        return ids[key]

    def root_of(code):
        seen = set()
        while db.get(code, {}).get("parent") and code not in seen:
            seen.add(code)
            code = db[code]["parent"]
        return code

    # stable order: by root time, then by post time
    def order_key(code):
        root = root_of(code)
        return (db[root].get("taken_at") or 0, root, db[code].get("taken_at") or 0, code)

    records, problems = [], []
    for code in sorted(classify, key=order_key):
        venue, kind, sentiment, topics, note = classify[code]
        rec = db.get(code)
        if not rec:
            problems.append(f"{code}: not in threads_posts.json")
            continue
        text = rec.get("text") or ""
        redacted = False
        if code in REDACT:
            old, new = REDACT[code]
            if old not in text:
                problems.append(f"{code}: fragment to redact not found")
            text = text.replace(old, new)
            redacted = True
        # choose a raw copy that contains the text (for redacted texts: the part before the replacement)
        probe = text.split("[личные сведения опущены]")[0].strip() if redacted else text
        candidates = [f"raw/{stem}.html" for stem in rec.get("seen_on", [])]
        candidates.sort(key=lambda f: (0 if "dom-full" in f else 1 if f == rec.get("page_raw") else 2, f))
        candidates += [f.replace(".html", "_graphql.json") for f in candidates if "dom" in f]
        raw_file = next((f for f in candidates if raw_has(f, probe)), None)
        if not raw_file:
            problems.append(f"{code}: text not found in any raw copy {candidates[:3]}")
            raw_file = candidates[0] if candidates else None
        entry = manifest.get(raw_file) or manifest.get((raw_file or "").replace("_graphql.json", ".html")) or {}
        shot = screenshots.get((raw_file or "")[4:7]) if raw_file and ("dom" in raw_file or raw_file[4:7] == "001") else None
        published = datetime.fromisoformat(rec["iso"].replace("Z", "+00:00"))
        local = published.astimezone(MINSK)
        root = root_of(code)
        parent = rec.get("parent")
        context = []
        if root != code:
            context.append(f"В ветке под постом @{db[root]['user']} ({db[root].get('permalink')}).")
            if parent and parent != root and db[parent]["user"] != rec["user"]:
                context.append(f"Ответ на реплику @{db[parent]['user']} ({db[parent].get('permalink')}).")
        context.append(f"Время публикации по Минску: {local.strftime('%d.%m.%Y %H:%M')}.")
        counters = []
        if rec.get("like_count") is not None:
            counters.append(f"отметок «нравится» {rec['like_count']}")
        if rec.get("direct_reply_count"):
            counters.append(f"счётчик ответов {rec['direct_reply_count']}")
        if counters:
            context.append("На момент фиксации: " + ", ".join(counters) + ".")
        media = media_index.get(code)
        if media is None:
            media = [f"{m['kind']} {m.get('idx', 1)} (не скачано): {rec.get('permalink')}" for m in rec.get("media") or []]
        records.append({
            "id": new_id("threads:" + code), "venue": venue, "platform": "threads", "kind": kind,
            "url": rec.get("permalink") or f"https://www.threads.com/@{rec['user']}/post/{code}",
            "author": rec["user"], "date_published": rec["iso"], "date_iso": local.strftime("%Y-%m-%d"),
            "rating": None, "text": text, "reply": None, "sentiment": sentiment, "topics": topics, "media": media,
            "captured_at": iso_tz(entry["fetched_at"]) if entry.get("fetched_at") else datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "raw_file": raw_file, "screenshot": shot, "access": "public", "status": "verified-raw",
            "notes": " ".join(([note] if note else []) + context),
        })

    ig_path = WORK / "ig_records.json"
    if ig_path.is_file():
        for item in json.loads(ig_path.read_text(encoding="utf-8")):
            key = item.pop("key")
            item = {"id": new_id(key), **item}
            parts = key.split(":")
            if len(parts) == 2 and ("ig:" + parts[1]) in media_index:
                item["media"] = media_index["ig:" + parts[1]]
            records.append(item)

    # screenshots taken after the collection (work/screenshot_map.json is written by build_screenshot_map.py)
    map_path = WORK / "screenshot_map.json"
    if map_path.is_file():
        shot_map = json.loads(map_path.read_text(encoding="utf-8"))
        for r in records:
            if r["url"] in shot_map and (BASE / shot_map[r["url"]]).is_file():
                r["screenshot"] = shot_map[r["url"]]

    ids_path.write_text(json.dumps(ids, ensure_ascii=False, indent=1), encoding="utf-8")
    records.sort(key=lambda r: r["id"])
    with open(BASE / "reviews.jsonl", "w", encoding="utf-8", newline="\n") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"records: {len(records)}; problems: {len(problems)}")
    for p in problems:
        print("  !", p)
    by = {}
    for r in records:
        by[(r["platform"], r["venue"], r["sentiment"])] = by.get((r["platform"], r["venue"], r["sentiment"]), 0) + 1
    for k in sorted(by):
        print("  ", k, by[k])


if __name__ == "__main__":
    main()
