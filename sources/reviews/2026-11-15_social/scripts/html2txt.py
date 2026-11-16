"""Грубое преобразование сохранённой HTML-страницы в текст для чтения (UTF-8).

usage: python -I html2txt.py <out_dir> <html> [<html> ...]
"""
import html
import re
import sys
from pathlib import Path


def decode(data):
    head = data[:3000].lower()
    if b"windows-1251" in head or b"cp1251" in head:
        return data.decode("cp1251", errors="replace")
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("cp1251", errors="replace")


def to_text(text):
    text = re.sub(r"(?is)<(script|style|svg|noscript)[^>]*>.*?</\1>", " ", text)
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"(?i)</(div|p|li|h[1-6]|tr|section|article|header|footer)>", "\n", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)
    return "\n".join(line.strip() for line in text.split("\n") if line.strip())


out_dir = Path(sys.argv[1])
out_dir.mkdir(parents=True, exist_ok=True)
for name in sys.argv[2:]:
    path = Path(name)
    raw = decode(path.read_bytes())
    title = re.search(r"(?is)<title[^>]*>(.*?)</title>", raw)
    body = to_text(raw)
    (out_dir / (path.stem + ".txt")).write_text(
        f"TITLE: {html.unescape(title.group(1)).strip() if title else None}\nBYTES: {len(raw)}\n\n{body}\n",
        encoding="utf-8", newline="\n")
print("ok")
