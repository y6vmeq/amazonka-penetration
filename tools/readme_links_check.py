"""Проверяет ссылки в путеводителе по проекту, журнале изменений и описаниях папок.

Запуск из корня проекта:
    python -I -X utf8 tools/readme_links_check.py            — корневой README.md
    python -I -X utf8 tools/readme_links_check.py --all      — README.md всех папок и CHANGELOG.md
    python -I -X utf8 tools/readme_links_check.py <файл.md>  — один файл

Каждая относительная ссылка должна вести на существующий файл или папку, ссылка вида #заголовок —
на заголовок в том же файле. Ссылка на пустую папку считается ошибкой: git пустые папки не хранит,
на GitHub она не откроется. Заодно текст проверяется фильтром tools/scope_filter.py: названий
заведений, исключённых из работы, в этих файлах быть не должно. Код возврата 1, если есть ошибки.
"""
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote

sys.path.insert(0, str(Path(__file__).resolve().parent))
import scope_filter  # noqa: E402  (соседний файл проекта)

ROOT = Path(__file__).resolve().parent.parent


def check(path: Path, quiet: bool = False) -> int:
    text = path.read_text(encoding="utf-8")
    base = path.resolve().parent
    links = re.findall(r"\]\(([^)\s]+)\)", text)
    headings = [line.lstrip("#").strip() for line in text.split("\n") if line.startswith("#")]
    anchors = {re.sub(r"[^\w\- ]", "", heading.lower()).replace(" ", "-") for heading in headings}
    bad, checked = [], 0
    for link in links:
        if link.startswith(("http://", "https://", "mailto:")):
            continue
        checked += 1
        if link.startswith("#"):
            if unquote(link[1:]) not in anchors:
                bad.append((link, "нет такого заголовка"))
            continue
        target = base / unquote(link.split("#", 1)[0])
        if not target.exists():
            bad.append((link, "нет файла или папки"))
        elif link.endswith("/") and not target.is_dir():
            bad.append((link, "ожидалась папка"))
        elif target.is_dir() and not any(target.iterdir()):
            bad.append((link, "папка пустая: git её не хранит, на GitHub ссылка не откроется"))
    mentions = [match.group(0) for match in scope_filter.MENTION.finditer(text)]
    name = path.resolve().relative_to(ROOT).as_posix()
    if not quiet or bad or mentions:
        print(f"{name}: ссылок {len(links)}, проверено относительных {checked}, ошибок {len(bad)}, совпадений фильтра {len(mentions)}")
        for link, reason in bad:
            print(f"  {reason}: {link}")
    return len(bad) + len(mentions)


def main() -> int:
    args = sys.argv[1:]
    if args == ["--all"]:
        out = subprocess.run(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
                             cwd=ROOT, capture_output=True, check=True).stdout.decode("utf-8")
        names = sorted(name for name in out.split("\0")
                       if name and (name.endswith("README.md") or name == "CHANGELOG.md") and (ROOT / name).is_file())
        problems = sum(check(ROOT / name, quiet=True) for name in names)
        print(f"проверено файлов: {len(names)}, ошибок: {problems}")
        return 1 if problems else 0
    path = Path(args[0]) if args else ROOT / "README.md"
    return 1 if check(path) else 0


if __name__ == "__main__":
    sys.exit(main())
