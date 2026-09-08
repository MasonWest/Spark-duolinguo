"""Phase 9.1 API smoke test (writes to the real DB — snapshots and restores).

Flow:
  1. Snapshot `study_days` (whole table) + the target `lesson_mastery` row.
  2. GET /api/dashboard  -> baseline streak
  3. GET  /api/lessons/{id}/quiz
  4. POST /api/lessons/{id}/quiz/submit  (all-correct)
  5. GET /api/dashboard  -> streak after a real submission
  6. Restore everything snapshotted in step 1.

Run:
    cd backend && .venv/Scripts/python.exe _p91_smoke.py [base_url]
"""

import json
import sqlite3
import sys
import urllib.request
from pathlib import Path

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:9001"
DB = Path(__file__).resolve().parent / "spark_quest.db"


def request(method, path, payload=None):
    op = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        BASE + path, data=data, method=method,
        headers={"Content-Type": "application/json"},
    )
    with op.open(req, timeout=20) as r:
        return json.loads(r.read().decode())


def snapshot_study_days(conn):
    rows = conn.execute("SELECT * FROM study_days ORDER BY id").fetchall()
    cols = [d[0] for d in conn.execute("SELECT * FROM study_days LIMIT 1").description]
    return cols, rows


def snapshot_mastery(conn, lesson_id):
    cur = conn.execute("SELECT * FROM lesson_mastery WHERE lesson_id = ?", (lesson_id,))
    cols = [d[0] for d in cur.description]
    return cols, cur.fetchall()


def restore(cols_sd, rows_sd, cols_m, rows_m, lesson_id):
    conn = sqlite3.connect(DB)
    conn.execute("DELETE FROM study_days")
    if rows_sd:
        conn.executemany(
            f"INSERT INTO study_days ({','.join(cols_sd)}) VALUES ({','.join('?' * len(cols_sd))})",
            rows_sd,
        )
    conn.execute("DELETE FROM lesson_mastery WHERE lesson_id = ?", (lesson_id,))
    if rows_m:
        conn.executemany(
            f"INSERT INTO lesson_mastery ({','.join(cols_m)}) VALUES ({','.join('?' * len(cols_m))})",
            rows_m,
        )
    conn.commit()
    conn.close()


def main():
    conn = sqlite3.connect(DB)
    d0 = request("GET", "/api/dashboard")
    lesson = d0["today_lesson"]
    if not lesson:
        print("无可推荐课程，跳过提交测试")
        return
    lid = lesson["id"]

    cols_sd, rows_sd = snapshot_study_days(conn)
    cols_m, rows_m = snapshot_mastery(conn, lid)
    conn.close()
    print(f"快照完成：study_days={len(rows_sd)} 行, lesson_mastery(lesson {lid})={len(rows_m)} 行")

    try:
        print(f"\n[基线] streak={d0['streak_days']} studied_today={d0['studied_today']} "
              f"longest={d0['longest_streak']} last={d0['last_study_date']}")

        quiz = request("GET", f"/api/lessons/{lid}/quiz")
        ids = [q["id"] for q in quiz["questions"]]
        print(f"[抽题] lesson {lid} 抽到 {len(ids)} 题")

        # 全部按第 0 项提交（不保证满分）—— 只在乎"提交"这个动作被记录
        res = request("POST", f"/api/lessons/{lid}/quiz/submit",
                      {"answers": [{"question_id": q, "selected_index": 0} for q in ids]})
        print(f"[提交] score={res['score']} status={res['status']} passed={res['passed']}")

        d1 = request("GET", "/api/dashboard")
        print(f"[提交后] streak={d1['streak_days']} studied_today={d1['studied_today']} "
              f"longest={d1['longest_streak']} last={d1['last_study_date']}")

        ok = d1["studied_today"] is True and d1["streak_days"] >= 1
        print(f"\n断言 studied_today=True 且 streak>=1 -> {'PASS' if ok else 'FAIL'}")

        conn = sqlite3.connect(DB)
        today_rows = conn.execute(
            "SELECT study_date, activity_count, lessons_done, reviews_done FROM study_days "
            "ORDER BY study_date DESC LIMIT 3"
        ).fetchall()
        conn.close()
        print("最近 study_days:", today_rows)
    finally:
        restore(cols_sd, rows_sd, cols_m, rows_m, lid)
        print("\n已还原 study_days 与 lesson_mastery")

    d2 = request("GET", "/api/dashboard")
    print(f"[还原后] streak={d2['streak_days']} studied_today={d2['studied_today']} "
          f"longest={d2['longest_streak']} last={d2['last_study_date']}")
    same = (d2["streak_days"], d2["studied_today"], d2["longest_streak"], d2["last_study_date"]) == (
        d0["streak_days"], d0["studied_today"], d0["longest_streak"], d0["last_study_date"])
    print(f"断言 还原后与基线一致 -> {'PASS' if same else 'FAIL'}")


if __name__ == "__main__":
    main()
