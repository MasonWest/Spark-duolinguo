"""Weak Questions API (Phase 10.1).

Endpoints:
    GET  /api/weak-questions                  -> derived list of weak questions
    GET  /api/weak-questions/{question_id}   -> a single question (no answer)
    POST /api/weak-questions/{question_id}/practice -> grade one re-practice

Design constraints (Phase 10.1, deliberately minimal):
  * This router reads/writes ONLY the `quiz_answer_log` fact table. It never
    touches `lesson_mastery` / SRS / streak / badge / user_stats.
  * "Weak question" = a question with >= 1 wrong answer in history. NOT "not
    currently mastered". A question answered wrong twice then right twice is
    STILL listed (wrong_count=2, last_attempt_correct=true) -- that is by design.
  * Aggregation is CROSS-SOURCE: quiz + review + practice logs are merged for the
    same question. `source` is only an event label, never a separate silo.
  * The practice endpoint commits a single standalone row and calls NONE of
    record_activity / increment_user_stats / evaluate_badges. A re-practice is
    just one more fact.
"""

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..models import (
    DEFAULT_USER_ID,
    CourseLevel,
    Lesson,
    QuizAnswerLog,
    QuizQuestion,
)
from ..schemas import (
    WeakQuestionDetailOut,
    WeakQuestionOut,
    WeakQuestionPracticeIn,
    WeakQuestionPracticeOut,
)

router = APIRouter(prefix="/api")


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _parse_options(raw: str) -> list:
    try:
        return json.loads(raw)
    except Exception:
        return []


@router.get("/weak-questions", response_model=list[WeakQuestionOut])
def list_weak_questions(db: Session = Depends(get_db)):
    """Derive the weak-question list from the fact table (read-only).

    One row per question that has EVER been answered wrong, across all sources.
    All counts/timestamps are computed here -- nothing is persisted.
    """
    logs = (
        db.scalars(
            select(QuizAnswerLog)
            .where(QuizAnswerLog.user_id == DEFAULT_USER_ID)
            .order_by(QuizAnswerLog.submitted_at)
        )
        .all()
    )

    # Group by question_id, preserving chronological order within each group.
    groups: dict = {}
    for log in logs:
        groups.setdefault(log.question_id, []).append(log)

    items: list[WeakQuestionOut] = []
    for qid, rows in groups.items():
        wrong_rows = [r for r in rows if r.is_correct == 0]
        if not wrong_rows:
            # No wrong answer ever -> not a weak question in Phase 10.1.
            continue
        rows_sorted = sorted(rows, key=lambda r: r.submitted_at)
        last = rows_sorted[-1]

        q = db.get(QuizQuestion, qid)
        if q is None:
            continue
        lesson = db.get(Lesson, q.lesson_id)
        level_order = 0
        if lesson is not None:
            level = db.get(CourseLevel, lesson.level_id)
            if level is not None:
                level_order = level.order_index

        items.append(
            WeakQuestionOut(
                question_id=qid,
                lesson_id=q.lesson_id,
                lesson_title=lesson.title if lesson else "",
                level_order=level_order,
                dimension=q.dimension,
                prompt=q.prompt,
                wrong_count=len(wrong_rows),
                last_wrong_at=max(r.submitted_at for r in wrong_rows).isoformat(),
                last_attempt_at=last.submitted_at.isoformat(),
                last_attempt_correct=bool(last.is_correct),
            )
        )

    # Most-wrong first; ties broken by most-recent wrong attempt.
    items.sort(key=lambda x: (x.wrong_count, x.last_wrong_at), reverse=True)
    return items


@router.get("/weak-questions/{question_id}", response_model=WeakQuestionDetailOut)
def get_weak_question(question_id: int, db: Session = Depends(get_db)):
    """Return a single weak question's prompt for re-practice.

    Deliberately excludes `correct_index` -- the answer must not leak to the
    practice UI. The practice endpoint grades server-side against the real value.
    """
    q = db.get(QuizQuestion, question_id)
    if q is None:
        raise HTTPException(status_code=404, detail="Question not found")
    return WeakQuestionDetailOut(
        id=q.id,
        type=q.type,
        prompt=q.prompt,
        options=_parse_options(q.options),
        dimension=q.dimension,
    )


@router.post(
    "/weak-questions/{question_id}/practice",
    response_model=WeakQuestionPracticeOut,
)
def practice_weak_question(
    question_id: int,
    payload: WeakQuestionPracticeIn,
    db: Session = Depends(get_db),
):
    """Grade one re-practice attempt and append a fact row.

    Server grades against `quizzes.correct_index` (never trusts the client).
    Appends a single `QuizAnswerLog` row with source="practice" and commits it
    STANDALONE. It does NOT call record_activity / increment_user_stats /
    evaluate_badges, and does NOT touch lesson_mastery / SRS / streak / badges.
    A re-practice is just one more fact; it can never silently change learning
    state.
    """
    q = db.get(QuizQuestion, question_id)
    if q is None:
        raise HTTPException(status_code=404, detail="Question not found")

    is_correct = payload.selected_index == q.correct_index

    db.add(
        QuizAnswerLog(
            lesson_id=q.lesson_id,
            question_id=q.id,
            source="practice",
            selected_index=payload.selected_index,
            correct_index=q.correct_index,
            is_correct=1 if is_correct else 0,
        )
    )
    db.commit()

    return WeakQuestionPracticeOut(
        is_correct=is_correct,
        correct_index=q.correct_index,
        explanation=q.explanation,
    )
