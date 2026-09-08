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
from ..models import DEFAULT_USER_ID, BadgeDefinition, CourseLevel, Lesson, UserBadge
from ..schemas import (
    BadgeOut,
    CurrentLevelOut,
    DashboardOut,
    ProgressOut,
    ReviewDueItem,
    TodayLessonOut,
)
from ..services import (
    compute_streak,
    due_reviews,
    lesson_status_map,
    ordered_lessons,
    recommend_today_lesson,
)
from .badges import build_badge_out

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

    # Phase 9.1: streak is derived on read from `study_days` -- nothing is
    # stored, so it can never drift out of sync with the activity log.
    streak = compute_streak(db, now=now)

    # Phase 9.2: a few most-recently-unlocked badges for the dashboard strip.
    # Secret badges that are unlocked are shown normally (build_badge_out only
    # blanks secrets that are still locked).
    recent_rows = db.execute(
        select(BadgeDefinition, UserBadge.unlocked_at)
        .join(UserBadge, UserBadge.badge_id == BadgeDefinition.id)
        .where(UserBadge.user_id == DEFAULT_USER_ID)
        .order_by(UserBadge.unlocked_at.desc())
        .limit(6)
    ).all()
    recent_ids = {b.id for b, _ in recent_rows}
    recent_at = {b.id: (ua.isoformat() if ua is not None else None) for b, ua in recent_rows}
    recent_badges = [build_badge_out(b, recent_ids, recent_at) for b, _ in recent_rows]

    return DashboardOut(
        progress=ProgressOut(completed=completed, total=total, percentage=percentage),
        current_level=current_level,
        today_lesson=today_out,
        streak_days=streak.current,
        studied_today=streak.studied_today,
        longest_streak=streak.longest,
        last_study_date=streak.last_study_date,
        reviews_due=reviews_due,
        recent_badges=recent_badges,
    )
