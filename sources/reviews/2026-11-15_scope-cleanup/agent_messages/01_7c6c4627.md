> Сообщение агента, дословно сохранённое основным сеансом из записи сеанса (скрипт `tools/save_agent_messages.py`). Субагенты не могут сами создавать файлы отчётов.

Дочистка выполнена: в текстовых файлах в рамках задания упоминаний не осталось (итоговая опись — 0), ни одна запись и ни один файл целиком не удалены, оценки всех 1115 записей не изменились. Отступлений от задания два: один файл сырой копии переименован, а не только правлен, и в `media.md` добавлена строка пояснения.

## Что изменено


| Вид | Файлов | Замен |
|---|---|---|
| Сырые копии (`raw/`) | 168 | 571 |
| Манифесты в `raw/` (адреса страниц в строках) | 2 | 5 |
| Рабочие выгрузки (`work/`, `notes/`) | 53 | 170 |
| Записи (`reviews.jsonl`, 8 записей) | 5 | 18 |
| Отчёты и сообщения агентов (`REPORT.md`, `agent_messages/`) | 5 | 5 |
| Скрипты агентов (ключевые слова поиска) | 4 | 6 |
| Расшифровки и субтитры ролика о фестивале | 3 | 4 |
| `meta.json` того же ролика | 1 | 4 |
| `checked_sources.jsonl` | 1 | 2 |

- **Манифесты:** обновлены 167 строк в 13 перечнях (12 `manifest.jsonl` и `derived.jsonl`): `sha256`, размер, поле `redacted`.
- **Хеши в других местах:** ещё 28 строк в 28 файлах — 27 `work/info_NNN.json` и таблица в `media.md`.
- **Свод:** `ALL.jsonl` и `INDEX.md` пересобраны; `reviews_merge` дал `collected=1115 unique=1001 format_errors=0`, как и до чистки.
- **Приложения к письмам:** все четыре описания в `letters/_src/` собираются; приложение санитарной службы по «Амазонке» совпало с лежащим в `letters/` побайтно.
- **Копии до правки:** 261 исходный файл плюс прежние `ALL.jsonl` и `INDEX.md` лежат в карантине `_strict` (73 МБ); остальной карантин не тронут.

Сверки после прогона:
- хеши всех 10,5 тыс. файлов проекта до и после: изменились только файлы из журнала и свод, изображения, видео и PDF не затронуты;
- 3726 строк перечней сходятся с диском;
- 86 изменённых JSON/JSONL разбираются с прежней структурой;
- повтор замен на копиях из карантина дал те же байты для 215 файлов.

## Восемь записей

| Запись | До | После | Где замена |
|---|---|---|---|
| aggregators-023 | OK | OK | notes |
| article-comments-086 | OK | OK | text, notes |
| article-comments-087 | OK | OK | text, notes |
| article-comments-112 | LOOSE | LOOSE | text, notes |
| crosslinks-014 | LOOSE | LOOSE | text, notes |
| crosslinks-015 | OK | OK | text, notes |
| media-forums-014 | OK | OK | notes |
| threads-instagram-012 | PARTIAL 85 % | PARTIAL 85 % | text, notes |

Во всех восьми в `notes` дописана заданная фраза.

## reviews_check по папкам

До и после одинаково, все 13 папок PASS, `missing=0`, `check_result.txt` побайтно прежние:

| Папка | Записей | ok | loose | partial | прочее |
|---|---|---|---|---|---|
| aggregators | 46 | 38 | 8 | 0 | — |
| article-comments | 143 | 57 | 86 | 0 | — |
| browser-gaps | 30 | 29 | 0 | 0 | 1 snippet |
| crosslinks | 26 | 15 | 6 | 0 | 5 snippet |
| employer | 14 | 2 | 0 | 5 | 7 snippet |
| google-maps | 104 | 98 | 6 | 0 | — |
| logged-in | 71 | 49 | 0 | 0 | 22 image |
| media-forums | 20 | 10 | 9 | 0 | 1 snippet |
| official | 33 | 23 | 9 | 0 | 1 snippet |
| search-engines | 142 | 98 | 0 | 0 | 44 snippet |
| social | 26 | 20 | 6 | 0 | — |
| threads-instagram | 126 | 125 | 0 | 1 | — |
| yandex-maps | 334 | 333 | 0 | 1 | — |

## Оставлено как не относящееся (282 случая)

| Случаев | Файлов | Что | Пример |
|---|---|---|---|
| 158 | 76 | улица Сурганова с другим домом или без номера | «г. Минск, ул. Сурганова, 43‑47», «ул. Сурганова, 9 (ЖЭУ №6)» |
| 19 | 10 | тег `#джентелменыудачи` (название фильма) | подпись ролика о гастрофесте |
| 7 | 1 | телефон в карточке бара «Бархат» | `023_google-maps_barhat-migaya-13_card.json` |
| 3 | 3 | ООО «Сели-Поели фуд», УНП 791071650 — другое юрлицо | списки санитарной службы 2024-04, 2025-04, 2026-04 |
| 2 + 2 | 1 | число 15287 и слово «Аур» в списке населённых пунктов | dreamjob.ru |
| 1 | 1 | имя снимка пользователя в ссылке | `2026-11-14_threads_masha-portugal_amazonka-13-11.md` |

Шаблонами вообще не ловятся и не тронуты: Restaurant, restaurantguru, «Лаура» (имя должностного лица в объявлении), шаурма, Науру, лауреат.

Ваши `final_check.py` и `check_folder.py` теперь показывают только случаи из этой таблицы и файлы из списка «не трогать».

## Решения за вами

- **Три строки «оставлено» — на грани.** «Сели-Поели фуд», телефон в карточке «Бархат»: ваши шаблоны их ловят, я оставил, потому что они относятся к другим лицам. Если нужно убрать и их, это три правила в `strict_patterns.py`.
- **Карточка «Бархат» связана с [исключено].** Она найдена по запросу «бар [исключено] Могилёв»: запрос был зашит в адресе карточки в base64 (в самой карточке и в манифесте google-maps), я его заменил.
- **Содержание об этих заведениях без названий осталось**, как и требовало задание: состав и вес сета в статьях о фестивале, ответы в ветках о том, кто владелец, координаты точки на mogilev.in, slivki.by и в KML-карте.
- **Правила в проекте устарели.** `CLAUDE.md`, `PROTOCOL.md`, `STATE.md` и описание в `tools/scope_filter.py` по-прежнему говорят, что дословные материалы не правятся. В `scope_filter.py` нет форм, которые я нашёл:
  - «aure»;
  - голое `15287` в перечнях карточек;
  - base64.

  При повторном сохранении отчётов агентов они могут вернуться.

## Изображения, видео и PDF (не трогались)

Название видно, проверено глазами:
- `C:\Users\y6vme\OneDrive\myDocuments\belarus\sources\reviews\2026-11-15_threads-instagram\screenshots\001_threads_masha_portugal_DfuxGCzjKsE.png`
- `C:\Users\y6vme\OneDrive\myDocuments\belarus\sources\reviews\2026-11-15_threads-instagram\screenshots\110_threads_masha_portugal_DfuxGCzjKsE_recheck.png`
- `C:\Users\y6vme\OneDrive\myDocuments\belarus\sources\reviews\2026-11-15_threads-instagram\screenshots\005_threads_ula.ruu_DfvGhOPCqXC.png`
- `C:\Users\y6vme\OneDrive\myDocuments\belarus\sources\reviews\2026-11-15_threads-instagram\screenshots\092_instagram_koroche__mogilev_DfpbpVNtnex_comments-expanded.png`
- `C:\Users\y6vme\OneDrive\myDocuments\belarus\sources\reviews\2026-11-15_article-comments\screenshots\042_tg_moymogilev_66759_post.png`

- `C:\Users\y6vme\OneDrive\myDocuments\belarus\sources\reviews\2026-11-15_media-social\media\telegram_moymogilev_66759\006.jpg` и обзорный лист `sheets\sheet_001.jpg` в той же папке
- `C:\Users\y6vme\OneDrive\myDocuments\belarus\sources\reviews\2026-11-15_media-social\media\tiktok_mogilevvv_7706196308712901906\image_10.jpg` и `sheets\sheet_001.jpg` там же



- `C:\Users\y6vme\OneDrive\myDocuments\belarus\sources\reviews\2026-11-15_official\raw\036_mzcge-by_mzcge-monitoring-plan-2025-03.pdf`
- `C:\Users\y6vme\OneDrive\myDocuments\belarus\sources\reviews\2026-11-15_search-engines\raw\083_mzcge-by_mzcge-monitoring-28022025.pdf`

Их текстовые копии `.txt` рядом исправлены и теперь расходятся с PDF; строк в манифесте у них нет.

## Что не сделано

- **Изображения просмотрены выборочно:** десятка три снимков и обзорных листов из примерно 5,2 тыс. изображений и 118 видео. Три группы ВКонтакте с медиа (`vk_202389635_20776`, `_21076`, `_30752`) не открывал.
- **`sources/reviews/2026-11-15_media-open/` и `.playwright-mcp/` не проверялись.** Когда агент закончит, по его папке нужен тот же проход (в `strict_scope.py` убрать её из исключений).
- **В `media.md` добавлена строка сверх задания:** пояснение, что размер и SHA-256 субтитров в таблице указаны после замены.
- **В скриптах агентов пометка записана как `\[исключено\]`**, иначе в регулярном выражении она стала бы набором букв.

## Где лежит

- Скрипты и журналы: `C:\Users\y6vme\AppData\Local\Temp\claude\100b58a5c7b086de\4eb31033-2696-4445-a42c-9e4b5218978b\scratchpad\strict\`
- Итоговая опись: `C:\Users\y6vme\AppData\Local\Temp\claude\100b58a5c7b086de\4eb31033-2696-4445-a42c-9e4b5218978b\scratchpad\strict\verify\verify_final.txt`
- Сводный журнал изменённых файлов: `C:\Users\y6vme\AppData\Local\Temp\claude\100b58a5c7b086de\4eb31033-2696-4445-a42c-9e4b5218978b\scratchpad\strict\changed_total.tsv`
