"""Общие функции для сборки выписок из сохранённых текстов актов.

Используется скриптами build_ukaz227.py и build_razresheniya.py из этой же папки.
Цитаты не набираются вручную: скрипт находит абзац в сохранённой копии по его началу
и переносит текст в выписку. Если абзац не найден или найден не один раз, сборка
останавливается.

Сохранённые страницы и файлы не исполняются: они читаются как текст.
"""
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SUPERSCRIPT = "⁰¹²³⁴⁵⁶⁷⁸⁹"
# Метка страницы из tools/pdf_text.py и колонтитул официального опубликования на pravo.by.
PAGE_BREAK = re.compile(
    r"\s*===== стр\. \d+ =====\s*"
    r"(?:Национальный правовой Интернет-портал Республики Беларусь, \d\d\.\d\d\.\d{4}, [\d/-]+[ \t]*\n[ \t]*\d+[ \t]*\n)?"
)


class BuildError(SystemExit):
    pass


def html_paragraphs(page):
    """Абзацы страницы ЭТАЛОН-ONLINE: теги убраны, надстрочные цифры превращены в ¹²³."""
    page = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", page)
    page = re.sub(
        r"(?is)<sup>\s*(\d+)\s*</sup>",
        lambda match: "".join(SUPERSCRIPT[int(digit)] for digit in match.group(1)),
        page,
    )
    page = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</tr>|</td>|</h\d>|</li>", "\n", page)
    page = html.unescape(re.sub(r"<[^>]*>", "", page)).replace("\xa0", " ")
    rows = [re.sub(r"[ \t]+", " ", row).strip() for row in page.splitlines()]
    return [row for row in rows if row]


class Lines:
    """Список абзацев с поиском по началу абзаца."""

    def __init__(self, rows, label):
        self.rows = rows
        self.label = label

    def index(self, start, exact=False, nth=None):
        if exact:
            found = [n for n, row in enumerate(self.rows) if row == start]
        else:
            found = [n for n, row in enumerate(self.rows) if row.startswith(start)]
        if not found:
            raise BuildError(f"[{self.label}] абзац не найден: {start[:90]}")
        if nth is not None:
            if nth >= len(found):
                raise BuildError(f"[{self.label}] нет вхождения № {nth}: {start[:90]}")
            return found[nth]
        if len(found) > 1:
            raise BuildError(f"[{self.label}] абзац найден {len(found)} раз(а): {start[:90]}")
        return found[0]

    def para(self, start, count=1, sep="\n", exact=False, nth=None):
        """Абзац, который начинается с `start`, и следующие за ним (всего `count`)."""
        n = self.index(start, exact=exact, nth=nth)
        return sep.join(self.rows[n:n + count])

    def after(self, start, offset=1, count=1, sep="\n", exact=False, nth=None):
        """Абзацы, которые идут через `offset` после абзаца, начинающегося с `start`."""
        n = self.index(start, exact=exact, nth=nth)
        return sep.join(self.rows[n + offset:n + offset + count])

    def between(self, begin, end, begin_nth=None, label=None):
        """Часть списка от абзаца, начинающегося с `begin`, до первого после него абзаца, начинающегося с `end`."""
        first = self.index(begin, nth=begin_nth)
        for n in range(first + 1, len(self.rows)):
            if self.rows[n].startswith(end):
                return Lines(self.rows[first:n], label or f"{self.label}: {begin[:40]}")
        raise BuildError(f"[{self.label}] конец участка не найден: {end[:90]}")

    def region(self, begin, end=None, label=None, begin_nth=None, end_nth=None):
        """Часть списка между абзацем `begin` (точное совпадение) и абзацем `end`."""
        first = self.index(begin, exact=True, nth=begin_nth)
        if end is None:
            last = len(self.rows)
        else:
            candidates = [n for n, row in enumerate(self.rows) if row == end and n > first]
            if not candidates:
                raise BuildError(f"[{self.label}] конец участка не найден: {end[:90]}")
            last = candidates[0 if end_nth is None else end_nth]
        return Lines(self.rows[first:last], label or f"{self.label}: {begin[:40]}")


class Source:
    """Сохранённая копия акта: путь, запись манифеста, текст."""

    def __init__(self, rel_path):
        self.rel = rel_path
        self.path = ROOT / rel_path
        if not self.path.is_file():
            raise BuildError(f"нет файла {rel_path}")
        self.manifest = self._manifest_record()

    def _manifest_record(self):
        manifest = self.path.parent / "manifest.jsonl"
        name = self.path.name
        if self.path.suffix == ".txt":
            name = self.path.with_suffix(".pdf").name
        if not manifest.is_file():
            return {}
        for row in manifest.read_text(encoding="utf-8").splitlines():
            if not row.strip():
                continue
            record = json.loads(row)
            if (record.get("file") or "").endswith(name):
                return record
        return {}

    @property
    def sha256(self):
        return self.manifest.get("sha256", "")

    @property
    def fetched(self):
        value = self.manifest.get("fetched_at", "")
        return value[:16].replace("T", " ") + " UTC" if value else ""

    @property
    def url(self):
        return self.manifest.get("url", "")

    def copy_note(self):
        """Строка для шапки выписки: путь, SHA-256, время загрузки."""
        rel = self.rel
        if self.path.suffix == ".txt" and self.path.with_suffix(".pdf").is_file():
            rel = str(Path(self.rel).with_suffix(".pdf")).replace("\\", "/")
        parts = [f"`{rel}`"]
        if self.sha256:
            parts.append(f"SHA-256 `{self.sha256}`")
        if self.fetched:
            parts.append(f"загружено {self.fetched}")
        return ", ".join(parts)


class HtmlSource(Source):
    def __init__(self, rel_path):
        super().__init__(rel_path)
        page = self.path.read_bytes().decode("utf-8-sig", errors="replace")
        self.lines = Lines(html_paragraphs(page), Path(rel_path).name)

    def edition(self):
        """Действующая редакция по перечню редакций на странице ЭТАЛОН-ONLINE."""
        rows = self.lines.rows
        n = rows.index("(действующая редакция)")
        return "«" + rows[n - 1] + "», " + rows[n + 1].replace(" - ", " — ")

    def future_editions(self):
        rows = self.lines.rows
        found = []
        for n, row in enumerate(rows):
            if row.startswith("(вступает в силу "):
                found.append(rows[n - 1] + " " + row)
        return found


class TxtSource(Source):
    """Текст, извлечённый из PDF программой tools/pdf_text.py."""

    def __init__(self, rel_path):
        super().__init__(rel_path)
        raw = self.path.read_text(encoding="utf-8-sig")
        text = PAGE_BREAK.sub(" ", raw)
        text = re.sub(r"\s+", " ", text)
        # составное слово, перенесённое на новую строку после дефиса
        self.text = re.sub(r"(?<=\w)- (?=\w)", "-", text)

    def frag(self, start, end=None, nth=None):
        """Участок текста от слов `start` до слов `end` включительно.

        Без `end` возвращаются сами слова `start` (проверяется, что они есть в тексте).
        Без `nth` начало должно встречаться в тексте один раз.
        """
        positions = [match.start() for match in re.finditer(re.escape(start), self.text)]
        if not positions:
            raise BuildError(f"[{self.path.name}] начало не найдено: {start[:90]}")
        if nth is None:
            if len(positions) > 1:
                raise BuildError(f"[{self.path.name}] начало найдено {len(positions)} раз(а): {start[:90]}")
            position = positions[0]
        else:
            if nth >= len(positions):
                raise BuildError(f"[{self.path.name}] нет вхождения № {nth}: {start[:90]}")
            position = positions[nth]
        if end is None:
            return start
        finish = self.text.find(end, position + len(start))
        if finish < 0:
            raise BuildError(f"[{self.path.name}] конец не найден: {end[:90]}")
        return self.text[position:finish + len(end)].strip()


def cut(text, start, end=None):
    """Часть абзаца от слов `start` до слов `end` включительно."""
    first = text.find(start)
    if first < 0:
        raise BuildError(f"в абзаце нет слов: {start[:80]}")
    if end is None:
        return text[first:]
    last = text.find(end, first)
    if last < 0:
        raise BuildError(f"в абзаце нет слов: {end[:80]}")
    return text[first:last + len(end)]


def check_quote(text):
    if text.count("«") != text.count("»"):
        raise BuildError(f"в цитате не сходятся кавычки: {text[:120]}")
    if "*" in text:
        raise BuildError(f"в цитате осталась звёздочка сноски: {text[:120]}")
    if any(char in text for char in SUPERSCRIPT):
        raise BuildError(f"в цитате остался надстрочный знак: {text[:120]}")
    return text


def q(text):
    """Цитата в кавычках-ёлочках (может занимать несколько строк)."""
    return "«" + check_quote(text.strip()) + "»"


def q1(text):
    """Цитата в одну строку — для таблиц."""
    text = re.sub(r"\s*\n\s*", " ", text.strip())
    if "|" in text:
        raise BuildError(f"в цитате для таблицы есть знак |: {text[:120]}")
    return "«" + check_quote(text) + "»"


def strip_marks(text):
    """Убирает знаки сносок (звёздочки) в конце абзаца."""
    return re.sub(r"\*+$", "", text.strip()).strip()


def sup_to_ellipsis(text):
    """Заменяет надстрочный знак сноски многоточием: проверка цитат сверяет части по отдельности."""
    return re.sub(f"[{SUPERSCRIPT}]+", "…", text)


def strip_leading_sup(text):
    """Убирает номер сноски (надстрочный знак или цифры) в начале текста сноски."""
    return re.sub(f"^[{SUPERSCRIPT}\\d]+\\s*", "", text.strip())


def table_cells(page):
    """Строки таблиц страницы: список списков ячеек. Теги внутри слов убираются без пробела."""
    page = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", page)
    result = []
    for row in re.findall(r"(?is)<tr\b[^>]*>(.*?)</tr>", page):
        cells = []
        for raw in re.findall(r"(?is)<td\b[^>]*>(.*?)</td>", row):
            raw = re.sub(
                r"(?is)<sup>\s*(\d+)\s*</sup>",
                lambda match: "".join(SUPERSCRIPT[int(digit)] for digit in match.group(1)),
                raw,
            )
            block = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</li>", " ¶ ", raw)
            glued = html.unescape(re.sub(r"<[^>]*>", "", block)).replace("\xa0", " ")
            spaced = html.unescape(re.sub(r"<[^>]*>", " ", block)).replace("\xa0", " ")
            glued = re.sub(r"\s+", " ", glued).strip()
            spaced = re.sub(r"\s+", " ", spaced).strip()
            # абзацы внутри ячейки: в «склеенном» виде — через пробел, в «по абзацам» — через точку с запятой
            parts = [part.strip() for part in glued.split("¶") if part.strip()]
            glued = " ".join(parts)
            spaced = " ".join(part.strip() for part in spaced.split("¶") if part.strip())
            spaced = re.sub(r" ([,.;:)])", r"\1", spaced).replace("( ", "(")
            cells.append((glued, spaced, "; ".join(parts)))
        if cells:
            result.append(cells)
    return result


def write(target_rel, parts):
    target = ROOT / target_rel
    body = "\n".join(parts).rstrip("\n") + "\n"
    target.write_text(body, encoding="utf-8", newline="\n")
    print("written", target_rel, "| знаков:", len(body))
