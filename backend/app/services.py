"""Shared course services.

Phase 2 introduces a dashboard that needs the "first available lesson".
The placeholder availability logic (Phase 1) is: the very first lesson in
course order is "available", everything else is "locked".

The real progress system arrives in Phase 5.
"""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import CourseLevel, Lesson


def first_lesson_id(db: Session) -> Optional[int]:
    """Id of the very first lesson in course order (level order, then lesson order)."""
    stmt = (
        select(Lesson.id)
        .join(CourseLevel, Lesson.level_id == CourseLevel.id)
        .order_by(CourseLevel.order_index, Lesson.order_index)
        .limit(1)
    )
    return db.scalar(stmt)


def lesson_status(lesson_id: int, first_id: Optional[int]) -> str:
    """Placeholder display status for a lesson.

    Phase 5 will replace this with the real progress system
    (locked / available / learning / passed / review / mastered).
    """
    if first_id is None:
        return "locked"
    return "available" if lesson_id == first_id else "locked"
