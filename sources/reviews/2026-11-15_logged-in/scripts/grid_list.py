"""Собирает work/ig_grid_<аккаунт>.tsv: код, вид, дата (вычислена по коду), отметки, комментарии, начало подписи."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from code_date import when

here = Path(__file__).resolve().parent.parent
rows_file, counts_file, out_name = sys.argv[1:4]
rows = json.loads((here / rows_file).read_text(encoding="utf-8"))["rows"]
counts = {}
if counts_file != "-":
    for line in json.loads((here / counts_file).read_text(encoding="utf-8"))["counts"]:
        code, likes, comments = line.split(" ")
        counts[code] = (likes, comments)
out = ["code\tkind\tdate_utc(computed)\tlikes\tcomments\tcaption_start"]
total = 0
for row in rows:
    code, kind, likes, comments, alt = [x.strip() for x in row.split(" | ", 4)]
    likes, comments = counts.get(code, (likes, comments))
    if comments.isdigit():
        total += int(comments)
    out.append("\t".join([code, "reel" if kind == "r" else "post", when(code).strftime("%Y-%m-%d %H:%M"), likes, comments, alt]))
(here / "work" / out_name).write_text("\n".join(out) + "\n", encoding="utf-8", errors="backslashreplace", newline="\n")
print(len(rows), "rows; comments total", total)
