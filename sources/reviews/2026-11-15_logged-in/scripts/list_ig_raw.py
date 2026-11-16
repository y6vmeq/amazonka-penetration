"""Печатает краткий перечень комментариев из сырых копий Instagram (для разметки записей).

Запуск: python -I -X utf8 scripts/list_ig_raw.py <номера сырых копий через пробел>
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent


def main():
    wanted = set(sys.argv[1:])
    for path in sorted((HERE / "raw").glob("*_instagram_*.json")):
        number = path.name.split("_")[0]
        if wanted and number not in wanted:
            continue
        raw = json.loads(path.read_text(encoding="utf-8"))
        post = raw.get("post") or {}
        print(f"== {path.name} | {raw.get('url')} | автор {post.get('user')} {str(post.get('dt'))[:16]} | подпись {len(post.get('text') or '')} зн.")
        for item in raw.get("comments") or []:
            text = (item.get("text") or "").replace("\n", " / ")
            parent = f" ^{item.get('parent')}" if item.get("parent") else ""
            print(f"   {item.get('pk')}{parent} | {item.get('user')} | {str(item.get('dt'))[:16]} | {text[:150]}")


if __name__ == "__main__":
    main()
