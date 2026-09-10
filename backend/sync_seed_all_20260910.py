# -*- coding: utf-8 -*-
"""全量把真库内容回写播种文件（course_seed.json / quiz_seed.json）。

用途：避免将来「删库重建」把已修复的正确内容回退成旧的错误内容。
这一版不做 Level 过滤——所有 Level 的 content / objective / description / 题库
一律以真库为准。

运行：cd backend && python sync_seed_all_20260910.py [--dry]
"""

import json
import shutil
import sqlite3
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
DB = BASE / "spark_quest.db"
SEED = BASE / "app" / "course_seed.json"
QUIZ = BASE / "app" / "quiz_seed.json"
STAMP = "20260910_all"
DRY = "--dry" in sys.argv

if not DRY:
    for f in (SEED, QUIZ):
        shutil.copy(f, f.with_suffix(f".json.bak_before_{STAMP}"))
        print(f"backup -> {f.with_suffix(f'.json.bak_before_{STAMP}').name}")

conn = sqlite3.connect(DB)
cur = conn.cursor()

# ---- 1) course_seed.json ----
cur.execute("SELECT slug, objective, description, content FROM lessons")
rows = cur.fetchall()
db_lesson = {slug: (ob, de, json.loads(raw)) for slug, ob, de, raw in rows}
print("lessons from DB:", len(db_lesson))

seed = json.loads(SEED.read_text(encoding="utf-8"))
hit = 0
for level in seed["levels"]:
    for lesson in level["lessons"]:
        slug = lesson.get("slug")
        if slug in db_lesson:
            ob, de, content = db_lesson[slug]
            lesson["content"] = content
            if ob is not None:
                lesson["objective"] = ob
            if de is not None:
                lesson["description"] = de
            hit += 1
if hit != len(db_lesson):
    raise SystemExit(f"[FAIL] course_seed 只命中 {hit} 课（应为 {len(db_lesson)}）")
if not DRY:
    SEED.write_text(json.dumps(seed, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"[OK] course_seed.json: {hit} lessons synced")

# ---- 2) quiz_seed.json ----
cur.execute(
    "SELECT l.slug, q.type, q.prompt, q.options, q.correct_index, q.explanation, q.dimension "
    "FROM quizzes q JOIN lessons l ON l.id=q.lesson_id "
    "ORDER BY l.level_id, l.order_index, q.order_index"
)
by_slug: dict[str, list] = {}
n = 0
for slug, qtype, prompt, options, ci, exp, dim in cur.fetchall():
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
        entry["questions"] = by_slug[slug]
        hit += 1
if hit != len(by_slug):
    raise SystemExit(f"[FAIL] quiz_seed 只命中 {hit} 课（应为 {len(by_slug)}）")
if not DRY:
    QUIZ.write_text(json.dumps(quiz, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"[OK] quiz_seed.json: {hit} entries synced, {n} questions")

conn.close()

# ---- 3) 回读校验 ----
json.loads(SEED.read_text(encoding="utf-8"))
json.loads(QUIZ.read_text(encoding="utf-8"))
print("[OK] both seed files re-parsed successfully")
print("[dry]" if DRY else "[written]")
