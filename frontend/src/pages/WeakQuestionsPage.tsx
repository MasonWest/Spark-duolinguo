import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import type {
  WeakQuestion,
  WeakQuestionDetail,
  WeakQuestionPracticeResult,
} from "../types";
import "./WeakQuestionsPage.css";

function relativeTime(iso: string | null): string {
  if (!iso) return "—";
  const then = new Date(iso).getTime();
  const days = Math.floor((Date.now() - then) / 86400000);
  if (days <= 0) return "今天";
  if (days === 1) return "昨天";
  if (days < 30) return `${days} 天前`;
  return iso.slice(0, 10);
}

type PracticeState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "open"; detail: WeakQuestionDetail }
  | {
      status: "result";
      detail: WeakQuestionDetail;
      result: WeakQuestionPracticeResult;
      selected: number;
    };

export default function WeakQuestionsPage() {
  const [list, setList] = useState<WeakQuestion[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [practice, setPractice] = useState<PracticeState>({ status: "idle" });
  const [practiceError, setPracticeError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/weak-questions")
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json() as Promise<WeakQuestion[]>;
      })
      .then(setList)
      .catch((e) => setError(String(e)));
  }, []);

  function refreshList() {
    fetch("/api/weak-questions")
      .then((r) => r.json())
      .then((d) => setList(d as WeakQuestion[]))
      .catch(() => {});
  }

  async function openPractice(q: WeakQuestion) {
    setPractice({ status: "loading" });
    setPracticeError(null);
    try {
      const res = await fetch(`/api/weak-questions/${q.question_id}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const detail = (await res.json()) as WeakQuestionDetail;
      setPractice({ status: "open", detail });
    } catch (e) {
      setPracticeError(String(e));
      setPractice({ status: "idle" });
    }
  }

  async function submitPractice(selected: number, detail: WeakQuestionDetail) {
    setPracticeError(null);
    try {
      const res = await fetch(`/api/weak-questions/${detail.id}/practice`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ selected_index: selected }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const result = (await res.json()) as WeakQuestionPracticeResult;
      setPractice({ status: "result", detail, result, selected });
      refreshList(); // 计数 / 最近一次对错可能已变化
    } catch (e) {
      setPracticeError(String(e));
    }
  }

  function closePractice() {
    setPractice({ status: "idle" });
    refreshList();
  }

  const count = list?.length ?? 0;

  return (
    <div className="container weak-page">
      <header className="weak-header">
        <Link to="/" className="back-link">
          ← 返回首页
        </Link>
        <h1 className="weak-title">🧠 薄弱题</h1>
        <p className="weak-sub">
          {list
            ? `共 ${count} 道 · 历史上答错过、值得重新练`
            : "加载中…"}
        </p>
      </header>

      {error && (
        <div className="card">
          <span className="status error">加载失败：{error}</span>
        </div>
      )}

      {list && count === 0 && (
        <div className="card weak-empty">
          🎉 暂时没有薄弱题。答错的题会自动出现在这里——过段时间再回来，独立重做它们。
        </div>
      )}

      <div className="weak-list">
        {list?.map((q) => (
          <article className="weak-card" key={q.question_id}>
            <div className="weak-card-main">
              <div className="weak-prompt">
                <span className="weak-x">❌</span>
                <span className="weak-prompt-text">{q.prompt}</span>
              </div>
              <div className="weak-meta">
                <span className="weak-dim">
                  {q.dimension ?? "未分类"} · L{q.level_order}
                </span>
                <span className="weak-count">
                  错误 {q.wrong_count} 次 · 最近一次 {relativeTime(q.last_wrong_at)}
                </span>
                {q.last_attempt_correct && (
                  <span className="weak-recovered">最近一次已做对</span>
                )}
              </div>
            </div>
            <button
              className="weak-practice-btn"
              onClick={() => openPractice(q)}
            >
              重新练习
            </button>
          </article>
        ))}
      </div>

      {practice.status !== "idle" && (
        <div className="practice-overlay" onClick={closePractice}>
          <div
            className="practice-panel"
            onClick={(e) => e.stopPropagation()}
          >
            {practice.status === "loading" && <p>加载中…</p>}

            {practice.status === "open" && (
              <>
                <div className="practice-prompt">{practice.detail.prompt}</div>
                <ul className="practice-options">
                  {practice.detail.options.map((opt, i) => (
                    <li key={i}>
                      <button
                        className="practice-option"
                        onClick={() => submitPractice(i, practice.detail)}
                      >
                        {opt}
                      </button>
                    </li>
                  ))}
                </ul>
                {practiceError && (
                  <p className="status error">{practiceError}</p>
                )}
                <button className="practice-close" onClick={closePractice}>
                  取消
                </button>
              </>
            )}

            {practice.status === "result" && (
              <>
                <div className="practice-prompt">{practice.detail.prompt}</div>
                <ul className="practice-options">
                  {practice.detail.options.map((opt, i) => {
                    let cls = "practice-option";
                    if (i === practice.result.correct_index) cls += " correct";
                    else if (
                      i === practice.selected &&
                      !practice.result.is_correct
                    )
                      cls += " wrong";
                    return (
                      <li key={i}>
                        <button className={cls} disabled>
                          {opt}
                          {i === practice.result.correct_index ? " ✓" : ""}
                          {i === practice.selected && !practice.result.is_correct
                            ? " ✗"
                            : ""}
                        </button>
                      </li>
                    );
                  })}
                </ul>
                <div
                  className={`practice-verdict ${
                    practice.result.is_correct ? "ok" : "bad"
                  }`}
                >
                  {practice.result.is_correct
                    ? "✅ 这次答对了！"
                    : "❌ 还是错了，再想想"}
                </div>
                <div className="practice-explanation">
                  <strong>解析：</strong>
                  {practice.result.explanation}
                </div>
                <div className="practice-actions">
                  <button
                    className="practice-retry"
                    onClick={() =>
                      setPractice({ status: "open", detail: practice.detail })
                    }
                  >
                    再试一次
                  </button>
                  <button className="practice-close" onClick={closePractice}>
                    返回列表
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}

      <p className="phase">Phase 10.1 · Weak Questions</p>
    </div>
  );
}
