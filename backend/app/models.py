"""ORM models for Spark Quest.

Phase 1 introduces the course data model:
    course_levels (1) -- (N) lessons

Later phases will add quizzes / user_progress / review_items /
parking_lot / study_sessions.
"""

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
