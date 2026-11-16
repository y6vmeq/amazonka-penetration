"""Перед удалением .playwright-mcp/ переносит в work/ то, что подтверждает недоступность страниц.

Запуск из корня проекта:
    python -I -X utf8 sources/reviews/2026-11-15_media-open/scripts/keep_evidence.py

1. Снимки страниц (текстовое дерево страницы, которое пишет Playwright) для публикаций,
   недоступных без входа, — в work/unavailable/.
2. Проверочный заход на обычную страницу DU05cvVjGcw: Playwright записал результат не в JSON
   (в данных было undefined), поэтому нужные поля выбираются построчно и пишутся в
   work/pagecheck_DU05cvVjGcw_fields.json. Содержимое файла (base64) не переносится.
"""
import json
import shutil
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
ROOT = BASE.parent.parent.parent
SRC = ROOT / ".playwright-mcp"

SNAPSHOTS = {
    "page-2026-11-15T21-02-43-965Z.yml": "threads_DYoobGljIIE_attempt1_21-02-43Z.yml",
    "page-2026-11-15T21-26-00-676Z.yml": "threads_DYoobGljIIE_attempt2_21-26-00Z.yml",
    "page-2026-11-15T21-07-50-967Z.yml": "instagram_CzMnCKsIsDR_embed_21-07-50Z.yml",
    "page-2026-11-15T21-13-28-475Z.yml": "instagram_CzMnCKsIsDR_page_21-13-28Z.yml",
    "page-2026-11-15T21-08-13-652Z.yml": "instagram_Cxm_B_0Iutl_embed_21-08-13Z.yml",
    "page-2026-11-15T21-13-39-751Z.yml": "instagram_Cxm_B_0Iutl_page_21-13-39Z.yml",
}


def main():
    target = BASE / "work" / "unavailable"
    target.mkdir(parents=True, exist_ok=True)
    for source_name, target_name in SNAPSHOTS.items():
        source = SRC / source_name
        if source.is_file():
            shutil.copyfile(source, target / target_name)
            print("kept", target_name, source.stat().st_size)
        else:
            print("NO SNAPSHOT", source_name)

    dump = SRC / "igp_DU05cvVjGcw.json"
    if dump.is_file():
        wanted = ("fetched_at", "page", "login_wall", "status", "type", "bytes", "sha256", "owner", "taken_at",
                  "media_type", "product_type", "original_width", "original_height", "carousel_count")
        found = {}
        with dump.open(encoding="utf-8") as handle:
            for line in handle:
                if len(line) > 400:  # строка с base64
                    continue
                name, _, value = line.strip().partition(": ")
                if name in wanted and name not in found:
                    found[name] = value.rstrip(",").strip("'")
        found["note"] = ("Проверочный заход на обычную страницу без входа: одно фото (не карусель); "
                         "файл совпал с сохранённым из плеера (тот же SHA-256), повторно не писался.")
        out = BASE / "work" / "pagecheck_DU05cvVjGcw_fields.json"
        out.write_text(json.dumps(found, ensure_ascii=False, indent=1), encoding="utf-8")
        print("kept", out.name, found.get("sha256"), found.get("taken_at"), found.get("carousel_count"))


if __name__ == "__main__":
    main()
