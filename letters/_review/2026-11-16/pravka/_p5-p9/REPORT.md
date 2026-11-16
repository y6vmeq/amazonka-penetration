> Сообщение агента, дословно сохранённое основным сеансом из записи сеанса (скрипт `tools/save_agent_messages.py`). Субагенты не могут сами создавать файлы отчётов.

I've split the tax letter into two and both pass every check. I've also added your points 28–34 to both letters. The old combined letter and its appendix are untouched.

**П5 «Амазонка»** (`letters/nalogovaya_amazonka.md`, text ≈24.0 thousand characters)
- 6 circumstances and 14 questions. One question lists seven requirements (Т1–Т7), each to be answered yes / no / not checked, with the norm.
- Quotes: 95, all found word for word. Standard check: 0 errors, 0 warnings. Appendix: 8 rows, all excerpts found. The trial Word build works.
- Self-score: К1 9.5, К2 9.5, К3 9.5, К4 9.5, К5 9.5, К6 9.6, К7 9.3, К8 9.4.

**П9 «Смак.BY»** (`letters/nalogovaya_smak-by.md`, text ≈22.6 thousand characters)
- 3 circumstances and 14 questions, tied to the address and the publications rather than to any person.
- «До подачи нужно» is down to four items, so it can be filed electronically right away. It asks the inspectorate to come to the site before 29.11.2026.
- Quotes: 88, all found. Standard check: 0 errors, 0 warnings. Appendix: 4 rows. The Word build works.
- Self-score: К1 9.5, К2 9.6, К3 9.5, К4 9.5, К5 9.5, К6 9.5, К7 9.3, К8 9.5.

**Opponent's findings:** 20 fixed, 3 partly fixed, none rejected.
- **О21:** the letters are not cut to 18 thousand characters and 10/6 questions, because the standard requires the table question and the per-request decision questions.
- **О22:** I could not check whether the обращения.бел form accepts a text of about 24 thousand characters.
- **О23:** the Ministry's address (220010, г. Минск, ул. Советская, 9) is confirmed from the saved nalog.gov.by page, but `authorities/mogilev-imns.md` still says «адрес не сверялся». I was not allowed to edit that file.

On the tax-secret point: подпункт 1.9 статьи 29 only says that information about violations and penalties is not a tax secret. It does not oblige the inspectorate to report it, and the letters claim only the first.

I tried writing an evasive reply to each letter. Neither works anymore: each now leaves specific questions unanswered (for example, who decided not to act and under which norm), and each gap is a ground for a complaint. The tests are written up in the files.

**Still weak:**
- П5 has only six reviews behind it, from September to November 2026.
- In П9, the link between the 01.11.2026 fundraising post and «Смак.BY» rests only on the name.
- The cash-register rules (Положение № 924/16) do not apply to a private individual who is not registered as an entrepreneur; for that case the letter relies on пункт 7 статьи 74 Налогового кодекса.

**Decisions for you:**
1. Fix the address note in `authorities/mogilev-imns.md`.
2. Move the two-licence information and the 9% cash discount into П3.
3. The man in the 12.11 video calls himself the director. Decide whether that goes in a later addition to П9 — it first needs checking by ear against the automatic transcript.
4. Remove the old combined letter.

The answers to the opponent are in `letters/_review/2026-11-16/otvety/nalogovaya_amazonka-smak-by.json`. The appendices are `letters/_src/nalogovaya_amazonka_prilozhenie-1.json` and `letters/_src/nalogovaya_smak-by_prilozhenie-1.json`, built into `letters/nalogovaya_amazonka_prilozhenie-1.md` and `letters/nalogovaya_smak-by_prilozhenie-1.md`.
