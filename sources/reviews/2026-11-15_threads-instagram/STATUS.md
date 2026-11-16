# STATUS: агент threads-instagram (сбор 15.11.2026)

Обновлено: 15.11.2026, 15:45 по Минску (12:45 UTC). Работа завершена, вкладки браузера закрыты. Итоговый отчёт отправлен координатору сообщением: файл `REPORT.md` в этой папке записывает основной сеанс из моего сообщения.

Поправка о времени. В промежуточном отчёте и в прежних версиях этого файла время в тексте было указано неверно (например, «15:05 по Минску» вместо 13:59). Верны машинные отметки: `fetched_at` в `raw/manifest.jsonl`, `captured_at` в `reviews.jsonl` и в `screenshots/index.jsonl` (все в UTC; Минск = UTC+3). Сбор шёл с 09:50 до 12:45 UTC.

## Что лежит на диске

- `reviews.jsonl` — 131 запись: Threads 97, Instagram 34. Проверка `python -I tools/reviews_check.py sources/reviews/2026-11-15_threads-instagram`: `records=131 ok=130 loose=0 partial=1 missing=0 no-raw=0 image=0 snippet=0 empty=0 format_errors=0 reply_problems=0` — PASS. PARTIAL — запись `threads-instagram-012`: по протоколу в ней заменена на `[личные сведения опущены]` фраза об образе жизни и автомобиле.
- `raw/` — 134 сырые копии (`raw/manifest.jsonl`): DOM страниц Threads после прокрутки, ответы сервера на GET страниц Threads и Instagram, ответы GraphQL, которые получили сами страницы.
- `media/` — 124 файла: 41 видео и 83 изображения; для каждого видео — `frames/`, `sheets/`, расшифровка. `media.md` — описание каждого файла с SHA-256, а в конце сводные разделы: «Сопоставление видео о ремонте», «Животные в зале», «Столы и посадочные места», «Теги», «Что не скачивалось», «Помещение по адресу «Смак.BY» в апреле 2024 г.».
- `screenshots/` — 57 снимков, у каждой из 131 записи есть снимок. `screenshots/index.jsonl` — для каждого снимка адрес страницы, время съёмки (UTC), SHA-256 и что с ним сделано.
- `work/` — рабочие данные: `threads_posts.json` (338 постов и ответов Threads), `tree.txt` (дерево ответов с полным текстом), `ig_posts.json` (публикации и комментарии Instagram), разметка `classify_threads.json` и `classify_ig.json`, журнал медиа `media_log.jsonl`, заметки `media_notes_*.json`, `screenshot_map.json`, `shots/` (проверки страниц перед снимками), `threads_profiles_checked.json` (какие профили Threads просмотрены).
- `scripts/` — скрипты сбора и сборки.

## Как сделаны снимки экрана

- Threads, страницы постов: снимок всей ветки от поста до конца ответов. Низ обрезан перед блоком «Связанные ветки» — там площадка показывает публикации посторонних авторов.
- Threads, страницы ответов: площадка сама прокручивает страницу к открытому ответу, посты выше него в кадр не попали (они есть на снимках корневых постов).
- Instagram, файлы `_view.png`: вид страницы без входа после закрытия окна с предложением зарегистрироваться (его же кнопкой «Закрыть»).
- Instagram, файлы `_comments-expanded.png`: область подписи и комментариев на странице прокручивается внутри карточки высотой около 390 пикселей. Чтобы вся подпись и все комментарии, которые страница отдаёт без входа, попали на один снимок, эта область растянута на всю высоту (изменён только стиль блока, текст не менялся). Низ обрезан под карточкой публикации.
- Перед каждым снимком скрипт записывал адрес открытой страницы и список видимых постов или авторов комментариев (`work/shots/*.json`); сверка: `scripts/shots_verify.py`.
- Первый снимок Instagram `049_instagram_gastrofest.mogilev_DfZejAqjGTZ.png` (10:54 UTC) закрыт окном «Посмотреть все комментарии» и почти не читается; оставлен, записи ссылаются на новые снимки.

## Threads: итог

Счётчик под корневым постом — число всех ответов ветки (со вложенными). Состояние на 12:18 UTC 15.11.2026.

| Корневой пост | Счётчик | Собрано | Медиа скачано и разобрано |
|---|---|---|---|
| https://www.threads.com/@masha_portugal/post/DfuxGCzjKsE | 57 | 55 | в ветке медиа нет; видео с тараканами автор не публиковала |
| https://www.threads.com/@_ananacc/post/Dfq-YE2EWpt | 61 | 60 | 8 фото |
| https://www.threads.com/@gurbamladshiy/post/DfsDkxTESCq | 63 | 58 | 1 фото, 1 видео (ещё 3 видео скачаны 14.11) |
| https://www.threads.com/@ula.ruu/post/DfvGhOPCqXC | 4 | 4 + вложенные | нет |
| https://www.threads.com/@ula.ruu/post/Dfmpin6Ctpv | 35 | 33 | нет |
| https://www.threads.com/@viksha2704/post/DfrlrgOkbQO | 49 | 37 | 1 видео, 3 фото |
| https://www.threads.com/@homutovivan.cheff/post/DfsF8sDiIBS | 37 | 34 | медиа о другом кафе, не скачивались |
| https://www.threads.com/@katsukitsu/post/Dfu9M6hmERg | 0 | пост | нет |
| аккаунт @amazonka_restobar_mogilev | видно 15 публикаций | 15 | 15 видео |

Проходы по главным веткам: первый сбор 09:55–10:20 UTC; повторный обход 11:24–11:26 UTC (новый ответ egorka.pro100 под постом viksha2704 — записан, `threads-instagram-127`); второй повторный обход 12:18–12:19 UTC (новый ответ malvineww под постом masha_portugal от 11:35 UTC — сохранён в `raw/116_…recheck2.html` и в `work/threads_posts.json`; сведений о заведении в нём нет, отдельной записью не оформлен). Страницы 18 ответов открывались ещё раз в 12:00–12:04 UTC для снимков: несобранных ответов на них нет.

## Instagram: итог

- Посты @gastrofest.mogilev: `/p/DfZejAqjGTZ/` («Амазонка», видно 5 комментариев из 8, 9 фото), `/p/DfhVI_UjMdT/` («Смак.BY», 11 из 22, 6 фото), `/p/DWoYqG7DOoj/` («Амазонка», весна 2026, 4 из 7, 7 фото).
- @amazonka_restobar_mogilev: описание профиля, 12 публикаций ленты и 12 рилсов, видимых без входа, плюс публикации из поисковой выдачи; медиа скачаны и разобраны.
- @smak.by_mogilev: по-прежнему 2 публикации, новых нет.
- @lukyanova_yelizaveta: новых деловых публикаций нет; 12 рилсов вкладки проверены (см. `media.md`, «Сопоставление видео о ремонте»).
- @amazonka_restobar_minsk, @gastrofest.by, @koroche__mogilev — профили просмотрены.
- Обзоры и чужие публикации о животных в зале: @zatestilmogilev, @koroche__mogilev, @mogilev_online, @vidosy_mogilev, @the_diaanaa, @eatandmeet.go — скачаны и разобраны.
- Сверка в 12:07–12:11 UTC: под 17 публикациями видны те же комментарии, что были собраны; новых нет.
- Последнее чтение наводок агентов search-engines и crosslinks (12:25 UTC) дало новые адреса; все открыты в 12:28–12:33 UTC:
  - https://www.instagram.com/p/CvCYnJLtsSi/ (@obzor_rb, 23.07.2023, об открытии заведения) — 2 фото и 4 видео скачаны и разобраны, запись `threads-instagram-130`;
  - https://www.instagram.com/p/CwJZX6YorC3/ (заведение, 20.08.2023) — фото скачано, запись `threads-instagram-131`;
  - https://www.instagram.com/reel/C5TFSglo8Mg/ (@slivkiby_mogilev, 03.04.2024) — о «Карчме на Шкловском базаре» по адресу ул. Будённого, 13/44; видео скачано и разобрано, записью не оформлено (не о «Смак.BY»), см. `media.md`;
  - https://www.instagram.com/p/C8X1LJToFgG/ и https://www.instagram.com/p/C8X0wE_I2jx/ — страница ошибки;
  - https://www.instagram.com/amazonka_mogilev_/ — магазин белья, не относится; https://www.instagram.com/colette_mogilev/ — ресто-бар «Colette», адреса в описании нет;
  - Threads: https://www.threads.com/@tg_minsk_kids/post/DfMmflAlx8n и https://www.threads.com/@tg_minsk_kids/post/Dd_mtCYCujP (афиша для детей в Минске называет минскую «Амазонку» с «контактными рептилиями»; сохранены, `raw/126…`, `raw/127…`), https://www.threads.com/@hansha1980/post/DYwa-gcDGnk и https://www.threads.com/@ilya_777_1907/post/DcDWxY5ClwO (упоминания минского заведения без сведений о нарушениях, не сохранялись), https://www.threads.com/@tg_minsk_kids/post/DfNNtKZF03Z (перенаправление на вход).

## Закрыто входом или недоступно

- Threads: поиск и страницы тегов; часть ответов веток (разница между счётчиком и собранным); профиль «Амазонки» дальше 15 публикаций; профили @smak.by_mogilev, @lukyanova_yelizaveta, @gastrofest.mogilev, @koroche_mogilev, @koroche__mogilev перенаправляют на вход.
- Instagram: остальные комментарии под постами (кнопка подгрузки без входа ничего не даёт); публикации старше 12 последних в каждом профиле; истории; страницы отметок (`/tagged/`); страницы тегов `/explore/tags/amazonkarestobar/`, `/explore/tags/gastrofest2026/`.
- Instagram, подборки историй в профиле @amazonka_restobar_mogilev (обложки: «РЕПТИЛИИ», «ГОСТИ», «МЕНЮ», «САЙТ ДОСТАВКИ», «КАЛЬЯН», «АВТОРСКИЕ КОКТЕЙЛИ»): страница подборки без входа показывает только предложение зарегистрироваться (`raw/115_instagram_highlight_…html`). Ссылки: https://www.instagram.com/stories/highlights/17932495397355084/ (рептилии), https://www.instagram.com/stories/highlights/17877971573548901/ (кальян), https://www.instagram.com/stories/highlights/18123963889433839/ (гости), https://www.instagram.com/stories/highlights/17884284482344115/ (меню), https://www.instagram.com/stories/highlights/18048706348833684/ (доставка), https://www.instagram.com/stories/highlights/17966902937017591/ (коктейли).
- Удалены или недоступны: https://www.instagram.com/p/DTDmtjeiE4Z/ , https://www.instagram.com/p/CxgZtl-o7H7/ , https://www.instagram.com/p/Cza3gcVIYU8/ , https://www.instagram.com/p/C8X1LJToFgG/ , https://www.instagram.com/p/C8X0wE_I2jx/ .
- https://www.instagram.com/amazonka_restobar/ (второй ник из объявлений о продаже бизнеса) — страница без данных профиля.

## Не сделано

- Не определено точное место метки на снимке карты из ответа arlertttts (нужна карта): `media/threads_arlertttts_DfvGpa0CNyk/…img2.jpg`.
- Не найден ответ со списком «Рестобар «Колетт» (Буденного, 13/44)» из поисковой выдачи (ветка https://www.threads.com/@anastacia_zarovskaya/post/DW6KBsLiJsn, 190 ответов, без входа видна часть).
- Ветка https://www.threads.com/@homutovivan.cheff/post/DfsF8sDiIBS после 10:15 UTC повторно не обходилась.

## Дополнительные указания координатора (все учтены)

1. Кадры из видео — `tools/video_frames.py`.
2. Сопоставление 12 видео о ремонте с рилсами — раздел в `media.md`.
3. Теги — раздел в `media.md`.
4. Число мест — раздел в `media.md`.
5. Животные в зале — записи в `reviews.jsonl` (`neutral`, `other`, в `notes` — «Животные в зале») и раздел в `media.md`.
6. Скачивать и разбирать все видео и фото, включая Instagram.
7. Отчёты — сообщением координатору.

## Как продолжать (если понадобится)

- Браузер: chrome-devtools MCP, контекст `threads-ig`; страницы открывать через `new_page` с `isolatedContext: "threads-ig"`, `background: true`. В этом сборе снимки экрана стабильно получались у вкладки, открытой в контексте первой; у второй вкладки `take_screenshot` часто завершался таймаутом. Поэтому все снимки сделаны в одной вкладке по очереди.
- Threads, полная выгрузка ветки: `emulate` viewport `1280x16000x1` → `navigate_page` с `initScript` (текст — `scripts/hook_init.js`, одной строкой) → `evaluate_script` (`sourcePath: scripts/threads_full.js`, `filePath: work/dump.json`) → `python -I scripts/save_dump.py work/dump.json threads <имя>`.
- Threads, вложенные ответы: `scripts/threads_crawl.js` (`window.__cfg = {seeds, visited, maxPages, delayMs, follow}`), выгрузка `scripts/threads_crawl_get.js`, сохранение `python -I scripts/save_dump.py <часть.json> [--only коды]`.
- Instagram: `scripts/ig_crawl.js` (`window.__igcfg = {urls, delayMs}`), выгрузка `scripts/ig_crawl_get.js`, сохранение тем же `save_dump.py`.
- Медиа: `scripts/media_plan.py threads` или `scripts/media_plan_ig.py` (ему нужен список кодов публикаций в `work/ig_media_codes.json`) → в браузере выполнить созданный `work/mcfg_all.js`, затем `scripts/fetch_media_next.js` с `filePath` → `python -I scripts/save_media.py <dump>` → `python -I scripts/process_videos.py` → `python -P tools/transcribe.py <видео…>` → заметки в `work/media_notes_*.json` → `python -I scripts/build_media_md.py`.
- Снимки: Threads — viewport `1280x5000x1`, перед снимком `scripts/shot_check.js` с `filePath: work/shots/<имя>.json`, затем `take_screenshot`; Instagram — viewport `1280x900x1`, `scripts/ig_shot_prep.js` → снимок `_view.png` → `scripts/ig_shot_expand.js` → снимок всей страницы `_comments-expanded.png`. После этого `python -I scripts/shots_verify.py`, `python -I scripts/shots_crop.py --apply`, `python -I scripts/build_screenshot_map.py`. Время съёмки для `screenshots/index.jsonl` берётся из `work/shots/_shot_times.json`; его пересобирает `python -I scripts/shot_times.py <запись сеанса агента .jsonl>`, затем `python -I scripts/build_screenshot_index.py`.
- Сборка и проверка: `python -I scripts/build_ig_records.py`, `python -I scripts/build_reviews.py`, `python -I tools/reviews_check.py sources/reviews/2026-11-15_threads-instagram`.

> 15.11.2026: по решению пользователя из этого файла удалены сведения о заведениях, исключённых из работы.
