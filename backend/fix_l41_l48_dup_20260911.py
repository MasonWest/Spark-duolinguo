# -*- coding: utf-8 -*-
"""Remove duplicated paragraph lines in L41 / L48 explanations.

L41 (分区数与并行度): the ④ 版本提示 paragraph about AQE default-on is
copy-pasted twice (identical). L48 (综合练习): the 版本提示 paragraph about
`explain()` showing the initial plan is copied twice identically.

Both the live DB (lessons.content) and the seed source
(app/course_seed.json, /levels[5]/lessons[1] for L41, /levels[5]/lessons[8]
for L48) must be fixed, or a re-seed would restore the duplication.

Method: drop the *second* occurrence of any repeated non-empty line in the
explanation field (blank lines preserved). Verified to remove exactly 1 line
per lesson.
"""
import sqlite3, json, shutil, os, sys

DB = "spark_quest.db"
SEED = "app/course_seed.json"
# course_seed.json path: levels[5] = Level 5; lessons[1] = L41, lessons[8] = L48
TARGETS = {
    41: ("levels", 5, "lessons", 1),
    48: ("levels", 5, "lessons", 8),
}

def dedup_lines(text):
    lines = text.split("\n")
    seen = set()
    out = []
    removed = 0
    for line in lines:
        if line.strip() == "":
            out.append(line)          # always keep blank lines
            continue
        if line in seen:
            removed += 1
            continue
        seen.add(line)
        out.append(line)
    return "\n".join(out), removed

def process_db(apply):
    con = sqlite3.connect(DB); cur = con.cursor()
    cur.execute("select id, content from lessons where id in (41,48)")
    for lid, content in cur.fetchall():
        c = json.loads(content)
        before = c["explanation"]
        after, removed = dedup_lines(before)
        print(f"  DB L{lid}: removed={removed} ④count={before.count('④')}->{after.count('④')} "
              f"AdaptiveSparkPlan={before.count('AdaptiveSparkPlan')}->{after.count('AdaptiveSparkPlan')}")
        if removed != 1:
            raise SystemExit(f"ABORT: L{lid} removed {removed} lines (expected 1)")
        c["explanation"] = after
        if apply:
            cur.execute("update lessons set content=? where id=?", (json.dumps(c, ensure_ascii=False), lid))
    if apply:
        con.commit()
    con.close()

def process_seed(apply):
    data = json.load(open(SEED, encoding="utf-8"))
    for lid, path in TARGETS.items():
        *_, lvl_key, lvl_idx, les_key, les_idx = path
        lesson = data[lvl_key][lvl_idx][les_key][les_idx]
        before = lesson["content"]["explanation"]
        after, removed = dedup_lines(before)
        print(f"  SEED L{lid}: removed={removed} ④count={before.count('④')}->{after.count('④')} "
              f"AdaptiveSparkPlan={before.count('AdaptiveSparkPlan')}->{after.count('AdaptiveSparkPlan')}")
        if removed != 1:
            raise SystemExit(f"ABORT: SEED L{lid} removed {removed} lines (expected 1)")
        lesson["content"]["explanation"] = after
    if apply:
        json.dump(data, open(SEED, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

def main():
    apply = "--apply" in sys.argv
    print("DRY-RUN" if not apply else "APPLY")
    if apply:
        shutil.copy(DB, DB + ".bak_before_l41l48dup_20260911")
        shutil.copy(SEED, SEED + ".bak_before_l41l48dup_20260911")
    print("--- DB ---"); process_db(apply)
    print("--- SEED ---"); process_seed(apply)
    if apply:
        print("Backups: %s, %s" % (DB+".bak_before_l41l48dup_20260911", SEED+".bak_before_l41l48dup_20260911"))

if __name__ == "__main__":
    main()
