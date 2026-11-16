<!-- dir-readme:generated — этот файл создаёт tools/dir_readmes.py; описание папки правится в tools/dir_readmes.json -->
# Рабочие скрипты прохода

Скрипты, которыми при сборе разбирались страницы и собирались записи. Нужны, чтобы повторить или проверить шаги сбора.

<!-- dir-readme:start -->
## Что в этой папке

| Файл или папка | Что это |
|---|---|
| [build_media_md.py](build_media_md.py) | Build media.md and work/media_index.json from the download log, video facts and hand-written notes. |
| [build_reviews.py](build_reviews.py) | Build reviews.jsonl from collected data and hand-made classification files. |
| [build_screenshot_index.py](build_screenshot_index.py) | Write screenshots/index.jsonl: one line per screenshot (file, url, captured_at, bytes, sha256, note). |
| [build_screenshot_map.py](build_screenshot_map.py) | Build work/screenshot_map.json: record URL -&gt; screenshot on which the publication is visible. |
| [fetch_media.js](fetch_media.js) | Сохранённый скрипт страницы, 1 КБ |
| [fetch_media_next.js](fetch_media_next.js) | Сохранённый скрипт страницы, 1 КБ |
| [hook_init.js](hook_init.js) | Сохранённый скрипт страницы, 1 КБ |
| [ig_crawl.js](ig_crawl.js) | Сохранённый скрипт страницы, 9 КБ |
| [ig_crawl_get.js](ig_crawl_get.js) | Сохранённый скрипт страницы, 1 КБ |
| [ig_extract.js](ig_extract.js) | Сохранённый скрипт страницы, 9 КБ |
| [ig_shot_expand.js](ig_shot_expand.js) | Сохранённый скрипт страницы, 3 КБ |
| [ig_shot_prep.js](ig_shot_prep.js) | Сохранённый скрипт страницы, 2 КБ |
| [media_plan.py](media_plan.py) | Plan media downloads: write browser configs (work/mcfg_NN.js) for fetch_media.js and a plan file. |
| [media_plan_ig.py](media_plan_ig.py) | Plan Instagram media downloads for the post codes listed in work/ig_media_codes.json. |
| [overview_sheets.py](overview_sheets.py) | Make one compact overview sheet per video from already extracted frames. |
| [process_videos.py](process_videos.py) | Frames and contact sheets for every downloaded video that has none yet. |
| [save_dump.py](save_dump.py) | Split browser dumps into raw copies + data files and merge Threads posts into one table. |
| [save_media.py](save_media.py) | Save media fetched in the browser (fetch_media.js dump) to media/&lt;folder&gt;/ and log them. |
| [shot_check.js](shot_check.js) | Сохранённый скрипт страницы, 1 КБ |
| [shot_times.py](shot_times.py) | Collect the moments when screenshots were returned by the browser, from the session log of the agent. |
| [shots_crop.py](shots_crop.py) | Cut the part of a screenshot that lies below the publication itself (suggested posts of unrelated authors). |
| [shots_verify.py](shots_verify.py) | Verify Threads screenshots taken with scripts/shot_check.js. |
| [threads_crawl.js](threads_crawl.js) | Сохранённый скрипт страницы, 11 КБ |
| [threads_crawl_get.js](threads_crawl_get.js) | Сохранённый скрипт страницы, 1 КБ |
| [threads_crawl_status.js](threads_crawl_status.js) | Сохранённый скрипт страницы, 1 КБ |
| [threads_extract.js](threads_extract.js) | Сохранённый скрипт страницы, 11 КБ |
| [threads_full.js](threads_full.js) | Сохранённый скрипт страницы, 12 КБ |
| [threads_load_all.js](threads_load_all.js) | Сохранённый скрипт страницы, 1 КБ |
| [threads_profiles.js](threads_profiles.js) | Сохранённый скрипт страницы, 5 КБ |
| [tree.py](tree.py) | Print reply trees from work/threads_posts.json and list posts whose direct replies are not all collected. |

[← Папка выше](../README.md) · [Путеводитель по проекту](../../../../README.md)
<!-- dir-readme:end -->
