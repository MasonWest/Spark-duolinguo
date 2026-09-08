import "./StreakBadge.css";

export type StreakVariant = "active" | "at-risk" | "broken";

/** Pure derivation — mirrors the backend rule, no state is ever stored. */
export function streakVariant(days: number, studiedToday: boolean): StreakVariant {
  if (days > 0 && studiedToday) return "active";
  if (days > 0) return "at-risk";
  return "broken";
}

const LABELS: Record<StreakVariant, string> = {
  active: "连续学习",
  "at-risk": "今天还没学",
  broken: "重新开始",
};

interface StreakBadgeProps {
  /** Current streak length in days (0 = broken). */
  days: number;
  studiedToday: boolean;
  className?: string;
}

export default function StreakBadge({ days, studiedToday, className = "" }: StreakBadgeProps) {
  const variant = streakVariant(days, studiedToday);
  const spoken = studiedToday
    ? `连续学习 ${days} 天，今天已完成`
    : days > 0
      ? `连续学习 ${days} 天，今天还没学，记录尚未中断`
      : "连续记录已中断，今天重新开始";

  return (
    <div
      className={`streak-badge is-${variant} ${className}`}
      role="status"
      aria-label={spoken}
      title={spoken}
    >
      <span className="streak-line">
        <span className="streak-flame" aria-hidden={true}>
          🔥
        </span>
        <span className="streak-count">{days}</span>
      </span>
      <span className="streak-label">{LABELS[variant]}</span>
    </div>
  );
}
