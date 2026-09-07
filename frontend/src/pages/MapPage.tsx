import { Fragment, useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import type { Level, Lesson } from "../types";
import { statusLabel } from "../types";
import JourneyRegion from "../components/map/JourneyRegion";
import MapBackdrop from "../components/map/MapBackdrop";
import RegionNav from "../components/map/RegionNav";
import "../components/map/map.css";

const VIEW_KEY = "sq_map_view";
type ViewMode = "map" | "list";

export default function MapPage() {
  const [levels, setLevels] = useState<Level[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<Set<number>>(new Set());
  const [view, setView] = useState<ViewMode>(
    () => (localStorage.getItem(VIEW_KEY) as ViewMode) || "map"
  );
  const [width, setWidth] = useState(() => Math.min(672, window.innerWidth - 48));
  const bodyRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetch("/api/levels")
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json() as Promise<Level[]>;
      })
      .then(setLevels)
      .catch((e) => setError(String(e)));
  }, []);

  // 默认展开：当前区 + 下一区（其余折叠，控制信息密度）
  useEffect(() => {
    if (!levels || levels.length === 0) return;
    const idx = levels.findIndex((l) => l.status !== "completed");
    const base = idx === -1 ? levels.length - 1 : idx;
    setExpanded(
      new Set([levels[base]?.id, levels[base + 1]?.id].filter((x): x is number => !!x))
    );
  }, [levels]);

  // 容器宽度：布局算法依赖它，窄屏自动收窄摆动幅度
  useEffect(() => {
    const el = bodyRef.current;
    if (!el || typeof ResizeObserver === "undefined") return;
    const ro = new ResizeObserver((entries) => {
      const w = entries[0].contentRect.width;
      if (w > 0) setWidth(w);
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, [view]);

  // 首次进入自动定位到焦点节点（用户不用自己找「我学到哪了」）
  useEffect(() => {
    if (!levels || view !== "map") return;
    const t = setTimeout(() => {
      document
        .querySelector(".lesson-node.is-current")
        ?.scrollIntoView({ block: "center", behavior: "smooth" });
    }, 160);
    return () => clearTimeout(t);
  }, [levels, view, expanded]);

  // 全图焦点：只有「available」才是真正的"我下一步该学"。
  // needs_review 是次级焦点（需要回头复习），不抢走蓝色大圆与光环。
  // 线性解锁决定了 available 在全 app 恒定只有 1 个。
  const currentLessonId = useMemo<number | null>(() => {
    if (!levels) return null;
    for (const l of levels) {
      const found = l.lessons.find((x) => x.status === "available");
      if (found) return found.id;
    }
    return null;
  }, [levels]);

  const totals = useMemo(() => {
    if (!levels) return { lessons: 0, done: 0 };
    const lessons = levels.reduce((n, l) => n + l.total_count, 0);
    const done = levels.reduce((n, l) => n + l.completed_count, 0);
    return { lessons, done };
  }, [levels]);

  function toggle(id: number) {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function jump(id: number) {
    setExpanded((prev) => new Set(prev).add(id));
    requestAnimationFrame(() => {
      document
        .getElementById(`region-${id}`)
        ?.scrollIntoView({ block: "start", behavior: "smooth" });
    });
  }

  function switchView(v: ViewMode) {
    setView(v);
    try {
      localStorage.setItem(VIEW_KEY, v);
    } catch {
      /* 隐私模式下 localStorage 不可用，忽略即可 */
    }
  }

  return (
    <>
      <MapBackdrop />
      <div className="container map-shell">
        <header className="map-header">
          <h1>🗺️ 课程地图</h1>
          <Link to="/" className="map-back-link">
            ← 返回首页
          </Link>
        </header>

        <p className="subtitle">
          {levels
            ? `${levels.length} 个区域 · ${totals.lessons} 课 · 已完成 ${totals.done} 课`
            : "Spark 学习路线"}
        </p>

        <div className="view-switch" role="group" aria-label="视图切换">
          <button
            type="button"
            className={view === "map" ? "is-active" : ""}
            onClick={() => switchView("map")}
            aria-pressed={view === "map"}
          >
            地图
          </button>
          <button
            type="button"
            className={view === "list" ? "is-active" : ""}
            onClick={() => switchView("list")}
            aria-pressed={view === "list"}
          >
            列表
          </button>
        </div>

        {error && (
          <div className="card">
            <span className="status error">加载失败：{error}</span>
          </div>
        )}

        {!error && levels === null && (
          <div className="card">
            <span className="status">加载课程数据中…</span>
          </div>
        )}

        {!error && levels !== null && levels.length === 0 && (
          <div className="card">
            <span className="status">数据库中暂无课程数据</span>
          </div>
        )}

        {levels !== null && levels.length > 0 && view === "map" && (
          <>
            <RegionNav levels={levels} onJump={jump} />
            <div ref={bodyRef}>
              {levels.map((l, i) => (
                <Fragment key={l.id}>
                  {i > 0 && (
                    <div
                      className={`region-link ${
                        levels[i - 1].status === "completed" ? "is-open" : "is-sealed"
                      }`}
                      aria-hidden="true"
                    >
                      <span />
                    </div>
                  )}
                  <JourneyRegion
                    level={l}
                    expanded={expanded.has(l.id)}
                    onToggle={toggle}
                    width={width}
                    currentLessonId={currentLessonId}
                  />
                </Fragment>
              ))}
            </div>
          </>
        )}

        {levels !== null && levels.length > 0 && view === "list" && (
          <ListView levels={levels} />
        )}
      </div>
    </>
  );
}

/** 列表视图：无障碍兜底。同一份数据，另一种呈现。 */
function ListView({ levels }: { levels: Level[] }) {
  return (
    <div className="map-list">
      {levels.map((l) => (
        <section key={l.id} className="map-list-level">
          <h2>{l.title}</h2>
          <p className="map-list-meta">
            {l.completed_count} / {l.total_count} 已掌握
          </p>
          <ol>
            {sorted(l.lessons).map((lesson) => (
              <li key={lesson.id} className={`is-${lesson.status}`}>
                {lesson.status === "locked" ? (
                  lesson.title
                ) : (
                  <Link to={`/lesson/${lesson.id}`}>{lesson.title}</Link>
                )}
                <span className={`chip chip-${lesson.status}`}>
                  {statusLabel[lesson.status]}
                </span>
                {lesson.due_for_review && (
                  <span className="chip chip-needs_review">待复习</span>
                )}
              </li>
            ))}
          </ol>
        </section>
      ))}
    </div>
  );
}

function sorted(lessons: Lesson[]): Lesson[] {
  return [...lessons].sort((a, b) => a.order_index - b.order_index);
}
