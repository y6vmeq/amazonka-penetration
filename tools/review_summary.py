"""Сводит замечания и оценки проверяющих по набору обращений в одну таблицу.

Запуск из корня проекта:
    python -I -X utf8 tools/review_summary.py letters/_review/<дата> [--write]

В папке проверки лежат подпапки по ролям проверяющих; в каждой — по файлу JSON на письмо:
    {"letter": "letters/<имя>.md", "role": "<роль>", "scores": {"К1": 9.5, ...},
     "findings": [{"id": "Н1", "severity": "критическое" | "существенное" | "мелкое",
                   "where": "...", "problem": "...", "fix": "..."}], "summary": "..."}
Ответы составителя на замечания — в подпапке otvety: {"letter": "...", "answers":
    [{"finding": "<роль>:<id>", "status": "исправлено" | "отклонено" | "частично", "what": "..."}]}.

Печатает по каждому письму: сколько замечаний какой тяжести дала каждая роль, сколько из них закрыто,
оценки по критериям К1–К8 от каждой оценивающей роли и наименьшую оценку. С ключом --write
сохраняет ту же сводку в <папка>/SVODKA.md.
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

CRITERIA = [f"К{n}" for n in range(1, 9)]
SEVERITIES = ["критическое", "существенное", "мелкое"]


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
            reviews.append(data)
    return reviews, answers


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
    overall_min = None
    for letter in sorted(by_letter):
        lines += [f"## {letter}", "", "| Роль | Критических | Существенных | Мелких | Закрыто |", "|---|---|---|---|---|"]
        score_rows = []
        for review in sorted(by_letter[letter], key=lambda item: item["_role"]):
            findings = review.get("findings") or []
            counts = [sum(1 for item in findings if item.get("severity") == severity) for severity in SEVERITIES]
            closed = sum(1 for item in findings if answers.get((letter, f"{review['_role']}:{item.get('id')}")) in ("исправлено", "отклонено", "частично"))
            if findings or not review.get("scores"):
                lines.append(f"| {review['_role']} | {counts[0]} | {counts[1]} | {counts[2]} | {closed} из {len(findings)} |")
            if review.get("scores"):
                score_rows.append((review["_role"], review["scores"]))
        if score_rows:
            lines += ["", "| Оценивающий | " + " | ".join(CRITERIA) + " | Наименьшая |", "|---|" + "---|" * (len(CRITERIA) + 1)]
            for role, scores in score_rows:
                values = [scores.get(criterion) for criterion in CRITERIA]
                numbers = [float(value) for value in values if isinstance(value, (int, float))]
                lowest = min(numbers) if numbers else None
                if lowest is not None:
                    overall_min = lowest if overall_min is None else min(overall_min, lowest)
                cells = ["—" if value is None else str(value).replace(".", ",") for value in values]
                lines.append(f"| {role} | " + " | ".join(cells) + f" | {'—' if lowest is None else str(lowest).replace('.', ',')} |")
        lines.append("")
    if overall_min is not None:
        lines += [f"**Наименьшая оценка по всему набору: {str(overall_min).replace('.', ',')}.** Порог приёмки — 9,5 по каждому критерию.", ""]
    text = "\n".join(lines)
    print(text)
    if "--write" in sys.argv:
        (folder / "SVODKA.md").write_text(text, encoding="utf-8", newline="\n")
        print("сохранено:", (folder / "SVODKA.md").as_posix())


if __name__ == "__main__":
    main()
