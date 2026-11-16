"""Извлекает текст из .docx и .pptx без запуска офисных программ.

Запуск из корня проекта:
    python -I -X utf8 tools/office_text.py <файл.docx|файл.pptx>

Пишет <файл>.txt рядом. Файл читается как zip-архив; из него берутся только XML с текстом
(word/document.xml либо ppt/slides/slideN.xml), текст вынимается регулярными выражениями.
Ничего не распаковывается на диск и не исполняется. Для .pptx перед текстом каждого слайда
ставится строка «===== слайд N =====» и перечисляются картинки слайда (их имена в архиве).
"""
import html
import re
import sys
import zipfile
from pathlib import Path

MAX_MEMBER = 30_000_000


def read(archive, name):
    info = archive.getinfo(name)
    if info.file_size > MAX_MEMBER:
        raise SystemExit(f"{name}: слишком большой ({info.file_size} байт)")
    return archive.read(name).decode("utf-8", "replace")


def docx_text(archive):
    xml = read(archive, "word/document.xml")
    out = []
    for paragraph in re.findall(r"(?s)<w:p\b.*?</w:p>", xml):
        text = "".join(html.unescape(t) for t in re.findall(r"(?s)<w:t\b[^>]*>(.*?)</w:t>", paragraph))
        text = re.sub(r"[ \t]+", " ", text).strip()
        if text:
            out.append(text)
    return out


def pptx_text(archive):
    names = archive.namelist()
    slides = sorted((n for n in names if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)),
                    key=lambda n: int(re.search(r"(\d+)\.xml$", n).group(1)))
    out = []
    for name in slides:
        number = int(re.search(r"(\d+)\.xml$", name).group(1))
        xml = read(archive, name)
        out.append(f"===== слайд {number} =====")
        rels_name = f"ppt/slides/_rels/slide{number}.xml.rels"
        if rels_name in names:
            rels = read(archive, rels_name)
            images = re.findall(r'Target="\.\./media/([^"]+)"', rels)
            if images:
                out.append("[картинки: " + ", ".join(sorted(set(images))) + "]")
        for paragraph in re.findall(r"(?s)<a:p\b.*?</a:p>", xml):
            text = "".join(html.unescape(t) for t in re.findall(r"(?s)<a:t\b[^>]*>(.*?)</a:t>", paragraph))
            text = re.sub(r"[ \t]+", " ", text).strip()
            if text:
                out.append(text)
    return out


def main():
    path = Path(sys.argv[1])
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if "word/document.xml" in names:
            lines = docx_text(archive)
        elif any(n.startswith("ppt/slides/") for n in names):
            lines = pptx_text(archive)
        else:
            raise SystemExit("не .docx и не .pptx")
    target = path.with_suffix(path.suffix + ".txt")
    target.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"строк: {len(lines)} знаков: {sum(len(x) for x in lines)} -> {target.as_posix()}")


if __name__ == "__main__":
    main()
