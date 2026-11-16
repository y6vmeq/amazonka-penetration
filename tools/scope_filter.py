"""Фильтр «вне рамок дела»: убирает из текста сведения о заведениях, которые пользователь
исключил из работы 15.11.2026 («Аура» и «Джентльмены», а также связанные с первым юрлицо,
кафе по тому же адресу, телефон, карточки и публикации).

Где используется:
  - tools/save_agent_messages.py — отчёты агентов проходят через redact_text, чтобы удалённые
    сведения не возвращались в проект при повторном сохранении;
  - разовые проходы чистки рабочих файлов сборов.

Что делает:
  redact_text(text)   — текст построчно: строка только об исключённом заведении удаляется;
                        в смешанной строке удаляются предложения, части предложений и элементы
                        перечислений о нём, а также их продолжения (до следующего упоминания
                        заведений по делу); оставшиеся названия заменяются пометкой MARK.
  redact_line(line)   — то же для одной строки; None значит «строку удалить».
  prune_json(node)    — то же для разобранного JSON: удаляет элементы списков и значения
                        словарей, которые относятся только к исключённым заведениям.
  mentions(text)      — есть ли в тексте упоминание или пометка.

Дословные материалы (reviews.jsonl, сырые копии, расшифровки) этим фильтром не правятся: он
удаляет целые фразы. Попутные упоминания в них заменены пометкой MARK отдельным строгим проходом
15.11.2026 — одинаково в записи и в её сырой копии, поэтому сверка reviews_check сохраняется.
В новых дословных материалах поступать так же: заменять только само упоминание, запись не удалять.
Изображения, видео и PDF не правятся.
"""
import base64
import json
import re

MARK = "[исключено]"

# Коды публикаций самих исключённых заведений и о них; в адресах и выгрузках встречаются и их номера.
POST_CODES = ("DfcEG5VjLhU", "DfvHONijFPl", "7jCTqJWX8jQ", "DWUtfygjDkG", "DWTgRhajPGT")
_CODE_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"


def _post_number(code):
    """Номер публикации Instagram или Threads по её коду (код — запись номера по основанию 64)."""
    value = 0
    for char in code:
        value = value * 64 + _CODE_ALPHABET.index(char)
    return str(value)


POST_NUMBERS = tuple(_post_number(code) for code in POST_CODES if code != "7jCTqJWX8jQ")

# Названия, записанные в base64 (например, поисковый запрос внутри адреса карточки на картах).
_B64_WORDS = (
    "Джентльмены", "джентльмены", "Джентельмены", "джентельмены", "Gentlemen", "gentlemen",
    "Аура", "АУРА", "аура", "Ауры", "Ауре", "Ауру", "Сели-Поели", "Сели Поели", "Сурганова, 46", "Сурганова,46",
    "aura_mogilev", "ресторанбараура", "Aura Могилев",
)


def _b64_cores(word, minimum=9):
    """Середины записи слова в base64 при трёх сдвигах: они не зависят от соседних байтов."""
    data = word.encode("utf-8")
    cores = set()
    for shift in range(3):
        encoded = base64.b64encode(b"\x00" * shift + data).decode("ascii").rstrip("=")
        core = encoded[(shift * 8 + 5) // 6:((shift + len(data)) * 8) // 6]
        if len(core) >= minimum:
            cores.add(core)
            cores.add(core.replace("+", "-").replace("/", "_"))
    return cores


B64_CORES = sorted({core for word in _B64_WORDS for core in _b64_cores(word)})
_B64 = "|".join(re.escape(core) for core in B64_CORES)
_HANDLE_LAT = r"(?<![A-Za-z])aura[_.\-]?(?:mogilev|restoclub|restobar|bar|gr(?:ou|u)pp?)[A-Za-z0-9_]*"
_TAG_LAT = r"(?<![A-Za-z])(?:restoranbar|restobar|restbar|kafe|cafe)aura(?![a-z])"
_TAG_CYR = r"(?<![А-Яа-яЁё])(?:ресторанбар|рестобар|рестбар|кафе|бар)а[уў]ра(?![а-яё])"
_HASHTAG_CYR = r"#а[уў]ра[а-яёўі0-9_]*"
_COMPOUND = r"а[уў]рагрупп|а[уў]рамогил[её]в|auramogilev"
# Название латиницей с русским окончанием («к aure») — только после русского слова.
_LAT_CASE = r"(?<=[а-яё] )aur(?:oy|oj|e|u|y)(?![A-Za-z0-9_\-/=+%&])"
_NAME_CYR = r"(?<![А-Яа-яЁёЎўІі])а[уў]р(?:ами|ах|ам|ой|ою|ай|а|ы|е|у)(?![а-яёўі])"
# «Джентльмены удачи» — название фильма (встречается тегом), к делу и к исключённым заведениям не относится.
_GENTL_CYR = r"дж[еэ]нт[еь]?ль?м[еэ]н(?![а-яё]{0,2}\s?удачи)[а-яёўі]*"
_GENTL_LAT = r"gentlem[ea]n|dzhentl|djente?l|dzentl"
_PHONE = (
    r"(?<!\d)500[\s\-–—.]{0,3}02[\s\-–—.]{0,3}20(?!\d)"
    r"|(?<!\d)(?:375|80)295000220(?!\d)"
)
_POSTS = "|".join(re.escape(code) for code in POST_CODES) + "|" + "|".join(r"(?<!\d)" + number + r"(?!\d)" for number in POST_NUMBERS)

# Упоминания исключённых заведений: названия, юрлицо, адрес, телефон, карточки, публикации.
# «Сели-Поели фуд» — другое юридическое лицо (УНП 791071650), оно не исключалось.
MENTION = re.compile(
    r"(?<![A-Za-z])aura(?![a-z])"
    r"|" + _HANDLE_LAT + r"|" + _TAG_LAT + r"|" + _LAT_CASE +
    r"|" + _NAME_CYR + r"|" + _HASHTAG_CYR + r"|" + _TAG_CYR + r"|" + _COMPOUND +
    r"|" + _GENTL_CYR + r"|" + _GENTL_LAT +
    r"|сел[иі][\s+_\-–—]{0,3}поел[иі](?!\s*фуд)|seli[\s+_\-]{0,3}poeli|790972924|business-entity/542050|employer/12140705"
    r"|(?:кафе|бар|ресторан)\w*\s*[«\"“]?\s*очаг(?![а-яё])|[«\"“]очаг[»\"”]|ochag"
    r"|сурганов\w*\W{0,6}(?:д(?:ом)?\.?\s*)?46(?!\d)|(?<![A-Za-z])surganov[a-z]*[\W_]{0,6}46(?!\d)"
    r"|" + _PHONE +
    r"|node/15287|66541391496|" + _POSTS +
    r"|" + _B64,
    re.I,
)
# Признаки того, что рядом есть материал по делу.
KEEP = re.compile(
    r"амазонк|amazonk|(?<![а-яё])смак|smak|колетт|colett|найсус|лукьянов|lukyanov|устинов"
    r"|791349254|791290567|790368798|бархат|barhat"
    r"|ленинск(?:ая|ой|ую)(?![а-яё])|leninskaya|буд[её]нного|budennogo|DfhVI_UjMdT|DfZejAqjGTZ",
    re.I,
)
SIGNAL = re.compile(MENTION.pattern + "|" + re.escape(MARK), re.I)


def _tokens(quotes):
    q = "[" + quotes + "]?"
    return [
        re.compile(r"(?:ООО|OOO)\s*" + q + r"\s*Сел[иі][\s+_\-–—]{0,3}Поел[иі](?!\s*фуд)\s*" + q, re.I),
        re.compile(q + r"\s*Сел[иі][\s+_\-–—]{0,3}Поел[иі](?!\s*фуд)\s*" + q, re.I),
        re.compile(r"seli[\s+_\-]{0,3}poeli[\w.-]*", re.I),
        re.compile(r"790972924"),
        re.compile(r"[@#]?" + _HANDLE_LAT + r"(?:\.[A-Za-z0-9_]+)*", re.I),
        re.compile(r"[@#]?" + _TAG_LAT, re.I),
        re.compile(r"[@#]?" + _TAG_CYR, re.I),
        re.compile(_HASHTAG_CYR, re.I),
        re.compile(r"[@#]?(?:" + _COMPOUND + r")\w*", re.I),
        re.compile(_LAT_CASE, re.I),
        re.compile(q + r"(?<![A-Za-z])aura(?![a-z])" + q, re.I),
        re.compile(q + _NAME_CYR + q, re.I),
        re.compile(q + r"(?:[@#]?" + _GENTL_CYR + r"|(?:" + _GENTL_LAT + r")\w*)" + q, re.I),
        re.compile(q + r"(?<![А-Яа-яЁё])очаг(?![а-яё])" + q, re.I),
        re.compile(r"ochag[\w.-]*", re.I),
        re.compile(r"(?:ул\.?\s*)?сурганов\w*\W{0,6}(?:д(?:ом)?\.?\s*)?46(?!\d)", re.I),
        re.compile(r"(?<![A-Za-z])surganov[a-z]*[\W_]{0,6}46(?!\d)", re.I),
        re.compile(r"(?:\+?\s*375[\s(\-]*29[\s)\-]*|(?<!\d)8[\s(\-]*0?29[\s)\-]*)?(?:" + _PHONE + r")"),
        re.compile(r"node/15287|66541391496|" + _POSTS),
        re.compile(r"[A-Za-z0-9+/_\-]*(?:" + _B64 + r")[A-Za-z0-9+/_\-]*=*"),
    ]


TOKENS = _tokens("«»\"“”'")
# Для JSON и JSONL: обычные кавычки и апострофы не трогаем, иначе ломается формат.
TOKENS_JSON = _tokens("«»“”")

# Сокращения, после которых точка не заканчивает предложение.
ABBREVIATIONS = {
    "ул", "пр", "пер", "г", "д", "к", "корп", "стр", "каб", "тел", "им", "т", "е", "см", "п", "пп",
    "ч", "ст", "руб", "коп", "тыс", "млн", "млрд", "мин", "сек", "гг", "в", "вв", "др", "наб", "пл",
    "обл", "пом", "оф", "эт", "кв", "с", "н", "э", "бул", "просп", "ш", "мкр", "зд", "рег", "изм",
    "ред", "абз", "подп", "прил", "разд", "гл", "рис", "табл", "напр", "б", "м", "р", "а", "пр-т",
    "б-р", "р-н", "no", "vs", "etc", "inc", "ltd", "co", "st",
}
LIST_PREFIX = re.compile(r"^(\s*(?:(?:[-*+]|\d+[.)]|>)\s+)*)")
HEADING = re.compile(r"^\s*#{1,6}\s")
# Ключи словаря, по которым видно, о каком заведении вся запись.
SUBJECT_KEYS = (
    "venue", "venue_guess", "owner", "user", "username", "account", "profile", "handle", "group", "id", "record",
    "record_id", "source", "source_id", "file", "path", "raw", "raw_file", "url", "final_url", "href", "link",
    "shortcode", "code", "name", "title", "key", "label", "html", "txt", "query", "requested",
)
# Ключи с дословным текстом: смешанные строки в них не правятся.
VERBATIM_KEYS = (
    "text", "caption", "body", "snippet", "description", "desc", "transcript", "reply", "content", "html", "alt",
    "accessibility_caption", "raw_text", "quote", "full_text",
)


def mentions(text):
    return bool(SIGNAL.search(text or ""))


def _has_keep(text):
    return bool(KEEP.search(text))


def redact_tokens(text, json_safe=False):
    """Заменяет названия и идентификаторы исключённых заведений пометкой."""
    for pattern in (TOKENS_JSON if json_safe else TOKENS):
        text = pattern.sub(MARK, text)
    return re.sub(r"(?:\[исключено\][ ,;/]*)+(?=\[исключено\])", "", text)


def _split(text, kind):
    """Делит текст на предложения ('sentence'), части через «; » ('clause') или элементы
    перечисления через «, » ('item'). Внутри скобок, «ёлочек» и обратных кавычек не делит."""
    parts, depth, start, in_code = [], 0, 0, False
    index, size = 0, len(text)
    paired_quotes = text.count("«") == text.count("»")
    openers, closers = ("(«", ")»") if paired_quotes else ("(", ")")
    while index < size:
        char = text[index]
        if char == "`":
            in_code = not in_code
        elif not in_code:
            if char in openers:
                depth += 1
            elif char in closers:
                depth = max(0, depth - 1)
            elif depth == 0:
                cut = None
                if kind == "clause" and text.startswith("; ", index):
                    cut = (index, index + 2)
                elif kind == "item" and text.startswith(", ", index):
                    cut = (index, index + 2)
                elif kind == "sentence" and char in ".!?" and text.startswith(" ", index + 1):
                    word_start = index
                    while word_start > start and (text[word_start - 1].isalpha() or text[word_start - 1] == "-"):
                        word_start -= 1
                    word = text[word_start:index].lower()
                    following = text[index + 2:index + 3]
                    starts_sentence = following.isupper() or following.isdigit() or following in "«`\"(*[—-"
                    is_abbreviation = len(word) == 1 or word in ABBREVIATIONS
                    if char != "." or (not is_abbreviation and starts_sentence):
                        cut = (index + 1, index + 2)
                if cut:
                    parts.append(text[start:cut[0]])
                    start = index = cut[1]
                    continue
        index += 1
    parts.append(text[start:])
    return [part for part in parts if part.strip()]


def _target_first(text):
    """Исключённое заведение названо раньше, чем заведение по делу: фраза о нём."""
    signal, keep = SIGNAL.search(text), KEEP.search(text)
    return bool(signal) and (keep is None or signal.start() < keep.start())


# Фраза, которая после удалённой фразы продолжает говорить о том же («Это…», «Там…»).
ANAPHORA = re.compile(
    r"^\W*(?:это|этот|эта|эти|он|она|оно|они|его|её|ее|их|там|здесь|тот же|та же|то же|те же|такой же)(?![а-яё])",
    re.I,
)
# Пометка как голый элемент перечисления: «X и [исключено]», «[исключено] и X», «, [исключено]».
_BARE_MARK = [
    re.compile(r"\s+(?:и|или|либо)\s+\[исключено\](?=[\s,.;:)»—-]|$)"),
    re.compile(r"\[исключено\]\s+(?:и|или|либо)\s+"),
    re.compile(r",\s*\[исключено\](?=\s*[,.;:)]|\s*$)"),
]


def _strip_bare_marks(text):
    for pattern in _BARE_MARK:
        text = pattern.sub("", text)
    return text


def _tidy(text):
    if text.count("«") == text.count("»"):
        parts = re.split(r"(«[^«»]*»)", text)
        text = "".join(part if part.startswith("«") else _strip_bare_marks(part) for part in parts)
    else:
        text = _strip_bare_marks(text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return re.sub(r"\s+([,.;:])", r"\1", text)


def _filter_clauses(sentence, dropping):
    """Части предложения через «; ». Возвращает (текст, удалена ли последняя часть)."""
    clauses = []
    for clause in _split(sentence, "clause"):
        signal, keep = mentions(clause), _has_keep(clause)
        if not signal:
            if dropping and (not keep or ANAPHORA.match(clause)):
                continue
            dropping = False
            clauses.append(clause)
            continue
        if not keep:
            dropping = True
            continue
        items = [item for item in _split(clause, "item") if not (mentions(item) and not _has_keep(item))]
        clause = _tidy(", ".join(items))
        if mentions(clause) and _target_first(clause):
            dropping = True
            continue
        dropping = False
        if clause.strip():
            clauses.append(clause)
    return "; ".join(clauses), dropping


def _filter_fragment(text):
    """Убирает из фрагмента (абзац, ячейка, строковое значение) всё об исключённых заведениях."""
    sentences, dropping = [], False
    for sentence in _split(text, "sentence"):
        signal, keep = mentions(sentence), _has_keep(sentence)
        if not signal:
            if dropping and (not keep or ANAPHORA.match(sentence)):
                continue
            dropping = False
            sentences.append(sentence)
            continue
        if not keep:
            dropping = True
            continue
        filtered, dropping = _filter_clauses(sentence, dropping)
        if filtered.strip():
            sentences.append(filtered)
            dropping = False
        else:
            dropping = True
    return " ".join(sentences).strip()


def _filter_cell(cell):
    """Ячейка таблицы в строке, где есть материал по делу."""
    if not mentions(cell):
        return cell
    if _has_keep(cell):
        return _filter_fragment(cell)
    sentences = []
    for sentence in _split(cell, "sentence"):
        clauses = []
        for clause in _split(sentence, "clause"):
            items = [item for item in _split(clause, "item") if not mentions(item)]
            if items:
                clauses.append(", ".join(items))
        if clauses:
            sentences.append("; ".join(clauses))
    return " ".join(sentences).strip()


def _has_letters(text):
    return bool(re.search(r"[A-Za-zА-Яа-яЁё0-9]", text.replace(MARK, "")))


def redact_line(line, json_safe=False):
    """None — строку удалить; иначе строка без сведений об исключённых заведениях."""
    if not mentions(line):
        return line
    if not _has_keep(line):
        return None
    line = redact_tokens(line, json_safe)
    if HEADING.match(line):
        return _tidy(line)
    stripped = line.strip()
    if stripped.startswith("|") and stripped.count("|") >= 2:
        cells = line.split("|")
        inner = [cell.strip() for cell in cells[1:-1]]
        first = next((cell for cell in inner if cell), "")
        if mentions(first) and not _has_keep(first):
            return None
        filtered = [_tidy(_filter_cell(cell)) or "—" for cell in inner]
        if not _has_letters(filtered[0]) and filtered[0] != inner[0]:
            return None
        result = cells[0] + "| " + " | ".join(filtered) + " |" + cells[-1]
    else:
        prefix = LIST_PREFIX.match(line).group(1)
        body = _tidy(_filter_fragment(line[len(prefix):]))
        if not _has_letters(body):
            return None
        result = prefix + body
    if result.count("**") % 2:
        result = result.replace("**", "")
    return result


BLOCK_TITLE = re.compile(r"^\*\*[^*]+\*\*\s*$")


def redact_text(text):
    """Построчная чистка. Если удалён заголовок, удаляется весь его раздел; если удалена строка-подпись
    вида **`файл`**, удаляется блок до следующей такой строки или заголовка."""
    kept, skip_level, skip_block = [], None, False
    for line in text.split("\n"):
        heading = re.match(r"^\s*(#{1,6})\s", line)
        title = bool(BLOCK_TITLE.match(line.strip()))
        if heading:
            if skip_level is not None and len(heading.group(1)) > skip_level:
                continue
            skip_level, skip_block = None, False
        elif skip_level is not None:
            continue
        elif title:
            skip_block = False
        elif skip_block:
            continue
        new = redact_line(line)
        if new is None:
            if heading:
                skip_level = len(heading.group(1))
            elif title:
                skip_block = True
            continue
        kept.append(new)
    return "\n".join(kept)


def _blob(node):
    return node if isinstance(node, str) else json.dumps(node, ensure_ascii=False)


def _about_target(node):
    """Запись целиком об исключённом заведении: это видно по полю вроде venue или owner."""
    if not isinstance(node, dict):
        return False
    for key in SUBJECT_KEYS:
        value = node.get(key)
        if isinstance(value, str) and mentions(value) and not _has_keep(value):
            return True
    return False


DROP = object()


def prune_json(node):
    """Возвращает узел без сведений об исключённых заведениях или DROP, если удалить весь узел."""
    blob = _blob(node)
    if not mentions(blob):
        return node
    if _about_target(node):
        return DROP
    if not isinstance(node, (list, dict)) and not _has_keep(blob):
        return DROP
    if isinstance(node, dict) and not _has_keep(blob):
        # Запись без слов дела, в собственных полях которой названо исключённое заведение.
        # Если упоминание только во вложенных списках (например, в перечне кодов), идём вглубь.
        own = [value for value in node.values() if isinstance(value, (str, int, float)) and not isinstance(value, bool)]
        if any(mentions(str(value)) for value in own):
            return DROP
    if isinstance(node, str):
        lines = []
        for line in node.split("\n"):
            if not mentions(line):
                lines.append(line)
            elif _has_keep(line):
                filtered = _tidy(_filter_fragment(redact_tokens(line)))
                if _has_letters(filtered):
                    lines.append(filtered)
        return "\n".join(lines)
    if isinstance(node, list):
        result = []
        for item in node:
            pruned = prune_json(item)
            if pruned is DROP or pruned in ("", [], {}) and item not in ("", [], {}):
                continue
            result.append(pruned)
        return result
    if isinstance(node, dict):
        result = {}
        for key, value in node.items():
            if mentions(key) and not _has_keep(key):
                continue
            if isinstance(value, str) and key.lower() in VERBATIM_KEYS and _has_keep(value):
                result[key] = value
                continue
            pruned = prune_json(value)
            if pruned is DROP:
                if isinstance(value, (list, dict)):
                    continue
                pruned = "" if isinstance(value, str) else None
            result[key] = pruned
        return result
    return node
