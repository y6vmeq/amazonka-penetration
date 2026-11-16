#!/usr/bin/env bash
# Пересобирает приложения и файлы Word набора обращений от 16.11.2026 (стандарт — letters/STANDART.md).
#
#   bash letters/_build_docx.sh
#
# Заявитель в файлах Word условный (Иванов Иван Иванович): подставленное выделено жёлтым, вверху пометка
# «ПРОЕКТ, не для подачи». Исходник каждого письма — файл .md с пустыми полями заявителя.
# Приложения с перечнями публикаций собираются из описаний letters/_src/<имя>_prilozhenie-N.json;
# выдержки сверяются со сводом sources/reviews/ALL.jsonl, и при расхождении сборка останавливается.
set -euo pipefail
cd "$(dirname "$0")/.."
WHO=(--applicant "Иванов Иван Иванович" --applicant-gen "Иванова Ивана Ивановича" --signature "И. И. Иванов")

LETTERS=(
  sanitarnaya-sluzhba_amazonka
  gorispolkom_amazonka_zdanie-fasad-reklama
  gorispolkom_amazonka_torgovlya
  prirodoohrana_amazonka_zhivotnye
  nalogovaya_amazonka-smak-by
  sanitarnaya-sluzhba_smak-by
  gorispolkom_smak-by_raboty-okna-vhod
  gorispolkom_smak-by_torgovlya
)

for name in "${LETTERS[@]}"; do
  if [ ! -f "letters/$name.md" ]; then
    echo "пропущено (нет файла): letters/$name.md"
    continue
  fi
  appendices=()
  for spec in letters/_src/"$name"_prilozhenie-*.json; do
    [ -f "$spec" ] || continue
    target="letters/$(basename "${spec%.json}").md"
    python -I -X utf8 tools/letter_appendix.py "$spec" "$target"
    appendices+=(--appendix "$target")
  done
  python -I -X utf8 tools/letter_to_docx.py "letters/$name.md" "letters/$name.docx" "${WHO[@]}" --variant 1 ${appendices[@]+"${appendices[@]}"}
done

# шаблон жалобы на ответ: без приложений
python -I -X utf8 tools/letter_to_docx.py letters/shablon_zhaloba-na-otvet.md letters/shablon_zhaloba-na-otvet.docx "${WHO[@]}"
