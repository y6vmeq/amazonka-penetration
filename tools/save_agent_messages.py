"""Сохраняет на диск сообщения субагентов из записи сеанса Claude Code.

Зачем: система не даёт субагентам создавать файлы отчётов, они присылают отчёт
текстом основному сеансу (сообщением либо итогом задачи). Этот скрипт достаёт такие сообщения из записи сеанса
дословно и раскладывает по папкам агентов.

Запуск из корня проекта:
    python -I tools/save_agent_messages.py <запись_сеанса.jsonl> <соответствие.json>

<соответствие.json> — объект {"<идентификатор агента>": "<папка агента>", ...}.
В каждой папке появятся:
    agent_messages/NN_<начало контрольной суммы>.md — все сообщения по порядку;
    REPORT.md — последнее длинное сообщение агента (перезаписывается), с пометкой,
                что файл записан основным сеансом; более поздние короткие
                сообщения (исправления) дописываются в конец.
Третьим аргументом можно передать JSON со списком строк, которые нужно скрыть:
[["что заменить", "на что"], ...].

Каждое сообщение проходит через tools/scope_filter.py: сведения о заведениях, исключённых
из работы, в файлы не попадают. Если такое сообщение уже сохранено, его файл не
перезаписывается: в нём могут быть ручные правки после чистки.
"""
import hashlib
import html
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import scope_filter  # noqa: E402  (соседний файл проекта)

REPORT_MIN_CHARS = 2000
MESSAGE = re.compile(r'<agent-message from="([0-9a-z]+)">\s*(.*?)\s*</agent-message>', re.S)
# Итог завершившегося агента приходит и так: уведомлением о задаче с блоком <result>.
RESULT = re.compile(
    r"<task-notification>\s*<task-id>([0-9a-z]+)</task-id>(?:(?!</task-notification>).)*?"
    r"<status>completed</status>(?:(?!</task-notification>).)*?<result>\s*(.*?)\s*</result>",
    re.S,
)
NOTE = (
    "> Сообщение агента, дословно сохранённое основным сеансом из записи сеанса "
    "(скрипт `tools/save_agent_messages.py`). Субагенты не могут сами создавать файлы отчётов.\n\n"
)
# Пометка, которую чистка оставляет в файле, из которого удалены сведения вне рамок работы.
SCOPE_NOTE = "удалены сведения о заведениях, исключённых из работы"


def strings(node):
    """Все строки из разобранного JSON, включая вложенные."""
    if isinstance(node, str):
        yield node
    elif isinstance(node, dict):
        for value in node.values():
            yield from strings(value)
    elif isinstance(node, list):
        for value in node:
            yield from strings(value)


def collect(transcript, with_results=False):
    """Возвращает {идентификатор агента: [сообщения по порядку, без повторов]}.

    Если агент ничего не присылал сообщением, а отчёт вернул итогом задачи
    (блок <result> в уведомлении), берётся этот итог. Если сообщения были,
    итог задачи не используется: обычно это краткая сводка того же отчёта.
    С with_results длинные итоги задачи добавляются после сообщений: так бывает,
    когда агент прислал короткие сообщения, а полный отчёт вернул итогом.
    """
    found, results, seen = {}, {}, set()
    with transcript.open(encoding="utf-8", errors="replace") as lines:
        for line in lines:
            if "agent-message" not in line and "task-notification" not in line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            for text in strings(record):
                for agent, body in MESSAGE.findall(text):
                    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
                    if digest in seen:
                        continue
                    seen.add(digest)
                    found.setdefault(agent, []).append((digest, body))
                for agent, body in RESULT.findall(text):
                    body = html.unescape(body)
                    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
                    if digest in seen:
                        continue
                    seen.add(digest)
                    results.setdefault(agent, []).append((digest, body))
    for agent, bodies in results.items():
        if agent not in found:
            found[agent] = bodies
        elif with_results:
            found[agent] += [(digest, body) for digest, body in bodies if len(body) >= REPORT_MIN_CHARS]
    return found


def main():
    with_results = "--results" in sys.argv
    args = [arg for arg in sys.argv[1:] if arg != "--results"]
    if len(args) not in (2, 3):
        sys.exit(
            "usage: python -I tools/save_agent_messages.py <transcript.jsonl> <mapping.json> [<redactions.json>] [--results]"
        )
    folders = json.loads(Path(args[1]).read_text(encoding="utf-8"))
    redactions = json.loads(Path(args[2]).read_text(encoding="utf-8")) if len(args) == 3 else []
    for agent, messages in collect(Path(args[0]), with_results).items():
        if agent not in folders:
            print(f"unknown agent, {len(messages)} message(s) skipped")
            continue
        folder = Path(folders[agent])
        (folder / "agent_messages").mkdir(parents=True, exist_ok=True)
        bodies, kept_as_is = [], 0
        for number, (digest, body) in enumerate(messages, 1):
            for old, new in redactions:
                body = body.replace(old, new)
            cleaned = scope_filter.redact_text(body)
            target = folder / "agent_messages" / f"{number:02d}_{digest[:8]}.md"
            saved = target.read_text(encoding="utf-8") if target.exists() else None
            if saved is not None and (cleaned != body or SCOPE_NOTE in saved):
                body = (saved[len(NOTE):] if saved.startswith(NOTE) else saved).rstrip("\n")
                kept_as_is += 1
            else:
                body = cleaned
                target.write_text(NOTE + body + "\n", encoding="utf-8", newline="\n")
            bodies.append(body)
        if kept_as_is:
            print(f"{ascii(str(folder))}: {kept_as_is} message(s) out of scope in part, saved copies kept")
        # Отчёт — последнее длинное сообщение; короткие сообщения после него —
        # это исправления и дополнения, их нельзя терять и нельзя ставить вместо отчёта.
        long_positions = [index for index, body in enumerate(bodies) if len(body) >= REPORT_MIN_CHARS]
        main = long_positions[-1] if long_positions else len(bodies) - 1
        report = NOTE + bodies[main] + "\n"
        for later in bodies[main + 1:]:
            report += "\n---\n\n## Более позднее сообщение агента (исправление или дополнение)\n\n" + later + "\n"
        (folder / "REPORT.md").write_text(report, encoding="utf-8", newline="\n")
        print(f"{ascii(str(folder))}: {len(messages)} message(s), report from #{main + 1}, {len(bodies[main])} chars")


if __name__ == "__main__":
    main()
