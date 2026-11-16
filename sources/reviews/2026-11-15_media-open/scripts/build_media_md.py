"""Собирает media.md из журнала файлов, данных страниц и заметок.

Запуск из корня проекта:
    python -I -X utf8 sources/reviews/2026-11-15_media-open/scripts/build_media_md.py

Берёт: media/manifest.jsonl (пути, размеры, SHA-256), work/pages/*.json (автор, подпись, время),
work/video_info.json (размер кадра, длительность), work/notes_*.json (что видно и слышно —
заметки, написанные после просмотра), work/intro.md и work/media_tail.md (вступление и сводки).
Пути, суммы и подписи подставляет программа — вручную они не набираются.
"""
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from PIL import Image

BASE = Path(__file__).resolve().parent.parent
WORK = BASE / "work"
MINSK = timezone(timedelta(hours=3))
PLATFORM = {"instagram": "Instagram", "threads": "Threads"}


EXTRA_NICKS = ["smak.by_mogilev", "the_diaanaa", "amazonka_restobar_minsk"]


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def protect_nicks(text, nicks):
    """Берёт ники с подчёркиваниями в обратные кавычки, иначе Markdown примет их за выделение.

    Не трогает блоки ``` и то, что уже стоит в обратных кавычках, в адресах и в путях.
    """
    result, fenced_block = [], False
    for line in text.split("\n"):
        if line.startswith("```"):
            fenced_block = not fenced_block
            result.append(line)
            continue
        if not fenced_block:
            parts = line.split("`")
            for index in range(0, len(parts), 2):  # чётные части — вне обратных кавычек
                for nick in nicks:
                    pattern = r"(?<![\w@/.\x00])" + re.escape(nick) + r"(?![\w/\x00])"
                    parts[index] = re.sub(pattern, "\x00" + nick + "\x00", parts[index])
            line = "`".join(parts).replace("\x00", "`")
        result.append(line)
    return "\n".join(result)


def fenced(text):
    text = (text or "").strip()
    if not text:
        return "(подписи нет)"
    return "```text\n" + text.replace("```", "'''") + "\n```"


def image_size(path):
    try:
        with Image.open(path) as image:
            return f"{image.width}×{image.height}"
    except OSError:
        return "?"


def published(page, extra_pages, note):
    """Возвращает (строка времени по Минску, откуда время)."""
    meta = page.get("meta") or {}
    if note.get("taken_at_override"):
        stamp, source = note["taken_at_override"], "из данных обычной страницы публикации"
    elif meta.get("taken_at"):
        stamp, source = meta["taken_at"], "из данных страницы"
    else:
        stamp, source = None, ""
        for other in extra_pages:
            if (other.get("meta") or {}).get("taken_at"):
                stamp, source = other["meta"]["taken_at"], "из данных обычной страницы публикации"
                break
    if stamp:
        moment = datetime.fromtimestamp(int(stamp), timezone.utc).astimezone(MINSK)
        return moment.strftime("%d.%m.%Y %H:%M"), source
    if page.get("published_utc"):
        moment = datetime.fromisoformat(page["published_utc"]).astimezone(MINSK)
        return moment.strftime("%d.%m.%Y %H:%M"), "по списку агента logged-in, с точностью до минут"
    return "не установлено", ""


def main():
    notes = {}
    for path in sorted(WORK.glob("notes_*.json")):
        notes.update(load_json(path))
    video_info = load_json(WORK / "video_info.json")
    files_by_group = {}
    for line in (BASE / "media" / "manifest.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            entry = json.loads(line)
            files_by_group.setdefault(entry["group"], []).append(entry)

    pages = {}
    extra = {}
    for path in sorted((WORK / "pages").glob("*.json")):
        page = load_json(path)
        code = (page.get("meta") or {}).get("code")
        key = f"{page.get('platform')}:{code}"
        stem_tail = path.stem.split(code or "\0")[-1]
        if stem_tail:  # файлы с добавкой (_page, _pagecheck) — повторные заходы
            extra.setdefault(key, []).append(page)
        else:
            pages[key] = page

    out = [(WORK / "intro.md").read_text(encoding="utf-8").rstrip(), ""]
    section = None
    number = 0
    described = set()
    for key, note in notes.items():
        page = pages.get(key)
        if not page:
            raise SystemExit(f"no page data for {key}")
        meta = page.get("meta") or {}
        group = page.get("group")
        entries = list(files_by_group.get(group, []))
        if not entries:
            raise SystemExit(f"no files for {key}")
        described.add(group)
        if note["section"] != section:
            section = note["section"]
            out += [f"## {section}", ""]
        number += 1
        platform, code = key.split(":", 1)
        when, when_source = published(page, extra.get(key, []), note)
        out.append(f"### {number}. `@{meta.get('owner')}` — {page.get('post_url')}")
        out.append("")
        out.append(f"- Площадка: {PLATFORM.get(platform, platform)}. Код публикации: `{code}`.")
        out.append(f"- Опубликовано: {when} по Минску" + (f" ({when_source})." if when_source else "."))
        out.append(f"- Что это: {note['kind']}.")
        out.append("- Подпись к публикации (дословно):")
        out.append("")
        out.append(fenced(note.get("caption_override") or meta.get("caption")))
        out.append("")
        out.append("| Файл | Вид | Кадр | Длительность | Байт | SHA-256 |")
        out.append("|---|---|---|---|---|---|")
        transcripts = []
        for entry in entries:
            rel = entry["file"]
            path = BASE / rel
            if rel.endswith(".mp4"):
                info = video_info.get(rel, {})
                size = f"{info.get('width', '?')}×{info.get('height', '?')}"
                duration = f"{info.get('duration', '?')} с; звук {'есть' if info.get('audio') else 'нет'}"
                kind = "видео"
                transcript = path.with_suffix("").as_posix() + ".transcript.txt"
                if Path(transcript).is_file():
                    transcripts.append(Path(transcript).relative_to(BASE).as_posix())
            else:
                size, duration, kind = image_size(path), "—", "фото"
            out.append(f"| `{rel}` | {kind} | {size} | {duration} | {entry['bytes']} | `{entry['sha256']}` |")
        out.append("")
        out.append(f"Скачано: {entries[0]['fetched_at']} (UTC)." + (
            f" Ещё один заход: {entries[-1]['fetched_at']}." if entries[-1]["fetched_at"][:16] != entries[0]["fetched_at"][:16]
            and len({e['page'] for e in entries}) > 1 else ""))
        out.append("")
        per_file = note.get("files") or {}
        if per_file:
            out.append("Что на файлах:")
            out.append("")
            for name, text in per_file.items():
                label = name.replace("img", "фото ").replace("video", "видео ")
                out.append(f"- **{label}:** {text}")
            out.append("")
        if note.get("desc"):
            out.append("Что видно:")
            out.append("")
            out += [f"- {line}" for line in note["desc"]]
            out.append("")
        out.append(f"- **Текст в кадре (дословно):** {note.get('text', 'не выписывался')}")
        if note.get("speech"):
            out.append(f"- **Звук:** {note['speech']}")
        if transcripts:
            out.append("- **Расшифровка (автоматическая, сверять на слух):** " + ", ".join(f"`{t}`" for t in transcripts))
        if note.get("animals"):
            out.append(f"- **Животные, дети, кальяны:** {note['animals']}")
        for line in note.get("extra") or []:
            out.append(f"- **Примечание:** {line}")
        sheets_dir = BASE / "media" / group / "sheets"
        if sheets_dir.is_dir():
            sheets = sorted(p.name for p in sheets_dir.glob("*.jpg"))
            if sheets:
                out.append(f"- **Обзорные листы:** `media/{group}/sheets/` — " + ", ".join(f"`{s}`" for s in sheets))
        out.append("")

    missing = sorted(set(files_by_group) - described)
    if missing:
        raise SystemExit(f"groups without notes: {missing}")
    out += [(WORK / "media_tail.md").read_text(encoding="utf-8").rstrip(), ""]
    nicks = {(page.get("meta") or {}).get("owner") for page in pages.values()} | set(EXTRA_NICKS)
    text = protect_nicks("\n".join(out), sorted((n for n in nicks if n and "_" in n), key=len, reverse=True))
    (BASE / "media.md").write_text(text, encoding="utf-8", newline="\n")
    videos = sum(1 for entries in files_by_group.values() for e in entries if e["file"].endswith(".mp4"))
    images = sum(len(entries) for entries in files_by_group.values()) - videos
    print(f"publications={number} videos={videos} images={images} -> media.md")


if __name__ == "__main__":
    main()
