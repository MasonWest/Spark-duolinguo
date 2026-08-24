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
    # Display status is computed per request (placeholder logic until Phase 5):
    # locked / available / passed
    status: str

    class Config:
        from_attributes = True


class LevelOut(BaseModel):
    id: int
    title: str
    description: str
    order_index: int
    status: str
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


class TodayLessonOut(BaseModel):
    id: int
    title: str
    slug: str
    description: str
    estimated_minutes: int
    level_id: int
    level_title: str


class DashboardOut(BaseModel):
    progress: ProgressOut
    current_level: Optional[CurrentLevelOut] = None
    today_lesson: Optional[TodayLessonOut] = None
    streak_days: int = 0  # Phase 6


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


class NextLessonOut(BaseModel):
    id: int
    title: str


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
    content: LessonContentOut
    next_lesson: Optional[NextLessonOut] = None
