"""Pydantic response schemas for the API."""

from typing import List, Optional

from pydantic import BaseModel


class LessonOut(BaseModel):
    id: int
    level_id: int
    title: str
    slug: str
    description: str
    objective: str
    estimated_minutes: int
    order_index: int
    # Derived display status (Phase 4): locked / available / mastered / needs_review
    status: str
    # Most recent quiz score (0-100) for this lesson, or None if never attempted
    mastery_score: Optional[int] = None
    # Phase 6b: review date has arrived (mastered + next_review_at <= now).
    # Not a new learning status -- only a visual hint for the map.
    due_for_review: bool = False

    class Config:
        from_attributes = True


class LevelOut(BaseModel):
    id: int
    title: str
    description: str
    order_index: int
    status: str
    completed_count: int = 0
    total_count: int = 0
    percentage: int = 0
    lessons: List[LessonOut] = []

    class Config:
        from_attributes = True


# ---- Phase 2: Dashboard ----


class ProgressOut(BaseModel):
    completed: int
    total: int
    percentage: int


class CurrentLevelOut(BaseModel):
    id: int
    title: str
    completed_count: int = 0
    total_count: int = 0
    percentage: int = 0


class TodayLessonOut(BaseModel):
    id: int
    title: str
    slug: str
    description: str
    estimated_minutes: int
    level_id: int
    level_title: str
    status: str = "available"  # available / needs_review


# ---- Phase 6b: 间隔复习（Lesson 级调度，不是新的学习状态） ----


class ReviewDueItem(BaseModel):
    """One lesson whose scheduled review date has arrived."""

    lesson_id: int
    title: str
    level_title: str
    # ISO timestamp of the scheduled review date (in the past => overdue).
    next_review_at: Optional[str] = None
    # Whole days the review is overdue (0 => due today).
    overdue_days: int = 0


class DashboardOut(BaseModel):
    progress: ProgressOut
    current_level: Optional[CurrentLevelOut] = None
    today_lesson: Optional[TodayLessonOut] = None
    streak_days: int = 0  # Phase 6
    # Phase 6b: lessons whose scheduled review date has arrived.
    reviews_due: List["ReviewDueItem"] = []


# ---- Phase 4: Quiz + Lesson Mastery ----


class QuizQuestionOut(BaseModel):
    """A quiz question as exposed to the learning page (no answer leaked)."""

    id: int
    type: str
    prompt: str
    options: List[str]
    dimension: Optional[str] = None  # Phase 6.1 cognitive-dimension tag


class QuizFetchOut(BaseModel):
    lesson_id: int
    lesson_title: str
    questions: List[QuizQuestionOut] = []


class QuizAnswerIn(BaseModel):
    question_id: int
    selected_index: int


class QuizSubmitIn(BaseModel):
    answers: List[QuizAnswerIn] = []


class QuizResultItem(BaseModel):
    question_id: int
    selected_index: int
    correct_index: int
    is_correct: bool
    explanation: str = ""


class QuizResultOut(BaseModel):
    lesson_id: int
    total: int
    correct: int
    score: int
    # Whether THIS submission reached >= 80% (independent of sticky status)
    passed: bool
    # Effective mastery status after this submission (sticky: never downgraded)
    status: str
    results: List[QuizResultItem] = []
    unlocked_next: bool
    next_lesson_id: Optional[int] = None


# ---- Phase 3: Lesson detail / learning page ----


class ExampleOut(BaseModel):
    title: str = ""
    code: str = ""
    note: str = ""


class CommonMistakeOut(BaseModel):
    mistake: str = ""
    why: str = ""
    fix: str = ""


class LessonContentOut(BaseModel):
    explanation: str = ""
    examples: List[ExampleOut] = []
    key_points: List[str] = []
    common_mistakes: List[CommonMistakeOut] = []
    # 连接块（课程内容重构实验新增；均为可选，老课程数据为空字符串）
    review: str = ""   # 上一课回顾
    problem: str = ""  # 本课要解决的问题
    preview: str = ""  # 下一课伏笔


class NextLessonOut(BaseModel):
    id: int
    title: str


# ---- Phase 5.x: 学习笔记 ----


class LessonNoteOut(BaseModel):
    id: int
    lesson_id: int
    content: str
    created_at: str


class NoteCreate(BaseModel):
    content: str


class LessonDetailOut(BaseModel):
    id: int
    level_id: int
    level_title: str
    title: str
    slug: str
    description: str
    objective: str
    estimated_minutes: int
    status: str
    mastery_score: Optional[int] = None
    content: LessonContentOut
    next_lesson: Optional[NextLessonOut] = None


# ---- Phase 6b: 复习接口 schema（放在 QuizResultItem 之后以便复用） ----


class ReviewFetchOut(BaseModel):
    """A review round: 5 questions drawn from the lesson bank (no answers)."""

    lesson_id: int
    lesson_title: str
    questions: List[QuizQuestionOut] = []


class ReviewSubmitIn(BaseModel):
    answers: List[QuizAnswerIn] = []


class ReviewResultOut(BaseModel):
    lesson_id: int
    total: int
    correct: int
    # 5/5 required -- 4/5 does NOT count as a pass.
    passed: bool
    # Learning status after this review. Phase 6b never changes it: a review
    # only runs on mastered lessons, and failing one never demotes them.
    status: str
    # Scheduling state after this submission.
    srs_stage: int
    review_count: int
    next_review_at: Optional[str] = None
    next_interval_days: int = 0
    results: List[QuizResultItem] = []
