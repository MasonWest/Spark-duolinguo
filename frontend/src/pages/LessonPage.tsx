import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import type { LessonDetail, LessonNote } from "../types";
import { statusLabel } from "../types";
import "./LessonPage.css";

export default function LessonPage() {
  const { id } = useParams<{ id: string }>();
  const [data, setData] = useState<LessonDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notFound, setNotFound] = useState(false);

  // 学习笔记（Phase 5.x）
  const [notes, setNotes] = useState<LessonNote[]>([]);
  const [noteDraft, setNoteDraft] = useState("");
  const [noteBusy, setNoteBusy] = useState(false);

  useEffect(() => {
    setData(null);
    setError(null);
    setNotFound(false);
    setNotes([]);
    setNoteDraft("");
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

  useEffect(() => {
    if (!id) return;
    fetch(`/api/lessons/${id}/notes`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json() as Promise<LessonNote[]>;
      })
      .then(setNotes)
      .catch(() => {
        /* 笔记加载失败时静默，不阻塞课程正文 */
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  function saveNote() {
    const content = noteDraft.trim();
    if (!content) return;
    setNoteBusy(true);
    fetch(`/api/lessons/${id}/notes`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content }),
    })
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json() as Promise<LessonNote>;
      })
      .then((note) => {
        setNotes((prev) => [note, ...prev]);
        setNoteDraft("");
      })
      .catch((e) => alert("保存笔记失败：" + e))
      .finally(() => setNoteBusy(false));
  }

  function deleteNote(noteId: number) {
    fetch(`/api/lessons/${id}/notes/${noteId}`, { method: "DELETE" })
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        setNotes((prev) => prev.filter((n) => n.id !== noteId));
      })
      .catch((e) => alert("删除笔记失败：" + e));
  }

  function formatNoteTime(iso: string): string {
    const d = new Date(iso);
    if (isNaN(d.getTime())) return "";
    const pad = (n: number) => String(n).padStart(2, "0");
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
  }

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

      {/* 上一课回顾 */}
      {c.review ? (
        <section className="card review-card">
          <h2>🔗 上一课回顾</h2>
          {c.review.split(/\n\n+/).map((para, i) => (
            <p key={i} className="para">{para}</p>
          ))}
        </section>
      ) : null}

      {/* 本课要解决的问题 */}
      {c.problem ? (
        <section className="card problem-card">
          <h2>❓ 本课要解决的问题</h2>
          {c.problem.split(/\n\n+/).map((para, i) => (
            <p key={i} className="para">{para}</p>
          ))}
        </section>
      ) : null}

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

      {/* 下一课伏笔 */}
      {c.preview ? (
        <section className="card preview-card">
          <h2>🔭 下一课伏笔</h2>
          {c.preview.split(/\n\n+/).map((para, i) => (
            <p key={i} className="para">{para}</p>
          ))}
        </section>
      ) : null}

      {/* 我的学习笔记 */}
      <section className="card note-card">
        <h2>📝 我的学习笔记</h2>
        <p className="para muted">
          记录你学习本课时的理解、疑问、心得或最终形成的认知。每次保存都会新增一条记录，不会覆盖历史。
        </p>
        <textarea
          className="note-input"
          placeholder="写下你的理解、疑问或感悟…"
          value={noteDraft}
          onChange={(e) => setNoteDraft(e.target.value)}
          rows={4}
        />
        <div className="note-actions">
          <button
            className="btn-primary"
            onClick={saveNote}
            disabled={noteBusy || !noteDraft.trim()}
          >
            {noteBusy ? "保存中…" : "保存笔记"}
          </button>
        </div>

        <div className="note-list">
          {notes.length === 0 ? (
            <p className="para muted">（还没有笔记，写下第一条吧）</p>
          ) : (
            notes.map((n) => (
              <div key={n.id} className="note-item">
                <div className="note-meta">
                  <span className="note-time">{formatNoteTime(n.created_at)}</span>
                  <button
                    className="note-delete"
                    onClick={() => deleteNote(n.id)}
                    title="删除这条笔记"
                  >
                    删除
                  </button>
                </div>
                <p className="note-content">{n.content}</p>
              </div>
            ))
          )}
        </div>
      </section>

      {/* 下一步 / 测验入口 */}
      <section className="card next-card">
        <h2>🚀 下一步</h2>

        {data.status === "locked" && (
          <p className="para">🔒 需先掌握前一课，才能解锁本课与测验。</p>
        )}

        {data.status === "mastered" && (
          <>
            <p className="para">✅ 本课已掌握（得分 {data.mastery_score ?? 0}%）。</p>
            {data.next_lesson ? (
              <Link to={`/lesson/${data.next_lesson.id}`} className="btn-primary">
                下一课：{data.next_lesson.title} →
              </Link>
            ) : (
              <p className="para">🏆 已是课程最后一课，恭喜通关！</p>
            )}
            <Link to={`/lesson/${data.id}/quiz`} className="back-link">
              复习测验
            </Link>
          </>
        )}

        {(data.status === "available" || data.status === "needs_review") && (
          <Link to={`/lesson/${data.id}/quiz`} className="btn-primary">
            {data.status === "needs_review" ? "复习测验（需努力）" : "开始测验"} →
          </Link>
        )}

        {data.status !== "mastered" && data.next_lesson && (
          <p className="next-hint">通过测验（正确率 ≥ 80%）即可解锁下一课</p>
        )}
      </section>

      <p className="phase">Phase 4 · 学习页面</p>
    </div>
  );
}
