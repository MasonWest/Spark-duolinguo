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
          <div className="current-level">{data.current_level.title}</div>
        </div>
      )}

      {/* 今日任务 */}
      <div className="card today-card">
        <h2>🎯 今日任务</h2>
        {data?.today_lesson ? (
          <>
            <div className="today-title">{data.today_lesson.title}</div>
            <div className="today-meta">
              <span>{data.today_lesson.level_title}</span>
              <span>·</span>
              <span>约 {data.today_lesson.estimated_minutes} 分钟</span>
            </div>
            <p className="today-desc">{data.today_lesson.description}</p>
            <Link to={`/lesson/${data.today_lesson.id}`} className="btn-primary">
              开始学习 →
            </Link>
            <p className="today-hint">学习页面 · Phase 3 已上线</p>
          </>
        ) : (
          <span className="status">暂无可推荐的任务</span>
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
