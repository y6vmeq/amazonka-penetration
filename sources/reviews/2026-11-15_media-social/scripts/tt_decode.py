"""Раскладывает выгрузку из браузера (scripts/tt_grab.js, tt_grab_multi.js и подобные) по файлам в media/<группа>/.

Запуск:
    python -I scripts/tt_decode.py <папка_сбора> <выгрузка.json> <группа> [--keep]
    python -I scripts/tt_decode.py <папка_сбора> <выгрузка.json> [--keep]     (выгрузка с несколькими группами)
Одна группа:  {"meta": {...}, "files": [{"name", "url", "type", "size", "sha256", "b64"}, ...]}.
Несколько:    {"results": [{"group": "...", "meta": {...}, "files": [...]}, ...], "remaining": [...]}.
Проверяет SHA-256, посчитанный на странице, пишет meta.json, дописывает media/manifest.jsonl.
Содержимое файлов не разбирается и не исполняется. Выгрузка после успеха удаляется.
"""
import base64
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

args = [a for a in sys.argv[1:] if not a.startswith("--")]
keep = "--keep" in sys.argv
collection, dump_path = Path(args[0]), Path(args[1])
single_group = args[2] if len(args) > 2 else None
obj = json.loads(dump_path.read_text(encoding="utf-8"))
if isinstance(obj, str):
    obj = json.loads(obj)


def extension(data):
    if data[4:8] == b"ftyp":
        return ".mp4"
    if data[:3] == b"\xff\xd8\xff":
        return ".jpg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return ".png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ".webp"
    if data[:6] == b"WEBVTT" or data[:9] == b"\xef\xbb\xbfWEBVTT":
        return ".vtt"
    if data[:3] == b"ID3" or data[:2] in (b"\xff\xfb", b"\xff\xf3"):
        return ".mp3"
    if data[:4] == b"\x1aE\xdf\xa3":
        return ".webm"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return ".gif"
    return ".bin"


def ascii_safe(text):
    return str(text).encode("ascii", "replace").decode()


def unpack(result, group, manifest_out):
    ok = True
    group_dir = collection / "media" / group
    group_dir.mkdir(parents=True, exist_ok=True)
    for number, f in enumerate(result["files"], 1):
        entry = {
            "group": group, "n": number, "url": f.get("url"), "file": None, "bytes": 0, "sha256": None,
            "content_type": f.get("type"), "status": f.get("status", 0), "note": "",
            "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "via": "fetch в браузере (chrome-devtools MCP), без входа",
        }
        if "b64" not in f:
            entry["note"] = "не получено: " + "; ".join(f.get("error") or [])[:300]
            print("  NOT SAVED", f["name"], ascii_safe(entry["note"])[:200])
        else:
            data = base64.b64decode(f["b64"])
            digest = hashlib.sha256(data).hexdigest()
            if digest != f["sha256"] or len(data) != f["size"]:
                entry["note"] = f"расхождение SHA-256: на странице {f['sha256']}, на диске {digest}"
                print("  MISMATCH", f["name"])
                ok = False
            else:
                target = group_dir / (f["name"] + extension(data))
                target.write_bytes(data)
                entry.update(file=target.relative_to(collection).as_posix(), bytes=len(data), sha256=digest)
                print("  OK", target.name, len(data), digest)
        manifest_out.write(json.dumps(entry, ensure_ascii=False) + "\n")
    meta = result.get("meta") or {}
    (group_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    if "id" in meta and "video" in meta:
        stats = meta.get("stats") or {}
        print("  META", meta["id"], meta.get("createTimeISO"), "dur", meta["video"].get("duration"),
              "plays", stats.get("playCount"), "comments", stats.get("commentCount"), "images", meta.get("imagePostCount"))
    return ok


manifest = collection / "media" / "manifest.jsonl"
(collection / "media").mkdir(parents=True, exist_ok=True)
all_ok = True
with manifest.open("a", encoding="utf-8", newline="\n") as out:
    if "results" in obj:
        for result in obj["results"]:
            if "error" in result:
                print("PAGE ERROR", ascii_safe(json.dumps(result, ensure_ascii=True))[:400])
                all_ok = False
                continue
            print(result["group"])
            all_ok = unpack(result, result["group"], out) and all_ok
        print("REMAINING", len(obj.get("remaining") or []), ascii_safe(obj.get("remaining")))
    elif "error" in obj:
        print("PAGE ERROR", ascii_safe(json.dumps(obj, ensure_ascii=True))[:600])
        sys.exit(1)
    else:
        print(single_group)
        all_ok = unpack(obj, single_group, out)
if all_ok and not keep:
    dump_path.unlink()
