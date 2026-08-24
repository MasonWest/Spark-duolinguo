"""ORM models for Spark Quest.

Phase 1 introduces the course data model:
    course_levels (1) -- (N) lessons

Later phases will add quizzes / user_progress / review_items /
parking_lot / study_sessions.
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class CourseLevel(Base):
    __tablename__ = "course_levels"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str]
    description: Mapped[str] = mapped_column(Text, default="")
    order_index: Mapped[int]
    status: Mapped[str] = mapped_column(default="active")

    lessons: Mapped[List["Lesson"]] = relationship(
        back_populates="level",
        order_by="Lesson.order_index",
        cascade="all, delete-orphan",
    )


class Lesson(Base):
    __tablename__ = "lessons"

    id: Mapped[int] = mapped_column(primary_key=True)
    level_id: Mapped[int] = mapped_column(ForeignKey("course_levels.id"))
    title: Mapped[str]
    slug: Mapped[str] = mapped_column(unique=True)
    description: Mapped[str] = mapped_column(Text, default="")
    objective: Mapped[str] = mapped_column(Text, default="")
    estimated_minutes: Mapped[int] = mapped_column(default=15)
    order_index: Mapped[int]
    prerequisites: Mapped[str] = mapped_column(Text, default="")
    content: Mapped[str] = mapped_column(Text, default="")

    level: Mapped[Optional[CourseLevel]] = relationship(back_populates="lessons")


# ---- Phase 4: Quiz + 最小进度 (Lesson Mastery) ----


class QuizQuestion(Base):
    """A single quiz question belonging to a lesson.

    All three question types (single_choice / true_false / application) are
    graded uniformly: the submitted option index must equal `correct_index`.
    `options` is stored as a JSON-encoded list of strings (for true_false the
    list is ["正确", "错误"]); the "simple application" type is just a
    single-choice question whose options are code snippets / statements.
    """

    __tablename__ = "quizzes"

    id: Mapped[int] = mapped_column(primary_key=True)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id"))
    type: Mapped[str] = mapped_column(default="single_choice")
    prompt: Mapped[str] = mapped_column(Text, default="")
    options: Mapped[str] = mapped_column(Text, default="[]")  # JSON list[str]
    correct_index: Mapped[int] = mapped_column(default=0)
    explanation: Mapped[str] = mapped_column(Text, default="")
    order_index: Mapped[int] = mapped_column(default=0)


class LessonMastery(Base):
    """Minimal per-lesson progress / mastery record (one row per lesson).

    `status` is the *current* mastery state: "mastered" or "needs_review".
    Once a lesson first reaches >= 80% it becomes "mastered" and stays
    "mastered" for Phase 4 (re-quizzes below 80% do NOT downgrade it).

    `weak_points` is a JSON list of question_ids answered wrong in the
    *most recent* quiz submission -- NOT a long-term weak-point model.
    A normalized attempt-history table is deferred to Phase 6 (Review).
    """

    __tablename__ = "lesson_mastery"

    id: Mapped[int] = mapped_column(primary_key=True)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id"), unique=True)
    status: Mapped[str] = mapped_column(default="needs_review")
    score: Mapped[int] = mapped_column(default=0)
    correct_count: Mapped[int] = mapped_column(default=0)
    total_count: Mapped[int] = mapped_column(default=0)
    attempts: Mapped[int] = mapped_column(default=0)
    last_quiz_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    weak_points: Mapped[str] = mapped_column(Text, default="[]")  # JSON list[int]
