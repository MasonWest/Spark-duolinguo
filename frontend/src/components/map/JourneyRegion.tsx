import type { Level } from "../../types";
import LessonNode from "./LessonNode";
import LessonPath from "./LessonPath";
import {
  NARROW_WIDTH,
  layoutRegion,
  regionHeight,
  regionTone,
  type RegionTone,
} from "./mapLayout";

interface Props {
  level: Level;
  expanded: boolean;
  onToggle: (levelId: number) => void;
  /** 可用内容宽度（px） */
  width: number;
  /** 全图焦点课程 id，用于标记当前节点 */
  currentLessonId: number | null;
}

function ToneMark({ tone }: { tone: RegionTone }) {
  if (tone === "past") {
    // 已通关：插旗
    return (
      <svg className="tone-mark" viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
        <path d="M7 3v18" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
        <path d="M8 4h11l-2.5 4L19 12H8z" fill="currentColor" />
      </svg>
    );
  }
  if (tone === "future") {
    // 未解锁：锁
    return (
      <svg className="tone-mark" viewBox="0 0 24 24" width="17" height="17" aria-hidden="true">
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
  return null;
}

export default function JourneyRegion({
  level,
  expanded,
  onToggle,
  width,
  currentLessonId,
}: Props) {
  const tone = regionTone(level);
  const amp = width < NARROW_WIDTH ? 0.6 : 1;
  // 不依赖后端返回顺序，按 order_index 稳定排序
  const lessons = [...level.lessons].sort((a, b) => a.order_index - b.order_index);
  const nodes = layoutRegion(lessons.length, { width, amplitude: amp });
  const height = regionHeight(lessons.length);

  const badge =
    tone === "past"
      ? `已通关 · ${level.completed_count} / ${level.total_count}`
      : tone === "future"
        ? `未解锁 · ${level.total_count} 课`
        : `进行中 · ${level.completed_count} / ${level.total_count}`;

  return (
    <section
      id={`region-${level.id}`}
      className={`region region-${tone} ${expanded ? "is-open" : "is-closed"}`}
      aria-labelledby={`region-title-${level.id}`}
    >
      <header className="region-head">
        <div className="region-head-main">
          <h2 className="region-title" id={`region-title-${level.id}`}>
            {level.title}
          </h2>
          <span className="region-badge">
            <ToneMark tone={tone} />
            {badge}
          </span>
        </div>
        <button
          type="button"
          className="region-toggle"
          onClick={() => onToggle(level.id)}
          aria-expanded={expanded}
          aria-controls={`region-body-${level.id}`}
        >
          {expanded ? "收起" : "展开"}
        </button>
      </header>

      <div id={`region-body-${level.id}`} className="region-body-wrap">
        {expanded ? (
          <div className="region-body" style={{ height }}>
            <LessonPath
              nodes={nodes}
              lessons={lessons}
              width={width}
              height={height}
            />
            {lessons.map((l, i) => (
              <LessonNode
                key={l.id}
                lesson={l}
                index={i}
                x={nodes[i].x}
                y={nodes[i].y}
                isCurrent={l.id === currentLessonId}
              />
            ))}
          </div>
        ) : (
          <p className="region-summary">{level.description}</p>
        )}
      </div>
    </section>
  );
}
