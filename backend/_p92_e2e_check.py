"""Phase 9.2 end-to-end checks (snapshot/restore friendly).

Covers the badge system end to end:
  * catalog shape: 20 badges, 8 journey + 12 special, codes stable
  * secret blanking for still-locked secrets (LATE_NIGHT / BUG_HUNTER)
  * backfill correctness: 6 expected unlocks from existing mastery data
    (LEVEL_0..3, QUIZ_100, WANMEI)
  * backfill idempotency: re-running does not change the unlock set
  * live submit path: BLITZ fires on a fast 5/5, suppressed when slow
  * BUG_HUNTER / LATE_NIGHT remain locked (no debug history / no late event)

Run:  python _p92_e2e_check.py
It snapshots spark_quest.db first and restores it on exit, so the live
database is never left mutated.
"""

import os
import shutil
import sys
import tempfile
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.main import app
from app.models import BadgeDefinition, LessonMastery, UserBadge
from sqlalchemy import select, func

DB_PATH = os.path.join(os.path.dirname(__file__), "spark_quest.db")
SNAPSHOT = os.path.join(tempfile.gettempdir(), "spark_quest_p92_e2e_snap.db")

EXPECTED_BACKFILL = {"LEVEL_0", "LEVEL_1", "LEVEL_2", "LEVEL_3", "QUIZ_100", "WANMEI"}


def q_correct_indices(db, lesson_id, n=5):
    from app.models import QuizQuestion
    qs = db.scalars(
        select(QuizQuestion)
        .where(QuizQuestion.lesson_id == lesson_id)
        .order_by(QuizQuestion.id)
        .limit(n)
    ).all()
    return [{"question_id": q.id, "selected_index": q.correct_index} for q in qs]


def snapshot():
    shutil.copy(DB_PATH, SNAPSHOT)


def restore():
    if os.path.exists(SNAPSHOT):
        shutil.copy(SNAPSHOT, DB_PATH)
        os.remove(SNAPSHOT)


def unlocked_codes(db):
    return {
        r[0]
        for r in db.execute(
            select(BadgeDefinition.code).join(
                UserBadge, UserBadge.badge_id == BadgeDefinition.id
            )
        ).all()
    }


def main() -> int:
    failures = []
    snapshot()
    try:
        with TestClient(app) as client:
            # --- catalog shape ---
            r = client.get("/api/badges")
            assert r.status_code == 200, f"badges {r.status_code}"
            badges = r.json()
            assert len(badges) == 20, f"expected 20, got {len(badges)}"
            journey = [b for b in badges if b["tier"] == "journey"]
            special = [b for b in badges if b["tier"] == "special"]
            assert len(journey) == 8, f"journey count {len(journey)}"
            assert len(special) == 12, f"special count {len(special)}"
            codes = {b["code"] for b in badges}
            assert codes == {
                "LEVEL_0", "LEVEL_1", "LEVEL_2", "LEVEL_3",
                "LEVEL_4", "LEVEL_5", "LEVEL_6", "LEVEL_7",
                "QUIZ_100", "QUIZ_500", "QUIZ_1000",
                "STREAK_7", "STREAK_30", "STREAK_100",
                "REVIEW_50", "LATE_NIGHT", "WANMEI", "BUG_HUNTER",
                "BLITZ", "QUANJING",
            }, f"unexpected codes {codes}"

            # --- secret blanking ---
            by_code = {b["code"]: b for b in badges}
            for sc in ("LATE_NIGHT", "BUG_HUNTER"):
                b = by_code[sc]
                assert b["is_secret"] and not b["unlocked"]
                assert b["name"] == "" and b["image"] == "", f"{sc} not blanked"
            print("[ok] catalog: 20 badges (8 journey + 12 special), secrets blanked")

            # --- backfill correctness ---
            with SessionLocal() as db:
                got = unlocked_codes(db)
            assert got == EXPECTED_BACKFILL, f"backfill mismatch: {got ^ EXPECTED_BACKFILL}"
            print(f"[ok] backfill unlocked exactly: {sorted(got)}")

            # --- backfill idempotency (re-evaluate, set must not change) ---
            r2 = client.get("/api/badges")
            after = {b["code"] for b in r2.json() if b["unlocked"]}
            assert after == EXPECTED_BACKFILL, f"idempotency broke: {after ^ EXPECTED_BACKFILL}"
            print("[ok] backfill idempotent on re-read")

            # --- live submit: BLITZ path ---
            with SessionLocal() as db:
                lesson_id = db.scalar(
                    select(LessonMastery.lesson_id)
                    .where(LessonMastery.status == "mastered")
                    .order_by(LessonMastery.lesson_id)
                    .limit(1)
                )
                assert lesson_id is not None
                answers = q_correct_indices(db, lesson_id)

            now_iso = lambda secs: (
                datetime.now(timezone.utc) - timedelta(seconds=secs)
            ).isoformat().replace("+00:00", "Z")

            r = client.post(
                f"/api/lessons/{lesson_id}/quiz/submit",
                json={"answers": answers, "started_at": now_iso(5)},
            )
            assert r.status_code == 200, f"submit {r.status_code}: {r.text}"
            nb = [b["code"] for b in r.json().get("new_badges", [])]
            assert "BLITZ" in nb, f"BLITZ should fire on fast 5/5; got {nb}"
            print(f"[ok] fast 5/5 unlocked: {nb}")

            # slow -> no BLITZ
            r = client.post(
                f"/api/lessons/{lesson_id}/quiz/submit",
                json={"answers": answers, "started_at": now_iso(120)},
            )
            assert r.status_code == 200
            nb2 = [b["code"] for b in r.json().get("new_badges", [])]
            assert "BLITZ" not in nb2, f"BLITZ must not fire when slow; got {nb2}"
            print(f"[ok] slow 5/5 suppressed: {nb2}")

            # after BLITZ, catalog shows it unlocked + still-locked secrets blanked
            r = client.get("/api/badges")
            by_code2 = {b["code"]: b for b in r.json()}
            assert by_code2["BLITZ"]["unlocked"] is True
            assert by_code2["LATE_NIGHT"]["name"] == ""  # still locked
            assert by_code2["BUG_HUNTER"]["name"] == ""  # still locked (0 debug)
            print("[ok] post-BLITZ catalog: BLITZ revealed, LATE_NIGHT/BUG_HUNTER still blanked")

            # BUG_HUNTER / LATE_NIGHT must NOT be in the unlocked set after this run
            with SessionLocal() as db:
                final = unlocked_codes(db)
            for must_stay_locked in ("BUG_HUNTER", "LATE_NIGHT"):
                assert must_stay_locked not in final, f"{must_stay_locked} should stay locked"
            print("[ok] BUG_HUNTER / LATE_NIGHT correctly remain locked")

        restore()
        print("\nALL PHASE 9.2 E2E CHECKS PASSED" if not failures else f"FAIL: {failures}")
        return 1 if failures else 0
    except Exception as e:  # noqa: BLE001
        restore()
        print(f"E2E FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
