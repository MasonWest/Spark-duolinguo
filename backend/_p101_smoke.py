"""Phase 10.1 smoke test — uses the REAL spark_quest.db via in-process TestClient.

Covers the acceptance matrix:
  * Quiz/Review/Practice all append to quiz_answer_log (source-tagged).
  * /api/weak-questions derives weak list CROSS-SOURCE (wrong_count, last_*).
  * "Weak" = ever wrong, NOT currently-not-mastered (last_attempt_correct=true
    still listed).
  * Practice touches NOTHING else: lesson_mastery / study_days / user_stats /
    user_badges must be byte-identical before/after a practice submit.

DB is restored from the .bak_before_p101 snapshot at the end.
"""
import os
import sqlite3
import sys
import shutil
import json

DB = os.path.join(os.path.dirname(__file__), "spark_quest.db")
SNAP = None
for f in os.listdir(os.path.dirname(__file__)):
    if f.startswith("spark_quest.db.bak_before_p101_"):
        SNAP = os.path.join(os.path.dirname(__file__), f)
        break
assert SNAP, "snapshot not found"

# --- read correct_index + option counts for lesson 1 from the REAL db ---
con = sqlite3.connect(DB)
rows = con.execute(
    "SELECT id, correct_index, options FROM quizzes WHERE lesson_id=1"
).fetchall()
con.close()
q_info = {r[0]: (r[1], len(json.loads(r[2]))) for r in rows}
assert q_info, "lesson 1 has no quizzes"

from fastapi.testclient import TestClient
import app.main as main_mod
from app.database import init_db

init_db()  # TestClient without `with` does not run lifespan; create the new table explicitly.

client = TestClient(main_mod.app)


def wrong_sel(qid):
    ci, n = q_info[qid]
    return (ci + 1) % n


def right_sel(qid):
    return q_info[qid][0]


def get_presented(lesson_id):
    r = client.get(f"/api/lessons/{lesson_id}/quiz")
    assert r.status_code == 200, r.status_code
    return [q["id"] for q in r.json()["questions"]]


def submit_quiz(lesson_id, wrong_qid):
    ids = get_presented(lesson_id)
    answers = [
        {"question_id": qid, "selected_index": wrong_sel(qid) if qid == wrong_qid else right_sel(qid)}
        for qid in ids
    ]
    r = client.post(f"/api/lessons/{lesson_id}/quiz/submit", json={"answers": answers})
    assert r.status_code == 200, (r.status_code, r.text)
    return r.json()


def submit_review(lesson_id, wrong_qid):
    r = client.get(f"/api/review/{lesson_id}")
    assert r.status_code == 200, (r.status_code, r.text)
    ids = [q["id"] for q in r.json()["questions"]]
    answers = [
        {"question_id": qid, "selected_index": wrong_sel(qid) if qid == wrong_qid else right_sel(qid)}
        for qid in ids
    ]
    r = client.post(f"/api/review/{lesson_id}/submit", json={"answers": answers})
    assert r.status_code == 200, (r.status_code, r.text)
    return r.json()


def weak_list():
    r = client.get("/api/weak-questions")
    assert r.status_code == 200, r.status_code
    return r.json()


def practice(qid, selected):
    r = client.post(f"/api/weak-questions/{qid}/practice", json={"selected_index": selected})
    assert r.status_code == 200, (r.status_code, r.text)
    return r.json()


def snap_state():
    con = sqlite3.connect(DB)
    s = {}
    s["study_days"] = con.execute("SELECT COUNT(*) FROM study_days").fetchone()[0]
    # Full latest study-day row: catches a stray record_activity even on a day
    # whose row already exists (COUNT alone would not).
    s["study_day_row"] = con.execute(
        "SELECT study_date, activity_count, lessons_done, reviews_done, last_at "
        "FROM study_days ORDER BY id DESC LIMIT 1"
    ).fetchone()
    s["user_badges"] = con.execute("SELECT COUNT(*) FROM user_badges").fetchone()[0]
    s["log_rows"] = con.execute("SELECT COUNT(*) FROM quiz_answer_log").fetchone()[0]
    s["mastery_1"] = con.execute(
        "SELECT status, score, attempts, weak_points, srs_stage, next_review_at "
        "FROM lesson_mastery WHERE lesson_id=1"
    ).fetchone()
    us = con.execute(
        "SELECT total_quiz_correct, total_quiz_submitted, total_reviews_passed, "
        "total_reviews_submitted, total_debug_correct FROM user_stats"
    ).fetchone()
    s["user_stats"] = us
    con.close()
    return s


fails = []


def check(name, cond):
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
    if not cond:
        fails.append(name)


print("=== Phase 10.1 smoke ===")

# Choose the question to fail: first presented id from a quiz pull.
presented = get_presented(1)
Q = presented[0]
print(f"  target question_id = {Q}")

# 1) Quiz submit with Q wrong (4/5 -> passed, lesson 1 mastered)
r = submit_quiz(1, Q)
check("quiz submit: score 80 passed", r["score"] == 80 and r["passed"] is True)
wl = weak_list()
item = next((x for x in wl if x["question_id"] == Q), None)
check("weak list contains Q after quiz wrong", item is not None)
check("Q wrong_count == 1 after 1 wrong", item and item["wrong_count"] == 1)
check("Q last_attempt_correct == false (last is wrong)", item and item["last_attempt_correct"] is False)
check("GET single question omits correct_index",
      "correct_index" not in client.get(f"/api/weak-questions/{Q}").json())

# 2) Practice Q wrong (source=practice) -> wrong_count should rise to 2
p = practice(Q, wrong_sel(Q))
check("practice wrong returns is_correct=false", p["is_correct"] is False)
check("practice returns correct_index", "correct_index" in p and "explanation" in p)
wl = weak_list()
item = next(x for x in wl if x["question_id"] == Q)
check("Q wrong_count == 2 after practice wrong", item["wrong_count"] == 2)
check("Q last_attempt_correct false (last is wrong)", item["last_attempt_correct"] is False)

# 3) Review submit with Q wrong (lesson 1 is mastered) -> wrong_count 3, last wrong
before = snap_state()
r = submit_review(1, Q)
check("review submit accepted (lesson mastered)", r["status"] == "mastered")
wl = weak_list()
item = next(x for x in wl if x["question_id"] == Q)
check("Q wrong_count == 3 across quiz+review+practice", item["wrong_count"] == 3)
check("Q last_attempt_correct false after review wrong", item["last_attempt_correct"] is False)

# 4) Practice Q CORRECT -> wrong_count stays 3, last_attempt_correct TRUE (cross-source merge)
after_review = snap_state()
p = practice(Q, right_sel(Q))
check("practice correct returns is_correct=true", p["is_correct"] is True)
wl = weak_list()
item = next(x for x in wl if x["question_id"] == Q)
check("Q wrong_count stays 3 after practice correct", item["wrong_count"] == 3)
check("Q last_attempt_correct TRUE after practice correct", item["last_attempt_correct"] is True)
check("Q still in weak list (ever wrong)", item is not None)

# 5) Practice must NOT pollute mastery / streak / badge / stats.
# Baseline = snapshot taken RIGHT BEFORE the practice-correct call
# (after_review), because the review submit legitimately changed things.
after_practice = snap_state()
check("practice did NOT add study_days row", after_practice["study_days"] == after_review["study_days"])
check("practice did NOT touch study-day row content", after_practice["study_day_row"] == after_review["study_day_row"])
check("practice did NOT add user_badges row", after_practice["user_badges"] == after_review["user_badges"])
check("practice did NOT change user_stats", after_practice["user_stats"] == after_review["user_stats"])
check("practice did NOT change lesson_mastery row", after_practice["mastery_1"] == after_review["mastery_1"])
check("practice DID append one log row", after_practice["log_rows"] == after_review["log_rows"] + 1)

# 6) No wrong_* / status / mastery columns leaked into quiz_answer_log
con = sqlite3.connect(DB)
cols = [c[1] for c in con.execute("PRAGMA table_info(quiz_answer_log)").fetchall()]
con.close()
leaked = [c for c in cols if c in ("wrong_count", "status", "mastery", "is_fixed", "review_count", "next_review_at")]
check("no status/wrong_count/mastery columns in log", leaked == [])

# 7) Frontend type/build (separate check, run by caller) — placeholder
print(f"\n=== {'ALL PASS' if not fails else 'FAILURES: ' + str(fails)} ===")

# Restore DB from snapshot
shutil.copyfile(SNAP, DB)
print("DB restored from snapshot.")
sys.exit(1 if fails else 0)
