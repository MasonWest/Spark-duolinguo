// API 数据类型（与后端 schemas.py 对应）

// Phase 4 status vocabulary (minimal subset; full state machine in Phase 5)
export type LessonStatus =
  | "locked"
  | "available"
  | "mastered"
  | "needs_review";

export interface Lesson {
  id: number;
  level_id: number;
  title: string;
  slug: string;
  description: string;
  objective: string;
  estimated_minutes: number;
  order_index: number;
  status: LessonStatus;
  mastery_score?: number | null;
}

export interface Level {
  id: number;
  title: string;
  description: string;
  order_index: number;
  status: string;
  completed_count: number;
  total_count: number;
  percentage: number;
  lessons: Lesson[];
}

export interface HealthInfo {
  app: string;
  status: string;
  database: string;
}

// ---- Phase 2: Dashboard ----

export interface Progress {
  completed: number;
  total: number;
  percentage: number;
}

export interface CurrentLevel {
  id: number;
  title: string;
  completed_count: number;
  total_count: number;
  percentage: number;
}

export interface TodayLesson {
  id: number;
  title: string;
  slug: string;
  description: string;
  estimated_minutes: number;
  level_id: number;
  level_title: string;
  status: "available" | "needs_review";
}

export interface Dashboard {
  progress: Progress;
  current_level: CurrentLevel | null;
  today_lesson: TodayLesson | null;
  streak_days: number;
}

export const statusIcon: Record<LessonStatus, string> = {
  locked: "🔒",
  available: "🔵",
  mastered: "🟢",
  needs_review: "🟡",
};

export const statusLabel: Record<LessonStatus, string> = {
  locked: "未解锁",
  available: "可学习",
  mastered: "已掌握",
  needs_review: "需复习",
};

// ---- Phase 3: Lesson detail / 学习页面 ----

export interface Example {
  title: string;
  code: string;
  note: string;
}

export interface CommonMistake {
  mistake: string;
  why: string;
  fix: string;
}

export interface LessonContent {
  explanation: string;
  examples: Example[];
  key_points: string[];
  common_mistakes: CommonMistake[];
  // 连接块（课程内容重构实验新增；老课程数据可能缺失）
  review?: string;
  problem?: string;
  preview?: string;
}

export interface NextLesson {
  id: number;
  title: string;
}

// ---- Phase 5.x: 学习笔记（单用户本地，无 user_id） ----

export interface LessonNote {
  id: number;
  lesson_id: number;
  content: string;
  created_at: string;
}

export interface LessonDetail {
  id: number;
  level_id: number;
  level_title: string;
  title: string;
  slug: string;
  description: string;
  objective: string;
  estimated_minutes: number;
  status: LessonStatus;
  mastery_score?: number | null;
  content: LessonContent;
  next_lesson: NextLesson | null;
}

// ---- Phase 4: Quiz + Lesson Mastery ----

export type QuizType = "single_choice" | "true_false" | "application";

export interface QuizQuestion {
  id: number;
  type: QuizType;
  prompt: string;
  options: string[];
  dimension?: string | null; // Phase 6.1 cognitive-dimension tag
}

export interface QuizFetch {
  lesson_id: number;
  lesson_title: string;
  questions: QuizQuestion[];
}

export interface QuizAnswer {
  question_id: number;
  selected_index: number;
}

export interface QuizSubmit {
  answers: QuizAnswer[];
}

export interface QuizResultItem {
  question_id: number;
  selected_index: number;
  correct_index: number;
  is_correct: boolean;
  explanation: string;
}

export interface QuizResult {
  lesson_id: number;
  total: number;
  correct: number;
  score: number;
  passed: boolean;
  status: string;
  results: QuizResultItem[];
  unlocked_next: boolean;
  next_lesson_id: number | null;
}
