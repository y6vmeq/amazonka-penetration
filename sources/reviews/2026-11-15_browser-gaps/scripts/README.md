<!-- dir-readme:generated — этот файл создаёт tools/dir_readmes.py; описание папки правится в tools/dir_readmes.json -->
# Рабочие скрипты прохода

Скрипты, которыми при сборе разбирались страницы и собирались записи. Нужны, чтобы повторить или проверить шаги сбора.

<!-- dir-readme:start -->
## Что в этой папке

| Файл или папка | Что это |
|---|---|
| [build_media_md.py](build_media_md.py) | Собирает media.md: перечень скачанных фото и видео с SHA-256 из media/manifest.jsonl. |
| [restoplace_table_photos.json](restoplace_table_photos.json) | Данные JSON, 4 КБ |
| [save_archive_copy.py](save_archive_copy.py) | Сохраняет выгрузку копии Wayback Machine (через save_capture.py) и печатает ключевые поля. |
| [save_capture.py](save_capture.py) | Раскладывает выгрузку страницы, сохранённую из браузера (Playwright MCP, |
| [save_stream_tracks.py](save_stream_tracks.py) | Сохраняет видео, полученное в браузере по сегментам (MPEG-DASH), и собирает один файл. |

[← Папка выше](../README.md) · [Путеводитель по проекту](../../../../README.md)
<!-- dir-readme:end -->
