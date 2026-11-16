"""Примерное время публикации Instagram по коду (коду соответствует номер, в старших битах которого время)."""
import sys
from datetime import datetime, timezone

ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"


def when(code):
    n = 0
    for ch in code[:11]:
        n = n * 64 + ALPHABET.index(ch)
    ms = (n >> 23) + 1314220021721
    return datetime.fromtimestamp(ms / 1000, timezone.utc)


if __name__ == "__main__":
    for code in sys.argv[1:]:
        print(code, when(code).isoformat(timespec="seconds"))
