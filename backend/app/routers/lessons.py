"""Lesson detail API (Phase 3).

Endpoint:
    GET /api/lessons/{lesson_id} -> full lesson content for the learning page

The structured content (explanation / examples / key_points /
common_mistakes) lives in lessons.content as a JSON text column, written
from course_seed.json at seed/backfill time — the React page never
hardcodes course text.

next_lesson follows global course order (level.order_index, then
lesson.order_index), so the last lesson of a level leads to the first
lesson of the next level.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import TypeAdapter
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..models import CourseLevel, Lesson
from ..schemas import (
    LessonContentOut,
    LessonDetailOut,
    NextLessonOut,
)
from ..services import compute_lesson_status, mastery_score

router = APIRouter(prefix="/api")

_content_adapter: TypeAdapter = TypeAdapter(LessonContentOut)


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _parse_content(raw: Optional[str]) -> LessonContentOut:
    """Parse the JSON text stored in lessons.content, tolerating bad/empty data."""
    if not raw or not raw.strip():
        return LessonContentOut()
    try:
        return _content_adapter.validate_json(raw)
    except Exception:
        return LessonContentOut()


def _ordered_lessons(db: Session) -> List[Lesson]:
    """All lessons in global course order (level order, then lesson order)."""
    stmt = (
        select(Lesson)
        .join(CourseLevel, Lesson.level_id == CourseLevel.id)
        .order_by(CourseLevel.order_index, Lesson.order_index)
    )
    return list(db.scalars(stmt).all())


@router.get("/lessons/{lesson_id}", response_model=LessonDetailOut)
def get_lesson(lesson_id: int, db: Session = Depends(get_db)):
    lesson = db.get(Lesson, lesson_id)
    if lesson is None:
        raise HTTPException(status_code=404, detail="Lesson not found")

    next_lesson: Optional[NextLessonOut] = None
    ordered = _ordered_lessons(db)
    for i, item in enumerate(ordered):
        if item.id == lesson.id and i + 1 < len(ordered):
            nxt = ordered[i + 1]
            next_lesson = NextLessonOut(id=nxt.id, title=nxt.title)
            break

    return LessonDetailOut(
        id=lesson.id,
        level_id=lesson.level_id,
        level_title=lesson.level.title if lesson.level else "",
        title=lesson.title,
        slug=lesson.slug,
        description=lesson.description,
        objective=lesson.objective,
        estimated_minutes=lesson.estimated_minutes,
        status=compute_lesson_status(lesson, db),
        mastery_score=mastery_score(lesson.id, db),
        content=_parse_content(lesson.content),
        next_lesson=next_lesson,
    )
