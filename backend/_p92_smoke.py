"""Phase 9.2 API smoke test (snapshot/restore friendly).

Run AFTER `python -m app.migrate` (or just `init_db`) has seeded badge
definitions + backfilled. Mutates the DB (unlocks BLITZ, bumps counters), so
the caller snapshots first and restores after.

Tests the live submit -> badge-unlock path that backfill cannot exercise:
  * BLITZ  (5/5 + started_at within 60s)
  * BLITZ must NOT fire when started_at is > 60s old
  * GET /api/badges secret blanking
  * GET /api/dashboard recent_badges
  * review submit increments counters without error
"""

import sys
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.main import app
from app.models import LessonMastery, QuizQuestion
from sqlalchemy import select


def q_correct_indices(db, lesson_id, n=5):
    qs = db.scalars(
        select(QuizQuestion)
        .where(QuizQuestion.lesson_id == lesson_id)
        .order_by(QuizQuestion.id)
        .limit(n)
    ).all()
    return [{"question_id": q.id, "selected_index": q.correct_index} for q in qs]


def main() -> int:
    failures = []
    with TestClient(app) as client:
        # 1) health
        r = client.get("/api/health")
        assert r.status_code == 200, f"health {r.status_code}"
        print("[ok] health")

        # 2) badges catalog: 20 total, secrets blanked when locked
        r = client.get("/api/badges")
        assert r.status_code == 200, f"badges {r.status_code}"
        badges = r.json()
        assert len(badges) == 20, f"expected 20 badges, got {len(badges)}"
        by_code = {b["code"]: b for b in badges}
        for secret_code in ("LATE_NIGHT", "BUG_HUNTER"):
            b = by_code[secret_code]
            assert b["is_secret"] is True
            assert b["unlocked"] is False, f"{secret_code} should be locked"
            assert b["name"] == "", f"{secret_code} name must be blanked when locked"
            assert b["image"] == "", f"{secret_code} image must be blanked when locked"
        # journey/special non-secret unlocked ones show real name
        assert by_code["QUIZ_100"]["name"] == "百题斩"
        print("[ok] /api/badges: 20 total, secret blanking correct")

        # 3) dashboard recent_badges + streak fields
        r = client.get("/api/dashboard")
        assert r.status_code == 200, f"dashboard {r.status_code}"
        d = r.json()
        assert "recent_badges" in d and isinstance(d["recent_badges"], list)
        assert "streak_days" in d and "longest_streak" in d
        print(f"[ok] dashboard: {len(d['recent_badges'])} recent badges, streak={d['streak_days']}")

        # pick a mastered lesson for the submit paths
        with SessionLocal() as db:
            lesson_id = db.scalar(
                select(LessonMastery.lesson_id)
                .where(LessonMastery.status == "mastered")
                .order_by(LessonMastery.lesson_id)
                .limit(1)
            )
            assert lesson_id is not None, "need a mastered lesson"
            answers_fast = q_correct_indices(db, lesson_id)
            answers_review = q_correct_indices(db, lesson_id)

        now_iso = lambda secs_ago: (
            datetime.now(timezone.utc) - timedelta(seconds=secs_ago)
        ).isoformat().replace("+00:00", "Z")

        # 4) FAST perfect submit -> BLITZ unlocks
        payload = {"answers": answers_fast, "started_at": now_iso(5)}
        r = client.post(f"/api/lessons/{lesson_id}/quiz/submit", json=payload)
        assert r.status_code == 200, f"quiz submit {r.status_code}: {r.text}"
        nb = r.json().get("new_badges", [])
        codes = [b["code"] for b in nb]
        assert "BLITZ" in codes, f"BLITZ should unlock on fast 5/5; got {codes}"
        print(f"[ok] fast 5/5 submit unlocked: {codes}")

        # 5) SLOW perfect submit -> BLITZ must NOT re-unlock (and nothing else)
        payload = {"answers": answers_fast, "started_at": now_iso(120)}
        r = client.post(f"/api/lessons/{lesson_id}/quiz/submit", json=payload)
        assert r.status_code == 200, f"quiz submit slow {r.status_code}: {r.text}"
        codes2 = [b["code"] for b in r.json().get("new_badges", [])]
        assert "BLITZ" not in codes2, f"BLITZ must NOT fire when >60s old; got {codes2}"
        print(f"[ok] slow 5/5 submit unlocked: {codes2} (BLITZ correctly suppressed)")

        # 6) review submit -> no error, new_badges is a list
        payload = {"answers": answers_review}
        r = client.post(f"/api/review/{lesson_id}/submit", json=payload)
        assert r.status_code == 200, f"review submit {r.status_code}: {r.text}"
        rj = r.json()
        assert "new_badges" in rj
        print(f"[ok] review submit ok, passed={rj['passed']}")

        # 7) after BLITZ, the catalog should now show it unlocked (name revealed)
        r = client.get("/api/badges")
        by_code2 = {b["code"]: b for b in r.json()}
        assert by_code2["BLITZ"]["unlocked"] is True, "BLITZ should be unlocked now"
        assert by_code2["BLITZ"]["name"] == "闪电战"
        # a still-locked secret stays blanked
        assert by_code2["LATE_NIGHT"]["name"] == "", "LATE_NIGHT still locked -> blanked"
        print("[ok] /api/badges reflects BLITZ unlock + secret still blanked")

    print("\nALL SMOKE CHECKS PASSED" if not failures else "FAILURES: " + str(failures))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
