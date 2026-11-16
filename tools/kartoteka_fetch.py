"""Выгрузка всех сведений по УНП из API kartoteka.by в sources/kartoteka/<дата>/.

Запуск:  python tools/kartoteka_fetch.py 791349254
Токен берётся из config/kartoteka.env (KARTOTEKA_API_TOKEN).
Сырые ответы сохраняются без изменений, чтобы их можно было приложить как источник.
"""
import datetime
import json
import pathlib
import sys
import time
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
BASE = "https://oldapi.kartoteka.by"

# endpoint -> имя параметра страницы (None = без пагинации)
ENDPOINTS = {
    "summary": None,
    "egr": None,
    "checks": "p",
    "debtors": "p",
    "court/writ": "page",
    "bankruptcy": None,
    "trades": "page",
    "service-register": None,
    "certs": "page",
    "cert-of-comp": None,
    "banks-guarantees": "page",
}
MAX_PAGES = 50


def load_token() -> str:
    for line in (ROOT / "config" / "kartoteka.env").read_text(encoding="utf-8").splitlines():
        if line.startswith("KARTOTEKA_API_TOKEN="):
            return line.split("=", 1)[1].strip()
    sys.exit("KARTOTEKA_API_TOKEN не найден в config/kartoteka.env")


def call(path: str, token: str, **params) -> dict:
    params["access-token"] = token
    url = f"{BASE}/{path}?{urllib.parse.urlencode(params)}"
    time.sleep(0.25)  # лимит API: 5 запросов в секунду
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def main() -> None:
    unp = sys.argv[1] if len(sys.argv) > 1 else "791349254"
    token = load_token()
    out = ROOT / "sources" / "kartoteka" / datetime.date.today().isoformat()
    out.mkdir(parents=True, exist_ok=True)

    limit = call("account/limit", token)
    print("account/limit:", json.dumps(limit, ensure_ascii=False))
    if not limit.get("success"):
        sys.exit("Токен не принят — выгрузка остановлена.")

    for ep, page_param in ENDPOINTS.items():
        pages = []
        for page in range(1, (MAX_PAGES if page_param else 1) + 1):
            params = {page_param: page} if page_param else {}
            resp = call(f"{ep}/{unp}", token, **params)
            pages.append(resp)
            data = resp.get("data")
            if not resp.get("success") or not data or not page_param:
                break
            got = sum(len(p.get("data") or []) for p in pages if isinstance(p.get("data"), list))
            if resp.get("total") is not None and got >= resp["total"]:
                break
        result = pages[0] if len(pages) == 1 else {"pages": pages}
        fname = out / f"{ep.replace('/', '_')}.json"
        fname.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        status = "ok" if pages[0].get("success") else f"ошибка: {pages[0].get('errors')}"
        print(f"{ep}: {len(pages)} стр., {status} -> {fname.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
