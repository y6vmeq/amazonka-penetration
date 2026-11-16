"""Собирает адрес запроса к справочному интерфейсу CDX веб-архива (только чтение перечня копий).

Запуск:
    python -I -X utf8 sources/official/2026-11-15_cge-lists/scripts/cdx_url.py <url-шаблон> [domain|prefix|exact] [слово в адресе] [доп. параметры k=v ...]

Печатает одну строку — адрес запроса. Слово в адресе (кириллица) превращается в фильтр по
urlkey: в ключе адреса процентные коды записаны строчными буквами.
"""
import sys
from urllib.parse import quote


def main():
    target = sys.argv[1]
    match_type = sys.argv[2] if len(sys.argv) > 2 else "prefix"
    word = sys.argv[3] if len(sys.argv) > 3 else ""
    extra = sys.argv[4:]
    parts = [
        "url=" + quote(target, safe="/:*.-_"),
        "output=json",
        "fl=original,timestamp,statuscode,mimetype,length",
        "collapse=urlkey",
        "filter=statuscode:200",
    ]
    # Звёздочка в конце шаблона сама задаёт поиск по началу адреса; вместе с matchType
    # интерфейс понимает её буквально и ничего не находит (проверено 15.11.2026: пустой ответ).
    if match_type != "exact" and not target.endswith("*"):
        parts.insert(1, "matchType=" + match_type)
    if word and word != "-":
        encoded = quote(word, safe="-_.~").lower()           # %d0%b8...
        pattern = ".*" + encoded + ".*"
        parts.append("filter=urlkey:" + quote(pattern, safe="-_.~*"))
    parts.extend(extra or ["limit=5000"])
    print("http://web.archive.org/cdx/search/cdx?" + "&".join(parts))


if __name__ == "__main__":
    main()
