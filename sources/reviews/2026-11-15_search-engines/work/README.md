<!-- dir-readme:generated — этот файл создаёт tools/dir_readmes.py; описание папки правится в tools/dir_readmes.json -->
# Рабочие файлы прохода

Промежуточные таблицы, выгрузки и списки. Итог прохода — в `REPORT.md` и других файлах уровнем выше.

<!-- dir-readme:start -->
## Что в этой папке

| Файл или папка | Что это |
|---|---|
| [chunks/](chunks/) | Вспомогательная подпапка · файлов: 57 |
| [STATE.md](STATE.md) | Рабочее состояние агента search-engines (для возобновления после сжатия контекста) |
| [domains.txt](domains.txt) | Текст, 7 КБ |
| [extra_leads.md](extra_leads.md) | Архивные копии официальных страниц, которые не открываются напрямую |
| [extract_verified.py](extract_verified.py) | Достаёт отзывы и фрагменты из сырых копий (raw/) и пишет work/verified.jsonl. |
| [fetch_list.txt](fetch_list.txt) | Текст, 12 КБ |
| [fetch_many.py](fetch_many.py) | Сохраняет сырые копии страниц по списку work/fetch_list.txt через tools/fetch_raw.py. |
| [final_list.txt](final_list.txt) | Текст, 31 КБ |
| [hash_check.txt](hash_check.txt) | Текст, 1 КБ |
| [peek.py](peek.py) | Показывает текст вокруг ключевых слов в сырой копии: python -I work/peek.py &lt;шаблон имени&gt; &lt;слово&gt; [ширина] [макс]. Результат — в work/peek.txt. |
| [progress.md](progress.md) | Ход работы (обновляется после каждой пачки) |
| [querylist.txt](querylist.txt) | Текст, 10 КБ |
| [reviews_meta.tsv](reviews_meta.tsv) | Таблица: строк — 46 |
| [verified.jsonl](verified.jsonl) | Записи, по одной в строке: строк — 98 |

[← Папка выше](../README.md) · [Путеводитель по проекту](../../../../README.md)
<!-- dir-readme:end -->
