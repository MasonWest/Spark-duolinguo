import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import type { Level } from "../types";
import { statusIcon, statusLabel } from "../types";
import "./MapPage.css";

export default function MapPage() {
  const [levels, setLevels] = useState<Level[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/levels")
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json() as Promise<Level[]>;
      })
      .then(setLevels)
      .catch((e) => setError(String(e)));
  }, []);

  return (
    <div className="container">
      <header className="map-header">
        <h1>🗺️ 课程地图</h1>
        <Link to="/" className="back-link">
          ← 返回首页
        </Link>
      </header>
      <p className="subtitle">Spark 学习路线：从环境搭建到 RDD 基础</p>

      <div className="legend">
        <span>🔵 可学习</span>
        <span>🟢 已掌握</span>
        <span>🟡 需复习</span>
        <span>🔒 未解锁</span>
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

      {levels !== null && levels.length === 0 && (
        <div className="card">
          <span className="status">数据库中暂无课程数据</span>
        </div>
      )}

      {levels !== null &&
        levels.map((level) => (
          <section key={level.id} className="level-card">
            <div className="level-head">
              <h2>{level.title}</h2>
              <span className="lesson-count">
                {level.lessons.length} 个知识点
              </span>
            </div>
            <p className="level-desc">{level.description}</p>
            <ol className="lesson-list">
              {level.lessons.map((lesson) => (
                <li
                  key={lesson.id}
                  className={`lesson-item ${lesson.status}`}
                  title={statusLabel[lesson.status]}
                >
                  <Link to={`/lesson/${lesson.id}`} className="lesson-link">
                    <span className="lesson-icon">{statusIcon[lesson.status]}</span>
                    <span className="lesson-order">{lesson.order_index + 1}</span>
                    <span className="lesson-title">{lesson.title}</span>
                    <span className="lesson-mins">
                      {lesson.estimated_minutes} 分钟
                    </span>
                  </Link>
                </li>
              ))}
            </ol>
          </section>
        ))}

      <p className="phase">Phase 4 · 课程地图</p>
    </div>
  );
}
