<!-- dir-readme:generated — этот файл создаёт tools/dir_readmes.py; описание папки правится в tools/dir_readmes.json -->
# Рабочие скрипты прохода

Скрипты, которыми при сборе разбирались страницы и собирались записи. Нужны, чтобы повторить или проверить шаги сбора.

<!-- dir-readme:start -->
## Что в этой папке

| Файл или папка | Что это |
|---|---|
| [build_media_md.py](build_media_md.py) | Собирает media.md из написанных вручную частей (work/media_part_*.md) и приложения с файлами. |
| [dense_sheets.py](dense_sheets.py) | Плотные обзорные листы из уже снятых кадров (для быстрого просмотра многих видео). |
| [dupes.py](dupes.py) | Ищет одинаковые по содержанию снимки в разных группах (перцептивный хеш dHash 16x16). |
| [list_media.py](list_media.py) | Выписывает из reviews.jsonl чужих агентов записи с медиа и ссылками (рабочая таблица). |
| [list_media_compact.py](list_media_compact.py) | Компактная таблица: записи чужих агентов, их ссылки и поля media. |
| [magilev_extract.py](magilev_extract.py) | Из сохранённых статей magilev.by выписывает фото (полный размер) с подписями и встроенные видео. |
| [manifest_add.py](manifest_add.py) | Дописывает в media/manifest.jsonl файлы, полученные не через tools/media_download.py (например, yt-dlp). |
| [ok_grab.js](ok_grab.js) | Сохранённый скрипт страницы, 3 КБ |
| [page_images.py](page_images.py) | Выписывает из сохранённых страниц (raw/*.html) адреса изображений и видео: &lt;img&gt;, srcset, data-src, |
| [preview.py](preview.py) | Уменьшенная копия снимка для просмотра (исходник не меняется). |
| [process_videos.py](process_videos.py) | Для каждой группы в media/ снимает кадры с лучшего по разрешению видео и готовит список для расшифровки. |
| [tg_extract.py](tg_extract.py) | Достаёт из сохранённых страниц Telegram (embed) адреса фото и видео, дату и текст поста. |
| [tg_lists.py](tg_lists.py) | Из work/tg_extract.json делает списки ссылок для tools/media_download.py (--list). |
| [tt_decode.py](tt_decode.py) | Раскладывает выгрузку из браузера (scripts/tt_grab.js, tt_grab_multi.js и подобные) по файлам в media/&lt;группа&gt;/. |
| [tt_grab.js](tt_grab.js) | Сохранённый скрипт страницы, 5 КБ |
| [tt_grab_multi.js](tt_grab_multi.js) | Сохранённый скрипт страницы, 6 КБ |
| [vk_lists.py](vk_lists.py) | Находит прямые адреса фото ВКонтакте для записей агента social. |

[← Папка выше](../README.md) · [Путеводитель по проекту](../../../../README.md)
<!-- dir-readme:end -->
