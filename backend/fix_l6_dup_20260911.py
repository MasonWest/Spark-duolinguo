# -*- coding: utf-8 -*-
"""Remove duplicated 版本提示 paragraph lines in L6 lessons (49/52/54/57).

Same copy-paste bug as L41/L48: the 2026-09-10 L5/L6 audit added 版本提示
paragraphs to explanations, and one got pasted twice verbatim in each of these
lessons (a ⑤ ⚠️ line about AQE runtime optimization, SMJ->BHJ etc.).

Fixes both the live DB (lessons.content) and the seed source
(app/course_seed.json). Removes the second occurrence of any repeated
non-empty line in the explanation field (blank lines preserved).
"""
import sqlite3, json, shutil, os, sys

DB = "spark_quest.db"
SEED = "app/course_seed.json"
# (db_id, seed_path) where seed_path is the location in course_seed.json
TARGETS = [
    (49, ("levels", 6, "lessons", 0)),
    (52, ("levels", 6, "lessons", 3)),
    (54, ("levels", 6, "lessons", 5)),
    (57, ("levels", 6, "lessons", 8)),
]

def dedup_lines(text):
    lines = text.split("\n")
    seen = set(); out = []; removed = 0
    for line in lines:
        if line.strip() == "":
            out.append(line); continue
        if line in seen:
            removed += 1; continue
        seen.add(line); out.append(line)
    return "\n".join(out), removed

def main():
    apply = "--apply" in sys.argv
    print("DRY-RUN" if not apply else "APPLY")
    if apply:
        for f, tag in [(DB, "db"), (SEED, "seed")]:
            bak = f + ".bak_before_l6dup_20260911"
            if not os.path.exists(bak):
                shutil.copy(f, bak)
                print("backup:", bak)

    # DB
    con = sqlite3.connect(DB); cur = con.cursor()
    cur.execute("select id, content from lessons where id in (%s)" % ",".join(str(t[0]) for t in TARGETS))
    dbmap = {r[0]: json.loads(r[1]) for r in cur.fetchall()}
    for lid, _ in TARGETS:
        c = dbmap[lid]
        after, removed = dedup_lines(c["explanation"])
        print(f"  DB L{lid}: removed={removed} ⑤count={c['explanation'].count('⑤')}->{after.count('⑤')}")
        assert removed in (0, 1), f"L{lid} removed {removed} (expected 0 or 1)"
        c["explanation"] = after
        if apply:
            cur.execute("update lessons set content=? where id=?", (json.dumps(c, ensure_ascii=False), lid))
    if apply:
        con.commit()
    con.close()

    # Seed
    sd = json.load(open(SEED, encoding="utf-8"))
    for lid, path in TARGETS:
        lvl = sd[path[0]][path[1]]
        lesson = lvl[path[2]][path[3]]
        before = lesson["content"]["explanation"]
        after, removed = dedup_lines(before)
        print(f"  SEED L{lid}: removed={removed} ⑤count={before.count('⑤')}->{after.count('⑤')}")
        assert removed in (0, 1), f"SEED L{lid} removed {removed} (expected 0 or 1)"
        lesson["content"]["explanation"] = after
    if apply:
        json.dump(sd, open(SEED, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print("seed written")

if __name__ == "__main__":
    main()
