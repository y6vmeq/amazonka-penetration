<!-- dir-readme:generated — этот файл создаёт tools/dir_readmes.py; описание папки правится в tools/dir_readmes.json -->
# Инструменты

Скрипты проекта: сбор и сохранение страниц, скачивание и разбор медиа, сверка цитат, сборка писем и документов, журнал изменений и отправка в GitHub. Как запускать — в `CLAUDE.md`. Скрипты на Python запускаются из корня проекта: `python -I -X utf8 tools/<имя>.py`.

<!-- dir-readme:start -->
## Что в этой папке

| Файл или папка | Что это |
|---|---|
| [b64_to_file.py](b64_to_file.py) | Превращает выгрузку base64 из браузера в файл и сверяет SHA-256 |
| [b64map_to_files.py](b64map_to_files.py) | Превращает набор выгрузок base64 из браузера в файлы и печатает SHA-256 |
| [changelog.py](changelog.py) | Журнал изменений проекта: запись в CHANGELOG.md и блок «Последние изменения» в README.md. |
| [dir_readmes.json](dir_readmes.json) | Тексты описаний папок для `dir_readmes.py` |
| [dir_readmes.py](dir_readmes.py) | Создаёт и обновляет README.md в папках проекта: описание папки и ссылки на её файлы и подпапки. |
| [fetch_raw.py](fetch_raw.py) | Сохраняет сырую копию веб-страницы как доказательство. |
| [frames_to_sheets.py](frames_to_sheets.py) | Раскладывает выгруженные из браузера кадры по файлам и собирает обзорные листы |
| [git_push.sh](git_push.sh) | Отправляет коммиты текущей ветки в GitHub по одному, от старого к новому. |
| [image_sheets.py](image_sheets.py) | Собирает обзорные листы из изображений, чтобы быстро просмотреть много фото. |
| [kartoteka_fetch.py](kartoteka_fetch.py) | Выгружает сведения по УНП через API kartoteka.by (нужен действующий токен) |
| [letter_appendix.py](letter_appendix.py) | Собирает приложение к обращению: перечень публикаций с дословными выдержками. |
| [letter_quotes_check.py](letter_quotes_check.py) | Сверяет цитаты «…» из проекта обращения с сохранёнными источниками. |
| [letter_standard_check.py](letter_standard_check.py) | Проверяет проект обращения на соответствие стандарту letters/STANDART.md (форма и обязательные блоки). |
| [letter_to_docx.py](letter_to_docx.py) | Оформляет проект обращения из letters/&lt;имя&gt;.md как документ Word. |
| [md_quotes_check.py](md_quotes_check.py) | Проверяет цитаты в кавычках-ёлочках из файла .md по сохранённым текстам актов. |
| [md_to_docx.py](md_to_docx.py) | Переводит рабочий файл Markdown (заголовки, абзацы, примечания «&gt;», таблицы, списки) в документ Word. |
| [media_download.py](media_download.py) | Скачивает фото и видео из открытых источников в папку сбора. |
| [office_text.py](office_text.py) | Извлекает текст из .docx и .pptx без запуска офисных программ. |
| [page_text.py](page_text.py) | Печатает текст и ссылки страницы, которых нет на странице-образце того же сайта |
| [pdf_pages.py](pdf_pages.py) | Превращает страницы PDF в изображения PNG |
| [pdf_text.py](pdf_text.py) | Извлекает текст из PDF в файл UTF-8 с пометками страниц. |
| [quotes_check.py](quotes_check.py) | Проверяет, что цитаты из нормативных актов дословно есть в сохранённых текстах. |
| [readme_links_check.py](readme_links_check.py) | Проверяет ссылки в путеводителе по проекту, журнале изменений и описаниях папок. |
| [review_summary.py](review_summary.py) | Сводит замечания и оценки проверяющих по набору обращений в одну таблицу. |
| [reviews_check.py](reviews_check.py) | Проверяет папку сбора отзывов: формат reviews.jsonl и дословность цитат. |
| [reviews_merge.py](reviews_merge.py) | Сводит записи всех папок сбора отзывов в общий перечень. |
| [save_agent_messages.py](save_agent_messages.py) | Сохраняет на диск сообщения субагентов из записи сеанса Claude Code. |
| [scope_filter.py](scope_filter.py) | Фильтр «вне рамок дела»: находит и убирает сведения о заведениях, исключённых из работы |
| [transcribe.py](transcribe.py) | Расшифровывает звук видео и аудио (faster-whisper, локально) |
| [video_frames.py](video_frames.py) | Снимает кадры из видеофайлов без браузера и ffmpeg (через PyAV) и собирает обзорные листы. |

[← Путеводитель по проекту](../README.md)
<!-- dir-readme:end -->
