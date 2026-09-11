# -*- coding: utf-8 -*-
"""
Rewrite Level 5 (lessons 40-48) quiz distractors so the correct answer is no
longer systematically the longest option.

Context (2026-09-11): after fixing the "all-A" bug, the correct option was still
the longest in 98% of L5 questions (median +13 chars) because distractors were
short stubs while the correct answer was a full sentence. This script replaces
each question's 3 distractors with plausible, factually-wrong, comparable-length
sentences (loaded from l5_distractors_20260911.json). The correct text and its
position (correct_index) are NEVER changed.

Usage:
  python rewrite_l5_distractors_20260911.py            # dry-run (print length deltas)
  python rewrite_l5_distractors_20260911.py --apply    # write to DB

Conventions (per project):
  - backup DB before apply
  - verify 4 options distinct, no replacement char (U+FFFD), correct text preserved
"""
import sqlite3, json, sys, shutil, os

DB = "spark_quest.db"
JSON_PATH = "l5_distractors_20260911.json"
BACKUP = DB + ".bak_before_l5distractors_20260911"
L5 = [40, 41, 42, 43, 44, 45, 46, 47, 48]

def main():
    with open(JSON_PATH, encoding="utf-8") as f:
        DISTRACTORS = {int(k): v for k, v in json.load(f)["distractors"].items()}

    apply = "--apply" in sys.argv
    if apply and not os.path.exists(BACKUP):
        shutil.copy(DB, BACKUP)
        print("backup ->", BACKUP)

    con = sqlite3.connect(DB); cur = con.cursor()
    cur.execute("select id, options, correct_index from quizzes where lesson_id in (%s)" % ",".join(map(str, L5)))
    rows = {r[0]: (json.loads(r[1]), r[2]) for r in cur.fetchall()}

    missing = [q for q in rows if q not in DISTRACTORS]
    if missing:
        print("MISSING distractor dict for qids:", missing); return

    longest_strict = 0
    longest_tied = 0
    problems = []
    for qid in sorted(rows):
        opts, ci = rows[qid]
        d = DISTRACTORS[qid]
        new = list(opts)
        slots = [i for i in range(4) if i != ci]
        if len(d) != 3 or len(slots) != 3:
            problems.append((qid, "slot/dict len mismatch", len(d), len(slots))); continue
        for slot, val in zip(slots, d):
            new[slot] = val
        correct_text = opts[ci]
        if new[ci] != correct_text:
            problems.append((qid, "correct text changed!")); continue
        if len(set(new)) != 4:
            problems.append((qid, "duplicate options after rewrite", new)); continue
        if any(chr(0xFFFD) in x for x in new):
            problems.append((qid, "replacement char found")); continue
        cl = len(correct_text); dl = [len(o) for i, o in enumerate(new) if i != ci]
        if cl > max(dl): longest_strict += 1
        if cl >= max(dl): longest_tied += 1
        if not apply:
            print(f"q{qid} ci={ci} correct_len={cl} new_lens={[len(o) for o in new]} margin={cl-max(dl)}")
        else:
            cur.execute("update quizzes set options=? where id=?", (json.dumps(new, ensure_ascii=False), qid))

    if problems:
        print("PROBLEMS:", problems)
        if apply:
            con.rollback()
        return

    if apply:
        con.commit()
        print(f"APPLIED. {len(rows)} questions rewritten.")
    else:
        print(f"DRY-RUN. {len(rows)} questions, no changes written.")
    print(f"correct strictly longest: {longest_strict}/{len(rows)} ({100*longest_strict//len(rows)}%)")
    print(f"correct longest-or-tied:  {longest_tied}/{len(rows)} ({100*longest_tied//len(rows)}%)")
    con.close()

if __name__ == "__main__":
    main()
