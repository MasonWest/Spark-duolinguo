// API 数据类型（与后端 schemas.py 对应）

export type LessonStatus = "locked" | "available" | "passed";

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
}

export interface Level {
  id: number;
  title: string;
  description: string;
  order_index: number;
  status: string;
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
}

export interface TodayLesson {
  id: number;
  title: string;
  slug: string;
  description: string;
  estimated_minutes: number;
  level_id: number;
  level_title: string;
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
  passed: "🟢",
};

export const statusLabel: Record<LessonStatus, string> = {
  locked: "未解锁",
  available: "可学习",
  passed: "已通过",
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
}

export interface NextLesson {
  id: number;
  title: string;
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
  content: LessonContent;
  next_lesson: NextLesson | null;
}
