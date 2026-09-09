"""ORM models for Spark Quest.

Phase 1 introduces the course data model:
    course_levels (1) -- (N) lessons

Later phases will add quizzes / user_progress / review_items /
parking_lot / study_sessions.
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import ForeignKey, Index, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base

# Single-user local app: there is no auth and no user table (Phase 9.1).
# `study_days.user_id` exists so the schema does not have to change shape when
# a real user system arrives; every row written today uses this sentinel.
DEFAULT_USER_ID = "local"


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
    # Phase 6.1: cognitive dimension tag (open vocabulary, e.g.
    # concept / why / mechanism / apply / comparison / debug). NULL allowed
    # for legacy rows; backfilled by migrate/backfill scripts.
    dimension: Mapped[Optional[str]] = mapped_column(nullable=True)


class LessonMastery(Base):
    """Minimal per-lesson progress / mastery record (one row per lesson).

    `status` is the *current* mastery state: "mastered" or "needs_review".
    Once a lesson first reaches >= 80% it becomes "mastered" and stays
    "mastered" for Phase 4 (re-quizzes below 80% do NOT downgrade it).

    `weak_points` is a JSON list of question_ids answered wrong in the
    *most recent* quiz submission -- NOT a long-term weak-point model.
    A normalized attempt-history table is deferred to Phase 6 (Review).

    ---- Phase 6b: spaced-review scheduling ----

    Review is NOT a new learning status. It is scheduling information attached
    on top of an already-`mastered` lesson, so the Phase 4/5 status vocabulary
    (locked / available / needs_review / mastered) is unchanged.

    `srs_stage` is the authoritative scheduling state: it is the index into
    `services.REVIEW_INTERVALS_DAYS` = [1, 3, 7, 14, 30, 60, 120]. It can NOT
    be derived from `next_review_at` because a failed review also schedules
    +3 days, which collides with the "passed stage 0" interval.

    `review_count` is purely informational (how many reviews were passed).
    It must never be used to re-derive `srs_stage`.
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

    # --- Phase 6b: spaced-review schedule (nullable: lessons never mastered) ---
    # Anchor of the whole schedule. NOT the same as `last_quiz_at`: that one is
    # "most recent attempt", this one is "first time the lesson was mastered".
    first_mastered_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    # Index into REVIEW_INTERVALS_DAYS; authoritative scheduling state.
    srs_stage: Mapped[int] = mapped_column(default=0)
    # When the next review becomes due (NULL -> lesson not in the review cycle).
    next_review_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    # Last time a review was actually taken (pass or fail).
    last_review_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    # Number of *passed* reviews; informational only (see class docstring).
    review_count: Mapped[int] = mapped_column(default=0)


# ---- Phase 5.x: 学习笔记（单用户本地应用，无需 user_id） ----


class LessonNote(Base):
    """User learning notes attached to a lesson.

    Each save creates a new row (history is never overwritten). Single-user
    local app, so no user_id. Notes are the learner's own record — not a
    feedback or comment system.
    """

    __tablename__ = "lesson_notes"

    id: Mapped[int] = mapped_column(primary_key=True)
    lesson_id: Mapped[int] = mapped_column(
        ForeignKey("lessons.id", ondelete="CASCADE"), index=True
    )
    content: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)


# ---- Phase 9.1: 每日学习行为（Streak 的唯一数据源） ----


class StudyDay(Base):
    """One row per (user, local calendar day) on which real learning happened.

    Why a table and not a derivation from `lesson_mastery`:
        `lesson_mastery.last_quiz_at` is the *most recent* attempt per lesson.
        Study lesson 3 on Sept 1, re-attempt it on Sept 5, and Sept 1 vanishes
        from the record -- history would be corrupted retroactively and the
        streak would shrink the more you use the app. Day-grain activity must
        be recorded independently of per-lesson state.

    What counts as a valid study day (Phase 9.1):
        quiz submit      YES (pass or fail)
        review submit    YES (pass or fail)
        lesson reading   NO
        note writing     NO
        opening dashboard NO

    `study_date` is a LOCAL calendar date "YYYY-MM-DD" (see
    `services.LOCAL_UTC_OFFSET_HOURS`), not a UTC date -- otherwise the day
    boundary would land at 08:00 local time for a UTC+8 user.

    `first_at` / `last_at` keep the existing UTC convention used by every other
    timestamp in this database.
    """

    __tablename__ = "study_days"
    __table_args__ = (
        UniqueConstraint("user_id", "study_date", name="uq_study_days_user_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(default=DEFAULT_USER_ID, index=True)
    # Local calendar day, "YYYY-MM-DD".
    study_date: Mapped[str]
    # Total valid learning actions that day (quiz + review submissions).
    activity_count: Mapped[int] = mapped_column(default=0)
    lessons_done: Mapped[int] = mapped_column(default=0)
    reviews_done: Mapped[int] = mapped_column(default=0)
    first_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    last_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)


# ---- Phase 9.2: Badge 成就系统 ----
#
# Three tables, deliberately split by responsibility:
#   badge_definitions : the catalog (facts about each badge). Seeded once.
#   user_badges      : per-user unlocks. Insert-only; never updated except via
#                      new unlocks. UNIQUE(user_id, badge_id) enforces idempotency.
#   user_stats       : lifetime counters incremented in the same transaction as
#                      the originating quiz/review submit. These are FACTS about
#                      real events (a question was answered, a review passed),
#                      not learning state. They are the only way to count
#                      lifetime totals -- lesson_mastery only stores the most
#                      recent attempt per lesson.
#
# Badge ENGINE lives in `badge_service.py`. The DB never holds "badge earned
# recently" or "level N completed" -- both are derived from user_badges and
# the existing tables on every read.


class BadgeDefinition(Base):
    """Catalog row for one Badge.

    `code` is the stable program identifier (e.g. LEVEL_0, QUIZ_100). Names
    shown to users can change without touching code; codes must not.

    `is_secret` is the single boolean for "hidden until earned" semantics:
    not-unlocked secret badges expose nothing in the API (name / description /
    image all blanked), only `?`.

    `image` is a web URL path (e.g. "/badges/level0.webp") relative to the
    frontend `public/` directory. Vite serves these directly; we never
    inline binary assets in SQLite.
    """

    __tablename__ = "badge_definitions"
    __table_args__ = (UniqueConstraint("code", name="uq_badge_definitions_code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str]  # stable program id, e.g. "LEVEL_0", "QUIZ_100"
    name: Mapped[str]  # display name (Chinese)
    description: Mapped[str] = mapped_column(Text, default="")  # unlock condition
    tier: Mapped[str]  # "journey" | "special"
    image: Mapped[str]  # web path, e.g. "/badges/level0.webp"
    sort_order: Mapped[int] = mapped_column(default=0)
    is_secret: Mapped[bool] = mapped_column(default=False)


class UserBadge(Base):
    """One unlocked-badge record per (user, badge). Insert-only."""

    __tablename__ = "user_badges"
    __table_args__ = (UniqueConstraint("user_id", "badge_id", name="uq_user_badges_user_badge"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(default=DEFAULT_USER_ID, index=True)
    badge_id: Mapped[int] = mapped_column(ForeignKey("badge_definitions.id"))
    unlocked_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)


class UserStats(Base):
    """Lifetime event counters, one row per user.

    All increments happen in the SAME transaction as the originating quiz /
    review submit, so the counters can never drift from the actual events.

    Backfill source notes (see `migrate.backfill_badges`):
      - total_quiz_submitted   : SUM(lesson_mastery.attempts)   -- ACCURATE
      - total_reviews_passed   : SUM(lesson_mastery.review_count) -- ACCURATE
      - total_quiz_correct     : SUM(lesson_mastery.correct_count) -- LOWER BOUND
        (only retains the most recent attempt per lesson; lifetime total is
         >= this number)
      - total_reviews_submitted: no field exists; lower bound =
        SUM(lesson_mastery.review_count)
      - total_debug_correct    : no historical record; starts at 0
    """

    __tablename__ = "user_stats"

    user_id: Mapped[str] = mapped_column(primary_key=True)
    total_quiz_correct: Mapped[int] = mapped_column(default=0)
    total_quiz_submitted: Mapped[int] = mapped_column(default=0)
    total_reviews_passed: Mapped[int] = mapped_column(default=0)
    total_reviews_submitted: Mapped[int] = mapped_column(default=0)
    total_debug_correct: Mapped[int] = mapped_column(default=0)


# ---- Phase 10.1: 薄弱题 / Weak Questions —— 逐题作答事实层（append-only） ----
#
# 这是「事实层」，不是「状态层」。只记录：某时刻、某用户、对某题、选了什么、
# 对错与否。所有「薄弱度 / 错几次 / 是否修复 / 哪些进 Review」都是读取时从本表
# 派生，绝不在此存任何聚合或状态列。
#
# 为什么是 quiz_answer_log 而不是 wrong_questions：
#   一旦叫 wrong_questions，后续极易往里塞 status / mastery / wrong_count /
#   review_count / next_review_at / is_fixed，最终造出第二套 Mastery。本表刻意
#   只存事件，把一切派生交给查询（与项目「事实存库、状态派生」原则一致）。
#
# source 只是事件来源标签（'quiz' | 'review' | 'practice'），不是三套独立错题
# 体系——Quiz/Review/Practice 对同一题的历史记录统一聚合。


class QuizAnswerLog(Base):
    """One append-only fact row per (user, question, attempt).

    Only facts, never state:
        at <submitted_at>, <user_id> answered <question_id> with
        <selected_index>, and the result was is_correct (against the
        <correct_index> snapshot taken at submit time).

    `correct_index` is an EVENT SNAPSHOT, not derived state: if the question's
    true answer is later revised in the seed, this row still records what the
    system judged at the time. That is exactly what an event log should do.

    `source` is a label only. Practice rows are written by a standalone commit
    that touches NOTHING else (no mastery / SRS / streak / badge / stats) — a
    re-practice is just one more fact.
    """

    __tablename__ = "quiz_answer_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Sentinel column, same as study_days / user_badges. Not a state field.
    user_id: Mapped[str] = mapped_column(default=DEFAULT_USER_ID)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id"))
    question_id: Mapped[int] = mapped_column(ForeignKey("quizzes.id"))
    # 'quiz' | 'review' | 'practice' — label only, not state.
    source: Mapped[str] = mapped_column(default="quiz")
    selected_index: Mapped[int]  # what the user actually picked
    # EVENT SNAPSHOT: the correct option index at submit time.
    correct_index: Mapped[int]
    is_correct: Mapped[int] = mapped_column(default=0)  # 0/1
    submitted_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    # The fact table's dominant access path is: one user -> one question ->
    # all historical attempts -> ordered by time. This composite index also
    # covers the (user_id) and (user_id, question_id) prefixes, replacing three
    # single-column indexes. A standalone lesson_id index is not worth it.
    __table_args__ = (
        Index(
            "ix_quiz_answer_log_user_question_time",
            "user_id",
            "question_id",
            "submitted_at",
        ),
    )
