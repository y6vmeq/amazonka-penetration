"""Собирает quotes.jsonl и law/animals-sanitary.md из спецификаций.

Запуск: python -I build.py <корень проекта>
Рядом лежат: specs/*.json (цитаты) и template.md (текст с метками {{q:id}}).

Запись спецификации:
  id, act, point, raw_file (относительно law/texts/animals-sanitary),
  либо start + end (цитата вырезается из текста сырой копии между ними, включительно),
  либо text (цитата задана вручную, для PDF с разорванными словами);
  after — необязательный якорь: поиск start начинается после него;
  bold — необязательный список фрагментов, которые в md выделяются полужирным.
"""
import html
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = Path(sys.argv[1])
FOLDER = ROOT / "law" / "texts" / "animals-sanitary"


def plain(path):
    data = path.read_bytes()
    for enc in ("utf-8-sig", "cp1251"):
        try:
            text = data.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        text = data.decode("utf-8", errors="replace")
    if path.suffix.lower() in (".html", ".htm"):
        text = re.sub(r"(?is)<(script|style|noscript)\b.*?</\1>", " ", text)
        text = re.sub(r"(?i)<br\s*/?>", "\n", text)
        text = re.sub(r"(?i)</(p|div|tr|li|h\d|table)>", "\n", text)
        text = re.sub(r"(?i)</(td|th)>", " ", text)
        text = re.sub(r"<[^>]*>", "", text)
        text = html.unescape(text)
    text = text.replace("\xa0", " ").replace("\u200b", "")
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def squeeze(text):
    return re.sub(r"\s+", " ", text).strip()


def find(text, needle, start=0):
    """Позиция needle в text без учёта различий в пробельных символах."""
    pattern = r"\s+".join(re.escape(part) for part in needle.split())
    match = re.compile(pattern).search(text, start)
    return (match.start(), match.end()) if match else (-1, -1)


def main():
    cache, quotes, errors = {}, {}, []
    for spec_file in sorted((HERE / "specs").glob("*.json")):
        for item in json.loads(spec_file.read_text(encoding="utf-8")):
            raw = FOLDER / item["raw_file"]
            if "text" in item:
                body = item["text"]
            else:
                source = raw.with_suffix(".txt") if raw.suffix.lower() == ".pdf" else raw
                if source not in cache:
                    cache[source] = plain(source)
                text = cache[source]
                offset = 0
                if item.get("after"):
                    _, offset = find(text, item["after"])
                    if offset < 0:
                        errors.append(f"{item['id']}: якорь after не найден")
                        continue
                begin, begin_end = find(text, item["start"], offset)
                if begin < 0:
                    errors.append(f"{item['id']}: start не найден")
                    continue
                if item.get("end"):
                    _, finish = find(text, item["end"], begin if item["end"] != item["start"] else begin_end)
                    if finish < 0:
                        errors.append(f"{item['id']}: end не найден")
                        continue
                else:
                    finish = begin_end
                body = text[begin:finish]
                if len(body) > item.get("max", 6000):
                    errors.append(f"{item['id']}: цитата слишком длинная ({len(body)} зн.) — проверь end")
                    continue
            if item["id"] in quotes:
                errors.append(f"{item['id']}: повтор id")
            quotes[item["id"]] = (item, body)

    with (FOLDER / "quotes.jsonl").open("w", encoding="utf-8", newline="\n") as out:
        for item, body in quotes.values():
            out.write(json.dumps({
                "id": item["id"], "act": item["act"], "point": item["point"],
                "text": squeeze(body), "raw_file": item["raw_file"],
            }, ensure_ascii=False) + "\n")

    template = (HERE / "template.md").read_text(encoding="utf-8")
    used = set()

    def render(match):
        key = match.group(1)
        if key not in quotes:
            errors.append(f"в шаблоне метка {key}, а цитаты нет")
            return f"[НЕТ ЦИТАТЫ {key}]"
        used.add(key)
        item, body = quotes[key]
        joiner = " " if item.get("inline") else "\n"
        body = joiner.join(line.strip() for line in body.strip().splitlines() if line.strip())
        for fragment in item.get("bold", []):
            if fragment in body:
                body = body.replace(fragment, f"**{fragment}**")
            else:
                errors.append(f"{key}: фрагмент для выделения не найден: {fragment[:40]}")
        return f"«{body}»"

    result = re.sub(r"\{\{q:([A-Za-z0-9_.\-]+)\}\}", render, template)
    (ROOT / "law" / "animals-sanitary.md").write_text(result, encoding="utf-8", newline="\n")
    unused = [key for key in quotes if key not in used]
    report = [f"quotes={len(quotes)} used_in_md={len(used)} unused={len(unused)} errors={len(errors)}"]
    report += [f"UNUSED {key}" for key in unused] + [f"ERROR {line}" for line in errors]
    (HERE / "build_report.txt").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(report[0])


if __name__ == "__main__":
    main()
