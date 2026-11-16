"""Сводит страницы поиска по сайтам komkur.info и masheka.by (work/info_NNN.json с extra.links)
в списки адресов статей: work/search_komkur-info.json и work/search_masheka-by.json
(тот же вид, что у scripts/save_search.py, чтобы затем запустить scripts/scan_articles.py).

Запуск из корня проекта:
    python -I -X utf8 sources/reviews/2026-11-15_article-comments/scripts/site_search_lists.py
"""
import json
import re
from collections import OrderedDict
from pathlib import Path

BASE = Path("sources/reviews/2026-11-15_article-comments")
WORK = BASE / "work"
ARTICLE = {
    "komkur.info": re.compile(r"^https://komkur\.info/(?!component|tag|images|media)[a-z0-9-]+/[a-z0-9-]{12,}/?$"),
    "masheka.by": re.compile(r"^https://masheka\.by/[a-z0-9/-]+/\d+-[a-z0-9-]+\.html$"),
}


def norm(url):
    return re.sub(r"[?#].*$", "", url or "").rstrip("/")


known = set()
for line in Path("sources/reviews/ALL.jsonl").read_text(encoding="utf-8-sig").splitlines():
    if line.strip():
        known.add(norm(json.loads(line).get("url")))

sites = {"komkur.info": {"queries": [], "urls": OrderedDict()}, "masheka.by": {"queries": [], "urls": OrderedDict()}}
for path in sorted(WORK.glob("info_*.json")):
    data = json.loads(path.read_text(encoding="utf-8"))
    extra = data.get("extra") or {}
    if not isinstance(extra, dict) or extra.get("site") not in sites or "links" not in extra:
        continue
    site = sites[extra["site"]]
    counted = 0
    for link in extra["links"]:
        url = norm(link["href"])
        if not ARTICLE[extra["site"]].match(url):
            continue
        counted += 1
        entry = site["urls"].setdefault(url, {"url": url, "text": link["text"][:160], "queries": [], "in_all": url in known})
        if extra["query"] not in entry["queries"]:
            entry["queries"].append(extra["query"])
    site["queries"].append({"query": extra["query"], "file": data["html"], "summary": extra.get("summary"), "article_links_on_page": counted, "name": extra.get("name")})

for name, site in sites.items():
    slug = name.replace(".", "-")
    result = {"site": name, "queries": site["queries"], "urls": list(site["urls"].values())}
    (WORK / f"search_{slug}.json").write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    print(name, "search pages:", len(site["queries"]), "unique article links:", len(site["urls"]), "known:", sum(1 for entry in site["urls"].values() if entry["in_all"]))
