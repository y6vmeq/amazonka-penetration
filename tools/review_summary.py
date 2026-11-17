"""Сводит замечания и оценки проверяющих по набору обращений в одну таблицу.

Запуск из корня проекта:
    python -I -X utf8 tools/review_summary.py letters/_review/<дата> [--write]

В папке проверки лежат подпапки по ролям проверяющих; в каждой — по файлу JSON на письмо:
    {"letter": "letters/<имя>.md", "role": "<роль>", "scores": {"К1": 9.5, ...},
     "findings": [{"id": "Н1", "severity": "критическое" | "существенное" | "мелкое",
                   "where": "...", "problem": "...", "fix": "..."}], "summary": "..."}
Ответы составителя на замечания — в подпапке otvety: {"letter": "...", "answers":
    [{"finding": "<роль>:<id>", "status": "исправлено" | "отклонено" | "частично", "what": "..."}]}.

Роли делятся на рабочие (оппонент, верификатор: их оценки относятся к прежней редакции письма и в приёмку
не идут) и приёмочные — роль начинается с «ocenka» (итоговая оценка независимого оценщика). Если один
оценщик оценивал письмо несколько раз (поле "round": 1, 2, …), в приёмку идёт его последний круг.

Печатает по каждому письму: сколько замечаний какой тяжести дала каждая роль и сколько из них закрыто;
рабочие оценки; итоговые оценки по критериям К1–К8 и наименьшую из них. Письмо принято, если у каждого
оценщика в последнем круге по каждому критерию не меньше 9,5. С ключом --write сохраняет сводку
в <папка>/SVODKA.md.
"""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

CRITERIA = [f"К{n}" for n in range(1, 9)]
SEVERITIES = ["критическое", "существенное", "мелкое"]
THRESHOLD = 9.5
EVALUATORS = 3  # два итоговых оценщика (роли А и Б) и третий, независимый (роль В, с 17.11.2026)
CLOSED = ("исправлено", "отклонено", "частично")


def load(folder):
    reviews, answers = [], {}
    for path in sorted(folder.rglob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as error:
            print(f"не прочитан {path.as_posix()}: {error}")
            continue
        if not isinstance(data, dict) or "letter" not in data:
            continue
        if "answers" in data:
            for item in data["answers"]:
                answers[(data["letter"], item.get("finding"))] = item.get("status", "")
        else:
            data["_role"] = data.get("role") or path.parent.name
            data["_round"] = int(data.get("round") or 1)
            reviews.append(data)
    return reviews, answers


def number(value):
    return "—" if value is None else str(value).replace(".", ",")


def state(lowest, evaluators):
    """Состояние письма: принято — только когда оценили все оценщики (EVALUATORS) и у каждого оценки не ниже порога."""
    if lowest is None:
        return "итоговой оценки нет"
    if lowest < THRESHOLD:
        return "на доработке"
    return "принято" if evaluators >= EVALUATORS else f"оценил {evaluators} из {EVALUATORS} — ждём остальных"


def score_line(label, scores):
    values = [scores.get(criterion) for criterion in CRITERIA]
    numbers = [float(value) for value in values if isinstance(value, (int, float))]
    lowest = min(numbers) if numbers else None
    return f"| {label} | " + " | ".join(number(value) for value in values) + f" | {number(lowest)} |", lowest


def main():
    args = [arg for arg in sys.argv[1:] if not arg.startswith("--")]
    if not args:
        sys.exit(__doc__)
    folder = Path(args[0])
    reviews, answers = load(folder)
    by_letter = defaultdict(list)
    for review in reviews:
        by_letter[review["letter"]].append(review)
    lines = [f"# Сводка проверки набора обращений ({folder.name})", "",
             "Составлена программой `tools/review_summary.py` по файлам проверяющих; руками не править.", ""]
    header = "| Оценивающий | " + " | ".join(CRITERIA) + " | Наименьшая |"
    rule = "|---|" + "---|" * (len(CRITERIA) + 1)
    totals = []
    for letter in sorted(by_letter):
        if "/_archive/" in letter or not Path(letter).is_file():
            # прежний проект, заменённый новыми письмами: в приёмку не идёт
            lines += [f"## {letter}", "", "Прежний проект, заменён новыми письмами набора (замечания по нему учтены в них); в приёмку не идёт.", ""]
            continue
        lines += [f"## {letter}", "", "| Роль | Круг | Критических | Существенных | Мелких | Закрыто |", "|---|---|---|---|---|---|"]
        working, final = [], {}
        for review in sorted(by_letter[letter], key=lambda item: (item["_role"], item["_round"])):
            role = review["_role"]
            findings = review.get("findings") or []
            counts = [sum(1 for item in findings if item.get("severity") == severity) for severity in SEVERITIES]
            closed = sum(1 for item in findings if answers.get((letter, f"{role}:{item.get('id')}")) in CLOSED)
            lines.append(f"| {role} | {review['_round']} | {counts[0]} | {counts[1]} | {counts[2]} | {closed} из {len(findings)} |")
            if not review.get("scores"):
                continue
            if role.startswith("ocenka"):
                key = re.sub(r"[-_ ]?\d+$", "", role)
                if key not in final or review["_round"] >= final[key]["_round"]:
                    final[key] = review
            else:
                working.append(review)
        if working:
            lines += ["", "Рабочие оценки (прежние редакции письма, в приёмку не идут):", "", header, rule]
            lines += [score_line(f"{review['_role']}", review["scores"])[0] for review in working]
        if final:
            lines += ["", "**Итоговая оценка (последний круг каждого оценщика):**", "", header, rule]
            lowest_all = []
            for key in sorted(final):
                review = final[key]
                row, lowest = score_line(f"{key}, круг {review['_round']}", review["scores"])
                lines.append(row)
                if lowest is not None:
                    lowest_all.append(lowest)
            lowest = min(lowest_all) if lowest_all else None
            verdict = state(lowest, len(final))
            lines += ["", f"Наименьшая итоговая оценка: **{number(lowest)}** — {verdict}."]
            totals.append((letter, lowest, len(final)))
        else:
            lines += ["", "Итоговой оценки ещё нет."]
            totals.append((letter, None, 0))
        lines.append("")
    lines += ["## Итог по набору", "", "| Письмо | Оценщиков | Наименьшая итоговая оценка | Состояние |", "|---|---|---|---|"]
    for letter, lowest, count in totals:
        lines.append(f"| {letter} | {count} | {number(lowest)} | {state(lowest, count)} |")
    graded = [lowest for _, lowest, _ in totals if lowest is not None]
    if graded and len(graded) == len(totals):
        lines += ["", f"**Наименьшая итоговая оценка по всему набору: {number(min(graded))}.** Порог приёмки — 9,5 по каждому критерию у каждого оценщика."]
    else:
        lines += ["", f"Итоговая оценка есть у {len(graded)} писем из {len(totals)}. Порог приёмки — 9,5 по каждому критерию у каждого оценщика."]
    lines.append("")
    text = "\n".join(lines)
    print(text)
    if "--write" in sys.argv:
        (folder / "SVODKA.md").write_text(text, encoding="utf-8", newline="\n")
        print("сохранено:", (folder / "SVODKA.md").as_posix())


if __name__ == "__main__":
    main()
