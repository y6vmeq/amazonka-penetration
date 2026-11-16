#!/usr/bin/env bash
# Собирает приложения и файлы Word всех проектов обращений с условным заявителем.
# Запуск из корня проекта: bash letters/_build_docx.sh
# Условный заявитель (Иванов Иван Иванович) подставляется только в файлы .docx; исходники .md остаются с пустыми полями.
set -euo pipefail

WHO=(--applicant "Иванов Иван Иванович" --applicant-gen "Иванова Ивана Ивановича" --signature "И. И. Иванов")
CGE="Адресат — первый из двух вариантов (городской центр гигиены); второй вариант — областной центр: 212011, г. Могилёв, ул. Гришина, 82."

python -I -X utf8 tools/letter_appendix.py letters/_src/sanitarnaya-sluzhba_amazonka_prilozhenie-1.json letters/sanitarnaya-sluzhba_amazonka_prilozhenie-1.md
python -I -X utf8 tools/letter_appendix.py letters/_src/sanitarnaya-sluzhba_smak-by_prilozhenie-1.json letters/sanitarnaya-sluzhba_smak-by_prilozhenie-1.md
python -I -X utf8 tools/letter_appendix.py letters/_src/gorispolkom_smak-by_prilozhenie-1.json letters/gorispolkom_smak-by_raboty-fasad-torgovlya_prilozhenie-1.md

python -I -X utf8 tools/letter_to_docx.py letters/sanitarnaya-sluzhba_amazonka.md letters/sanitarnaya-sluzhba_amazonka.docx "${WHO[@]}" --variant 1 --appendix letters/sanitarnaya-sluzhba_amazonka_prilozhenie-1.md --note "$CGE"
python -I -X utf8 tools/letter_to_docx.py letters/gorispolkom_amazonka_fasad-vyveska-terrasa.md letters/gorispolkom_amazonka_fasad-vyveska-terrasa.docx "${WHO[@]}"
python -I -X utf8 tools/letter_to_docx.py letters/sanitarnaya-sluzhba_smak-by.md letters/sanitarnaya-sluzhba_smak-by.docx "${WHO[@]}" --variant 1 --appendix letters/sanitarnaya-sluzhba_smak-by_prilozhenie-1.md --note "$CGE"
python -I -X utf8 tools/letter_to_docx.py letters/gorispolkom_smak-by_raboty-fasad-torgovlya.md letters/gorispolkom_smak-by_raboty-fasad-torgovlya.docx "${WHO[@]}" --appendix letters/gorispolkom_smak-by_raboty-fasad-torgovlya_prilozhenie-1.md
