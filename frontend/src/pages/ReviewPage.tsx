import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import type { ReviewFetch, ReviewResult, ReviewSubmit } from "../types";
// 复习页与测验页共用题目卡片 / 结果卡片样式，避免重复造一套 CSS。
import "./QuizPage.css";
import "./ReviewPage.css";

type Choice = Record<number, number>; // question_id -> selected_index

export default function ReviewPage() {
  const { id } = useParams<{ id: string }>();
  const [quiz, setQuiz] = useState<ReviewFetch | null>(null);
  const [choices, setChoices] = useState<Choice>({});
  const [result, setResult] = useState<ReviewResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notFound, setNotFound] = useState(false);
  const [forbidden, setForbidden] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const loadReview = useCallback(() => {
    setQuiz(null);
    setChoices({});
    setResult(null);
    setError(null);
    setNotFound(false);
    setForbidden(false);
    fetch(`/api/review/${id}`)
      .then((res) => {
        if (res.status === 404) {
          setNotFound(true);
          return null;
        }
        if (res.status === 403) {
          setForbidden(true);
          return null;
        }
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json() as Promise<ReviewFetch>;
      })
      .then((data) => {
        if (data) setQuiz(data);
      })
      .catch((e) => setError(String(e)));
  }, [id]);

  useEffect(() => {
    loadReview();
  }, [loadReview]);

  function select(qid: number, idx: number) {
    setChoices((c) => ({ ...c, [qid]: idx }));
  }

  function allAnswered(): boolean {
    if (!quiz) return false;
    return quiz.questions.every((q) => choices[q.id] !== undefined);
  }

  function submit() {
    if (!quiz || !allAnswered()) return;
    setSubmitting(true);
    setError(null);
    const payload: ReviewSubmit = {
      answers: quiz.questions.map((q) => ({
        question_id: q.id,
        selected_index: choices[q.id],
      })),
    };
    fetch(`/api/review/${id}/submit`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    })
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json() as Promise<ReviewResult>;
      })
      .then(setResult)
      .catch((e) => setError(String(e)))
      .finally(() => setSubmitting(false));
  }

  if (notFound) {
    return <Shell title="😕 找不到这节课" body={`课程不存在（id = ${id}）。`} />;
  }

  if (forbidden) {
    return (
      <Shell
        title="🔒 还不能复习"
        body="间隔复习只对已掌握的课程开放，请先完成本课的学习测验。"
      />
    );
  }

  if (error && !quiz && !result) {
    return <Shell title="加载失败" body={error} />;
  }

  if (!quiz) {
    return (
      <div className="container review-container">
        <div className="card">
          <span className="status">准备复习题目中…</span>
        </div>
      </div>
    );
  }

  // ---- 结果页 ----
  if (result) {
    return (
      <div className="container review-container">
        <header className="review-header">
          <Link to="/" className="back-link">
            ← 返回首页
          </Link>
          <span className="review-level">间隔复习</span>
        </header>

        <h1 className="review-title">{quiz.lesson_title}</h1>

        <div className={`review-banner ${result.passed ? "ok" : "retry"}`}>
          {result.passed ? "🎉 复习通过" : "📖 本次复习还需要巩固"}
          <span className="review-score">
            {result.correct} / {result.total} · 需要 5 / 5 才算通过
          </span>
        </div>

        <section className="card">
          <h2>逐题回顾</h2>
          {result.results.map((r, i) => (
            <div
              key={r.question_id}
              className={`quiz-result-item ${r.is_correct ? "correct" : "wrong"}`}
            >
              <div className="quiz-result-q">
                <span className="quiz-no">题 {i + 1}</span>
                <span>
                  {quiz.questions.find((q) => q.id === r.question_id)?.prompt}
                </span>
              </div>
              <div className="quiz-result-mark">
                {r.is_correct ? "✅ 正确" : "❌ 错误"}
              </div>
              {!r.is_correct && (
                <div className="quiz-result-explain">{r.explanation}</div>
              )}
            </div>
          ))}
        </section>

        <section className="card review-next">
          {result.passed ? (
            <>
              <p className="para">
                ✅ 下次复习：{result.next_interval_days} 天后（已于第{" "}
                {result.srs_stage} 档 · 累计复习 {result.review_count} 次）
              </p>
              <Link to="/" className="btn-primary">
                完成，返回首页 →
              </Link>
            </>
          ) : (
            <>
              <p className="para">
                先回到课程内容重新读一遍，读完后可以立刻再挑战一次。
                <br />
                <span className="muted">
                  另已安排在 {result.next_interval_days} 天后再次提醒你复习本课。
                </span>
              </p>
              <Link
                to={`/lesson/${quiz.lesson_id}?from=review`}
                className="btn-primary"
              >
                重新阅读本课 →
              </Link>
              <button className="btn-ghost" onClick={loadReview}>
                直接再挑战一次
              </button>
            </>
          )}
        </section>

        <p className="phase">Phase 6b · Spaced Review</p>
      </div>
    );
  }

  // ---- 答题页 ----
  return (
    <div className="container review-container">
      <header className="review-header">
        <Link to="/" className="back-link">
          ← 返回首页
        </Link>
        <span className="review-level">间隔复习</span>
      </header>

      <h1 className="review-title">{quiz.lesson_title}</h1>
      <p className="subtitle">
        共 {quiz.questions.length} 题 · 必须 5 / 5 全部答对才算复习通过
      </p>

      {quiz.questions.map((q, i) => (
        <section key={q.id} className="card quiz-question">
          <div className="quiz-q-head">
            <span className="quiz-no">第 {i + 1} / {quiz.questions.length} 题</span>
            {q.dimension && <span className="quiz-dim">{dimLabel(q.dimension)}</span>}
          </div>
          <p className="quiz-prompt">{q.prompt}</p>
          <div className="quiz-options">
            {q.options.map((opt, oi) => (
              <label
                key={oi}
                className={`quiz-option ${choices[q.id] === oi ? "selected" : ""}`}
              >
                <input
                  type="radio"
                  name={`q-${q.id}`}
                  checked={choices[q.id] === oi}
                  onChange={() => select(q.id, oi)}
                />
                <span className="quiz-option-text">{opt}</span>
              </label>
            ))}
          </div>
        </section>
      ))}

      {error && <div className="status error">{error}</div>}

      <button
        className="btn-primary quiz-submit"
        onClick={submit}
        disabled={!allAnswered() || submitting}
      >
        {submitting ? "提交中…" : allAnswered() ? "提交复习" : "请答完所有题目"}
      </button>

      <p className="phase">Phase 6b · Spaced Review</p>
    </div>
  );
}

function Shell({ title, body }: { title: string; body: string }) {
  return (
    <div className="container review-container">
      <div className="card">
        <h2>{title}</h2>
        <p className="status">{body}</p>
      </div>
      <Link to="/" className="btn-primary">
        ← 返回首页
      </Link>
    </div>
  );
}

const DIM_LABELS: Record<string, string> = {
  concept: "概念理解",
  why: "为什么",
  mechanism: "运行机制",
  apply: "场景应用",
  comparison: "对比辨析",
  debug: "排错调优",
};

function dimLabel(d: string): string {
  return DIM_LABELS[d] ?? d;
}
