"""Проверка существования открытых каналов Telegram без сохранения страниц.

usage: python -I tgprobe.py <out_txt> <handle> [<handle> ...]
Для каждого имени запрашивает https://t.me/s/<handle> и пишет: тип, название, описание, счётчики,
дату последнего сообщения. Страницы на диск не сохраняются.
"""
import html
import re
import subprocess
import sys
import time
from pathlib import Path

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36")


def clean(fragment):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def probe(handle):
    cmd = ["curl", "--silent", "--location", "--compressed", "--connect-timeout", "20", "--max-time", "60",
           "--user-agent", UA, "--header", "Accept-Language: ru,be;q=0.8,en;q=0.5",
           "--write-out", "\n%{http_code}\t%{url_effective}", f"https://t.me/s/{handle}"]
    res = subprocess.run(cmd, capture_output=True)
    body = res.stdout.decode("utf-8", "replace")
    text, _, tail = body.rpartition("\n")
    status, _, final = tail.partition("\t")
    if "/s/" in final:
        title = re.search(r'<div class="tgme_channel_info_header_title"[^>]*>(.*?)</div>', text, re.S)
        desc = re.search(r'<div class="tgme_channel_info_description"[^>]*>(.*?)</div>', text, re.S)
        counters = re.findall(r'<span class="counter_value">([^<]*)</span>\s*<span class="counter_type">([^<]*)</span>', text)
        times = re.findall(r'<time datetime="([^"]+)"', text)
        return (f"{handle}: CHANNEL title={clean(title.group(1)) if title else None!r} "
                f"counters={counters} last={times[-1] if times else None} desc={clean(desc.group(1))[:300] if desc else None!r}")
    title = re.search(r'<div class="tgme_page_title"[^>]*>(.*?)</div>', text, re.S)
    extra = re.search(r'<div class="tgme_page_extra"[^>]*>(.*?)</div>', text, re.S)
    desc = re.search(r'<div class="tgme_page_description[^"]*"[^>]*>(.*?)</div>', text, re.S)
    if title:
        return (f"{handle}: NO-PREVIEW title={clean(title.group(1))!r} extra={clean(extra.group(1)) if extra else None!r} "
                f"desc={clean(desc.group(1))[:300] if desc else None!r}")
    return f"{handle}: none (http={status})"


out = Path(sys.argv[1])
with out.open("a", encoding="utf-8", newline="\n") as handle_file:
    for name in sys.argv[2:]:
        handle_file.write(probe(name) + "\n")
        handle_file.flush()
        time.sleep(0.8)
