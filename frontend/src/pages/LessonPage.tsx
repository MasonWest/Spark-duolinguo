import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import type { LessonDetail } from "../types";
import { statusLabel } from "../types";
import "./LessonPage.css";

export default function LessonPage() {
  const { id } = useParams<{ id: string }>();
  const [data, setData] = useState<LessonDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notFound, setNotFound] = useState(false);

  useEffect(() => {
    setData(null);
    setError(null);
    setNotFound(false);
    fetch(`/api/lessons/${id}`)
      .then((res) => {
        if (res.status === 404) {
          setNotFound(true);
          throw new Error("课程不存在");
        }
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json() as Promise<LessonDetail>;
      })
      .then(setData)
      .catch((e) => {
        if (!notFound) setError(String(e));
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  if (notFound) {
    return (
      <div className="container">
        <div className="card">
          <h2>😕 找不到这节课</h2>
          <p className="status">课程不存在（id = {id}）。</p>
        </div>
        <Link to="/map" className="btn-primary">
          ← 返回课程地图
        </Link>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container">
        <div className="card">
          <span className="status error">加载失败：{error}</span>
        </div>
        <Link to="/map" className="btn-primary">
          ← 返回课程地图
        </Link>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="container">
        <div className="card">
          <span className="status">加载课程内容中…</span>
        </div>
      </div>
    );
  }

  const c = data.content;

  return (
    <div className="container lesson-container">
      <header className="lesson-header">
        <Link to="/map" className="back-link">
          ← 返回课程地图
        </Link>
        <span className="lesson-level">{data.level_title}</span>
      </header>

      {/* 标题 + 元信息 */}
      <h1 className="lesson-title">{data.title}</h1>
      <div className="lesson-meta">
        <span className="meta-chip time">⏱️ 约 {data.estimated_minutes} 分钟</span>
        <span className="meta-chip status-chip">{statusLabel[data.status]}</span>
      </div>

      {/* 学习目标 */}
      <section className="card objective-card">
        <h2>🎯 学习目标</h2>
        <p className="objective-text">{data.objective}</p>
      </section>

      {/* 概念解释 */}
      <section className="card">
        <h2>📖 概念解释</h2>
        {c.explanation ? (
          c.explanation.split(/\n\n+/).map((para, i) => (
            <p key={i} className="para">
              {para}
            </p>
          ))
        ) : (
          <p className="para muted">（本课暂无解释内容）</p>
        )}
      </section>

      {/* 示例 */}
      <section className="card">
        <h2>💻 示例</h2>
        {c.examples.length === 0 && (
          <p className="para muted">（本课暂无示例）</p>
        )}
        {c.examples.map((ex, i) => (
          <div key={i} className="example">
            <div className="example-title">
              <span className="example-no">例 {i + 1}</span>
              {ex.title}
            </div>
            <pre className="code-block">
              <code>{ex.code}</code>
            </pre>
            {ex.note && <p className="example-note">💡 {ex.note}</p>}
          </div>
        ))}
      </section>

      {/* 必记知识 */}
      <section className="card key-points-card">
        <h2>🧠 必记知识</h2>
        {c.key_points.length === 0 ? (
          <p className="para muted">（本课暂无要点）</p>
        ) : (
          <ul className="key-points">
            {c.key_points.map((p, i) => (
              <li key={i}>{p}</li>
            ))}
          </ul>
        )}
      </section>

      {/* 常见错误 */}
      <section className="card mistakes-card">
        <h2>⚠️ 常见错误</h2>
        {c.common_mistakes.length === 0 ? (
          <p className="para muted">（本课暂无常见错误）</p>
        ) : (
          c.common_mistakes.map((m, i) => (
            <div key={i} className="mistake">
              <div className="mistake-title">❌ {m.mistake}</div>
              <div className="mistake-row">
                <span className="mistake-label">原因</span>
                <span>{m.why}</span>
              </div>
              <div className="mistake-row fix">
                <span className="mistake-label">纠正</span>
                <span>✅ {m.fix}</span>
              </div>
            </div>
          ))
        )}
      </section>

      {/* 下一步 */}
      <section className="card next-card">
        <h2>🚀 下一步</h2>
        {data.next_lesson ? (
          <Link to={`/lesson/${data.next_lesson.id}`} className="btn-primary">
            下一课：{data.next_lesson.title} →
          </Link>
        ) : (
          <p className="para">🎉 已是当前课程的最后一课！</p>
        )}
        <p className="next-hint">Quiz 将在 Phase 4 上线</p>
      </section>

      <p className="phase">Phase 3 · 学习页面</p>
    </div>
  );
}
