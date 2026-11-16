"""Проверка существования сообществ ВКонтакте без сохранения страниц.

usage: python -I vkprobe.py <out_txt> <screen_name> [...]
"""
import html
import re
import subprocess
import sys
import time
from pathlib import Path

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36")
JSON_STRING = r'((?:[^"\\]|\\.)*)'


def probe(name):
    cmd = ["curl", "--silent", "--location", "--compressed", "--connect-timeout", "20", "--max-time", "60",
           "--user-agent", UA, "--header", "Accept-Language: ru,be;q=0.8,en;q=0.5",
           "--write-out", "\n%{http_code}\t%{url_effective}", f"https://vk.com/{name}"]
    res = subprocess.run(cmd, capture_output=True)
    raw = res.stdout
    try:
        body = raw.decode("utf-8")
    except UnicodeDecodeError:
        body = raw.decode("cp1251", "replace")
    text, _, tail = body.rpartition("\n")
    status = tail.split("\t")[0]
    title = re.search(r"<title>(.*?)</title>", text, re.S)
    group = re.search(r'"groups":\[\{"id":(\d+),"description":"' + JSON_STRING + r'","members_count":(\d+)', text)
    gname = re.search(r'"name":"' + JSON_STRING + r'","screen_name":"' + re.escape(name) + '"', text)
    info = f"{name}: http={status} bytes={len(text)} title={html.unescape(title.group(1)).strip() if title else None!r}"
    if group:
        info += (f" | id={group.group(1)} members={group.group(3)} name={gname.group(1) if gname else None!r} "
                 f"desc={group.group(2)[:200]!r}")
    else:
        gid = re.search(r'"group_id":(\d+)|"owner_id":-(\d+)|public(\d+)|club(\d+)', text)
        info += f" | group-json not found; id-guess={gid.group(0) if gid else None}"
    return info


out = Path(sys.argv[1])
with out.open("a", encoding="utf-8", newline="\n") as handle:
    for name in sys.argv[2:]:
        handle.write(probe(name) + "\n")
        handle.flush()
        time.sleep(1.5)
