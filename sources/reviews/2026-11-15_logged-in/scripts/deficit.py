"""Сравнивает счётчики ответов, показанные страницей, с числом уже известных прямых ответов.

Запуск: python -I -X utf8 scripts/deficit.py <raw-файл> [<raw-файл> ...]
Известное = прежний проход (work/prev_children.json) + новые посты из всех raw/*.json этого прохода
(родитель нового поста берётся из work/parents.json, который ведётся вручную).
"""
import json
import sys
from pathlib import Path

here = Path(__file__).resolve().parent.parent
prev = json.loads((here / "work" / "prev_children.json").read_text(encoding="utf-8"))
children = {k: list(v) for k, v in prev["children"].items()}
parents_file = here / "work" / "parents.json"
parents = json.loads(parents_file.read_text(encoding="utf-8")) if parents_file.is_file() else {}
for child, parent in parents.items():
    children.setdefault(parent, [])
    if child not in children[parent]:
        children[parent].append(child)

for name in sys.argv[1:]:
    data = json.loads(Path(name).read_text(encoding="utf-8"))
    print("==", name, "seen", len(data["seen"]), "fresh", len(data["fresh"]))
    for n, row in enumerate(data["seen"]):
        user, code, likes, replies = row.split(" ")
        if replies in ("null", ""):
            continue
        dom = int(replies.replace(" ", "").replace(" ", "")) if replies.isdigit() else None
        have = len(children.get(code, []))
        if n == 0:
            print(f"   root {user} {code}: counter {replies} (considered separately)")
            continue
        if dom is not None and dom != have:
            print(f"   DEFICIT {user} {code}: page shows {dom}, known direct children {have}")
