"""Write screenshots/index.jsonl: one line per screenshot (file, url, captured_at, bytes, sha256, note).

Usage (from project root): python -I <scripts>/build_screenshot_index.py

captured_at is the moment the browser returned the screenshot (UTC), taken from work/shots/_shot_times.json
(collected from the session log), because cropping rewrites the files and their modification time.
"""
import hashlib
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
BASE = Path(__file__).resolve().parent.parent
SHOTS = BASE / "screenshots"
WORK = BASE / "work" / "shots"
RENAMED = {"110_threads_masha_portugal_DfuxGCzjKsE_recheck.png": "recheck_masha_portugal_DfuxGCzjKsE.png"}
PROFILES = {
    "profile_instagram_amazonka_restobar_mogilev.png": "https://www.instagram.com/amazonka_restobar_mogilev/",
    "profile_instagram_smak.by_mogilev.png": "https://www.instagram.com/smak.by_mogilev/",
}
NOTE_ROOT = ("Снимок всей страницы поста с ответами. Обрезан снизу перед блоком «Связанные ветки» "
             "(публикации посторонних авторов, которые подставляет площадка).")
NOTE_REPLY = ("Страница ответа: площадка сама прокручивает её к открытому посту, посты выше него в кадр не попали. "
              "Обрезан снизу перед блоком «Связанные ветки».")
NOTE_PROFILE = "Снимок всей страницы профиля, как она открывается без входа."
NOTE_VIEW = "Вид страницы без входа после закрытия окна с предложением зарегистрироваться (его кнопкой «Закрыть»)."
NOTE_EXPANDED = ("Область подписи и комментариев растянута на всю высоту (изменён только стиль блока, текст не менялся), "
                 "чтобы на одном снимке были вся подпись и все комментарии, которые страница отдаёт без входа. "
                 "Обрезан снизу под карточкой публикации (ниже — «Ещё публикации»).")
NOTE_FIRST = ("Первый снимок: страница закрыта окном «Посмотреть все комментарии», текст почти не читается. "
              "Заменён снимками _view и _comments-expanded.")


def main():
    times = json.loads((WORK / "_shot_times.json").read_text(encoding="utf-8"))
    manifest = {}
    for line in (BASE / "raw" / "manifest.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            e = json.loads(line)
            manifest.setdefault(e["file"].split("/")[-1][:3], e)
    lines = []
    for path in sorted(SHOTS.glob("*.png")):
        name = path.name
        stamp = times.get(name) or times.get(RENAMED.get(name, ""))
        captured = stamp[-1] if stamp else None
        url, note, loaded = None, None, None
        if name in PROFILES:
            url, note = PROFILES[name], NOTE_PROFILE
        elif "_instagram_" in name:
            kind = "expand" if name.endswith("_comments-expanded.png") else "prep" if name.endswith("_view.png") else None
            if kind:
                meta = WORK / (re.sub(r"_(comments-expanded|view)\.png$", "", name) + f"_{kind}.json")
                if meta.is_file():
                    url = json.loads(meta.read_text(encoding="utf-8"))["url"]
                note = NOTE_EXPANDED if kind == "expand" else NOTE_VIEW
                if kind == "expand" and meta.is_file() and not json.loads(meta.read_text(encoding="utf-8")).get("expanded"):
                    note = "Подпись и комментарии помещаются без прокрутки; " + NOTE_VIEW[0].lower() + NOTE_VIEW[1:] + " Обрезан снизу под карточкой публикации."
            else:
                note = NOTE_FIRST
            url = url or manifest.get(name[:3], {}).get("url")
        else:
            meta = WORK / (path.stem + ".json")
            entry = manifest.get(name[:3], {})
            if meta.is_file():
                url, note = json.loads(meta.read_text(encoding="utf-8"))["url"], NOTE_REPLY
                if path.stem[:3] in ("051", "053", "055"):  # these pages are root posts
                    note = NOTE_ROOT
            else:
                url = entry.get("url")
                note = NOTE_PROFILE if "_profile_" in name else NOTE_ROOT
                if name.endswith("_recheck.png"):
                    loaded = entry.get("fetched_at")
        data = path.read_bytes()
        item = {"file": f"screenshots/{name}", "url": url, "captured_at": captured, "bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(), "note": note}
        if loaded:
            item["page_loaded_at"] = loaded
        lines.append(item)
        if not url or not captured:
            print("  ! incomplete:", name, url, captured)
    with open(SHOTS / "index.jsonl", "w", encoding="utf-8", newline="\n") as f:
        for item in lines:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    print(f"screenshots/index.jsonl: {len(lines)} files")


if __name__ == "__main__":
    main()
