"""Course map API (Phase 1).

Endpoints:
    GET /api/levels                    -> all levels with nested lessons
    GET /api/levels/{level_id}/lessons -> lessons of a single level

Lesson display status is a placeholder in Phase 1/2: the first lesson overall
is "available", everything else is "locked". The real progress system arrives
in Phase 5.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..models import CourseLevel, Lesson
from ..schemas import LessonOut, LevelOut
from ..services import lesson_status_map

router = APIRouter(prefix="/api")


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _to_lesson_out(lesson: Lesson, status_map: dict, score_map: dict) -> LessonOut:
    return LessonOut(
        **{c.name: getattr(lesson, c.name) for c in Lesson.__table__.columns},
        status=status_map.get(lesson.id, "locked"),
        mastery_score=score_map.get(lesson.id),
    )


@router.get("/levels", response_model=List[LevelOut])
def list_levels(db: Session = Depends(get_db)):
    status_map, score_map = lesson_status_map(db)
    levels = db.scalars(select(CourseLevel).order_by(CourseLevel.order_index)).all()
    result = []
    for level in levels:
        level_out = LevelOut(
            **{c.name: getattr(level, c.name) for c in CourseLevel.__table__.columns},
            lessons=[],
        )
        level_out.lessons = [
            _to_lesson_out(lesson, status_map, score_map) for lesson in level.lessons
        ]
        result.append(level_out)
    return result


@router.get("/levels/{level_id}/lessons", response_model=List[LessonOut])
def list_lessons(level_id: int, db: Session = Depends(get_db)):
    level = db.get(CourseLevel, level_id)
    if level is None:
        raise HTTPException(status_code=404, detail="Level not found")
    status_map, score_map = lesson_status_map(db)
    return [_to_lesson_out(lesson, status_map, score_map) for lesson in level.lessons]
