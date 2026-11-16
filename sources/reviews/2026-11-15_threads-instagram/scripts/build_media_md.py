"""Build media.md and work/media_index.json from the download log, video facts and hand-written notes.

Usage (from project root): python -I <scripts>/build_media_md.py
Inputs: work/media_log.jsonl, work/video_info.json, work/media_notes_*.json, work/media_extra_sections.md (optional)
SHA-256 and paths are never typed by hand: they come from the log written at download time.
"""
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
BASE = Path(__file__).resolve().parent.parent
WORK = BASE / "work"
MINSK = timezone(timedelta(hours=3))

# media collected on 14.11.2026 (outside this folder), referenced but not downloaded again
EARLIER = {
    "DfsDkxTESCq": [
        "sources/threads/media/2026-11-13_gurbamladshiy_DfsDkxTESCq/2026-11-13_gurbamladshiy_DfsDkxTESCq_video1.mp4 (скачано 14.11.2026, SHA-256 b18d4a8e0d1f90f4b13b5e725b015733e6a475d79c1570064654a1c61cd59e45; путь от корня проекта)",
        "sources/threads/media/2026-11-13_gurbamladshiy_DfsDkxTESCq/2026-11-13_gurbamladshiy_DfsDkxTESCq_video2.mp4 (скачано 14.11.2026, SHA-256 b642ed79172ef4a3c5979aa43d1727cb54b5bc0346459d40847e74485b444dd9; путь от корня проекта)",
    ],
    "DfsH9uSDGQm": [
        "sources/threads/media/2026-11-13_gurbamladshiy_DfsDkxTESCq/2026-11-13_gurbamladshiy_DfsDkxTESCq_reply_2026-11-13T170542Z.mp4 (скачано 14.11.2026, SHA-256 a11b0415ab6553701158dddea173d645663a7b4c16d366e38550ac615ef65896; путь от корня проекта)",
    ],
}
# media that belong to a text-less reply are attached to the record of the post they illustrate
ATTACH = {"DfrmeALEf45": "DfrlrgykfGf"}


def minsk(iso):
    if not iso:
        return ""
    if isinstance(iso, (int, float)):
        dt = datetime.fromtimestamp(iso, timezone.utc)
    else:
        dt = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
    return dt.astimezone(MINSK).strftime("%d.%m.%Y %H:%M")


def main():
    log = [json.loads(l) for l in (WORK / "media_log.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    info = json.loads((WORK / "video_info.json").read_text(encoding="utf-8")) if (WORK / "video_info.json").is_file() else {}
    notes = {}
    for f in sorted(WORK.glob("media_notes_*.json")):
        notes.update(json.loads(f.read_text(encoding="utf-8")))

    index = {}
    groups = {}
    for e in log:
        groups.setdefault((e["platform"], e["code"]), []).append(e)
        code = ATTACH.get(e["code"], e["code"])
        if e["platform"] == "instagram":
            code = "ig:" + code
        index.setdefault(code, []).append(f"{e['file']} (SHA-256 {e['sha256']}; источник: {e['post_url']})")
    for code, items in EARLIER.items():
        index[code] = items + index.get(code, [])
    (WORK / "media_index.json").write_text(json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")

    n_video = sum(1 for e in log if e["kind"] == "video")
    n_image = sum(1 for e in log if e["kind"] != "video")
    out = [
        "# Медиа: threads-instagram (сбор 15.11.2026)",
        "",
        f"Скачано и разобрано в этом сборе: видео — {n_video}, изображений — {n_image}. "
        "Файлы получены в браузере без входа в аккаунты: запрос к адресу файла, который указан в данных самой страницы; "
        "SHA-256 посчитан в браузере до сохранения и ещё раз после записи на диск — значения совпали (иначе файл не сохраняется).",
        "",
        "- Расшифровка звука: `tools/transcribe.py` (faster-whisper large-v3-turbo), файлы `*.transcript.txt` рядом с видео. "
        "Расшифровка автоматическая: перед цитированием сверить на слух.",
        "- Кадры: `tools/video_frames.py`, папки `frames/`; обзорные листы — `sheets/` (`sheet_*` — по 8 кадров, `overview_*` — 12 кадров на одном листе).",
        "- Людей в кадре я не опознавал. Вид насекомых и животных по снимкам не определял: записано только то, что видно, и то, как это названо в подписи.",
        "- Время публикации — по Минску.",
        "",
    ]
    extra_top = WORK / "media_extra_top.md"
    if extra_top.is_file():
        out += [extra_top.read_text(encoding="utf-8").rstrip(), ""]

    order = sorted(groups, key=lambda k: (k[0] != "threads", min(str(e.get("published") or "") for e in groups[k]), k[1]))
    current_platform = None
    for platform, code in order:
        items = groups[(platform, code)]
        if platform != current_platform:
            out += [f"## {'Threads' if platform == 'threads' else 'Instagram'}", ""]
            current_platform = platform
        first = items[0]
        out += [f"### @{first['author']} — {first['post_url']}", "", f"Опубликовано: {minsk(first.get('published'))}. Автор: @{first['author']}.", ""]
        for e in items:
            note = notes.get(e["key"], {})
            vi = info.get(e["file"])
            facts = f"{e['bytes']} байт"
            if vi:
                facts += f", {vi['width']}×{vi['height']}, {vi['duration']:.1f} с, звук {'есть' if vi['audio'] else 'нет'}"
            out += [
                f"**`{e['file']}`**",
                "",
                f"- SHA-256: `{e['sha256']}`",
                f"- Что это: {note.get('what', e['kind'])}; {facts}.",
                f"- Описание: {note.get('desc', '(описание не внесено)')}",
            ]
            if note.get("text"):
                out.append(f"- Текст в кадре: {note['text']}")
            if note.get("speech"):
                out.append("- Звук: " + " ".join(note["speech"]))
            if note.get("seats"):
                out.append(f"- Столы и места: {note['seats']}")
            if note.get("animals"):
                out.append(f"- Животные: {note['animals']}")
            if vi and vi.get("sheets"):
                out.append("- Обзорные листы: " + ", ".join(f"`{s}`" for s in vi["sheets"][:4]) + (" …" if len(vi["sheets"]) > 4 else ""))
            if e["kind"] == "video":
                tr = (BASE / e["file"]).with_suffix(".transcript.txt")
                if tr.is_file():
                    out.append(f"- Расшифровка: `{tr.relative_to(BASE).as_posix()}`")
            out.append("")
    extra = WORK / "media_extra_sections.md"
    if extra.is_file():
        out += [extra.read_text(encoding="utf-8").rstrip(), ""]
    (BASE / "media.md").write_text("\n".join(out), encoding="utf-8", newline="\n")
    missing = [e["key"] for e in log if e["key"] not in notes]
    print(f"media.md: {len(log)} files ({n_video} video, {n_image} images); without notes: {len(missing)}")
    for m in missing:
        print("   no notes:", m)


if __name__ == "__main__":
    main()
