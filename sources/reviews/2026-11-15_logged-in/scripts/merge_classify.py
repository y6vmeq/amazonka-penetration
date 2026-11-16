"""Дописывает элементы из файла-части в work/classify.json и готовит stories.jsonl.

Запуск: python -I -X utf8 scripts/merge_classify.py work/classify_part_02.json

Элемент с номером, который уже есть в classify.json, заменяет прежний (чтобы часть можно было
исправить и влить повторно). stories.jsonl в корне папки сбора — копия work/stories.jsonl:
по одной строке на элемент истории или подборки.
"""
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent


def main():
    path = HERE / "work" / "classify.json"
    spec = json.loads(path.read_text(encoding="utf-8"))
    part = json.loads((HERE / sys.argv[1]).read_text(encoding="utf-8"))
    ids = [e["id"] for e in part]
    if len(ids) != len(set(ids)):
        raise SystemExit("в части повторяются номера")
    replaced = {e["id"] for e in part} & {e["id"] for e in spec}
    spec = [e for e in spec if e["id"] not in replaced] + part
    spec.sort(key=lambda e: e["id"])
    path.write_text("[\n" + ",\n".join(" " + json.dumps(e, ensure_ascii=False) for e in spec) + "\n]\n",
                    encoding="utf-8", newline="\n")
    shutil.copyfile(HERE / "work" / "stories.jsonl", HERE / "stories.jsonl")
    print("entries:", len(spec), "added:", len(part) - len(replaced), "replaced:", len(replaced))


if __name__ == "__main__":
    main()
