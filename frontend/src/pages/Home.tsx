import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import type { Dashboard } from "../types";
import { ProgressRing, Badge, Icon } from "../components/ui";
import "./Home.css";

export default function Home() {
  const [data, setData] = useState<Dashboard | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/dashboard")
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json() as Promise<Dashboard>;
      })
      .then(setData)
      .catch((e) => setError(String(e)));
  }, []);

  const p = data?.progress;
  const cl = data?.current_level;
  const tl = data?.today_lesson;
  const reviews = data?.reviews_due ?? [];

  if (error) {
    return (
      <div className="dashboard-page">
        <div className="card" style={{ textAlign: "center", padding: "48px 24px" }}>
          <h2>加载失败</h2>
          <p className="status error">{error}</p>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="dashboard-page">
        <div className="card" style={{ textAlign: "center", padding: "48px 24px" }}>
          <span className="status">加载中…</span>
        </div>
      </div>
    );
  }

  const currentLevelTitle = cl?.title ?? "—";
  const currentLessonNum = tl ? (cl?.completed_count ?? 0) + 1 : (cl?.completed_count ?? 0);
  const totalLessonsInLevel = cl?.total_count ?? 0;

  const todayStatus = tl?.status === "needs_review" ? "warning" : "primary";
  const todayStatusLabel = tl?.status === "needs_review" ? "需复习" : "可学习";
  const ctaText = tl?.status === "needs_review" ? "继续挑战 (复习测验)" : "开始学习";
  const hintText = tl?.status === "needs_review"
    ? "建议先温习课程内容，再次尝试测验"
    : "点击开始今天的 Spark 探索之旅";

  return (
    <div className="dashboard-page">
      {/* Hero: 当前学习定位 */}
      <header className="hero-bar">
        <div className="hero-location">
          <Icon name="location" size={16} aria-hidden={true} />
          <span className="hero-level">{currentLevelTitle}</span>
          <span className="hero-lesson">Lesson {currentLessonNum} / {totalLessonsInLevel}</span>
        </div>
        <ProgressRing
          percentage={p!.percentage}
          size={56}
          showLabel
          className="hero-ring"
          aria-label={`总进度 ${p!.percentage}%`}
        />
      </header>

      {/* Primary Action: 今日任务 - 最强视觉焦点 */}
      <main className="primary-action">
        {tl ? (
          <div className="primary-card focus-ring">
            <div className="primary-header">
              <Badge variant={todayStatus} size="sm">{todayStatusLabel}</Badge>
              <h1 className="primary-title">{tl.title}</h1>
            </div>
            <div className="primary-meta">
              <span><Icon name="lesson" size={14} aria-hidden={true} /> {tl.level_title}</span>
              <span><Icon name="clock" size={14} aria-hidden={true} /> 约 {tl.estimated_minutes} 分钟</span>
            </div>
            <p className="primary-desc">{tl.description}</p>
            <Link to={`/lesson/${tl.id}`} className="btn-primary btn-block">
              <span>{ctaText}</span>
              <Icon name="chevron" size={18} aria-hidden={true} />
            </Link>
            <p className="primary-hint">{hintText}</p>
          </div>
        ) : (
          <div className="primary-card all-completed">
            <Icon name="check" size={48} aria-hidden={true} />
            <p>太棒了！你已经完成了目前所有的课程！</p>
            <Link to="/map" className="btn-ghost">去课程地图回顾</Link>
          </div>
        )}
      </main>

      {/* Secondary: 可折叠，默认收起 */}
      <section className="secondary-zone">
        <button
          className="secondary-toggle"
          aria-expanded="false"
          aria-controls="secondary-content"
          onClick={(e) => {
            const btn = e.currentTarget;
            const content = document.getElementById("secondary-content");
            const expanded = btn.getAttribute("aria-expanded") === "true";
            btn.setAttribute("aria-expanded", String(!expanded));
            if (content) content.hidden = expanded;
          }}
        >
          <span>更多</span>
          <Icon name="chevron" size={16} className="toggle-icon" aria-hidden={true} />
        </button>
        <div id="secondary-content" className="secondary-content" hidden>
          {/* 今日复习 - 仅有数据时渲染 */}
          {reviews.length > 0 && (
            <div className="secondary-section review-section">
              <h2 className="section-title">
                <Icon name="review" size={16} aria-hidden={true} /> 今日复习
                <Badge variant="review" size="sm">{reviews.length}</Badge>
              </h2>
              <ul className="review-list">
                {reviews.map((r) => (
                  <li key={r.lesson_id} className="review-item">
                    <Link to={`/review/${r.lesson_id}`} className="review-link">
                      <span className="review-title">{r.title}</span>
                      <span className="review-meta">
                        {r.level_title} · {r.overdue_days > 0 ? `逾期 ${r.overdue_days} 天` : "今天到期"}
                      </span>
                    </Link>
                    <Link to={`/review/${r.lesson_id}`} className="btn-ghost btn-sm">去复习</Link>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* 进度摘要 */}
          <div className="secondary-section progress-section">
            <h2 className="section-title"><Icon name="progress" size={16} aria-hidden={true} /> 进度摘要</h2>
            <dl className="progress-summary">
              <div className="progress-row">
                <dt>总进度</dt>
                <dd><strong>{p!.completed} / {p!.total}</strong> · {p!.percentage}%</dd>
              </div>
              <div className="progress-row">
                <dt>当前 Level</dt>
                <dd><strong>{cl!.completed_count} / {cl!.total_count}</strong> · {cl!.percentage}%</dd>
              </div>
            </dl>
          </div>

          {/* 课程地图入口 */}
          <div className="secondary-section map-section">
            <Link to="/map" className="map-link">
              <Icon name="map" size={18} aria-hidden={true} />
              <span>查看完整学习路线</span>
              <Icon name="chevron" size={16} aria-hidden={true} />
            </Link>
          </div>
        </div>
      </section>

      {/* Footer: Map 入口二次保障 */}
      <footer className="footer-nav">
        <Link to="/map" className="footer-map-link">
          <Icon name="map" size={16} aria-hidden={true} /> 查看完整学习路线 →
        </Link>
      </footer>
    </div>
  );
}