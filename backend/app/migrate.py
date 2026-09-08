"""Database migrations for Spark Quest.

Phase 6.1 adds a `dimension` column to the `quizzes` table. SQLite cannot use
`CREATE TABLE ... IF NOT EXISTS` to add columns to existing tables, so we run an
explicit, idempotent ALTER via this module.

Run standalone:
    cd backend
    python -m app.migrate

It is also invoked automatically from `database.init_db` so existing databases
get the column on next startup.
"""

import logging
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

try:
    # When imported as part of the `app` package (e.g. from database.init_db).
    from .database import engine, logger, SessionLocal
except ImportError:  # pragma: no cover - standalone script execution
    from app.database import engine, logger, SessionLocal


def add_quiz_dimension_column() -> None:
    """Add `quizzes.dimension` (TEXT, nullable) if it does not exist yet.

    Idempotent: safe to run on fresh DBs (column already present via
    create_all) or on existing DBs (column missing -> ALTER).
    """
    with engine.connect() as conn:
        existing = {
            row[1]
            for row in conn.execute(text("PRAGMA table_info(quizzes)")).fetchall()
        }
        if "dimension" in existing:
            logger.info("Migration: quizzes.dimension already present, skipping.")
            return
        conn.execute(text("ALTER TABLE quizzes ADD COLUMN dimension TEXT"))
        conn.commit()
        logger.info("Migration: added 'dimension' column to quizzes.")


def _table_columns(conn, table: str) -> set:
    return {row[1] for row in conn.execute(text(f"PRAGMA table_info({table})")).fetchall()}


# Phase 6b: spaced-review scheduling columns on `lesson_mastery`.
# No new table is created -- review is scheduling data attached to an existing
# mastered lesson, not a separate entity.
REVIEW_COLUMNS = {
    "first_mastered_at": "DATETIME",
    "srs_stage": "INTEGER NOT NULL DEFAULT 0",
    "next_review_at": "DATETIME",
    "last_review_at": "DATETIME",
    "review_count": "INTEGER NOT NULL DEFAULT 0",
}


def add_lesson_mastery_review_columns() -> None:
    """Add the Phase 6b review-schedule columns to `lesson_mastery`.

    Idempotent: safe on fresh DBs (columns already present via create_all) and
    on existing DBs (missing columns -> ALTER).
    """
    with engine.connect() as conn:
        existing = _table_columns(conn, "lesson_mastery")
        for name, decl in REVIEW_COLUMNS.items():
            if name in existing:
                continue
            conn.execute(text(f"ALTER TABLE lesson_mastery ADD COLUMN {name} {decl}"))
            logger.info(f"Migration: added '{name}' column to lesson_mastery.")
        conn.commit()


def backfill_mastered_review_schedule() -> None:
    """One-off backfill for lessons mastered *before* Phase 6b existed.

    Historical rows have no real "first mastered" timestamp -- only the most
    recent quiz time. We therefore treat `last_quiz_at` as an APPROXIMATE
    anchor: it is the best available signal, not ground truth. Newly mastered
    lessons (from now on) use a real `first_mastered_at`.

    Effect: legacy mastered lessons enter the review cycle at stage 0, i.e.
    due 1 day after their (approximate) mastery time. Long-mastered lessons
    will therefore already be overdue and show up in "today's review".
    """
    with engine.connect() as conn:
        existing = _table_columns(conn, "lesson_mastery")
        if "next_review_at" not in existing:
            return
        result = conn.execute(
            text(
                """
                UPDATE lesson_mastery
                   SET first_mastered_at = last_quiz_at,
                       srs_stage = 0,
                       next_review_at = datetime(last_quiz_at, '+1 day'),
                       review_count = 0
                 WHERE status = 'mastered'
                   AND next_review_at IS NULL
                   AND last_quiz_at IS NOT NULL
                """
            )
        )
        conn.commit()
        if result.rowcount:
            logger.info(
                f"Migration: backfilled review schedule for {result.rowcount} "
                "pre-existing mastered lesson(s) (last_quiz_at used as "
                "approximate first_mastered_at)."
            )


def backfill_study_days() -> None:
    """One-off Phase 9.1 backfill: rebuild past study days from mastery rows.

    IMPORTANT: this is a LOWER BOUND, not ground truth. `lesson_mastery` only
    stores the *most recent* quiz / review time per lesson, so any day whose
    only activity was re-attempting an already-recorded lesson is invisible
    here. Real per-day history starts the moment this migration runs.

    Idempotent: `INSERT OR IGNORE` on the (user_id, study_date) unique key, so
    re-running never duplicates rows and never overwrites live counters.
    """
    from .models import DEFAULT_USER_ID
    from .services import LOCAL_UTC_OFFSET_HOURS

    offset = f"{LOCAL_UTC_OFFSET_HOURS:+d} hours"
    with engine.connect() as conn:
        result = conn.execute(
            text(
                f"""
                INSERT OR IGNORE INTO study_days
                    (user_id, study_date, activity_count,
                     lessons_done, reviews_done, first_at, last_at)
                SELECT :uid,
                       date(datetime(t, '{offset}')),
                       COUNT(*),
                       SUM(CASE WHEN src = 'quiz'   THEN 1 ELSE 0 END),
                       SUM(CASE WHEN src = 'review' THEN 1 ELSE 0 END),
                       MIN(t),
                       MAX(t)
                  FROM (
                        SELECT last_quiz_at   AS t, 'quiz'   AS src
                          FROM lesson_mastery
                         WHERE last_quiz_at IS NOT NULL
                        UNION ALL
                        SELECT last_review_at AS t, 'review' AS src
                          FROM lesson_mastery
                         WHERE last_review_at IS NOT NULL
                       )
                 GROUP BY date(datetime(t, '{offset}'))
                """
            ),
            {"uid": DEFAULT_USER_ID},
        )
        conn.commit()
        if result.rowcount:
            logger.info(
                f"Migration: backfilled {result.rowcount} study day(s) from "
                "lesson_mastery (approximate -- see backfill_study_days docstring)."
            )


def backfill_badges() -> None:
    """One-off Phase 9.2 backfill: seed the `user_stats` baseline from existing
    `lesson_mastery` rows, then unlock any badges derivable from PRE-EXISTING
    data (no live submit event).

    NOT called from `run_migrations` -- it must run AFTER course/quiz seeding so
    the `LEVEL_*` badge definitions already exist (they are derived from
    `course_levels`). `database.init_db` calls it directly after `_seed_quizzes`.

    Idempotent and SAFE:
    * `user_stats` is only written if the row does NOT exist yet (ORM `get`
      then `add`). Re-running after the app is live -- when real submits have
      already incremented the counters via `increment_user_stats` -- never
      overwrites them. This is the one-time historical baseline only.
    * `evaluate_badges` re-checks all 20 rules but only unlocks badges not
      already present in `user_badges` (UNIQUE(user_id, badge_id) + INSERT OR
      IGNORE), so re-running is a no-op for unlocks too.
    * Event-only badges (BLITZ, LATE_NIGHT) are intentionally NOT unlocked here:
      there is no real submit event to attribute them to. They unlock on the
      live submit path instead (`event_kind` set, so `is_late_night` and the
      blitz clock are evaluated against the actual study time).
    """
    from .models import DEFAULT_USER_ID, UserStats
    from .badge_service import evaluate_badges

    with SessionLocal() as db:
        row = db.execute(
            text(
                """
                SELECT COALESCE(SUM(attempts), 0),
                       COALESCE(SUM(review_count), 0),
                       COALESCE(SUM(correct_count), 0)
                  FROM lesson_mastery
                """
            )
        ).first()
        attempts = int(row[0]) if row else 0
        reviews = int(row[1]) if row else 0
        correct = int(row[2]) if row else 0

        # One-time baseline only. (Field precision per the user_stats docstring
        # in models.py: attempts/reviews are EXACT; correct_count is a LOWER
        # BOUND; total_debug_correct has no history -> 0.)
        stats = db.get(UserStats, DEFAULT_USER_ID)
        if stats is None:
            db.add(
                UserStats(
                    user_id=DEFAULT_USER_ID,
                    total_quiz_correct=correct,
                    total_quiz_submitted=attempts,
                    total_reviews_passed=reviews,
                    total_reviews_submitted=reviews,
                    total_debug_correct=0,
                )
            )
            db.flush()
        # else: leave live counters untouched.

        newly = evaluate_badges(db, DEFAULT_USER_ID, event_kind=None)
        db.commit()
        if newly:
            logger.info(
                "Migration: backfilled badges, unlocked %s: %s",
                len(newly),
                ", ".join(b["code"] for b in newly),
            )


def run_migrations() -> None:
    """Run DDL/backfill migrations in order. Called from init_db.

    NOTE: badge seeding + backfill are intentionally NOT here (see
    `backfill_badges` docstring and `database.init_db`); they depend on
    course/quiz data being present first.
    """
    add_quiz_dimension_column()
    add_lesson_mastery_review_columns()
    backfill_mastered_review_schedule()
    backfill_study_days()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_migrations()
    print("Migrations complete.")
