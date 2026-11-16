<!-- dir-readme:generated — этот файл создаёт tools/dir_readmes.py; описание папки правится в tools/dir_readmes.json -->
# Рабочие скрипты прохода

Скрипты, которыми при сборе разбирались страницы и собирались записи. Нужны, чтобы повторить или проверить шаги сбора.

<!-- dir-readme:start -->
## Что в этой папке

| Файл или папка | Что это |
|---|---|
| [build_reviews.py](build_reviews.py) | Собирает reviews.jsonl из сырых копий по описанию в records_spec.json. |
| [fetch2.py](fetch2.py) | Обёртка над tools/fetch_raw.py: та же функция fetch() и тот же manifest.jsonl. |
| [html2txt.py](html2txt.py) | Грубое преобразование сохранённой HTML-страницы в текст для чтения (UTF-8). |
| [records_spec.json](records_spec.json) | Данные JSON, 24 КБ |
| [search.py](search.py) | Запросы к поисковику Brave Search через curl; выдача сохраняется во временной папке. |
| [tgcomments.py](tgcomments.py) | Комментарии к постам каналов Telegram через открытый виджет обсуждения |
| [tgparse.py](tgparse.py) | Разбор сохранённых страниц t.me/s/&lt;канал&gt;: сообщения в читаемый UTF-8. |
| [tgpeek.py](tgpeek.py) | Просмотр последних сообщений канала без сохранения страницы: первые 160 знаков каждого. |
| [tgprobe.py](tgprobe.py) | Проверка существования открытых каналов Telegram без сохранения страниц. |
| [ttparse.py](ttparse.py) | Разбор сохранённых страниц TikTok: встраиваемые страницы тегов и профилей (/embed/tag/&lt;тег&gt;, |
| [vk_decode.py](vk_decode.py) | Раскодирует данные постов из сохранённой страницы vk.com в отдельный JSON рядом с ней. |
| [vkparse.py](vkparse.py) | Разбор сохранённых страниц vk.com (стена, пост, поиск по стене): посты и комментарии. |
| [vkprobe.py](vkprobe.py) | Проверка существования сообществ ВКонтакте без сохранения страниц. |
| [ysearch.py](ysearch.py) | Запросы к поисковику Yahoo Search через curl; выдача сохраняется во временной папке (не в проекте). |
| [ytparse.py](ytparse.py) | Разбор сохранённых страниц YouTube: выдача поиска (ytInitialData) и страница видео |

[← Папка выше](../README.md) · [Путеводитель по проекту](../../../../README.md)
<!-- dir-readme:end -->
