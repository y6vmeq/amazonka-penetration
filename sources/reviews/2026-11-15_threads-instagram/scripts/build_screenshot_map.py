"""Build work/screenshot_map.json: record URL -> screenshot on which the publication is visible.

Usage (from project root): python -I <scripts>/build_screenshot_map.py
Run after shots_verify.py (it writes work/shots/_visible.json) and before build_reviews.py, which applies the map.

Sources of the map:
  * Threads post pages captured with shot_check.js: posts rendered from the opened post down to the end of the thread;
  * Threads profile of the venue (all 15 posts are rendered on one tall page);
  * re-check screenshots of two root pages (110, 114);
  * Instagram post pages captured with ig_shot_expand.js: the post itself and every comment whose author is listed
    in work/shots/<name>_expand.json.
Records found on the full-page screenshots of the root pages (001, 018-022) are not in the map: build_reviews.py
assigns those itself. The result does not depend on the screenshots currently written in reviews.jsonl.
"""
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
BASE = Path(__file__).resolve().parent.parent
SHOTS = BASE / "work" / "shots"
ROOT_PAGES = {"001", "018", "019", "020", "021", "022"}
FIXED = {
    "DfuxGCzjKsE": "screenshots/110_threads_masha_portugal_DfuxGCzjKsE_recheck.png",
    "DfwqokTAOCY": "screenshots/114_threads_viksha2704_DfrlrgOkbQO_recheck.png",
}
PROFILE = "screenshots/023_threads_profile_amazonka_restobar_mogilev.png"


def main():
    records = [json.loads(line) for line in (BASE / "reviews.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    visible = json.loads((SHOTS / "_visible.json").read_text(encoding="utf-8"))
    ig = {}
    for path in sorted(SHOTS.glob("*_instagram_*_expand.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        code = data["url"].rstrip("/").split("/")[-1]
        shot = "screenshots/" + path.name.replace("_expand.json", "_comments-expanded.png")
        if (BASE / shot).is_file():
            ig[code] = (shot, [a.rsplit(" y=", 1)[0] for a in data.get("authors") or []])
    result, missing = {}, []
    for r in records:
        raw_file = r.get("raw_file") or ""
        shot = None
        if r["platform"] == "threads":
            code = r["url"].rstrip("/").split("/")[-1]
            if code in FIXED:
                shot = FIXED[code]
            elif raw_file.startswith("raw/023_"):
                shot = PROFILE
            elif raw_file[4:7] in ROOT_PAGES and ("dom" in raw_file or raw_file[4:7] == "001"):
                continue  # full-page screenshot of the root page, assigned by build_reviews.py itself
            else:
                shot = visible.get(code)
        else:
            parts = r["url"].rstrip("/").split("/")
            code = parts[parts.index("c") - 1] if "c" in parts else parts[-1]
            if code in ig:
                shot, authors = ig[code]
                if r["kind"] == "comment" and r["author"] not in authors:
                    print(f"  ! {r['id']}: comment author {r['author']} is not on {shot}")
                    shot = None
        if shot and (BASE / shot).is_file():
            result[r["url"]] = shot
        else:
            missing.append(r["id"])
    (BASE / "work" / "screenshot_map.json").write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"mapped: {len(result)}; still without screenshot: {len(missing)} {missing}")


if __name__ == "__main__":
    main()
