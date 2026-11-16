"""Строит таблицу публикаций из раздела отметок профиля заведения (raw/038) с датами.

Запуск: python -I -X utf8 scripts/tagged_list.py [коды для печати...]

Дата вычисляется из кода публикации (как в scripts/code_date.py): число в коде сдвигается
на 23 бита и прибавляется к началу отсчёта Instagram. Пишет work/ig_tagged_amazonka_restobar_mogilev.tsv.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"


def code_date(code):
    number = 0
    for char in code:
        number = number * 64 + ALPHABET.index(char)
    return datetime.fromtimestamp(((number >> 23) + 1314220021721) / 1000, timezone.utc)


def main():
    raw = json.loads((HERE / "raw" / "038_instagram_amazonka_restobar_mogilev_tagged.json").read_text(encoding="utf-8"))
    rows = []
    for code, kind, caption in raw["items"]:
        # подпись обрезана площадкой по числу знаков: половинку разрезанного эмодзи отбрасываем
        caption = "".join(ch for ch in caption if not 0xD800 <= ord(ch) <= 0xDFFF)
        rows.append((code_date(code), code, "рилс" if kind == "r" else "публикация", caption))
    rows.sort(reverse=True)
    out = HERE / "work" / "ig_tagged_amazonka_restobar_mogilev.tsv"
    lines = ["дата_UTC\tкод\tвид\tадрес\tначало_подписи"]
    for date, code, kind, caption in rows:
        lines.append(f"{date:%Y-%m-%d %H:%M}\t{code}\t{kind}\thttps://www.instagram.com/p/{code}/\t{caption}")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("rows:", len(rows), "| первая:", f"{rows[-1][0]:%Y-%m-%d}", "| последняя:", f"{rows[0][0]:%Y-%m-%d}")
    wanted = set(sys.argv[1:])
    for date, code, kind, caption in rows:
        if code in wanted:
            print(f"{date:%d.%m.%Y}\t{code}\t{kind}")


if __name__ == "__main__":
    main()
