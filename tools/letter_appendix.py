"""Собирает приложение к обращению: перечень публикаций с дословными выдержками.

Запуск из корня проекта:
    python -I -X utf8 tools/letter_appendix.py <описание.json> <приложение.md>

Описание — JSON: {"title": "...", "note": "...", "items": [{"id": "yandex-maps-063",
"phrases": ["..."], "field": "text" | "reply", "about": "...", "date": "..."}, ...]}.

Для каждой записи берутся из sources/reviews/ALL.jsonl площадка, дата и адрес публикации.
Необязательное поле "date" заменяет дату в графе «Дата публикации»: оно нужно, когда выдержка взята
из ответа заведения (у ответа своя дата) или когда на странице дата показана относительно
(«год назад»): тогда писать так, как на странице, с датой сбора. Дата записи при этом не меняется.
Каждая выдержка должна дословно содержаться в тексте записи (или в ответе заведения,
если field = "reply"); иначе программа останавливается. Имена авторов в приложение не идут.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path.cwd()
PLATFORMS = {
    "yandex-maps": "Яндекс Карты",
    "google-maps": "Google Карты",
    "threads": "Threads",
    "instagram": "Instagram",
    "mogilev.in": "mogilev.in",
    "mcge.by": "сайт областного центра гигиены",
    "tiktok": "TikTok",
    "telegram": "Telegram",
    "vk": "ВКонтакте",
    "ok": "Одноклассники",
    "youtube": "YouTube",
    "restoplace": "сервис бронирования Restoplace",
    "restoplace.ws": "сервис бронирования Restoplace",
    "mogilev.gov.by": "сайт Могилёвского горисполкома",
    "lenadm-mogilev.gov.by": "сайт администрации Ленинского района г. Могилёва",
    "mzcge.by": "сайт Могилёвского зонального центра гигиены и эпидемиологии",
    "grp.nalog.gov.by": "Государственный реестр плательщиков (сервис МНС)",
    "gastrofest.by": "сайт фестиваля Gastrofest",
}
MONTHS = "января февраля марта апреля мая июня июля августа сентября октября ноября декабря".split()


def norm(text):
    return re.sub(r"\s+", " ", str(text or "")).strip()


def human_date(iso):
    iso = str(iso or "")
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", iso)
    if m:
        return f"{int(m.group(3))} {MONTHS[int(m.group(2)) - 1]} {m.group(1)} г."
    m = re.fullmatch(r"(\d{4})-(\d{2})", iso)
    if m:
        return f"{'январь февраль март апрель май июнь июль август сентябрь октябрь ноябрь декабрь'.split()[int(m.group(2)) - 1]} {m.group(1)} г."
    return iso + " г." if re.fullmatch(r"\d{4}", iso) else iso


def main():
    spec = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    records = {}
    for line in (ROOT / "sources/reviews/ALL.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            record = json.loads(line)
            records[record["id"]] = record
    out = [f"# {spec['title']}", ""]
    if spec.get("note"):
        out += [spec["note"], ""]
    out += [
        "| № | Площадка | Дата публикации | Адрес публикации | Дословная выдержка | О чём | Фото и видео при публикации | Запись в базе |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for number, item in enumerate(spec["items"], 1):
        record = records.get(item["id"])
        if record is None:
            raise SystemExit(f"нет записи {item['id']}")
        source = norm(record.get(item.get("field", "text")))
        for phrase in item["phrases"]:
            if norm(phrase) not in source:
                raise SystemExit(f"{item['id']}: выдержка не найдена дословно: {phrase}")
        quotes = "; ".join("«" + norm(p) + "»" for p in item["phrases"])
        if item.get("field") == "reply":
            quotes = "ответ от имени заведения: " + quotes
        media = record.get("media") or []
        platform = PLATFORMS.get(record.get("platform"), str(record.get("platform")))
        out.append(
            f"| {number} | {platform} | {norm(item.get('date')) or human_date(record.get('date_iso'))} | {record.get('url')} | {quotes} | "
            f"{item.get('about', '')} | {item.get('media_note') or (str(len(media)) if media else '—')} | {item['id']} |"
        )
    out += ["", "Графа «Запись в базе» — внутренняя: перед подачей её убрать. Выдержки перенесены программой из сохранённых копий страниц; орфография авторов сохранена.", ""]
    Path(sys.argv[2]).write_text("\n".join(out), encoding="utf-8", newline="\n")
    print("записано:", sys.argv[2], "строк:", len(spec["items"]))


if __name__ == "__main__":
    main()
