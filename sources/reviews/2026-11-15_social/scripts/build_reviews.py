"""Собирает reviews.jsonl из сырых копий по описанию в records_spec.json.

Запуск из корня проекта:
    python -I sources/reviews/2026-11-15_social/scripts/build_reviews.py

Текст, автор и дата каждой записи берутся программно из сырой копии (raw/...), вручную не
набираются. В records_spec.json задаются только: какая сырая копия, какой пост или комментарий,
заведение, тональность, темы и пояснения.

Типы источников (поле "src"):
  tg_post        страница t.me/s/<канал>...; key = "<канал>/<id>"
  tg_comment     страница виджета обсуждения t.me/<канал>/<id>?embed=1&discussion=1; key = id комментария
  vk_post        страница vk.com (стена, поиск по стене, пост); key = "<owner_id>_<post_id>", например "-202389635_20776"
  vk_reply       то же; key = "<owner_id>_<reply_id>"
  tt_embed       встраиваемая страница TikTok (/embed/tag/..., /embed/@...); key = id видео
  tt_video       страница видео TikTok; key = id видео
  yt_video       страница видео YouTube (watch?v=...); key = id видео
  yt_search      страница выдачи YouTube; key = id видео (текст — название из выдачи)
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
COLLECTION = HERE.parent
sys.path.insert(0, str(HERE))
import tgparse  # noqa: E402
import tgcomments  # noqa: E402
import ttparse  # noqa: E402
import vk_decode  # noqa: E402
import vkparse  # noqa: E402
import ytparse  # noqa: E402

VK_NOTE = ("Поле raw_file — производная копия: данные постов, раскодированные из атрибута data-exec исходной "
           "страницы {source} (одно действие html.unescape, см. raw/derived.jsonl); исходная страница лежит рядом.")

FIELDS = ["id", "venue", "platform", "kind", "url", "author", "date_published", "date_iso", "rating", "text",
          "reply", "sentiment", "topics", "media", "captured_at", "raw_file", "screenshot", "access", "status",
          "notes"]


def load_manifest():
    result = {}
    for line in (COLLECTION / "raw" / "manifest.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            record = json.loads(line)
            if record.get("file"):
                result[record["file"]] = record
    return result


def read_raw(raw_file):
    data = (COLLECTION / raw_file).read_bytes()
    if "vk-com" in raw_file:
        return vkparse.decode(data)
    return data.decode("utf-8", "replace")


def from_tg_post(text, key):
    for message in tgparse.messages(text):
        if message["post"] == key:
            media = []
            if message["media"]:
                media.append(f"{', '.join(message['media'])} — в посте {message['url']}")
            return {
                "url": message["url"],
                "author": message["owner"],
                "date_published": message["datetime"],
                "date_iso": (message["datetime"] or "")[:10] or None,
                "text": message["text"],
                "media": media,
            }
    raise KeyError(key)


def from_tg_comment(text, key):
    for comment in tgcomments.comments(text):
        if comment["comment_id"] == str(key):
            return {
                "url": comment["url"],
                "author": comment["author"],
                "date_published": comment["date_shown"],
                "date_iso": (comment["datetime"] or "")[:10] or None,
                "text": comment["text"],
                "media": comment["media"],
            }
    raise KeyError(key)


def from_vk_post(text, key):
    for post in vkparse.posts(text):
        candidates = [(post["post"], post, post["owner"] or post["author"])]
        for copy in post["copy_history"]:
            candidates.append((copy["url"].split("wall")[-1], copy, copy["owner"]))
        for post_key, item, owner in candidates:
            if post_key == key:
                return {
                    "url": item["url"],
                    "author": owner,
                    "date_published": item["date"],
                    "date_iso": (item["date"] or "")[:10] or None,
                    "text": item["text"],
                    "media": item["attachments"],
                }
    raise KeyError(key)


def from_vk_reply(text, key):
    for reply in vkparse.replies(text):
        if reply["reply"] == key:
            return {
                "url": reply["url"],
                "author": reply["author"],
                "date_published": reply["date_shown"],
                "date_iso": (reply["date"] or "")[:10] or None,
                "text": reply["text"],
                "media": reply["media"],
            }
    raise KeyError(key)


def from_tt_embed(text, key):
    for video in ttparse.embed_videos(text):
        if str(video["id"]) == str(key):
            return {
                "url": video["url"],
                "author": video["author"],
                "date_published": video["created"],
                "date_iso": (video["created"] or "")[:10] or None,
                "text": video["desc"].strip(),
                "media": [f"видео {video['url']}"],
            }
    raise KeyError(key)


def from_tt_video(text, key):
    scope = ttparse.universal(text) or {}
    item = (((scope.get("webapp.video-detail") or {}).get("itemInfo") or {}).get("itemStruct")) or {}
    if str(item.get("id")) != str(key):
        raise KeyError(key)
    author = (item.get("author") or {}).get("uniqueId")
    created = ttparse.iso(item.get("createTime"))
    url = f"https://www.tiktok.com/@{author}/video/{item.get('id')}"
    return {
        "url": url,
        "author": author,
        "date_published": created,
        "date_iso": (created or "")[:10] or None,
        "text": (item.get("desc") or "").strip(),
        "media": [f"видео {url}"],
    }


def from_yt_video(text, key):
    details = ytparse.video_details(text) or {}
    if details.get("id") != key:
        raise KeyError(key)
    url = f"https://www.youtube.com/watch?v={key}"
    published = details.get("publish_date") or details.get("upload_date")
    return {
        "url": url,
        "author": details.get("channel"),
        "date_published": published,
        "date_iso": (published or "")[:10] or None,
        "text": (details.get("description") or "").strip() or (details.get("title") or ""),
        "media": [f"видео {url}"],
        "title": details.get("title"),
    }


def from_yt_search(text, key):
    items, _ = ytparse.search_results(text)
    for item in items:
        if item["id"] == key:
            return {
                "url": item["url"],
                "author": item["channel"] or None,
                "date_published": item["published"] or None,
                "date_iso": None,
                "text": item["title"],
                "media": [f"видео {item['url']}"],
            }
    raise KeyError(key)


EXTRACTORS = {
    "tg_post": from_tg_post,
    "tg_comment": from_tg_comment,
    "vk_post": from_vk_post,
    "vk_reply": from_vk_reply,
    "tt_embed": from_tt_embed,
    "tt_video": from_tt_video,
    "yt_video": from_yt_video,
    "yt_search": from_yt_search,
}


def main():
    spec = json.loads((HERE / "records_spec.json").read_text(encoding="utf-8"))
    manifest = load_manifest()
    cache = {}
    lines = []
    problems = []
    for entry in spec:
        raw_file = entry["raw_file"]
        try:
            if raw_file not in cache:
                cache[raw_file] = read_raw(raw_file)
            data = EXTRACTORS[entry["src"]](cache[raw_file], entry["key"])
        except (KeyError, OSError) as error:
            problems.append(f"{entry['id']}: не найдено в {raw_file}: {error!r}")
            continue
        notes = entry.get("notes", "")
        if data.get("title") and entry.get("title_in_notes", True):
            notes = (f"Название видео: «{data['title']}». " + notes).strip()
        output_raw = raw_file
        if entry["src"] == "vk_post":
            output_raw = vk_decode.decode_file(raw_file)
            notes = (notes + " " + VK_NOTE.format(source=raw_file)).strip()
        record = {
            "id": entry["id"],
            "venue": entry["venue"],
            "platform": entry["platform"],
            "kind": entry["kind"],
            "url": entry.get("url") or data["url"],
            "author": entry.get("author", data["author"]),
            "date_published": data["date_published"],
            "date_iso": data["date_iso"],
            "rating": entry.get("rating"),
            "text": data["text"],
            "reply": entry.get("reply"),
            "sentiment": entry["sentiment"],
            "topics": entry["topics"],
            "media": entry.get("media", data["media"]),
            "captured_at": (manifest.get(raw_file) or {}).get("fetched_at") or entry.get("captured_at"),
            "raw_file": output_raw,
            "screenshot": None,
            "access": entry.get("access", "public"),
            "status": entry.get("status", "verified-raw"),
            "notes": notes,
        }
        if not record["text"].strip():
            problems.append(f"{entry['id']}: пустой текст")
            continue
        lines.append(json.dumps({field: record[field] for field in FIELDS}, ensure_ascii=False))
    (COLLECTION / "reviews.jsonl").write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8", newline="\n")
    print(f"records={len(lines)} problems={len(problems)}")
    for problem in problems:
        print(ascii(problem))


if __name__ == "__main__":
    main()
