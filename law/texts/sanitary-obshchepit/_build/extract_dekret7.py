"""Разбирает на пункты «Общие санитарно-эпидемиологические требования…» (Декрет № 7).

Запуск из корня проекта:
    python -I law/texts/sanitary-obshchepit/_build/extract_dekret7.py <страница_эталон.html> <out.json>

Результат: {"<номер>": {"paragraphs": [...], "footnotes": [...]}, "_chapters": {...}}.
Знаки сносок (<sup>3</sup>) записываются надстрочными цифрами: при сверке они
приравниваются к обычным (NFKC).
"""
import html
import json
import re
import sys
from pathlib import Path

SUPERSCRIPT = str.maketrans("0123456789–", "⁰¹²³⁴⁵⁶⁷⁸⁹–")
START = "Общие санитарно-эпидемиологические требования к содержанию и эксплуатации"
END = "Общие требования в области охраны окружающей среды к содержанию и эксплуатации"


def clean(fragment):
    fragment = re.sub(r"(?is)<sup[^>]*>(.*?)</sup>", lambda m: html.unescape(re.sub(r"<[^>]*>", "", m.group(1))).strip().translate(SUPERSCRIPT), fragment)
    fragment = re.sub(r"(?i)<br\s*/?>", " ", fragment)
    fragment = html.unescape(re.sub(r"<[^>]*>", "", fragment)).replace("\xa0", " ")
    return re.sub(r"\s+", " ", fragment).strip()


def main():
    source, target = sys.argv[1], sys.argv[2]
    text = Path(source).read_bytes().decode("utf-8-sig")
    paragraphs = [(match.group(1), clean(match.group(2))) for match in re.finditer(r'(?is)<p\b([^>]*)>(.*?)</p>', text)]
    start = next(i for i, (_, body) in enumerate(paragraphs) if body.startswith(START))
    end = next(i for i, (_, body) in enumerate(paragraphs) if body.startswith(END))
    points, chapters, current, expected, chapter = {}, {}, None, 1, None
    for attributes, body in paragraphs[start + 1:end]:
        if not body or set(body) == {"_"}:
            continue
        if body.startswith("ГЛАВА "):
            chapter = body
            chapters[chapter] = {"first_point": expected}
            current = None
            continue
        if body in ("УТВЕРЖДЕНО",) or body.startswith(("Декрет Президента", "Республики Беларусь", "23.11.2017")):
            continue
        if "snoski" in attributes:
            if current is not None:
                points[str(current)]["footnotes"].append(body)
            continue
        if re.match(rf"^{expected}\. ", body):
            current = expected
            points[str(current)] = {"paragraphs": [], "footnotes": [], "chapter": chapter}
            expected += 1
        if current is not None:
            points[str(current)]["paragraphs"].append(body)
    points["_chapters"] = chapters
    Path(target).write_text(json.dumps(points, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    print(f"points={len(points) - 1} chapters={len(chapters)}")
    for name, info in chapters.items():
        print(" ", info["first_point"], name[:150])


if __name__ == "__main__":
    main()
