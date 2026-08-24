"""Database engine setup for Spark Quest.

- engine / Base / SessionLocal
- init_db(): create tables and seed course data when empty
"""

import json
import logging
from pathlib import Path

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

logger = logging.getLogger("spark_quest")

# SQLite file lives next to the backend/ directory (backend/spark_quest.db)
DB_PATH = Path(__file__).resolve().parent.parent / "spark_quest.db"

DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # needed by SQLite + FastAPI
    echo=False,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    """Base class for ORM models."""


SEED_FILE = Path(__file__).resolve().parent / "course_seed.json"


def check_database_connection() -> bool:
    """Open a connection and run a trivial query.

    SQLite creates the file on first connect, so this both verifies
    connectivity and initializes the database file.
    """
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return DB_PATH.exists()


def init_db() -> None:
    """Create tables and seed course data if the database is empty."""
    # Import here so models are registered on Base before create_all.
    from . import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _seed_course_data()


def _seed_course_data() -> None:
    """Insert seed levels/lessons only when course_levels is empty.

    When the course data already exists (e.g. DB created in Phase 1/2),
    lesson content is backfilled by slug instead — Phase 3 added structured
    content (explanation / examples / key_points / common_mistakes) to the
    seed file, and existing rows still have an empty `content` placeholder.
    """
    from .models import CourseLevel, Lesson

    data = json.loads(SEED_FILE.read_text(encoding="utf-8"))

    with Session(engine) as session:
        already_seeded = session.scalar(select(CourseLevel).limit(1)) is not None
        if not already_seeded:
            for level_data in data["levels"]:
                lessons = level_data.pop("lessons", [])
                level = CourseLevel(**level_data)
                for lesson_data in lessons:
                    level.lessons.append(Lesson(**lesson_data))
                session.add(level)
            session.commit()
            n_levels = len(data["levels"])
            n_lessons = sum(len(l["lessons"]) for l in data["levels"])
            logger.info("Seeded course data: %s levels, %s lessons.", n_levels, n_lessons)
        else:
            logger.info("Course data already present, skipping seed.")

        _backfill_lesson_content(session, data)


def _backfill_lesson_content(session: Session, data: dict) -> None:
    """Fill empty lessons.content from the seed file, matched by slug.

    Idempotent: rows that already carry content are left untouched, so
    hand-edited content in the DB is never overwritten on restart.
    """
    from .models import Lesson

    seed_content = {
        lesson["slug"]: json.dumps(lesson["content"], ensure_ascii=False)
        for level in data["levels"]
        for lesson in level["lessons"]
        if lesson.get("content")
    }
    if not seed_content:
        return

    updated = 0
    for lesson in session.scalars(select(Lesson)).all():
        if not (lesson.content or "").strip() and lesson.slug in seed_content:
            lesson.content = seed_content[lesson.slug]
            updated += 1
    if updated:
        session.commit()
        logger.info("Backfilled lesson content for %s lessons.", updated)
