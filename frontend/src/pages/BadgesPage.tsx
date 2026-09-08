import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import type { Badge } from "../types";
import "./BadgesPage.css";

export default function BadgesPage() {
  const [badges, setBadges] = useState<Badge[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/badges")
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json() as Promise<Badge[]>;
      })
      .then(setBadges)
      .catch((e) => setError(String(e)));
  }, []);

  const journey = badges?.filter((b) => b.tier === "journey") ?? [];
  const special = badges?.filter((b) => b.tier === "special") ?? [];
  const unlockedCount = badges?.filter((b) => b.unlocked).length ?? 0;
  const total = badges?.length ?? 0;

  return (
    <div className="container badges-page">
      <header className="badges-header">
        <Link to="/" className="back-link">
          ← 返回首页
        </Link>
        <h1 className="badges-title">🏅 徽章墙</h1>
        <p className="badges-sub">
          {badges ? `已解锁 ${unlockedCount} / ${total}` : "加载中…"}
        </p>
      </header>

      {error && (
        <div className="card">
          <span className="status error">加载失败：{error}</span>
        </div>
      )}

      {badges && (
        <>
          <BadgeGroup title="🗺️ 旅程徽章" hint="每掌握一个 Level 解锁一枚" badges={journey} />
          <BadgeGroup title="⭐ 特别成就" hint="靠累计数据与特殊时刻触发" badges={special} />
        </>
      )}

      <p className="phase">Phase 9.2 · Achievement Badges</p>
    </div>
  );
}

function BadgeGroup({
  title,
  hint,
  badges,
}: {
  title: string;
  hint: string;
  badges: Badge[];
}) {
  return (
    <section className="badge-group">
      <h2 className="badge-group-title">{title}</h2>
      <p className="badge-group-hint">{hint}</p>
      <div className="badge-grid">
        {badges.map((b) => (
          <BadgeCard key={b.code} badge={b} />
        ))}
      </div>
    </section>
  );
}

function BadgeCard({ badge }: { badge: Badge }) {
  const secretLocked = badge.is_secret && !badge.unlocked;
  return (
    <div
      className={[
        "badge-card",
        badge.unlocked ? "unlocked" : "locked",
        secretLocked ? "secret" : "",
      ].join(" ")}
    >
      <div className="badge-card-img">
        {badge.image && !secretLocked ? (
          <img src={badge.image} alt={badge.name} loading="lazy" />
        ) : (
          <span className="badge-card-q">?</span>
        )}
      </div>
      <div className="badge-card-name">{secretLocked ? "神秘徽章" : badge.name || "未命名"}</div>
      <div className="badge-card-desc">
        {secretLocked ? "尚未解锁的秘密成就" : badge.description}
      </div>
      <div className="badge-card-status">
        {badge.unlocked
          ? badge.unlocked_at
            ? `已解锁 · ${badge.unlocked_at.slice(0, 10)}`
            : "已解锁"
          : "未解锁"}
      </div>
    </div>
  );
}
