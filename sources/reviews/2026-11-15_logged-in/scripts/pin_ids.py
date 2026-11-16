"""Закрепляет номера записей в work/classify.json (поле id) и проставляет снимки экрана.

Запуск: python -I -X utf8 sources/reviews/2026-11-15_logged-in/scripts/pin_ids.py

Номер записи раньше определялся местом элемента в списке; после закрепления удаление
элемента не сдвигает номера остальных. Повторный запуск ничего не меняет.
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
SHOTS = {
    "Dfu8iMZmZaw": "screenshots/017_threads_kalinovskaya_Dfu8iMZmZaw_1.png",
    "Dfu8iMsGUOD": "screenshots/017_threads_kalinovskaya_Dfu8iMZmZaw_1.png",
    "Dfu8jBMGQzW": "screenshots/017_threads_kalinovskaya_Dfu8iMZmZaw_2.png",
    "DfwYUrWgA5V": "screenshots/017_threads_kalinovskaya_Dfu8iMZmZaw_3.png",
    "DfwteagjkUW": "screenshots/019_threads_kalinovskaya_DfwbseaDgV7_1.png",
    "Dfws4-jkWkm": "screenshots/019_threads_kalinovskaya_DfwbseaDgV7_1.png",
    "DfvA-X1kV8k": "screenshots/017_threads_kalinovskaya_Dfu8iMZmZaw_3.png",
    "DfoNBHAja74": "screenshots/007_threads_innatalankova_DfoNBHAja74.png",
    "Dft2Yo6DcPK": "screenshots/009_threads_ivar_takis_1945_DfsEYnhCDE1_2_biolokaciya.png",
    "DfsI4pNilot": "screenshots/009_threads_ivar_takis_1945_DfsEYnhCDE1_1.png",
    "DfsEYnhCDE1": "screenshots/009_threads_ivar_takis_1945_DfsEYnhCDE1_1.png",
    "DRKMuTziDzK": "screenshots/025_threads_amazonka_DRKMuTziDzK.png",
    "DRl8r77iBkI": "screenshots/025_threads_amazonka_DRl8r77iBkI.png",
    "DYoobGljIIE": "screenshots/025_threads_amazonka_DYoobGljIIE.png",
    "DPtenIyCJ7P": "screenshots/025_threads_amazonka_DPtenIyCJ7P_frame1.png",
}


def main():
    path = HERE / "work" / "classify.json"
    spec = json.loads(path.read_text(encoding="utf-8"))
    taken = {entry["id"] for entry in spec if "id" in entry}
    changed = 0
    for position, entry in enumerate(spec, 1):
        if "id" not in entry:
            if position in taken:
                raise SystemExit(f"номер {position} уже занят")
            entry["id"] = position
            taken.add(position)
            changed += 1
        shot = SHOTS.get(entry["code"])
        if shot and not entry.get("screenshot"):
            if not (HERE / shot).is_file():
                raise SystemExit(f"нет файла {shot}")
            entry["screenshot"] = shot
            changed += 1
    ordered = []
    for entry in spec:
        first = {"id": entry["id"]}
        first.update({k: v for k, v in entry.items() if k != "id"})
        ordered.append(first)
    text = "[\n" + ",\n".join(" " + json.dumps(e, ensure_ascii=False) for e in ordered) + "\n]\n"
    path.write_text(text, encoding="utf-8", newline="\n")
    print("entries:", len(ordered), "changed fields:", changed)


if __name__ == "__main__":
    main()
