<!-- dir-readme:generated — этот файл создаёт tools/dir_readmes.py; описание папки правится в tools/dir_readmes.json -->
# Рабочие скрипты прохода

Скрипты, которыми при сборе разбирались страницы и собирались записи. Нужны, чтобы повторить или проверить шаги сбора.

<!-- dir-readme:start -->
## Что в этой папке

| Файл или папка | Что это |
|---|---|
| [build_media_md.py](build_media_md.py) | Собирает media.md из журнала файлов, данных страниц и заметок. |
| [crop_strip.py](crop_strip.py) | Вырезает один и тот же прямоугольник из нескольких кадров и ставит вырезки в ряд (для сравнения). |
| [drop_group.py](drop_group.py) | Убирает ошибочно сохранённую группу: файлы media/&lt;группа&gt;/ и её строки в media/manifest.jsonl. |
| [dup_check.py](dup_check.py) | Ищет среди скачанных в этом проходе файлов побайтные дубли файлов, уже лежащих в проекте. |
| [ig_embed_fetch.js](ig_embed_fetch.js) | Сохранённый скрипт страницы, 4 КБ |
| [ig_page_fetch.js](ig_page_fetch.js) | Сохранённый скрипт страницы, 4 КБ |
| [keep_evidence.py](keep_evidence.py) | Перед удалением .playwright-mcp/ переносит в work/ то, что подтверждает недоступность страниц. |
| [link_records.py](link_records.py) | Сопоставляет скачанные публикации с записями прежних сборов (по коду публикации в url записи). |
| [manifest_rename_fields.py](manifest_rename_fields.py) | Переименовывает в media/manifest.jsonl поля width/height/duration в declared_*. |
| [patch_notes.py](patch_notes.py) | Точечные правки заметок после повторного просмотра кадров (каждая правка — замена поля целиком). |
| [process_videos.py](process_videos.py) | Кадры и обзорные листы для каждого скачанного видео, у которого их ещё нет. |
| [save_dump.py](save_dump.py) | Сохраняет выгрузку из браузера (результат ig_embed_fetch.js или threads_fetch.js) в media/. |
| [scope_check.py](scope_check.py) | Проверяет текстовые файлы прохода фильтром проекта tools/scope_filter.py (заведения вне рамок работы). |
| [strip_dump.py](strip_dump.py) | Кладёт данные выгрузки без base64 в work/pages/ и ничего больше не делает. |
| [table_publications.py](table_publications.py) | Печатает таблицу «публикация → папка → файлы → длительность» по журналу файлов. |
| [threads_fetch.js](threads_fetch.js) | Сохранённый скрипт страницы, 4 КБ |
| [verify_media.py](verify_media.py) | Проверка папки media/ перед сдачей. |

[← Папка выше](../README.md) · [Путеводитель по проекту](../../../../README.md)
<!-- dir-readme:end -->
