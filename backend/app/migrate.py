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


def run_migrations() -> None:
    """Run all migrations in order. Called from init_db."""
    add_quiz_dimension_column()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_migrations()
    print("Migrations complete.")
