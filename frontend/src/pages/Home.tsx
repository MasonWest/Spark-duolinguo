import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import type { Dashboard } from "../types";
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

  const connected = data !== null;
  const p = data?.progress;

  return (
    <div className="container">
      <h1>🔥 Spark Quest</h1>
      <p className="subtitle">今天系统让你学什么？</p>

      {/* 总进度 */}
      <div className="card">
        <h2>📊 总进度</h2>
        {error ? (
          <span className="status error">加载失败：{error}</span>
        ) : !data ? (
          <span className="status">加载中…</span>
        ) : (
          <>
            <div className="progress-bar">
              <div
                className="progress-fill"
                style={{ width: `${p!.percentage}%` }}
              />
            </div>
            <div className="progress-text">
              已完成 {p!.completed} / {p!.total} · {p!.percentage}%
            </div>
          </>
        )}
      </div>

      {/* 当前 Level */}
      {data?.current_level && (
        <div className="card">
          <h2>📍 当前阶段</h2>
          <div className="current-level-header">
            <span className="current-level-title">{data.current_level.title}</span>
            <span className="current-level-count">
              {data.current_level.completed_count} / {data.current_level.total_count}
            </span>
          </div>
          <div className="progress-bar level-progress">
            <div
              className="progress-fill level-fill"
              style={{ width: `${data.current_level.percentage}%` }}
            />
          </div>
        </div>
      )}

      {/* 今日任务 */}
      <div className="card today-card">
        <h2>🎯 今日任务</h2>
        {data?.today_lesson ? (
          <>
            <div className="today-title">
              {data.today_lesson.status === "needs_review" && (
                <span className="status-badge review">需复习</span>
              )}
              {data.today_lesson.title}
            </div>
            <div className="today-meta">
              <span>{data.today_lesson.level_title}</span>
              <span>·</span>
              <span>约 {data.today_lesson.estimated_minutes} 分钟</span>
            </div>
            <p className="today-desc">{data.today_lesson.description}</p>
            <Link to={`/lesson/${data.today_lesson.id}`} className="btn-primary">
              {data.today_lesson.status === "needs_review" ? "继续挑战 (复习测验) →" : "开始学习 →"}
            </Link>
            <p className="today-hint">
              {data.today_lesson.status === "needs_review" 
                ? "建议先温习课程内容，再次尝试测验" 
                : "点击开始今天的 Spark 探索之旅"}
            </p>
          </>
        ) : (
          <div className="all-completed">
            <span className="trophy">🏆</span>
            <p>太棒了！你已经完成了目前所有的课程！</p>
            <Link to="/map" className="btn-secondary">去课程地图回顾 →</Link>
          </div>
        )}
      </div>

      {/* 课程地图入口 */}
      <div className="card">
        <h2>🗺️ 课程地图</h2>
        <Link to="/map" className="map-link">
          查看完整学习路线 →
        </Link>
      </div>

      <p className="phase">
        Phase 2 · Dashboard{connected ? "" : " · 连接中"}
      </p>
    </div>
  );
}
