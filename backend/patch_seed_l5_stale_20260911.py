# -*- coding: utf-8 -*-
"""Sync the 2 stale-prompt L5 questions (q456 / q516) into seed_level5.py.

The 2026-09-10 L5/L6 audit changed these two questions' PROMPTS in the DB but
never wrote them back to the seed. The earlier distractor-rewrite patch
(2026-09-11) matched seed<->DB by normalized prompt, so it skipped these two
and they still carry OLD prompts + OLD short-stub distractors. On a re-seed
those two would resurrect the "correct is always longest" bug.

This script maps the two stale seed prompts to their DB counterparts by qid
and overwrites prompt + options + correct_index, so the seed mirrors the DB.

DB is the live source of truth.
"""
import sqlite3, json, re, shutil, os, ast, sys

DB = "spark_quest.db"
SEED = "seed_level5.py"
L5 = [40, 41, 42, 43, 44, 45, 46, 47, 48]

# stale seed prompt -> DB qid
STALE_MAP = {
    "为什么 groupBy / join / orderBy 会触发 Shuffle？": 456,
    "数 Stage 的公式是？": 516,
}

def norm(s):
    return re.sub(r"\s+", "", s).strip()

def main():
    con = sqlite3.connect(DB); cur = con.cursor()
    db_by_qid = {}
    db_by_prompt = {}
    cur.execute("select id, prompt, options, correct_index from quizzes where lesson_id in (%s)" % ",".join(map(str, L5)))
    for qid, p, o, ci in cur.fetchall():
        db_by_qid[qid] = (p, json.loads(o), ci)
        db_by_prompt[norm(p)] = (p, json.loads(o), ci)
    con.close()

    src = open(SEED, encoding="utf-8").read()
    idx = src.index("LEVEL5_QUIZZES = ")
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
            if key in db_by_prompt:
                # normal path: prompt already matches DB
                p, opts, ci = db_by_prompt[key]
                q["options"] = opts
                q["correct_index"] = ci
                matched += 1
            elif q["prompt"] in STALE_MAP:
                # stale prompt: pull the DB question by qid, overwrite prompt too
                qid = STALE_MAP[q["prompt"]]
                p, opts, ci = db_by_qid[qid]
                q["prompt"] = p
                q["options"] = opts
                q["correct_index"] = ci
                matched += 1
                print("  stale-prompt synced: seed '%s' -> DB q%d ('%s')" % (q["prompt"], qid, p))
            else:
                skipped += 1
                print("  SKIP (no DB match): '%s'" % q["prompt"])

    new_block = "LEVEL5_QUIZZES = " + json.dumps(data, ensure_ascii=False, indent=2)
    new_src = src[:idx] + new_block + src[i+1:]

    if "--apply" in sys.argv:
        bak = SEED + ".bak_before_l5stale_20260911"
        if not os.path.exists(bak):
            shutil.copy(SEED, bak)
        open(SEED, "w", encoding="utf-8").write(new_src)
        compile(new_src, SEED, "exec")  # syntax check
        print("APPLIED. matched=%d skipped=%d. backup=%s" % (matched, skipped, bak))
    else:
        print("DRY-RUN. matched=%d skipped=%d" % (matched, skipped))

if __name__ == "__main__":
    main()
