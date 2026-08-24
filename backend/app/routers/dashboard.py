"""Dashboard API (Phase 2).

Endpoint:
    GET /api/dashboard -> total progress, current level, today's lesson

Today-lesson recommendation rule (Phase 4 minimal):
    the first lesson the user has NOT yet mastered (available or needs_review),
    so the dashboard always points at the next actionable lesson.

"completed" counts lessons with status "mastered".
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
from ..services import lesson_status_map, ordered_lessons

router = APIRouter(prefix="/api")


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/dashboard", response_model=DashboardOut)
def get_dashboard(db: Session = Depends(get_db)):
    status_map, _ = lesson_status_map(db)
    ordered = ordered_lessons(db)

    total = len(ordered)
    # Minimal progress: a lesson counts as completed once it is mastered.
    completed = sum(1 for lid in status_map if status_map[lid] == "mastered")
    percentage = int(round(completed / total * 100)) if total else 0

    # Today's lesson = first lesson the user has NOT yet mastered (whether it is
    # freshly "available" or a "needs_review" retry). This keeps the dashboard
    # pointing at the next actionable lesson instead of going blank after a
    # sub-80% attempt.
    today_lesson = next((l for l in ordered if status_map.get(l.id) != "mastered"), None)
    current_level = None
    today_out = None

    if today_lesson is not None:
        level = db.get(CourseLevel, today_lesson.level_id)
        today_out = TodayLessonOut(
            id=today_lesson.id,
            title=today_lesson.title,
            slug=today_lesson.slug,
            description=today_lesson.description,
            estimated_minutes=today_lesson.estimated_minutes,
            level_id=today_lesson.level_id,
            level_title=level.title if level else "",
        )
        current_level = CurrentLevelOut(id=level.id, title=level.title) if level else None

    return DashboardOut(
        progress=ProgressOut(completed=completed, total=total, percentage=percentage),
        current_level=current_level,
        today_lesson=today_out,
        streak_days=0,  # Phase 6
    )
