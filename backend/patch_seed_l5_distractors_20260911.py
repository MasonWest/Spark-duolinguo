# -*- coding: utf-8 -*-
"""Sync Level 5 distractor rewrite into seed_level5.py for durability.

The DB is the live source of truth. This overwrites each L5 quiz's options +
correct_index in LEVEL5_QUIZZES with the DB's current (rewritten) values,
matched by normalized prompt. The 2 known stale prompts are left untouched.
"""
import sqlite3, json, re, shutil, os, ast

DB = "spark_quest.db"
SEED = "seed_level5.py"
L5 = [40, 41, 42, 43, 44, 45, 46, 47, 48]

def norm(s):
    return re.sub(r"\s+", "", s).strip()

def main():
    con = sqlite3.connect(DB); cur = con.cursor()
    cur.execute("select prompt, options, correct_index from quizzes where lesson_id in (%s)" % ",".join(map(str, L5)))
    db = {norm(p): (json.loads(o), ci) for p, o, ci in cur.fetchall()}
    con.close()

    src = open(SEED, encoding="utf-8").read()
    idx = src.index("LEVEL5_QUIZZES = [")
    start = idx + len("LEVEL5_QUIZZES = ")
    depth = 0; i = start
    while i < len(src):
        if src[i] == '[': depth += 1
        elif src[i] == ']':
            depth -= 1
            if depth == 0: break
        i += 1
    block = src[start:i+1]
    data = ast.literal_eval(block)

    matched = skipped = 0
    for entry in data:
        for q in entry["questions"]:
            key = norm(q["prompt"])
            if key in db:
                opts, ci = db[key]
                q["options"] = opts
                q["correct_index"] = ci
                matched += 1
            else:
                skipped += 1

    new_block = "LEVEL5_QUIZZES = " + json.dumps(data, ensure_ascii=False, indent=2)
    new_src = src[:idx] + new_block + src[i+1:]

    if "--apply" in __import__("sys").argv:
        bak = SEED + ".bak_before_l5seeddistractors_20260911"
        if not os.path.exists(bak):
            shutil.copy(SEED, bak)
        open(SEED, "w", encoding="utf-8").write(new_src)
        print("APPLIED. matched=%d skipped=%d. backup=%s" % (matched, skipped, bak))
        # basic syntax check
        compile(new_src, SEED, "exec")
        print("syntax OK")
    else:
        print("DRY-RUN. matched=%d skipped=%d" % (matched, skipped))

if __name__ == "__main__":
    main()
