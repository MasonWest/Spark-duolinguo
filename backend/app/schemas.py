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


class DashboardOut(BaseModel):
    progress: ProgressOut
    current_level: Optional[CurrentLevelOut] = None
    today_lesson: Optional[TodayLessonOut] = None
    streak_days: int = 0  # Phase 6


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
