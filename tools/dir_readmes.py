"""Создаёт и обновляет README.md в папках проекта: описание папки и ссылки на её файлы и подпапки.

Запуск из корня проекта:
    python -I -X utf8 tools/dir_readmes.py            — создать и обновить описания
    python -I -X utf8 tools/dir_readmes.py --check    — только показать, какие описания устарели (код 1)

Тексты описаний — в tools/dir_readmes.json: для конкретной папки (dirs), по имени папки (kinds),
пояснения к файлам (files). Перечень файлов и подпапок программа составляет сама; в него попадают
только файлы, которые хранятся в git (то, что перечислено в .gitignore, не показывается).

README не создаётся в хранилищах сырых копий и медиа (raw, screenshots, media и глубже, а также
frames, sheets, pages): там лежат доказательства, и их перечни (manifest.jsonl) должны сходиться
с диском. Такие папки описываются уровнем выше. Корневой README.md программа не трогает.

Файл, который программа создала сама, начинается с пометки «dir-readme:generated» и при запуске
переписывается целиком. В README, написанном руками (например, authorities/README.md), программа
ведёт только блок между метками «dir-readme:start» и «dir-readme:end».

Названия заведений, исключённых из работы, в описания не попадают: файл с таким именем в перечень
не включается, а готовый текст проверяется фильтром tools/scope_filter.py.
"""
import ast
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parent))
import scope_filter  # noqa: E402  (соседний файл проекта)

ROOT = Path(__file__).resolve().parent.parent
CONFIG = json.loads((Path(__file__).resolve().parent / "dir_readmes.json").read_text(encoding="utf-8"))
STORES = set(CONFIG["stores"])
GENERATED = "<!-- dir-readme:generated — этот файл создаёт tools/dir_readmes.py; описание папки правится в tools/dir_readmes.json -->"
START, END = "<!-- dir-readme:start -->", "<!-- dir-readme:end -->"
MANY = 40
TYPES = {
    ".pdf": "документ PDF", ".docx": "документ Word", ".pptx": "презентация PowerPoint", ".xlsx": "таблица Excel",
    ".jpg": "изображение", ".jpeg": "изображение", ".png": "изображение", ".webp": "изображение", ".gif": "изображение",
    ".mp4": "видео", ".webm": "видео", ".mov": "видео", ".m4a": "звук", ".mp3": "звук", ".wav": "звук",
    ".html": "сохранённая страница", ".json": "данные JSON", ".txt": "текст", ".js": "сохранённый скрипт страницы",
}


def git_files() -> set[str]:
    out = subprocess.run(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
                         cwd=ROOT, capture_output=True, check=True).stdout
    return {path for path in out.decode("utf-8").split("\0") if path and (ROOT / path).is_file()}


def human(size: int) -> str:
    if size >= 1024 * 1024:
        return f"{size / 1024 / 1024:.1f} МБ".replace(".", ",")
    return f"{max(1, round(size / 1024))} КБ"


def clean(text: str, limit: int = 170) -> str:
    text = re.sub(r"\s+", " ", text.replace("**", "").replace("|", "/")).strip()
    text = text.replace("<", "&lt;").replace(">", "&gt;")
    return text if len(text) <= limit else text[:limit - 1].rstrip() + "…"


def capital(text: str) -> str:
    return text[:1].upper() + text[1:]


def first_heading(path: Path) -> str:
    try:
        with path.open(encoding="utf-8", errors="replace") as handle:
            lines = [next(handle, "") for _ in range(40)]
    except OSError:
        return ""
    for line in lines:
        if line.startswith("#"):
            return line.lstrip("#").strip()
    for line in lines:
        stripped = line.strip().lstrip(">").strip()
        if stripped and not stripped.startswith(("<!--", "---", "|")):
            return stripped
    return ""


def script_summary(path: Path) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    if path.suffix == ".py":
        try:
            doc = ast.get_docstring(ast.parse(text)) or ""
        except SyntaxError:
            doc = ""
        if doc:
            return doc.strip().split("\n")[0]
    for line in text.split("\n")[:15]:
        if line.startswith("#") and not line.startswith("#!"):
            return line.lstrip("#").strip()
    return ""


def count_lines(path: Path) -> int:
    with path.open("rb") as handle:
        return sum(1 for line in handle if line.strip())


def describe_file(path: Path) -> str:
    name, suffix, size = path.name, path.suffix.lower(), human(path.stat().st_size)
    note = CONFIG["files"].get(name, "")
    if suffix == ".jsonl":
        return f"{note or 'записи, по одной в строке'}: строк — {count_lines(path)}"
    if note:
        return note
    if suffix == ".md":
        return clean(first_heading(path)) or "текст"
    if suffix in (".py", ".sh", ".ps1"):
        return clean(script_summary(path)) or "скрипт"
    if suffix in (".tsv", ".csv"):
        return f"таблица: строк — {count_lines(path)}"
    return f"{TYPES.get(suffix, 'файл')}, {size}"


def dir_text(rel: str) -> tuple[str, str]:
    name = rel.rsplit("/", 1)[-1]
    entry = CONFIG["dirs"].get(rel) or CONFIG["kinds"].get(name)
    if entry:
        return entry["title"], entry["about"]
    return name, "Вспомогательная подпапка; что в ней лежит, перечислено ниже."


def is_store(rel: str) -> bool:
    return any(part in STORES for part in rel.split("/"))


def link(name: str, folder: bool = False) -> str:
    target = quote(name) + ("/" if folder else "")
    return f"[{name}{'/' if folder else ''}]({target})"


def listing(rel: str, files: set[str], targets: set[str]) -> str:
    base = ROOT / rel
    prefix = rel + "/"
    inside = [path for path in files if path.startswith(prefix)]
    rows, hidden = [], 0
    subdirs = sorted(child.name for child in base.iterdir() if child.is_dir() and child.name not in (".git", "__pycache__"))
    for name in subdirs:
        child = f"{rel}/{name}"
        count = sum(1 for path in inside if path.startswith(child + "/") and not path.endswith("/README.md"))
        if scope_filter.mentions(name):
            hidden += 1
            continue
        if child in targets:
            text = dir_text(child)[0]
            if text == name:
                text = "вспомогательная подпапка"
            label = link(name, folder=True)
        elif name in STORES:
            text = CONFIG["stores"][name]
            label = link(name, folder=True) if count else f"`{name}/`"
        else:
            text = "медиа и производные файлы"
            label = link(name, folder=True) if count else f"`{name}/`"
        rows.append(f"| {label} | {capital(clean(text))} · {'файлов: ' + str(count) if count else 'пока пусто'} |")
    own = sorted(path[len(prefix):] for path in inside if "/" not in path[len(prefix):] and not path.endswith("/README.md"))
    shown = own
    if len(own) > MANY:
        shown = [name for name in own if name in CONFIG["files"] or name.lower().endswith((".md", ".jsonl", ".py", ".sh"))]
    rest = Counter()
    for name in own:
        if scope_filter.mentions(name):
            hidden += 1
            continue
        if name not in shown:
            rest[Path(name).suffix.lower().lstrip(".") or "без расширения"] += 1
            continue
        text = describe_file(base / name)
        if scope_filter.mentions(text):
            text = f"{TYPES.get(Path(name).suffix.lower(), 'файл')}, {human((base / name).stat().st_size)}"
        rows.append(f"| {link(name)} | {capital(clean(text, 220))} |")
    parts = []
    if rows:
        parts.append("| Файл или папка | Что это |\n|---|---|\n" + "\n".join(rows))
    else:
        parts.append("Других файлов в папке пока нет.")
    if rest:
        summary = ", ".join(f"{ext} — {count}" for ext, count in rest.most_common())
        parts.append(f"Ещё файлов: {sum(rest.values())} ({summary}). Они видны в списке файлов папки.")
    if hidden:
        parts.append(f"Не показано файлов и папок: {hidden} (в имени есть название заведения, исключённого из работы).")
    return "\n\n".join(parts)


def footer(rel: str) -> str:
    depth = rel.count("/") + 1
    if depth == 1:
        return "[← Путеводитель по проекту](../README.md)"
    return f"[← Папка выше](../README.md) · [Путеводитель по проекту]({'../' * depth}README.md)"


def build(rel: str, files: set[str], targets: set[str]) -> str:
    path = ROOT / rel / "README.md"
    title, about = dir_text(rel)
    block = f"{START}\n## Что в этой папке\n\n{listing(rel, files, targets)}\n\n{footer(rel)}\n{END}"
    existing = path.read_text(encoding="utf-8") if path.is_file() else ""
    if existing and not existing.startswith(GENERATED):
        if START in existing and END in existing:
            head, rest = existing.split(START, 1)
            tail = rest.split(END, 1)[1]
            return f"{head}{block}{tail}"
        return existing.rstrip("\n") + "\n\n" + block + "\n"
    return f"{GENERATED}\n# {title}\n\n{about}\n\n{block}\n"


def main() -> int:
    check = "--check" in sys.argv[1:]
    files = git_files()
    targets = set()
    for path in ROOT.rglob("*"):
        if not path.is_dir():
            continue
        rel = path.relative_to(ROOT).as_posix()
        if rel.startswith(".git") or "__pycache__" in rel.split("/") or is_store(rel):
            continue
        targets.add(rel)
    created = updated = same = 0
    stale = []
    for rel in sorted(targets):
        text = build(rel, files, targets)
        found = [match.group(0) for match in scope_filter.MENTION.finditer(text)]
        if found:
            sys.exit(f"{rel}/README.md: в тексте есть название заведения, исключённого из работы")
        path = ROOT / rel / "README.md"
        old = path.read_text(encoding="utf-8") if path.is_file() else None
        if old == text:
            same += 1
            continue
        stale.append(rel)
        if check:
            continue
        path.write_text(text, encoding="utf-8", newline="\n")
        if old is None:
            created += 1
        else:
            updated += 1
    if check:
        print(f"описаний папок: {len(targets)}, устарело или отсутствует: {len(stale)}")
        for rel in stale[:40]:
            print("  ", rel)
        return 1 if stale else 0
    print(f"описаний папок: {len(targets)} | создано {created}, обновлено {updated}, без изменений {same}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
