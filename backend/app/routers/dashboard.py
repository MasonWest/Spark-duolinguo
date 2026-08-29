"""Dashboard API (Phase 2).

Endpoint:
    GET /api/dashboard -> total progress, current level, today's lesson

Today-lesson recommendation rule (Phase 4 minimal):
    the first lesson the user has NOT yet mastered (available or needs_review),
    so the dashboard always points at the next actionable lesson.

"completed" counts lessons with status "mastered".
"""

from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..models import CourseLevel, Lesson
from ..schemas import (
    CurrentLevelOut,
    DashboardOut,
    ProgressOut,
    ReviewDueItem,
    TodayLessonOut,
)
from ..services import (
    due_reviews,
    lesson_status_map,
    ordered_lessons,
    recommend_today_lesson,
)

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
    completed = sum(1 for lid in status_map if status_map[lid] == "mastered")
    percentage = int(round(completed / total * 100)) if total else 0

    # Phase 5 refined recommendation:
    # 1. Earliest needs_review
    # 2. Earliest available
    recommendation = recommend_today_lesson(db)

    current_level = None
    today_out = None

    if recommendation is not None:
        today_lesson, status = recommendation
        level = db.get(CourseLevel, today_lesson.level_id)
        today_out = TodayLessonOut(
            id=today_lesson.id,
            title=today_lesson.title,
            slug=today_lesson.slug,
            description=today_lesson.description,
            estimated_minutes=today_lesson.estimated_minutes,
            level_id=today_lesson.level_id,
            level_title=level.title if level else "",
            status=status,
        )

        if level:
            # Calculate level-specific progress
            level_lessons = level.lessons
            lvl_total = len(level_lessons)
            lvl_completed = sum(1 for l in level_lessons if status_map.get(l.id) == "mastered")
            lvl_pct = int(round(lvl_completed / lvl_total * 100)) if lvl_total else 0

            current_level = CurrentLevelOut(
                id=level.id,
                title=level.title,
                completed_count=lvl_completed,
                total_count=lvl_total,
                percentage=lvl_pct,
            )

    # Phase 6b: lessons whose scheduled review date has arrived.
    now = datetime.utcnow()
    reviews_due = []
    for lesson, mastery in due_reviews(db, now=now):
        level = db.get(CourseLevel, lesson.level_id)
        overdue = max(0, (now - mastery.next_review_at).days) if mastery.next_review_at else 0
        reviews_due.append(
            ReviewDueItem(
                lesson_id=lesson.id,
                title=lesson.title,
                level_title=level.title if level else "",
                next_review_at=(
                    mastery.next_review_at.isoformat() if mastery.next_review_at else None
                ),
                overdue_days=overdue,
            )
        )

    return DashboardOut(
        progress=ProgressOut(completed=completed, total=total, percentage=percentage),
        current_level=current_level,
        today_lesson=today_out,
        streak_days=0,  # Phase 6
        reviews_due=reviews_due,
    )
