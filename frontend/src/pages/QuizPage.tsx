import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import type { QuizFetch, QuizQuestion, QuizResult, QuizSubmit } from "../types";
import "./QuizPage.css";

type Choice = Record<number, number>; // question_id -> selected_index

export default function QuizPage() {
  const { id } = useParams<{ id: string }>();
  const [quiz, setQuiz] = useState<QuizFetch | null>(null);
  const [choices, setChoices] = useState<Choice>({});
  const [result, setResult] = useState<QuizResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notFound, setNotFound] = useState(false);
  const [locked, setLocked] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  function loadQuiz() {
    setQuiz(null);
    setChoices({});
    setResult(null);
    setError(null);
    setNotFound(false);
    setLocked(false);
    fetch(`/api/lessons/${id}/quiz`)
      .then((res) => {
        if (res.status === 404) {
          setNotFound(true);
          throw new Error("课程不存在");
        }
        if (res.status === 403) {
          setLocked(true);
          throw new Error("本课尚未解锁");
        }
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json() as Promise<QuizFetch>;
      })
      .then(setQuiz)
      .catch((e) => {
        if (!notFound && !locked) setError(String(e));
      });
  }

  useEffect(() => {
    loadQuiz();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

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
    const payload: QuizSubmit = {
      answers: quiz.questions.map((q) => ({
        question_id: q.id,
        selected_index: choices[q.id],
      })),
    };
    fetch(`/api/lessons/${id}/quiz/submit`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    })
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json() as Promise<QuizResult>;
      })
      .then(setResult)
      .catch((e) => setError(String(e)))
      .finally(() => setSubmitting(false));
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

  if (locked) {
    return (
      <div className="container">
        <div className="card">
          <h2>🔒 本课尚未解锁</h2>
          <p className="status">请先掌握前一课，再来挑战测验。</p>
        </div>
        <Link to="/map" className="btn-primary">
          ← 返回课程地图
        </Link>
      </div>
    );
  }

  if (error && !quiz && !result) {
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

  if (!quiz) {
    return (
      <div className="container">
        <div className="card">
          <span className="status">加载测验中…</span>
        </div>
      </div>
    );
  }

  // ---- Result view ----
  if (result) {
    const mastered = result.status === "mastered";
    return (
      <div className="container quiz-container">
        <header className="lesson-header">
          <Link to="/map" className="back-link">
            ← 返回课程地图
          </Link>
          <span className="lesson-level">{quiz.lesson_title}</span>
        </header>

        <h1 className="lesson-title">测验结果</h1>
        <div className={`result-banner ${mastered ? "ok" : "retry"}`}>
          {mastered ? "🎉 已掌握！" : "🟡 还需努力"}
          <span className="result-score">得分 {result.score}%（{result.correct}/{result.total}）</span>
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
                <span>{quiz.questions.find((q) => q.id === r.question_id)?.prompt}</span>
              </div>
              <div className="quiz-result-mark">
                {r.is_correct ? "✅ 正确" : "❌ 错误"}
              </div>
              {!r.is_correct && (
                <div className="quiz-result-explain">
                  <span className="mistake-label">解析</span>
                  {r.explanation}
                </div>
              )}
            </div>
          ))}
        </section>

        <section className="card next-card">
          {mastered ? (
            <>
              {result.unlocked_next && result.next_lesson_id ? (
                <Link to={`/lesson/${result.next_lesson_id}`} className="btn-primary">
                  下一课已解锁，继续学习 →
                </Link>
              ) : (
                <p className="para">🏆 已是课程最后一课，恭喜通关！</p>
              )}
              <button className="btn-ghost" onClick={loadQuiz}>
                复习本課测验
              </button>
            </>
          ) : (
            <>
              <p className="para">薄弱点已记录，建议复习后再试一次。</p>
              <button className="btn-primary" onClick={loadQuiz}>
                重新测验
              </button>
              <Link to={`/lesson/${quiz.lesson_id}`} className="btn-ghost">
                返回学习页面
              </Link>
            </>
          )}
        </section>

        <p className="phase">Phase 4 · Mastery Quiz</p>
      </div>
    );
  }

  // ---- Quiz view ----
  return (
    <div className="container quiz-container">
      <header className="lesson-header">
        <Link to={`/lesson/${quiz.lesson_id}`} className="back-link">
          ← 返回学习页面
        </Link>
        <span className="lesson-level">{quiz.lesson_title}</span>
      </header>

      <h1 className="lesson-title">Mastery 测验</h1>
      <p className="subtitle">共 {quiz.questions.length} 题 · 正确率 ≥ 80% 即掌握本课</p>

      {quiz.questions.map((q: QuizQuestion, i) => (
        <section key={q.id} className="card quiz-question">
          <div className="quiz-q-head">
            <span className="quiz-no">题 {i + 1}</span>
            <span className="quiz-type">{typeLabel(q.type)}</span>
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
        {submitting ? "提交中…" : allAnswered() ? "提交测验" : "请答完所有题目"}
      </button>

      <p className="phase">Phase 4 · Mastery Quiz</p>
    </div>
  );
}

function typeLabel(t: string): string {
  if (t === "true_false") return "判断题";
  if (t === "application") return "应用题";
  return "单选题";
}
