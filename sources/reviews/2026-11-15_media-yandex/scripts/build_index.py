"""Собирает рабочий указатель всех фото: файл, лист, SHA-256, отзыв или номер галереи, заведение, дата.

Запуск из корня проекта:
    python -I sources/reviews/2026-11-15_media-yandex/scripts/build_index.py

Читает (только читает) манифесты и списки из папок yandex-maps и aggregators,
пересчитывает SHA-256 каждого файла и сверяет с манифестом, определяет размер
изображения. Пишет в свою папку photo_index.json и photo_index.tsv.
"""
import hashlib
import json
import re
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parents[1]
YANDEX = ROOT / "sources/reviews/2026-11-15_yandex-maps"
AGGREGATORS = ROOT / "sources/reviews/2026-11-15_aggregators"


def read_jsonl(path):
    with open(path, encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def sha256_of(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def image_size(path):
    try:
        with Image.open(path) as image:
            return image.size[0], image.size[1], image.format
    except OSError as error:
        return None, None, f"ERR {error}"


def photo_key(url):
    """Идентификатор снимка в адресе avatars.mds.yandex.net (предпоследняя часть пути)."""
    match = re.search(r"/get-altay/\d+/([0-9a-f]+)/", url or "")
    return match.group(1) if match else None


def sheet_map(folder):
    result = {}
    for line in (folder / "media_sheets/sheets_index.tsv").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        sheet, label = line.split("\t")
        result[label.split(" (")[0]] = sheet
    return result


def main():
    rows = []

    # --- Яндекс Карты ---
    reviews = {record["id"]: record for record in read_jsonl(YANDEX / "reviews.jsonl")}
    gallery = json.loads((YANDEX / "raw/015_yandex-maps_amazonka_photos-list.json").read_text(encoding="utf-8"))
    gallery_by_n = {photo["n"]: photo for photo in gallery["photos"]}
    gallery_by_key = {photo_key(photo["url"]): photo for photo in gallery["photos"]}
    sheets = sheet_map(YANDEX)
    for entry in read_jsonl(YANDEX / "media/manifest.jsonl"):
        if not entry.get("file"):
            rows.append({"set": "yandex-maps", "group": entry["group"], "n": entry["n"], "file": None,
                         "url": entry["url"], "note": entry.get("note", "")})
            continue
        path = YANDEX / entry["file"]
        relative = entry["file"].split("media/", 1)[1]
        width, height, image_format = image_size(path)
        actual_sha = sha256_of(path)
        row = {
            "set": "yandex-maps",
            "group": entry["group"],
            "n": entry["n"],
            "file": path.relative_to(ROOT).as_posix(),
            "sheet": sheets.get(relative),
            "url": entry["url"],
            "sha256": actual_sha,
            "sha_matches_manifest": actual_sha == entry["sha256"],
            "bytes": path.stat().st_size,
            "width": width, "height": height, "format": image_format,
        }
        if entry["group"] == "gallery":
            photo = gallery_by_n.get(entry["n"], {})
            row.update({
                "source_record": f"gallery-{entry['n']}",
                "venue": "amazonka-mogilev",
                "date": (photo.get("uploaded_at") or "")[:10],
                "tags": photo.get("tags", []),
                "rating": None,
                "gallery_n": entry["n"],
            })
        else:
            review = reviews.get(entry["group"], {})
            twin = gallery_by_key.get(photo_key(entry["url"]))
            row.update({
                "source_record": entry["group"],
                "venue": review.get("venue"),
                "date": review.get("date_iso"),
                "tags": twin.get("tags", []) if twin else [],
                "rating": review.get("rating"),
                "gallery_n": twin["n"] if twin else None,
                "gallery_uploaded": (twin.get("uploaded_at") or "")[:10] if twin else None,
            })
        rows.append(row)

    # --- Площадки отзывов ---
    aggregator_reviews = {record["id"]: record for record in read_jsonl(AGGREGATORS / "reviews.jsonl")}
    sheets = sheet_map(AGGREGATORS)
    for entry in read_jsonl(AGGREGATORS / "media/manifest.jsonl"):
        if not entry.get("file"):
            rows.append({"set": "aggregators", "group": entry["group"], "n": entry["n"], "file": None,
                         "url": entry["url"], "note": entry.get("note", "")})
            continue
        path = AGGREGATORS / entry["file"]
        relative = entry["file"].split("media/", 1)[1]
        width, height, image_format = image_size(path)
        actual_sha = sha256_of(path)
        review = aggregator_reviews.get(entry["group"], {})
        rows.append({
            "set": "aggregators",
            "group": entry["group"],
            "n": entry["n"],
            "file": path.relative_to(ROOT).as_posix(),
            "sheet": "agg_" + (sheets.get(relative) or "?"),
            "url": entry["url"],
            "sha256": actual_sha,
            "sha_matches_manifest": actual_sha == entry["sha256"],
            "bytes": path.stat().st_size,
            "width": width, "height": height, "format": image_format,
            "source_record": entry["group"],
            "venue": review.get("venue"),
            "platform": review.get("platform"),
            "date": review.get("date_iso"),
            "tags": [],
            "rating": review.get("rating"),
            "gallery_n": None,
        })

    # одинаковые файлы
    by_sha = {}
    for row in rows:
        if row.get("sha256"):
            by_sha.setdefault(row["sha256"], []).append(row["file"])
    for row in rows:
        if row.get("sha256"):
            row["same_as"] = [other for other in by_sha[row["sha256"]] if other != row["file"]]

    (OUT / "photo_index.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    columns = ["set", "sheet", "file", "source_record", "venue", "date", "rating", "gallery_n", "tags",
               "width", "height", "bytes", "sha256", "sha_matches_manifest", "same_as"]
    lines = ["\t".join(columns)]
    for row in rows:
        if not row.get("file"):
            continue
        lines.append("\t".join(
            ",".join(value) if isinstance(value, list) else ("" if value is None else str(value))
            for value in (row.get(column) for column in columns)
        ))
    (OUT / "photo_index.tsv").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

    files = [row for row in rows if row.get("file")]
    print("files", len(files), "no-file entries", len(rows) - len(files))
    print("sha mismatches", sum(1 for row in files if not row["sha_matches_manifest"]))
    print("unreadable", sum(1 for row in files if row["width"] is None))
    print("no sheet", [row["file"] for row in files if not row.get("sheet") or row["sheet"].endswith("?")])
    print("review photos with gallery twin", sum(1 for row in files if row["set"] == "yandex-maps" and row["group"] != "gallery" and row.get("gallery_n")))
    print("distinct sha", len(by_sha))


if __name__ == "__main__":
    main()
