"""Collect the moments when screenshots were returned by the browser, from the session log of the agent.

Usage (from project root): python -I <scripts>/shot_times.py <session-log.jsonl>

The log is read line by line; for every tool result that contains "Saved screenshot to <path>.png" the time stamp
of the log entry is stored. Writes work/shots/_shot_times.json: file name -> list of UTC time stamps
(build_screenshot_index.py uses the last one). The log itself is not changed.
"""
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
BASE = Path(__file__).resolve().parent.parent
PATTERN = re.compile(r"Saved screenshot to (.+?\.png)")


def texts(content):
    if isinstance(content, list):
        for part in content:
            if isinstance(part, dict) and part.get("type") == "tool_result":
                inner = part.get("content")
                if isinstance(inner, str):
                    yield inner
                elif isinstance(inner, list):
                    for x in inner:
                        if isinstance(x, dict) and x.get("text"):
                            yield x["text"]


def main():
    out = {}
    with open(sys.argv[1], encoding="utf-8", errors="replace") as f:
        for line in f:
            if "Saved screenshot to" not in line:
                continue
            try:
                entry = json.loads(line)
            except ValueError:
                continue
            if entry.get("type") != "user" or not entry.get("timestamp"):
                continue
            for text in texts(entry.get("message", {}).get("content")):
                for m in PATTERN.finditer(text):
                    name = re.split(r"[\\/]+", m.group(1))[-1]
                    out.setdefault(name, []).append(entry["timestamp"])
    target = BASE / "work" / "shots" / "_shot_times.json"
    target.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{target.name}: {len(out)} screenshots")


if __name__ == "__main__":
    main()
