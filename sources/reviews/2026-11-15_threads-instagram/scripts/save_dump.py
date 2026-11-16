"""Split browser dumps into raw copies + data files and merge Threads posts into one table.

Usage (from project root):
    python -I <scripts>/save_dump.py <dump.json> [<platform> <short-name>]

Two dump formats are accepted:
  1. single rendered page (threads_extract.js / ig_*.js): {url, fetched_at, html, posts?, dom?, ...}
     -> needs <platform> and <short-name>; raw copy = document.documentElement.outerHTML ("dom").
  2. crawl chunk (threads_crawl_get.js): {pages: [{url, fetched_at, html, posts, ...}], parent: {...}}
     -> raw copy = body of the HTTP response the page context received for a same-origin GET ("page-fetch").

Writes raw/NNN_<platform>_<name>.html, appends raw/manifest.jsonl, writes work/pages/NNN_<...>.json (no html),
updates work/threads_posts.json (post code -> merged record with parent, seen_on, raw files).
"""
import hashlib
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

BASE = Path(__file__).resolve().parent.parent
RAW = BASE / "raw"
WORK = BASE / "work"
PAGES = WORK / "pages"
DB = WORK / "threads_posts.json"


def next_number():
    manifest = RAW / "manifest.jsonl"
    numbers = [0]
    if manifest.is_file():
        for line in manifest.read_text(encoding="utf-8").splitlines():
            if line.strip():
                name = json.loads(line)["file"].split("/")[-1]
                if name[:3].isdigit():
                    numbers.append(int(name[:3]))
    return max(numbers) + 1


def safe(name):
    return re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip("-")[:80]


def write_raw(html, url, fetched_at, platform, short, kind):
    RAW.mkdir(exist_ok=True)
    PAGES.mkdir(parents=True, exist_ok=True)
    stem = f"{next_number():03d}_{platform}_{safe(short)}"
    data = html.encode("utf-8")
    (RAW / f"{stem}.html").write_bytes(data)
    entry = {
        "file": f"raw/{stem}.html", "url": url, "fetched_at": fetched_at, "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(), "method": "browser", "kind": kind,
    }
    with open(RAW / "manifest.jsonl", "a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return stem, entry


def merge_threads(stem, posts):
    db = json.loads(DB.read_text(encoding="utf-8")) if DB.is_file() else {}
    mains = [p for p in posts if p["ctx"]["kind"] == "main"]
    main_code = mains[0]["code"] if mains else None
    chains = {}

    def chain_key(ctx):
        return f"{ctx.get('src', '')}|{ctx['kind']}|{ctx.get('chain')}"

    for p in posts:
        ctx = p["ctx"]
        if ctx["kind"] in ("direct_reply", "pinned_reply"):
            chains.setdefault(chain_key(ctx), {})[ctx["pos"]] = p["code"]
        elif ctx["kind"] == "self_thread":
            chains.setdefault("self", {})[ctx["pos"]] = p["code"]
        elif ctx["kind"] == "ancestor":
            chains.setdefault("anc", {})[ctx["pos"]] = p["code"]
    parents = {}
    if "anc" in chains and main_code:
        last = chains["anc"][max(chains["anc"])]
        if last != main_code:
            parents[main_code] = last
    for p in posts:
        ctx = p["ctx"]
        kind = ctx["kind"]
        if kind in ("direct_reply", "pinned_reply"):
            chain = chains[chain_key(ctx)]
            parents[p["code"]] = chain.get(ctx["pos"] - 1) if ctx["pos"] > 0 else main_code
        elif kind == "self_thread":
            parents[p["code"]] = chains["self"].get(ctx["pos"] - 1) if ctx["pos"] > 0 else main_code
        elif kind == "ancestor" and ctx["pos"] > 0:
            parents[p["code"]] = chains["anc"].get(ctx["pos"] - 1)
    for p in posts:
        kind = p["ctx"]["kind"]
        if kind == "related":
            continue
        rec = db.get(p["code"], {})
        for key, value in p.items():
            if key in ("ctx", "path"):
                continue
            if value in (None, [], "") and rec.get(key) not in (None, [], ""):
                continue
            # quoted/reposted/ancestor copies may be truncated views: never overwrite a full record's media/text with less
            if key in ("media", "text") and rec.get(key) and kind in ("quoted", "reposted") :
                continue
            rec[key] = value
        rec.setdefault("seen_on", [])
        if stem not in rec["seen_on"]:
            rec["seen_on"].append(stem)
        rec.setdefault("ctx_kinds", [])
        if kind not in rec["ctx_kinds"]:
            rec["ctx_kinds"].append(kind)
        if parents.get(p["code"]) and not rec.get("parent"):
            rec["parent"] = parents[p["code"]]
        if kind == "main":
            rec["page_raw"] = f"raw/{stem}.html"
        db[p["code"]] = rec
    DB.write_text(json.dumps(db, ensure_ascii=False, indent=1), encoding="utf-8")


def merge_instagram(stem, obj):
    """work/ig_posts.json: code -> {media record, comments {pk: ...}, raw files}; work/ig_profiles.json."""
    path = WORK / "ig_posts.json"
    db = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    raw = f"raw/{stem}.html"
    m = re.search(r"/(?:p|reel|reels)/([A-Za-z0-9_-]+)", obj.get("url", ""))
    page_code = m.group(1) if m else None
    for media in obj.get("medias", []):
        code = media["code"]
        rec = db.get(code, {"comments": {}, "seen_on": []})
        full = media.get("taken_at") is not None
        for key, value in media.items():
            if key == "path":
                continue
            if value in (None, [], "") and rec.get(key) not in (None, [], ""):
                continue
            if key == "media" and rec.get("media") and not full:
                continue
            rec[key] = value
        if stem not in rec["seen_on"]:
            rec["seen_on"].append(stem)
        if code == page_code:
            rec["page_raw"] = raw
            rec["fetched_at"] = obj["fetched_at"]
        db[code] = rec
    if page_code:
        rec = db.setdefault(page_code, {"code": page_code, "comments": {}, "seen_on": [stem]})
        rec.setdefault("page_raw", raw)
        rec.setdefault("fetched_at", obj["fetched_at"])
        for c in obj.get("comments", []):
            old = rec["comments"].get(c["pk"], {})
            old.update({k: v for k, v in c.items() if k != "path"})
            old["raw_file"] = raw
            rec["comments"][c["pk"]] = old
        rec["metas"] = obj.get("metas") or rec.get("metas")
        rec["more_comments_left"] = obj.get("more_comments_left")
    path.write_text(json.dumps(db, ensure_ascii=False, indent=1), encoding="utf-8")
    if obj.get("profiles"):
        ppath = WORK / "ig_profiles.json"
        pdb = json.loads(ppath.read_text(encoding="utf-8")) if ppath.is_file() else {}
        for p in obj["profiles"]:
            if p.get("biography") is not None or p.get("followers") is not None:
                old = pdb.get(p["username"], {})
                old.update({k: v for k, v in p.items() if v not in (None, [], "")})
                old["raw_file"] = raw
                old["fetched_at"] = obj["fetched_at"]
                pdb[p["username"]] = old
        ppath.write_text(json.dumps(pdb, ensure_ascii=False, indent=1), encoding="utf-8")
    mains = [x for x in obj.get("medias", []) if x["code"] == page_code]
    if mains:
        x = max(mains, key=lambda t: len(t.get("media") or []))
        print(f"  post {x['code']} by {x.get('user')} {x.get('iso')} likes={x.get('like_count')} comments={x.get('comment_count')} "
              f"media={[mm['kind'] for mm in x.get('media') or []]} coauthors={x.get('coauthors')} type={x.get('product_type')}")
        print("  caption:", (x.get("caption") or "").replace("\n", " ⏎ ")[:400])
    for c in obj.get("comments", []):
        print(f"   c {c['user'][:22]:22} {(c.get('iso') or '')[:16]} lk={c.get('likes')} ch={c.get('children')} "
              f"{'↳' if c.get('parent') else ' '} {c['text'].replace(chr(10), ' ⏎ ')[:230]}")


def summary(stem, page):
    posts = [p for p in page.get("posts", []) if p["ctx"]["kind"] != "related"]
    print(f"{stem}: url={page['url']} posts={len(posts)} login={page.get('loginRedirect') or page.get('login_wall')}")
    for p in posts:
        ctx = p["ctx"]
        text = (p["text"] or "").replace("\n", " ")[:60]
        media = ",".join(m["kind"] for m in p["media"]) or "-"
        print(f"   {ctx['kind'][:6]:6} c{ctx.get('chain', '')!s:2} p{ctx.get('pos', '')!s:2} {p['code']:12} "
              f"{p['user'][:22]:22} {p['iso'][5:16] if p['iso'] else '':11} drc={p['direct_reply_count']} "
              f"lk={p['like_count']} lvl={p['reply_level']} to={p['reply_to']} m={media} | {text}")


def main():
    dump_path = Path(sys.argv[1])
    obj = json.loads(dump_path.read_text(encoding="utf-8"))
    if isinstance(obj, str):
        obj = json.loads(obj)
    quiet = "--quiet" in sys.argv
    if "pages" in obj:
        only = set(sys.argv[sys.argv.index("--only") + 1].split(",")) if "--only" in sys.argv else None
        for page in obj["pages"]:
            html = page.pop("html")
            if only is not None and page["code"] not in only:
                print("skipped (not relevant):", page["url"])
                continue
            if not html:
                print("no html for", page["url"])
                continue
            main_posts = [p for p in page["posts"] if p["ctx"]["kind"] == "main"]
            user = main_posts[0]["user"] if main_posts else "unknown"
            stem, entry = write_raw(html, page["url"], page["fetched_at"], "threads", f"{user}_{page['code']}", "page-fetch")
            page["raw_file"] = entry["file"]
            (PAGES / f"{stem}.json").write_text(json.dumps(page, ensure_ascii=False, indent=1), encoding="utf-8")
            merge_threads(stem, page["posts"])
            if quiet:
                print(f"{stem}: posts={len([p for p in page['posts'] if p['ctx']['kind'] != 'related'])}")
            else:
                summary(stem, page)
        print("left in browser:", obj.get("left"))
        return
    if "ig_pages" in obj:
        for page in obj["ig_pages"]:
            html = page.pop("html", "")
            if not html:
                print("no html for", page["url"], page.get("status"), page.get("error"))
                continue
            m = re.search(r"instagram\.com/(?:([^/]+)/)?(p|reel|reels)/([A-Za-z0-9_-]+)(/embed)?", page["url"])
            if m:
                owner = next((x.get("user") for x in page.get("medias", []) if x["code"] == m.group(3) and x.get("user")), None) or m.group(1) or "post"
                short = f"{owner}_{m.group(3)}{'_embed' if m.group(4) else ''}"
            else:
                short = "page_" + re.sub(r"https?://www\.instagram\.com/", "", page["url"]).strip("/").replace("/", "_")
            stem, entry = write_raw(html, page["url"], page["fetched_at"], "instagram", short, "page-fetch")
            page["raw_file"] = entry["file"]
            (PAGES / f"{stem}.json").write_text(json.dumps(page, ensure_ascii=False, indent=1), encoding="utf-8")
            print(f"{stem}: status={page.get('status')} login={page.get('login')} final={page.get('finalUrl')}")
            merge_instagram(stem, page)
        print("left in browser:", obj.get("left"), "running:", obj.get("running"), "stop:", obj.get("stopReason"))
        return
    platform, short = sys.argv[2], sys.argv[3]
    html = obj.pop("html")
    stem, entry = write_raw(html, obj["url"], obj["fetched_at"], platform, short, "dom")
    obj["raw_file"] = entry["file"]
    gql_raw = obj.pop("gql_raw", None)
    if gql_raw:
        # responses the page received from its own GraphQL endpoint while it was being scrolled (lazy-loaded replies)
        data = json.dumps(gql_raw, ensure_ascii=False, indent=0).encode("utf-8")
        gql_name = f"raw/{stem}_graphql.json"
        (BASE / gql_name).write_bytes(data)
        with open(RAW / "manifest.jsonl", "a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps({"file": gql_name, "url": obj["url"], "fetched_at": obj["fetched_at"], "bytes": len(data),
                                "sha256": hashlib.sha256(data).hexdigest(), "method": "browser",
                                "kind": "graphql-responses-received-by-page"}, ensure_ascii=False) + "\n")
        obj["gql_file"] = gql_name
        print(f"saved {gql_name} bytes={len(data)} responses={len(gql_raw)}")
    (PAGES / f"{stem}.json").write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"saved {entry['file']} bytes={entry['bytes']} sha256={entry['sha256'][:16]} dom={obj.get('dom_count')} "
          f"views={obj.get('views_text')} login_wall={obj.get('login_wall')} not_found={obj.get('not_found')}")
    if platform == "threads" and obj.get("posts"):
        merge_threads(stem, obj["posts"])
        if not quiet:
            summary(stem, obj)
    if platform == "instagram":
        print(f"  login_wall={obj.get('login_wall')} clicks={obj.get('click_log')} more_left={obj.get('more_comments_left')} "
              f"medias={len(obj.get('medias', []))} comments={len(obj.get('comments', []))} gql={[(g['friendly'], g['comments']) for g in obj.get('gql', [])]}")
        merge_instagram(stem, obj)


if __name__ == "__main__":
    main()
