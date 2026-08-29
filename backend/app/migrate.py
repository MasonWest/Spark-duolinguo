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

from sqlalchemy import text

try:
    # When imported as part of the `app` package (e.g. from database.init_db).
    from .database import engine, logger
except ImportError:  # pragma: no cover - standalone script execution
    from app.database import engine, logger


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


def run_migrations() -> None:
    """Run all migrations in order. Called from init_db."""
    add_quiz_dimension_column()
    add_lesson_mastery_review_columns()
    backfill_mastered_review_schedule()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_migrations()
    print("Migrations complete.")
