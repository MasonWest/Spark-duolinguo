"""Spaced-review API (Phase 6b).

Endpoints:
    GET  /api/review/due                     -> lessons whose review date arrived
    GET  /api/review/{lesson_id}             -> a 5-question review round
    POST /api/review/{lesson_id}/submit      -> grade + reschedule

Design constraints (Phase 6b, deliberately minimal):
  * The review unit is the LESSON, never a single question.
  * No new table: the schedule lives on the existing `lesson_mastery` row.
  * Review is NOT a new learning status. It only runs on `mastered` lessons,
    and a failed review never demotes a lesson (status stays "mastered").
  * Passing requires 5/5 -- stricter than the 80% learning-quiz threshold.
  * On failure `next_review_at` moves 3 days out, but the user may retry
    immediately: "next scheduled review" and "allowed to retry now" are two
    different concepts and are deliberately decoupled.
"""

import json
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..models import CourseLevel, Lesson, LessonMastery, QuizQuestion
from ..schemas import (
    QuizQuestionOut,
    QuizResultItem,
    ReviewDueItem,
    ReviewFetchOut,
    ReviewResultOut,
    ReviewSubmitIn,
)
from ..services import (
    REVIEW_QUESTION_COUNT,
    advance_review_schedule,
    defer_review_schedule,
    due_reviews,
)
from .quizzes import _parse_options, _sample_quiz_questions

router = APIRouter(prefix="/api")


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _parse_weak_points(raw: str) -> List[int]:
    try:
        value = json.loads(raw or "[]")
        return [int(x) for x in value]
    except Exception:
        return []


def _priority_dimensions(mastery: LessonMastery, db: Session) -> List[str]:
    """Dimensions the learner got wrong last round (simple ordering hint)."""
    weak_ids = _parse_weak_points(mastery.weak_points)
    if not weak_ids:
        return []
    dims = db.scalars(
        select(QuizQuestion.dimension).where(QuizQuestion.id.in_(weak_ids))
    ).all()
    return [d for d in dict.fromkeys(dims) if d]


@router.get("/review/due", response_model=List[ReviewDueItem])
def list_due_reviews(db: Session = Depends(get_db)):
    """All lessons whose scheduled review date has arrived, in course order."""
    now = datetime.utcnow()
    items: List[ReviewDueItem] = []
    for lesson, mastery in due_reviews(db, now=now):
        level = db.get(CourseLevel, lesson.level_id)
        overdue = 0
        if mastery.next_review_at is not None:
            overdue = max(0, (now - mastery.next_review_at).days)
        items.append(
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
    return items


@router.get("/review/{lesson_id}", response_model=ReviewFetchOut)
def get_review(lesson_id: int, db: Session = Depends(get_db)):
    """Start a review round: 5 questions from the lesson bank (no answers).

    Allowed whenever the lesson is mastered -- including right after a failed
    review (the retry path), because `next_review_at` only schedules the next
    *automatic* prompt and must never block an immediate retry.
    """
    lesson = db.get(Lesson, lesson_id)
    if lesson is None:
        raise HTTPException(status_code=404, detail="Lesson not found")

    mastery = db.scalars(
        select(LessonMastery).where(LessonMastery.lesson_id == lesson_id)
    ).first()
    if mastery is None or mastery.status != "mastered":
        raise HTTPException(
            status_code=403, detail="只有已掌握的课程才能进入间隔复习"
        )

    all_questions = db.scalars(
        select(QuizQuestion)
        .where(QuizQuestion.lesson_id == lesson_id)
        .order_by(QuizQuestion.order_index)
    ).all()
    if not all_questions:
        raise HTTPException(status_code=400, detail="No quiz for this lesson")

    questions = _sample_quiz_questions(
        list(all_questions),
        n=REVIEW_QUESTION_COUNT,
        priority_dims=_priority_dimensions(mastery, db),
    )

    return ReviewFetchOut(
        lesson_id=lesson.id,
        lesson_title=lesson.title,
        questions=[
            QuizQuestionOut(
                id=q.id,
                type=q.type,
                prompt=q.prompt,
                options=_parse_options(q.options),
                dimension=q.dimension,
            )
            for q in questions
        ],
    )


@router.post("/review/{lesson_id}/submit", response_model=ReviewResultOut)
def submit_review(lesson_id: int, payload: ReviewSubmitIn, db: Session = Depends(get_db)):
    """Grade a review round. 5/5 passes; anything less is a failure."""
    lesson = db.get(Lesson, lesson_id)
    if lesson is None:
        raise HTTPException(status_code=404, detail="Lesson not found")

    mastery = db.scalars(
        select(LessonMastery).where(LessonMastery.lesson_id == lesson_id)
    ).first()
    if mastery is None or mastery.status != "mastered":
        raise HTTPException(
            status_code=403, detail="只有已掌握的课程才能进入间隔复习"
        )

    questions = db.scalars(
        select(QuizQuestion)
        .where(QuizQuestion.lesson_id == lesson_id)
        .order_by(QuizQuestion.order_index)
    ).all()
    if not questions:
        raise HTTPException(status_code=400, detail="No quiz for this lesson")

    q_by_id = {q.id: q for q in questions}
    for ans in payload.answers:
        if ans.question_id not in q_by_id:
            raise HTTPException(
                status_code=422,
                detail=f"Unknown question_id {ans.question_id} for lesson {lesson_id}",
            )

    total = len(payload.answers)
    if total != REVIEW_QUESTION_COUNT:
        raise HTTPException(
            status_code=422,
            detail=f"复习需提交 {REVIEW_QUESTION_COUNT} 道题，本次收到 {total} 道",
        )

    correct = 0
    weak_points: List[int] = []
    results: List[QuizResultItem] = []
    selected_by_q = {a.question_id: a.selected_index for a in payload.answers}

    for q in questions:
        selected = selected_by_q.get(q.id)
        if selected is None:
            continue
        is_correct = selected == q.correct_index
        if is_correct:
            correct += 1
        else:
            weak_points.append(q.id)
        results.append(
            QuizResultItem(
                question_id=q.id,
                selected_index=selected,
                correct_index=q.correct_index,
                is_correct=is_correct,
                explanation=q.explanation,
            )
        )

    passed = correct == total  # 5/5 -- 4/5 does NOT pass.

    now = datetime.utcnow()
    if passed:
        interval_days = advance_review_schedule(mastery, now=now)
    else:
        interval_days = defer_review_schedule(mastery, now=now)
    # `weak_points` keeps its original meaning: wrong question ids from the
    # most recent round (drives the next round's dimension ordering).
    mastery.weak_points = json.dumps(weak_points, ensure_ascii=False)
    # NOTE: status / score / attempts / last_quiz_at are intentionally NOT
    # touched here -- a review is scheduling, not re-learning. The 5-question
    # review score must never overwrite the 10-question learning-quiz score.

    db.commit()
    db.refresh(mastery)

    return ReviewResultOut(
        lesson_id=lesson_id,
        total=total,
        correct=correct,
        passed=passed,
        status=mastery.status,
        srs_stage=mastery.srs_stage,
        review_count=mastery.review_count,
        next_review_at=(
            mastery.next_review_at.isoformat() if mastery.next_review_at else None
        ),
        next_interval_days=interval_days,
        results=results,
    )
