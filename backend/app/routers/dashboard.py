"""Dashboard API (Phase 2).

Endpoint:
    GET /api/dashboard -> total progress, current level, today's lesson

Today-lesson recommendation rule (simplest, until Phase 5):
    find the first "available" lesson (== first lesson in course order).

No user_progress table is created in Phase 2; "completed" stays 0.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..models import CourseLevel, Lesson
from ..schemas import (
    CurrentLevelOut,
    DashboardOut,
    ProgressOut,
    TodayLessonOut,
)
from ..services import first_lesson_id

router = APIRouter(prefix="/api")


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/dashboard", response_model=DashboardOut)
def get_dashboard(db: Session = Depends(get_db)):
    total = db.scalar(select(func.count()).select_from(Lesson)) or 0
    # No real progress system until Phase 5.
    completed = 0
    percentage = int(round(completed / total * 100)) if total else 0

    today_id = first_lesson_id(db)
    today_lesson = None
    current_level = None

    if today_id is not None:
        lesson = db.get(Lesson, today_id)
        if lesson is not None:
            level = db.get(CourseLevel, lesson.level_id)
            today_lesson = TodayLessonOut(
                id=lesson.id,
                title=lesson.title,
                slug=lesson.slug,
                description=lesson.description,
                estimated_minutes=lesson.estimated_minutes,
                level_id=lesson.level_id,
                level_title=level.title if level else "",
            )
            current_level = CurrentLevelOut(
                id=level.id, title=level.title
            ) if level else None

    return DashboardOut(
        progress=ProgressOut(
            completed=completed, total=total, percentage=percentage
        ),
        current_level=current_level,
        today_lesson=today_lesson,
        streak_days=0,  # Phase 6
    )
