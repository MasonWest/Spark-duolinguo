"""Quiz + Lesson Mastery API (Phase 4).

Endpoints:
    GET  /api/lessons/{lesson_id}/quiz      -> questions (no answer leaked)
    POST /api/lessons/{lesson_id}/quiz/submit -> grade, mastery status, unlock

Grading is deterministic and server-side: a question is correct iff the
submitted option index equals the stored `correct_index`. No AI, no free-text
scoring.

Mastery is "sticky" in Phase 4: once a lesson first reaches >= 80% it becomes
`mastered` and a later sub-80% re-quiz does NOT downgrade it (nor re-lock the
next lesson). A sub-80% first attempt is `needs_review` and can be retaken.
"""

import json
import random
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..models import Lesson, LessonMastery, QuizQuestion
from ..schemas import (
    QuizFetchOut,
    QuizQuestionOut,
    QuizResultItem,
    QuizResultOut,
    QuizSubmitIn,
)
from ..services import compute_lesson_status, ordered_lessons

router = APIRouter(prefix="/api")

MASTERY_THRESHOLD = 80  # score >= 80 -> mastered


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _parse_options(raw: str) -> List[str]:
    try:
        return json.loads(raw)
    except Exception:
        return []


def _sample_quiz_questions(questions: List[QuizQuestion], n: int = 5) -> List[QuizQuestion]:
    """Phase 6.1: draw `n` questions, preferring dimension diversity.

    Questions are grouped by their `dimension` tag (NULL -> "uncategorized").
    We take one from as many distinct dimensions as possible, then fill the
    remainder from whatever is left. There is NO hard constraint (e.g. we do
    not require a fixed number of dimensions) — diversity is only preferred
    when the lesson naturally has variety, so future lessons are never boxed
    in by the rule.
    """
    if len(questions) <= n:
        return list(questions)

    groups: dict = {}
    for q in questions:
        key = (q.dimension or "uncategorized") or "uncategorized"
        groups.setdefault(key, []).append(q)

    dims = list(groups.keys())
    random.shuffle(dims)

    picked: List[QuizQuestion] = []
    for d in dims:
        if len(picked) >= n:
            break
        bucket = list(groups[d])
        random.shuffle(bucket)
        picked.append(bucket[0])

    picked_ids = {id(q) for q in picked}
    remaining = [q for q in questions if id(q) not in picked_ids]
    random.shuffle(remaining)
    while len(picked) < n and remaining:
        picked.append(remaining.pop())

    random.shuffle(picked)
    return picked


@router.get("/lessons/{lesson_id}/quiz", response_model=QuizFetchOut)
def get_quiz(lesson_id: int, db: Session = Depends(get_db)):
    lesson = db.get(Lesson, lesson_id)
    if lesson is None:
        raise HTTPException(status_code=404, detail="Lesson not found")
    if compute_lesson_status(lesson, db) == "locked":
        raise HTTPException(status_code=403, detail="Lesson is locked; master the previous lesson first")

    all_questions = db.scalars(
        select(QuizQuestion)
        .where(QuizQuestion.lesson_id == lesson_id)
        .order_by(QuizQuestion.order_index)
    ).all()

    # Phase 6.1: sample 5 from the bank, preferring dimension diversity.
    questions = _sample_quiz_questions(all_questions, n=5)

    return QuizFetchOut(
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


@router.post("/lessons/{lesson_id}/quiz/submit", response_model=QuizResultOut)
def submit_quiz(lesson_id: int, payload: QuizSubmitIn, db: Session = Depends(get_db)):
    lesson = db.get(Lesson, lesson_id)
    if lesson is None:
        raise HTTPException(status_code=404, detail="Lesson not found")
    if compute_lesson_status(lesson, db) == "locked":
        raise HTTPException(status_code=403, detail="Lesson is locked; master the previous lesson first")

    questions = db.scalars(
        select(QuizQuestion)
        .where(QuizQuestion.lesson_id == lesson_id)
        .order_by(QuizQuestion.order_index)
    ).all()
    if not questions:
        raise HTTPException(status_code=400, detail="No quiz for this lesson")

    q_by_id = {q.id: q for q in questions}
    # All submitted question_ids must belong to this lesson.
    for ans in payload.answers:
        if ans.question_id not in q_by_id:
            raise HTTPException(
                status_code=422,
                detail=f"Unknown question_id {ans.question_id} for lesson {lesson_id}",
            )

    # Phase 6.1: only the 5 questions actually presented (and answered) are
    # graded. `questions` holds the full bank (10); `payload.answers` lists the
    # 5 submitted, so we grade exactly those.
    total = len(payload.answers)
    correct = 0
    weak_points: List[int] = []
    results: List[QuizResultItem] = []
    selected_by_q = {a.question_id: a.selected_index for a in payload.answers}

    for q in questions:
        selected = selected_by_q.get(q.id)
        if selected is None:
            # This question was not part of the presented 5; skip it.
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

    score = round(correct / total * 100)
    this_passed = score >= MASTERY_THRESHOLD

    # Sticky mastery: never downgrade an already-mastered lesson in Phase 4.
    existing = db.scalars(
        select(LessonMastery).where(LessonMastery.lesson_id == lesson_id)
    ).first()
    if existing is not None and existing.status == "mastered":
        effective_status = "mastered"
    else:
        effective_status = "mastered" if this_passed else "needs_review"

    if existing is None:
        existing = LessonMastery(lesson_id=lesson_id)
        db.add(existing)

    existing.status = effective_status
    existing.score = score
    existing.correct_count = correct
    existing.total_count = total
    # SQLAlchemy applies the `default=0` only at INSERT time, so a freshly
    # created object has attempts=None until flush. Tolerate None to be safe.
    existing.attempts = (existing.attempts or 0) + 1
    existing.last_quiz_at = datetime.utcnow()
    existing.weak_points = json.dumps(weak_points, ensure_ascii=False)
    db.commit()
    db.refresh(existing)

    # Unlock next lesson (derived from mastered predecessor).
    ordered = ordered_lessons(db)
    idx = next((i for i, l in enumerate(ordered) if l.id == lesson_id), None)
    next_lesson = ordered[idx + 1] if (idx is not None and idx + 1 < len(ordered)) else None
    unlocked_next = effective_status == "mastered" and next_lesson is not None

    return QuizResultOut(
        lesson_id=lesson_id,
        total=total,
        correct=correct,
        score=score,
        passed=this_passed,
        status=effective_status,
        results=results,
        unlocked_next=unlocked_next,
        next_lesson_id=next_lesson.id if next_lesson is not None else None,
    )
