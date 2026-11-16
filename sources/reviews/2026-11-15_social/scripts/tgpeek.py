"""Просмотр последних сообщений канала без сохранения страницы: первые 160 знаков каждого.

usage: python -I tgpeek.py <out_txt> <handle> [...]
"""
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tgparse  # noqa: E402

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36")
out = Path(sys.argv[1])
with out.open("a", encoding="utf-8", newline="\n") as handle:
    for name in sys.argv[2:]:
        res = subprocess.run(["curl", "--silent", "--location", "--compressed", "--max-time", "60",
                              "--user-agent", UA, f"https://t.me/s/{name}"], capture_output=True)
        text = res.stdout.decode("utf-8", "replace")
        title, desc, counters = tgparse.channel_info(text)
        handle.write(f"##### {name} | {title!r} | {counters}\n# {desc!r}\n")
        for m in tgparse.messages(text):
            first = " ".join(m["text"].split())[:160]
            handle.write(f"  {m['datetime']} fwd={m['forwarded_from']!r}: {first}\n")
        handle.write("\n")
        time.sleep(1)
