"""Извлекает текст из PDF в файл UTF-8 с пометками страниц.

Запуск из корня проекта:
    python -I tools/pdf_text.py <файл.pdf> [<файл.txt>] [--pypdf]

Если имя выходного файла не указано, текст пишется рядом: <файл>.txt. Так его находит
tools/reviews_check.py и tools/quotes_check.py, когда сырая копия — PDF.

По умолчанию текст извлекает PyMuPDF: он сохраняет пробелы так, как они стоят в PDF.
Прежний способ (pypdf, флаг --pypdf) в выровненных по ширине строках вставлял пробел
внутрь слова или между словами: «переплан ировки», «грузоподъемник и организации»
вместо «грузоподъемники организации». Сверка «только по буквам» (LOOSE) такую ошибку
не ловит, поэтому цитаты из актов нужно брать из текста, извлечённого PyMuPDF.
Колонтитулы страниц остаются в тексте: пункт, который переходит на другую страницу,
в quotes.jsonl записывают двумя частями.
"""
import sys
from pathlib import Path


def extract_pages(source, use_pypdf):
    if not use_pypdf:
        try:
            import pymupdf
        except ImportError:
            print("pymupdf is not installed, falling back to pypdf", file=sys.stderr)
        else:
            with pymupdf.open(str(source)) as document:
                return [page.get_text("text") for page in document], "pymupdf"
    from pypdf import PdfReader
    return [page.extract_text() or "" for page in PdfReader(str(source)).pages], "pypdf"


def main():
    arguments = [argument for argument in sys.argv[1:] if argument != "--pypdf"]
    if len(arguments) not in (1, 2):
        sys.exit("usage: python -I tools/pdf_text.py <file.pdf> [<file.txt>] [--pypdf]")
    source = Path(arguments[0])
    target = Path(arguments[1]) if len(arguments) == 2 else source.with_suffix(".txt")
    pages, engine = extract_pages(source, "--pypdf" in sys.argv[1:])
    with target.open("w", encoding="utf-8", newline="\n") as output:
        for number, text in enumerate(pages, 1):
            output.write(f"\n===== стр. {number} =====\n{text}\n")
    print(f"engine={engine} pages={len(pages)} chars={sum(len(text) for text in pages)} -> {ascii(str(target))}")


if __name__ == "__main__":
    main()
