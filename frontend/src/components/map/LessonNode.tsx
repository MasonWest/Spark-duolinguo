import { Link } from "react-router-dom";
import type { Lesson, LessonStatus } from "../../types";
import { statusLabel } from "../../types";

interface Props {
  lesson: Lesson;
  /** 课序（0-based），用于显示「第 N 课」 */
  index: number;
  x: number;
  y: number;
  /** 全图唯一的焦点节点（第一个 available / needs_review） */
  isCurrent: boolean;
}

function Glyph({ status }: { status: LessonStatus }) {
  if (status === "mastered") {
    return (
      <svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true">
        <path
          d="M5 12.5l4.5 4.5L19 7"
          fill="none"
          stroke="currentColor"
          strokeWidth="3"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    );
  }
  if (status === "needs_review") {
    return (
      <svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true">
        <path d="M12 5v9" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
        <circle cx="12" cy="19" r="1.9" fill="currentColor" />
      </svg>
    );
  }
  if (status === "locked") {
    return (
      <svg viewBox="0 0 24 24" width="19" height="19" aria-hidden="true">
        <rect x="5" y="11" width="14" height="9" rx="2.5" fill="currentColor" />
        <path
          d="M8.5 11V8a3.5 3.5 0 017 0v3"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
        />
      </svg>
    );
  }
  // available —— 播放三角是最直接的行动号召
  return (
    <svg viewBox="0 0 24 24" width="24" height="24" aria-hidden="true">
      <path d="M8 5l12 7-12 7z" fill="currentColor" />
    </svg>
  );
}

export default function LessonNode({ lesson, index, x, y, isCurrent }: Props) {
  const s = lesson.status;
  const locked = s === "locked";
  const due = Boolean(lesson.due_for_review);

  const cls = [
    "lesson-node",
    `is-${s}`,
    isCurrent ? "is-current" : "",
    due ? "is-due" : "",
  ]
    .filter(Boolean)
    .join(" ");

  const style = { left: x, top: y };
  const aria = `第 ${index + 1} 课：${lesson.title}（${statusLabel[s]}）`;

  const body = (
    <>
      <span className="node-orb">
        <Glyph status={s} />
      </span>
      <span className="node-title">
        {index + 1}. {lesson.title}
      </span>
    </>
  );

  if (locked) {
    return (
      <div className={cls} style={style} aria-disabled="true" title={aria}>
        {body}
      </div>
    );
  }

  return (
    <Link
      className={cls}
      style={style}
      to={`/lesson/${lesson.id}`}
      aria-label={aria}
      title={aria}
    >
      {body}
    </Link>
  );
}
