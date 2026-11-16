"""Собирает выписки по санитарным требованиям к объектам общественного питания.

Запуск из корня проекта:
    python -I law/texts/sanitary-obshchepit/_build/build.py

Читает (всё лежит рядом):
    dekret7_sanitary_points.json   — делает extract_dekret7.py из страницы ЭТАЛОН-ONLINE;
    sanpin12_red20_points.json     — делает extract_points.py из PDF редакции № 20;
    sanpin12_v0_points.json        — то же из PDF первоначальной редакции;
    ../../animals-sanitary/quotes.jsonl — уже сверенные цитаты (метки {{aq:id}});
    template_dekret7.md, template_sanpin12.md.
Пишет:
    law/dekret-7-2017_sanitarnye-trebovaniya.md
    law/sanpin-12-2017_obshchepit.md
    law/texts/sanitary-obshchepit/quotes.jsonl   (проверяет tools/quotes_check.py)

Метки в шаблонах:
    {{d7:16}}        пункт 16 Общих требований целиком
    {{d7:40:3-4}}    части (абзацы) 3–4 пункта 40; можно «1,3» или «2-»
    {{d7fn:40:1}}    первая сноска к пункту 40
    {{sp:10}}        СанПиН № 12 в редакции постановления № 20
    {{v0:11}}        СанПиН № 12 в первоначальной редакции
    {{aq:dekret7-p8}}  цитата из law/texts/animals-sanitary/quotes.jsonl
Выделение: {{sp:10|b=изолированы от жилых помещений;;самостоятельные входы}}.
Цитата выводится в кавычках-ёлочках, абзацы — с новой строки.
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FOLDER = HERE.parent
ROOT = FOLDER.parent.parent.parent

SOURCES = {
    "d7": {
        "points": "dekret7_sanitary_points.json",
        "raw_file": "../animals-sanitary/raw/010_etalonline-by_dekret7-etalon.html",
        "act": "Декрет Президента Республики Беларусь от 23.11.2017 № 7 «О развитии предпринимательства», "
               "Общие санитарно-эпидемиологические требования к содержанию и эксплуатации капитальных строений "
               "(зданий, сооружений), изолированных помещений и иных объектов, принадлежащих субъектам хозяйствования",
    },
    "sp": {
        "points": "sanpin12_red20_points.json",
        "raw_file": "../animals-sanitary/raw/063_www-ohrana-truda-by_ohrana-truda-attach1416-sanpin12-red20.pdf",
        "act": "Санитарные нормы и правила «Санитарно-эпидемиологические требования для объектов общественного "
               "питания», утв. постановлением Минздрава от 10.02.2017 № 12, в редакции постановления Минздрава "
               "от 03.03.2017 № 20",
    },
    "v0": {
        "points": "sanpin12_v0_points.json",
        "raw_file": "../animals-sanitary/raw/013_faolex-fao-org_sanpin12-faolex-v0.pdf",
        "act": "Санитарные нормы и правила «Санитарно-эпидемиологические требования для объектов общественного "
               "питания», утв. постановлением Минздрава от 10.02.2017 № 12, первоначальная редакция "
               "(заменена редакцией постановления от 03.03.2017 № 20)",
    },
}
TEMPLATES = {
    "template_dekret7.md": ROOT / "law" / "dekret-7-2017_sanitarnye-trebovaniya.md",
    "template_sanpin12.md": ROOT / "law" / "sanpin-12-2017_obshchepit.md",
}
MARK = re.compile(r"\{\{(d7fn|d7|sp|v0|aq):([^}|]+?)(?:\|b=([^}]*))?\}\}")


def select(items, spec):
    """Выбирает элементы по записи «2», «1,3», «3-4», «2-»; нумерация с единицы."""
    if not spec:
        return list(range(len(items)))
    chosen = []
    for part in spec.split(","):
        if "-" in part:
            first, last = part.split("-")
            chosen.extend(range(int(first) - 1, int(last) if last else len(items)))
        else:
            chosen.append(int(part) - 1)
    if any(index < 0 or index >= len(items) for index in chosen):
        raise SystemExit(f"нет такой части: {spec} (всего {len(items)})")
    return chosen


def label(point, spec, footnote=False):
    if footnote:
        return f"сноска {spec} к п. {point}"
    if not spec:
        return f"п. {point}"
    return f"п. {point}, части (абзацы) {spec.replace('-', '–')}"


def chunks_for_check(paragraphs):
    """Делит цитату на куски, каждый из которых лежит на одной странице сырой копии."""
    chunks, current_page, current = [], None, []
    for paragraph in paragraphs:
        text, pages, breaks = paragraph["text"], paragraph.get("pages") or [0], paragraph.get("breaks") or []
        bounds = [0] + list(breaks) + [len(text)]
        for index, page in enumerate(pages):
            segment = text[bounds[index]:bounds[index + 1]].strip() if index + 1 < len(bounds) else ""
            if not segment:
                continue
            if page != current_page and current:
                chunks.append("\n".join(current))
                current = []
            current_page = page
            current.append(segment)
    if current:
        chunks.append("\n".join(current))
    return chunks


def main():
    points = {key: json.loads((HERE / source["points"]).read_text(encoding="utf-8")) for key, source in SOURCES.items()}
    ready = {}
    for line in (FOLDER.parent / "animals-sanitary" / "quotes.jsonl").read_text(encoding="utf-8-sig").splitlines():
        if line.strip():
            entry = json.loads(line)
            ready[entry["id"]] = entry
    quotes, seen = [], set()

    def add(identifier, act, point, text, raw_file):
        if identifier in seen:
            return
        seen.add(identifier)
        quotes.append({"id": identifier, "act": act, "point": point, "text": text, "raw_file": raw_file})

    def render(match):
        kind, body, bold = match.group(1), match.group(2).strip(), match.group(3)
        if kind == "aq":
            entry = ready.get(body)
            if entry is None:
                raise SystemExit(f"нет цитаты {body} в animals-sanitary/quotes.jsonl")
            text = entry["text"]
            add(f"aq-{body}", entry["act"], entry["point"], text, "../animals-sanitary/" + entry["raw_file"])
        else:
            number, _, spec = body.partition(":")
            source_key = "d7" if kind == "d7fn" else kind
            point = points[source_key].get(number)
            if point is None:
                raise SystemExit(f"нет пункта {number} в {source_key}")
            source = SOURCES[source_key]
            if kind == "d7fn":
                notes = [point["footnotes"][index] for index in select(point["footnotes"], spec)]
                text = "\n".join(notes)
                add(f"d7-p{number}-fn{spec}", source["act"], label(number, spec, footnote=True), text, source["raw_file"])
            else:
                indices = select(point["paragraphs"], spec)
                chosen = [point["paragraphs"][index] for index in indices]
                chosen = [item if isinstance(item, dict) else {"text": item} for item in chosen]
                text = "\n".join(item["text"] for item in chosen)
                # Несмежные абзацы в сырой копии не идут подряд: сверяем каждую группу отдельно.
                pieces, run = [], []
                for position, index in enumerate(indices):
                    if run and index != indices[position - 1] + 1:
                        pieces.extend(chunks_for_check(run))
                        run = []
                    run.append(chosen[position])
                pieces.extend(chunks_for_check(run))
                suffix = f"-{spec.replace(',', '_')}" if spec else ""
                for index, piece in enumerate(pieces, 1):
                    part = f" (кусок {index} из {len(pieces)} для сверки)" if len(pieces) > 1 else ""
                    tail = f"-s{index}" if len(pieces) > 1 else ""
                    add(f"{kind}-p{number}{suffix}{tail}", source["act"], label(number, spec) + part, piece, source["raw_file"])
        if bold:
            for fragment in bold.split(";;"):
                fragment = fragment.strip()
                if fragment not in text:
                    raise SystemExit(f"нет фрагмента для выделения в {match.group(0)[:60]}: {fragment}")
                text = text.replace(fragment, f"**{fragment}**", 1)
        return f"«{text}»"

    for template_name, target in TEMPLATES.items():
        template = (HERE / template_name).read_text(encoding="utf-8")
        result = MARK.sub(render, template)
        left = re.findall(r"\{\{[^}]*\}\}", result)
        if left:
            raise SystemExit(f"{template_name}: не разобраны метки {left[:5]}")
        target.write_text(result, encoding="utf-8", newline="\n")
        print(f"{template_name} -> {target.relative_to(ROOT).as_posix()} ({len(result)} chars)")
    with (FOLDER / "quotes.jsonl").open("w", encoding="utf-8", newline="\n") as output:
        for quote in quotes:
            output.write(json.dumps(quote, ensure_ascii=False) + "\n")
    print(f"quotes={len(quotes)}")


if __name__ == "__main__":
    sys.exit(main())
