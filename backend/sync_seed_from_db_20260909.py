# -*- coding: utf-8 -*-
"""把 Level 4 真库内容回写播种文件，避免将来「删库重建」把修复过的正确内容
回退成旧的错误内容。

只回写 Level 4：
  - app/course_seed.json  -> L4 九课的 content
  - app/quiz_seed.json    -> l4-* 九个 entry 的 questions

运行：cd backend && python sync_seed_from_db_20260909.py
"""

import json
import shutil
import sqlite3
from pathlib import Path

BASE = Path(__file__).resolve().parent
DB = BASE / "spark_quest.db"
SEED = BASE / "app" / "course_seed.json"
QUIZ = BASE / "app" / "quiz_seed.json"
STAMP = "20260909"

for f in (SEED, QUIZ):
    shutil.copy(f, f.with_suffix(f".json.bak_before_l4fix_{STAMP}"))
    print(f"backup -> {f.with_suffix(f'.json.bak_before_l4fix_{STAMP}').name}")

conn = sqlite3.connect(DB)
cur = conn.cursor()
cur.execute("SELECT id FROM course_levels WHERE order_index=4")
level_id = cur.fetchone()[0]

# ---- 1) course_seed.json ----
cur.execute(
    "SELECT slug, content FROM lessons WHERE level_id=? ORDER BY order_index", (level_id,)
)
db_content = {slug: json.loads(raw) for slug, raw in cur.fetchall()}
print("lessons from DB:", len(db_content))

seed = json.loads(SEED.read_text(encoding="utf-8"))
hit = 0
for level in seed["levels"]:
    if level.get("order_index") != 4:
        continue
    for lesson in level["lessons"]:
        slug = lesson.get("slug")
        if slug in db_content:
            lesson["content"] = db_content[slug]
            hit += 1
if hit != 9:
    raise SystemExit(f"[FAIL] course_seed 只命中 {hit} 课（应为 9）")
SEED.write_text(json.dumps(seed, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"[OK] course_seed.json: {hit} lessons synced")

# ---- 2) quiz_seed.json ----
cur.execute(
    "SELECT l.slug, q.id, q.type, q.prompt, q.options, q.correct_index, q.explanation, q.dimension "
    "FROM quizzes q JOIN lessons l ON l.id=q.lesson_id WHERE l.level_id=? "
    "ORDER BY l.order_index, q.order_index",
    (level_id,),
)
by_slug: dict[str, list[dict]] = {}
n = 0
for slug, qid, qtype, prompt, options, ci, exp, dim in cur.fetchall():
    by_slug.setdefault(slug, []).append(
        {
            "type": qtype,
            "prompt": prompt,
            "options": json.loads(options),
            "correct_index": ci,
            "explanation": exp,
            "dimension": dim,
        }
    )
    n += 1
print("quizzes from DB:", n)

quiz = json.loads(QUIZ.read_text(encoding="utf-8"))
hit = 0
for entry in quiz["quizzes"]:
    slug = entry.get("lesson_slug")
    if slug in by_slug:
        if len(by_slug[slug]) != 10:
            raise SystemExit(f"[FAIL] {slug} 题目数为 {len(by_slug[slug])}")
        entry["questions"] = by_slug[slug]
        hit += 1
if hit != 9:
    raise SystemExit(f"[FAIL] quiz_seed 只命中 {hit} 课（应为 9）")
QUIZ.write_text(json.dumps(quiz, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"[OK] quiz_seed.json: {hit} entries synced, {n} questions")

conn.close()

# ---- 3) 回读校验 ----
json.loads(SEED.read_text(encoding="utf-8"))
json.loads(QUIZ.read_text(encoding="utf-8"))
print("[OK] both seed files re-parsed successfully")
