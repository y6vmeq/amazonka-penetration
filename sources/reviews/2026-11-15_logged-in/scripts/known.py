"""Собирает списки уже собранного прежним проходом (threads-instagram), чтобы отсеивать повторы в странице."""
import json
from pathlib import Path

here = Path(__file__).resolve().parent.parent
prev = here.parent / "2026-11-15_threads-instagram"
threads = json.loads((prev / "work" / "threads_posts.json").read_text(encoding="utf-8"))
ig = json.loads((prev / "work" / "ig_posts.json").read_text(encoding="utf-8"))

t_codes = sorted(threads.keys())
ig_comment_pks = []
ig_posts = {}
for code, post in ig.items():
    comments = post.get("comments") or {}
    ig_posts[code] = {
        "n_comments_collected": len(comments),
        "user": post.get("user"),
        "iso": post.get("iso"),
    }
    for pk, c in comments.items():
        ig_comment_pks.append(pk)
        children = c.get("children") or {}
        if isinstance(children, dict):
            ig_comment_pks.extend(children.keys())
out = {
    "threads_codes": t_codes,
    "ig_comment_pks": sorted(set(ig_comment_pks)),
    "ig_posts": ig_posts,
}
(here / "work" / "known.json").write_text(json.dumps(out, ensure_ascii=False, indent=0), encoding="utf-8")
(here / "work" / "known_threads_codes.txt").write_text(",".join(t_codes), encoding="utf-8")
(here / "work" / "known_ig_pks.txt").write_text(",".join(sorted(set(ig_comment_pks))), encoding="utf-8")
print(len(t_codes), len(set(ig_comment_pks)), len(ig_posts))
print(len(",".join(t_codes)), len(",".join(sorted(set(ig_comment_pks)))))
