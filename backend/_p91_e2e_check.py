"""Phase 9.1 Streak -- end-to-end checks.

Runs on a TEMPORARY database copy / throwaway file so the real
`backend/spark_quest.db` is never written to. The only read against the real DB
is `compute_streak` (read-only by construction).

Run:
    cd backend
    .venv/Scripts/python.exe _p91_e2e_check.py
"""

import os
import shutil
import sqlite3
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import DEFAULT_USER_ID, StudyDay
from app.services import (
    LOCAL_UTC_OFFSET_HOURS,
    compute_streak,
    local_today,
    record_activity,
)

PASS, FAIL = [], []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(f"{'  OK ' if cond else 'FAIL'}  {name}{('  -> ' + str(detail)) if detail else ''}")


def make_session(path):
    engine = create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)()


def raw_days(path):
    c = sqlite3.connect(path)
    rows = c.execute("SELECT study_date, activity_count FROM study_days ORDER BY study_date").fetchall()
    c.close()
    return rows


def seed_days(path, rows):
    """Insert raw study-day rows directly (no activity semantics)."""
    c = sqlite3.connect(path)
    c.executemany(
        "INSERT INTO study_days (user_id,study_date,activity_count,lessons_done,reviews_done) "
        "VALUES (?,?,?,?,?)",
        [("local", d, n, n if k == "quiz" else 0, n if k == "review" else 0) for d, n, k in rows],
    )
    c.commit()
    c.close()


print(f"\n=== Phase 9.1 Streak E2E  (LOCAL_UTC_OFFSET_HOURS={LOCAL_UTC_OFFSET_HOURS}) ===\n")

tmpdir = tempfile.mkdtemp(prefix="sq_p91_")
db = os.path.join(tmpdir, "t.db")
Session = sessionmaker(autoflush=False, expire_on_commit=False)

# ---------------------------------------------------------------- 1. empty DB
print("[1] 空库")
s = make_session(db)
st = compute_streak(s)
check("空库 current=0", st.current == 0, st.current)
check("空库 longest=0", st.longest == 0, st.longest)
check("空库 studied_today=False", st.studied_today is False)
check("空库 last_study_date=None", st.last_study_date is None)
s.close()

# ------------------------------------------------- 2/3. record_activity 幂等
print("\n[2] record_activity 同一天多次只增一行")
s = make_session(db)
now = datetime(2026, 9, 7, 2, 0, 0)  # UTC -> 本地 09-07 10:00
record_activity(s, "quiz", now=now)
record_activity(s, "review", now=now)
record_activity(s, "quiz", now=now)
s.commit()
rows = raw_days(db)
check("同一天 3 次动作 -> 1 行", len(rows) == 1, rows)
check("activity_count=3", rows[0][1] == 3, rows[0])
st = compute_streak(s, now=now)
check("current=1", st.current == 1, st.current)
check("studied_today=True", st.studied_today is True)
check("longest=1", st.longest == 1, st.longest)
s.close()

# ------------------------------------------------------- 4. 连续三天
print("\n[3] 连续三天")
db3 = os.path.join(tmpdir, "t3.db")
s = make_session(db3)
seed_days(db3, [("2026-09-05", 1, "quiz"), ("2026-09-06", 1, "quiz"), ("2026-09-07", 2, "review")])
st = compute_streak(s, now=datetime(2026, 9, 7, 3, 0))
check("current=3", st.current == 3, st.current)
check("longest=3", st.longest == 3, st.longest)
check("studied_today=True", st.studied_today is True)
s.close()

# --------------------------------------- 5. 今天没学、昨天学了 -> 不断
print("\n[4] 今天没学、昨天学了（宽限日，不断链）")
db4 = os.path.join(tmpdir, "t4.db")
s = make_session(db4)
seed_days(db4, [("2026-09-04", 1, "quiz"), ("2026-09-05", 1, "quiz"), ("2026-09-06", 1, "quiz")])
st = compute_streak(s, now=datetime(2026, 9, 7, 3, 0))  # 本地 09-07
check("current 保持 3（不因今天没学而清零）", st.current == 3, st.current)
check("studied_today=False", st.studied_today is False)
check("longest=3", st.longest == 3, st.longest)
s.close()

# --------------------------------------------- 6. 前天才学 -> 已断
print("\n[5] 最后学习是前天 -> 断链")
db5 = os.path.join(tmpdir, "t5.db")
s = make_session(db5)
seed_days(db5, [("2026-09-03", 1, "quiz"), ("2026-09-04", 1, "quiz"), ("2026-09-05", 1, "quiz")])
st = compute_streak(s, now=datetime(2026, 9, 7, 3, 0))
check("current=0（隔了一整天）", st.current == 0, st.current)
check("longest 仍为 3（历史最长不因断链丢失）", st.longest == 3, st.longest)
s.close()

# --------------------------------------- 7. 断一天后重来 -> current 回到 1
print("\n[6] 断链后重新学习")
db6 = os.path.join(tmpdir, "t6.db")
s = make_session(db6)
seed_days(db6, [("2026-09-03", 1, "quiz"), ("2026-09-04", 1, "quiz"), ("2026-09-07", 1, "quiz")])
st = compute_streak(s, now=datetime(2026, 9, 7, 3, 0))
check("current=1", st.current == 1, st.current)
check("longest=2", st.longest == 2, st.longest)
s.close()

# ------------------------------------------------------- 8. 时区边界
print("\n[7] 时区：本地日期必须按 LOCAL_UTC_OFFSET_HOURS 折算")
db7 = os.path.join(tmpdir, "t7.db")
s = make_session(db7)
# UTC 2026-09-06 23:30 -> 本地 2026-09-07 07:30（UTC+8）
utc_evening = datetime(2026, 9, 6, 23, 30, 0)
check("local_today(UTC 09-06 23:30) == 2026-09-07", local_today(utc_evening) == "2026-09-07", local_today(utc_evening))
record_activity(s, "quiz", now=utc_evening)
s.commit()
rows = raw_days(db7)
check("记到本地当天 09-07，不是 09-06", rows[0][0] == "2026-09-07", rows)
st = compute_streak(s, now=utc_evening)
check("studied_today 按本地日判定为 True", st.studied_today is True)
s.close()

# ------------------------------------------------- 9. kind 校验
print("\n[8] 未知 kind 必须报错（防静默漏记）")
s = make_session(os.path.join(tmpdir, "t8.db"))
try:
    record_activity(s, "note")
    check("record_activity('note') 抛 ValueError", False)
except ValueError:
    check("record_activity('note') 抛 ValueError", True)
s.close()

# --------------------------------------- 10. 事务性：未 commit 不落库
print("\n[9] 事务边界：flush 后未 commit 不落库")
db9 = os.path.join(tmpdir, "t9.db")
s = make_session(db9)
record_activity(s, "quiz", now=datetime(2026, 9, 7, 3, 0))
in_session = s.scalars(select(StudyDay)).all()
check("flush 后 session 内可见（可与业务写入同事务）", len(in_session) == 1)
s.rollback()
check("rollback 后磁盘无记录", raw_days(db9) == [], raw_days(db9))
s.close()

# --------------------------------------- 11. 真库只读核对
print("\n[10] 真库（只读）")
real = Path(__file__).resolve().parent / "spark_quest.db"
if real.exists():
    eng = create_engine(f"sqlite:///{real}", connect_args={"check_same_thread": False})
    S = sessionmaker(bind=eng)
    s = S()
    st = compute_streak(s)
    days = [r[0] for r in raw_days(str(real))]
    print(f"      回填学习日: {days}")
    print(f"      current={st.current} longest={st.longest} studied_today={st.studied_today} last={st.last_study_date}")
    check("真库 current >= 1", st.current >= 1, st.current)
    check("真库 longest >= 1", st.longest >= 1, st.longest)
    check("真库回填天数 = 9", len(days) == 9, len(days))
    s.close()
else:
    print("      (真库不存在，跳过)")

shutil.rmtree(tmpdir, ignore_errors=True)

print(f"\n=== {len(PASS)} passed, {len(FAIL)} failed ===")
if FAIL:
    for f in FAIL:
        print("  FAILED:", f)
    sys.exit(1)
print("ALL GREEN")
