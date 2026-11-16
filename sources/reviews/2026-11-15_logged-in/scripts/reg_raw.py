"""Регистрирует сырую копию, записанную из выдачи браузера, и сверяет её с подписью, посчитанной в странице.

Запуск: python -I -X utf8 scripts/reg_raw.py <файл в raw/> <подпись> [<вторая подпись>] [--url адрес]

Страница считает две подписи (функция H.sig): для строки, которую она отдала кусками (знаки вне ASCII,
кроме кириллицы, записаны там как uXXXX с обратной косой чертой), и для той же строки с настоящими
знаками (real=...). Подпись = длина строки в единицах UTF-16 и два 32-битных FNV-1a.
Файл считается верным, если с одной из подписей совпал либо его текст как есть, либо его
каноническая запись (json.dumps без пробелов, ensure_ascii=False) — она равна JSON.stringify страницы.
После сверки файл переписывается в канонической записи (настоящие знаки, UTF-8, без перевода строки),
в raw/manifest.jsonl добавляется строка с адресом, временем, SHA-256 и способом получения.
"""
import hashlib
import json
import sys
from pathlib import Path

METHOD = "текст извлечён из страницы в браузере с входом; это не побайтовая копия страницы"


def fnv(units, seed):
    h = seed & 0xFFFFFFFF
    for u in units:
        h ^= u
        h = (h * 16777619) & 0xFFFFFFFF
    return h


def units_of(text):
    data = text.encode("utf-16-le", "surrogatepass")
    return [int.from_bytes(data[i:i + 2], "little") for i in range(0, len(data), 2)]


def sig(text):
    units = units_of(text)
    return f"{len(units)},{fnv(units, 2166136261)},{fnv(units, 84696351)}"


def main():
    args = sys.argv[1:]
    url = None
    if "--url" in args:
        i = args.index("--url")
        url = args[i + 1]
        del args[i:i + 2]
    path = Path(args[0])
    wanted = set(args[1:])
    text = path.read_text(encoding="utf-8").rstrip("\r\n")
    data = json.loads(text)
    canonical = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    got = {sig(text), sig(canonical)}
    if not (got & wanted):
        print("MISMATCH", "file:", sorted(got), "page:", sorted(wanted))
        sys.exit(1)
    # Одиночные суррогаты (обрезанный посередине эмодзи) в UTF-8 не записать: оставляем их в виде \uXXXX.
    safe = "".join(f"\\u{ord(ch):04x}" if 0xD800 <= ord(ch) <= 0xDFFF else ch for ch in canonical)
    path.write_bytes(safe.encode("utf-8"))
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    line = {
        "file": f"raw/{path.name}",
        "url": url or data.get("url"),
        "fetched_at": data.get("at"),
        "sha256": sha,
        "bytes": path.stat().st_size,
        "page_signature": sorted(got & wanted)[0],
        "method": METHOD,
    }
    manifest = path.parent / "manifest.jsonl"
    old = manifest.read_text(encoding="utf-8").splitlines() if manifest.is_file() else []
    old = [l for l in old if l.strip() and json.loads(l).get("file") != line["file"]]
    old.append(json.dumps(line, ensure_ascii=False))
    manifest.write_text("\n".join(old) + "\n", encoding="utf-8", newline="\n")
    print("OK", path.name, sha[:16], "keys:", ",".join(data.keys()) if isinstance(data, dict) else type(data).__name__)


if __name__ == "__main__":
    main()
