<!-- dir-readme:generated — этот файл создаёт tools/dir_readmes.py; описание папки правится в tools/dir_readmes.json -->
# Рабочие скрипты прохода

Скрипты, которыми при сборе разбирались страницы и собирались записи. Нужны, чтобы повторить или проверить шаги сбора.

<!-- dir-readme:start -->
## Что в этой папке

| Файл или папка | Что это |
|---|---|
| [batch_pages.js](batch_pages.js) | Сохранённый скрипт страницы, 6 КБ |
| [batch_pages.min.js](batch_pages.min.js) | Сохранённый скрипт страницы, 5 КБ |
| [batch_search.js](batch_search.js) | Сохранённый скрипт страницы, 3 КБ |
| [batch_search.min.js](batch_search.min.js) | Сохранённый скрипт страницы, 2 КБ |
| [batch_tg.js](batch_tg.js) | Сохранённый скрипт страницы, 4 КБ |
| [batch_tg.min.js](batch_tg.min.js) | Сохранённый скрипт страницы, 3 КБ |
| [batch_tg_disc.js](batch_tg_disc.js) | Сохранённый скрипт страницы, 3 КБ |
| [batch_tg_disc.min.js](batch_tg_disc.min.js) | Сохранённый скрипт страницы, 2 КБ |
| [batch_tg_search.js](batch_tg_search.js) | Сохранённый скрипт страницы, 3 КБ |
| [batch_tg_search.min.js](batch_tg_search.min.js) | Сохранённый скрипт страницы, 2 КБ |
| [batch_vk.js](batch_vk.js) | Сохранённый скрипт страницы, 4 КБ |
| [batch_vk.min.js](batch_vk.min.js) | Сохранённый скрипт страницы, 3 КБ |
| [build_media_md.py](build_media_md.py) | Собирает media.md: описание скачанных фото (раздел 11 PROTOCOL.md). |
| [checked.py](checked.py) | Дописывает строку в рабочую таблицу checked.jsonl (одна проверенная страница). |
| [gen_set_jobs.py](gen_set_jobs.py) | Собирает сценарий scripts/set_jobs_magilev.js: кладёт во вкладку-накопитель задания для batch_pages.js |
| [gen_site_new_jobs.py](gen_site_new_jobs.py) | Собирает scripts/set_jobs_site_new.js: задания batch_pages.js для новых статей komkur.info и masheka.by |
| [init_helpers.js](init_helpers.js) | Сохранённый скрипт страницы, 7 КБ |
| [init_helpers.min.js](init_helpers.min.js) | Сохранённый скрипт страницы, 5 КБ |
| [init_tg.js](init_tg.js) | Сохранённый скрипт страницы, 9 КБ |
| [init_tg.min.js](init_tg.min.js) | Сохранённый скрипт страницы, 8 КБ |
| [init_vk.js](init_vk.js) | Сохранённый скрипт страницы, 9 КБ |
| [init_vk.min.js](init_vk.min.js) | Сохранённый скрипт страницы, 8 КБ |
| [list_urls.py](list_urls.py) | Выписывает из свода ALL.jsonl адреса по площадкам для прохода article-comments. |
| [magilev_search.js](magilev_search.js) | Сохранённый скрипт страницы, 5 КБ |
| [magilev_search.min.js](magilev_search.min.js) | Сохранённый скрипт страницы, 3 КБ |
| [minify.py](minify.py) | Сжимает сценарий для browser_run_code_unsafe: убирает строки-комментарии и отступы. |
| [ok_inspect.py](ok_inspect.py) | Осмотр сохранённых страниц ok.ru (сырой HTML с сервера): есть ли в разметке комментарии. |
| [save_file_raw.py](save_file_raw.py) | Кладёт уже скачанный файл (например, страницу, полученную curl с другим User-Agent) в raw/ и в manifest. |
| [save_raw.py](save_raw.py) | Превращает снимок страницы из браузера в сырую копию и записывает её в manifest. |
| [save_search.py](save_search.py) | Раскладывает выгрузку поиска по сайту (scripts/magilev_search.js и ему подобные) в сырые копии. |
| [scan_summary.py](scan_summary.py) | Краткая сводка work/scan_&lt;сайт&gt;.json: по каждой статье — какие упоминания найдены. |
| [set_jobs_magilev.js](set_jobs_magilev.js) | Сохранённый скрипт страницы, 5 КБ |
| [set_jobs_search.js](set_jobs_search.js) | Сохранённый скрипт страницы, 3 КБ |
| [set_jobs_site_new.js](set_jobs_site_new.js) | Сохранённый скрипт страницы, 4 КБ |
| [site_search_lists.py](site_search_lists.py) | Сводит страницы поиска по сайтам komkur.info и masheka.by (work/info_NNN.json с extra.links) |

[← Папка выше](../README.md) · [Путеводитель по проекту](../../../../README.md)
<!-- dir-readme:end -->
