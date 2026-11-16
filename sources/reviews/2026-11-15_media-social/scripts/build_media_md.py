"""Собирает media.md из написанных вручную частей (work/media_part_*.md) и приложения с файлами.

Запуск из корня проекта: python -I <папка_сбора>/scripts/build_media_md.py <папка_сбора>
Приложение строится по media/manifest.jsonl: группа, файл, размер, SHA-256, исходная ссылка.
Попутно пересчитывает SHA-256 каждого файла на диске и сообщает о расхождениях.
"""
import hashlib
import json
import sys
from collections import OrderedDict
from pathlib import Path

collection = Path(sys.argv[1])
manifest_path = collection / "media" / "manifest.jsonl"
entries = [json.loads(line) for line in manifest_path.read_text(encoding="utf-8").splitlines() if line.strip()]

groups = OrderedDict()
failed = []
for entry in entries:
    if entry.get("file"):
        groups.setdefault(entry["group"], []).append(entry)
    else:
        failed.append(entry)

VIDEO = {".mp4", ".webm", ".mov", ".m4a"}
IMAGE = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
problems = []
video_groups, image_count, video_files = set(), 0, 0
for group, items in groups.items():
    for entry in items:
        path = collection / entry["file"]
        if not path.is_file():
            problems.append(f"нет файла: {entry['file']}")
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != entry["sha256"]:
            problems.append(f"SHA-256 не совпал: {entry['file']}")
        suffix = path.suffix.lower()
        if suffix in VIDEO and suffix != ".m4a":
            video_groups.add(group)
            video_files += 1
        elif suffix in IMAGE and path.stem not in ("cover", "poster"):
            image_count += 1

ORDER_PREFIXES = ["tiktok_", "telegram_", "ok_", "youtube_", "facebook_", "vk_", "magilev_", "komkur_", "mogilev-in_", "mycity_",
                  "b4y_", "biznesmarket_", "olo_", "koko_", "biztorg_"]


def order_key(name):
    for index, prefix in enumerate(ORDER_PREFIXES):
        if name.startswith(prefix):
            return (index, name)
    return (len(ORDER_PREFIXES), name)


def short_url(url, limit=110):
    url = url or ""
    return url if len(url) <= limit else url[:limit] + "…"


lines = []
lines.append("# Медиа из публикаций в соцсетях, СМИ и объявлениях: скачано и разобрано (media-social)")
lines.append("")
lines.append("- Дата работы: 15.11.2026, 11:10–12:12 UTC (14:10–15:12 по Минску). Папка: `sources/reviews/2026-11-15_media-social/`.")
lines.append("- Задача: скачать и разобрать фото и видео из находок агентов `social`, `crosslinks`, `media-forums` (у `employer` и `official` в полях `media` пусто). "
             "Яндекс Карты, Google Карты, Threads, Instagram и площадки отзывов разбирают другие агенты.")
lines.append(f"- Итог: {len(video_groups)} видео ({video_files} видеофайлов с вариантами качества) и {image_count} фото; "
             f"{len(groups)} групп в `media/`, {sum(len(v) for v in groups.values())} файлов в `media/manifest.jsonl`.")
lines.append("- Статус сведений: публикации в соцсетях и СМИ; по существу не проверены. Видео и фото показывают то, что в них видно и слышно, "
             "но не доказывают сами по себе нарушение: в обращениях — «просим проверить».")
lines.append("- Правила разбора: людей по лицу не опознавал; имена на бейджах сотрудников и ники отмеченных пользователей не выписывал; "
             "вид животных сам не определял (названия — только из подписей и речи). Расшифровки речи автоматические (faster-whisper large-v3-turbo; "
             "у TikTok — ещё и его собственные субтитры): перед цитированием сверить на слух.")
lines.append("- Цитаты из расшифровок: исправлены только очевидные ошибки распознавания в написании слов (например, «Гастрафест» → «Гастрофест», «Арестобар» → «рестобар»), "
             "пунктуация расставлена по смыслу. Там, где от спорного слова зависит смысл, оставлено написание расшифровки с пометкой. "
             "Дословный вывод программы — в файлах `*.transcript.txt` и `*.vtt`.")
lines.append("- Как устроены папки: `media/<группа>/` — исходные файлы; `frames/` — кадры (`tNNN.Ns.jpg`, имя — секунда ролика) и листы `sheet_*.jpg`; "
             "`sheets/` — обзорные листы; `frames_*/` — плотные кадры отдельных отрезков; `*.transcript.txt` — расшифровка рядом с видео; "
             "`media/_preview/` — уменьшенные копии и склейки для просмотра (производные, не исходники).")
lines.append("- SHA-256 всех исходных файлов — в приложении в конце и в `media/manifest.jsonl`.")
lines.append("")
lines.append("## Самое существенное (подробности — в разделах)")
lines.append("")
summary_path = collection / "work" / "media_part_0_summary.md"
if summary_path.is_file():
    lines.append(summary_path.read_text(encoding="utf-8").strip())
    lines.append("")
for part in sorted((collection / "work").glob("media_part_[1-9]*.md")):
    lines.append(part.read_text(encoding="utf-8").strip())
    lines.append("")
gaps_path = collection / "work" / "media_part_z_gaps.md"
if gaps_path.is_file():
    lines.append(gaps_path.read_text(encoding="utf-8").strip())
    lines.append("")

lines.append("## Приложение. Файлы и SHA-256")
lines.append("")
lines.append("Источник — `media/manifest.jsonl`. Кадры, листы, расшифровки, `meta.json` и `*.info.json` — производные или служебные файлы, в таблицу не входят.")
lines.append("")
for group in sorted(groups, key=order_key):
    lines.append(f"### `media/{group}/`")
    lines.append("")
    lines.append("| Файл | Байт | SHA-256 | Исходная ссылка |")
    lines.append("|---|---|---|---|")
    for entry in sorted(groups[group], key=lambda e: e["file"]):
        name = entry["file"].rsplit("/", 1)[-1]
        lines.append(f"| `{name}` | {entry['bytes']} | `{entry['sha256']}` | {short_url(entry['url'])} |")
    lines.append("")
if failed:
    lines.append("### Не получено (строки манифеста без файла)")
    lines.append("")
    for entry in failed:
        lines.append(f"- `{entry['group']}`: {short_url(entry.get('url') or '', 90)} — {entry.get('note') or entry.get('status')}")
    lines.append("")

(collection / "media.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
print(f"groups={len(groups)} files={sum(len(v) for v in groups.values())} videos={len(video_groups)} video_files={video_files} images={image_count} failed={len(failed)}")
for problem in problems:
    print("PROBLEM", problem.encode("ascii", "replace").decode())
