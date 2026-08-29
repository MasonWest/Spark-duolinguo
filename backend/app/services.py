"""Shared course / mastery services.

Phase 4 introduces the real (minimal) lesson-status derivation, driven by the
`lesson_mastery` table instead of the old placeholder rule (only the first
lesson available, everything else locked).

Status vocabulary (Phase 4 minimal subset -- the full state machine with
learning / passed / review arrives in Phase 5):
    locked        predecessor lesson not yet mastered
    available     unlocked, never attempted
    needs_review  attempted but scored < 80%
    mastered      most recent submission scored >= 80% (sticky in Phase 4)

Unlock rule: the first lesson in course order is always available; any other
lesson is available only if its immediate predecessor is mastered. Because
`mastered` is sticky (never downgraded in Phase 4), unlock is also sticky.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import CourseLevel, Lesson, LessonMastery


# ---- Phase 6b: spaced-review schedule ----
#
# Deliberately NOT an SRS algorithm (no SM-2, no per-user curve fitting).
# A fixed, explainable ladder: `srs_stage` indexes into this list.
REVIEW_INTERVALS_DAYS = [1, 3, 7, 14, 30, 60, 120]
# A failed review does NOT reset the ladder -- it only inserts one short
# consolidation review. `srs_stage` is kept as-is.
REVIEW_FAIL_INTERVAL_DAYS = 3
# A review round is 5 questions and requires 5/5 (stricter than the 80%
# mastery threshold used by the learning quiz).
REVIEW_QUESTION_COUNT = 5


def is_due_for_review(mastery: Optional[LessonMastery], now: Optional[datetime] = None) -> bool:
    """True if this lesson's next review date has arrived.

    Only `mastered` lessons participate in the review cycle; a lesson without
    a scheduled review date is not due.
    """
    if mastery is None or mastery.status != "mastered":
        return False
    if mastery.next_review_at is None:
        return False
    return mastery.next_review_at <= (now or datetime.utcnow())


def due_lesson_ids(db: Session, now: Optional[datetime] = None) -> Set[int]:
    """Lesson ids whose review is due (batch, single query)."""
    stmt = select(LessonMastery.lesson_id).where(
        LessonMastery.status == "mastered",
        LessonMastery.next_review_at.is_not(None),
        LessonMastery.next_review_at <= (now or datetime.utcnow()),
    )
    return set(db.scalars(stmt).all())


def due_reviews(db: Session, now: Optional[datetime] = None) -> List[Tuple[Lesson, LessonMastery]]:
    """(lesson, mastery) pairs due for review, in global course order."""
    now = now or datetime.utcnow()
    due_ids = due_lesson_ids(db, now)
    if not due_ids:
        return []
    masteries = {
        m.lesson_id: m
        for m in db.scalars(
            select(LessonMastery).where(LessonMastery.lesson_id.in_(due_ids))
        ).all()
    }
    return [(l, masteries[l.id]) for l in ordered_lessons(db) if l.id in masteries]


def init_review_schedule(mastery: LessonMastery, now: Optional[datetime] = None) -> None:
    """First mastery: anchor the schedule and schedule the first review (+1 day)."""
    now = now or datetime.utcnow()
    mastery.first_mastered_at = now
    mastery.srs_stage = 0
    mastery.last_review_at = None
    mastery.review_count = 0
    mastery.next_review_at = now + timedelta(days=REVIEW_INTERVALS_DAYS[0])


def advance_review_schedule(mastery: LessonMastery, now: Optional[datetime] = None) -> int:
    """Review passed (5/5): climb one rung of the ladder.

    Returns the newly scheduled interval in days (for UI display).
    """
    now = now or datetime.utcnow()
    max_stage = len(REVIEW_INTERVALS_DAYS) - 1
    mastery.srs_stage = min(mastery.srs_stage + 1, max_stage)
    mastery.review_count = (mastery.review_count or 0) + 1
    mastery.last_review_at = now
    interval = REVIEW_INTERVALS_DAYS[mastery.srs_stage]
    mastery.next_review_at = now + timedelta(days=interval)
    return interval


def defer_review_schedule(mastery: LessonMastery, now: Optional[datetime] = None) -> int:
    """Review failed (<5/5): insert one short consolidation review in 3 days.

    `srs_stage` is intentionally left untouched -- failing is a consolidation
    step, not a demotion. The user may still retry immediately; this date is
    only the next *scheduled* review.
    """
    now = now or datetime.utcnow()
    mastery.last_review_at = now
    mastery.next_review_at = now + timedelta(days=REVIEW_FAIL_INTERVAL_DAYS)
    return REVIEW_FAIL_INTERVAL_DAYS


def ordered_lessons(db: Session) -> List[Lesson]:
    """All lessons in global course order (level order, then lesson order)."""
    stmt = (
        select(Lesson)
        .join(CourseLevel, Lesson.level_id == CourseLevel.id)
        .order_by(CourseLevel.order_index, Lesson.order_index)
    )
    return list(db.scalars(stmt).all())


def _mastery_by_lesson(db: Session) -> Dict[int, LessonMastery]:
    return {m.lesson_id: m for m in db.scalars(select(LessonMastery)).all()}


def compute_lesson_status(lesson: Lesson, db: Session) -> str:
    """Derived display status for a single lesson (Phase 4 minimal subset)."""
    masteries = _mastery_by_lesson(db)
    m = masteries.get(lesson.id)
    if m is not None and m.status == "mastered":
        return "mastered"
    if m is not None and m.status == "needs_review":
        return "needs_review"

    ordered = ordered_lessons(db)
    idx = next((i for i, l in enumerate(ordered) if l.id == lesson.id), None)
    if idx is None or idx == 0:
        # First lesson in course order is always available.
        return "available"
    predecessor = ordered[idx - 1]
    pred_m = masteries.get(predecessor.id)
    return "available" if (pred_m is not None and pred_m.status == "mastered") else "locked"


def mastery_score(lesson_id: int, db: Session) -> Optional[int]:
    """Most recent quiz score for a lesson, or None if never attempted."""
    m = db.scalars(
        select(LessonMastery).where(LessonMastery.lesson_id == lesson_id)
    ).first()
    return m.score if m is not None else None


def lesson_status_map(
    db: Session,
) -> Tuple[Dict[int, str], Dict[int, Optional[int]]]:
    """Batch-compute (status, score) for every lesson in one pass.

    Returns (status_by_lesson_id, score_by_lesson_id). Used by list endpoints
    to avoid N+1 queries.
    """
    masteries = _mastery_by_lesson(db)
    ordered = ordered_lessons(db)

    status: Dict[int, str] = {}
    for i, lesson in enumerate(ordered):
        m = masteries.get(lesson.id)
        if m is not None and m.status == "mastered":
            status[lesson.id] = "mastered"
        elif m is not None and m.status == "needs_review":
            status[lesson.id] = "needs_review"
        elif i == 0:
            status[lesson.id] = "available"
        else:
            pred_m = masteries.get(ordered[i - 1].id)
            status[lesson.id] = (
                "available" if (pred_m is not None and pred_m.status == "mastered") else "locked"
            )

    scores = {lid: m.score for lid, m in masteries.items()}
    return status, scores


def recommend_today_lesson(db: Session) -> Optional[Tuple[Lesson, str]]:
    """Recommend the "Today Lesson" based on Phase 5 priority:
    1. Earliest lesson with status 'needs_review'
    2. Earliest lesson with status 'available'
    3. None if everything is mastered or all remaining are locked
    """
    status_map, _ = lesson_status_map(db)
    ordered = ordered_lessons(db)

    # 1. Find the earliest "needs_review"
    for lesson in ordered:
        if status_map.get(lesson.id) == "needs_review":
            return lesson, "needs_review"

    # 2. Find the earliest "available"
    for lesson in ordered:
        if status_map.get(lesson.id) == "available":
            return lesson, "available"

    return None


def compute_level_status(level: CourseLevel, status_map: Dict[int, str]) -> str:
    """Dynamically compute Level status:
    - completed: all lessons are mastered
    - in_progress: at least one lesson is mastered/needs_review/learning
    - available: first lesson is available (and not started)
    - locked: first lesson is locked
    """
    lessons = level.lessons
    if not lessons:
        return "available"

    statuses = [status_map.get(l.id, "locked") for l in lessons]

    if all(s == "mastered" for s in statuses):
        return "completed"
    
    if any(s in ["mastered", "needs_review"] for s in statuses):
        return "in_progress"

    # Check status of the first lesson
    first_status = statuses[0]
    if first_status == "available":
        return "available"
    
    return "locked"
