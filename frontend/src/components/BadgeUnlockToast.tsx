import { useEffect } from "react";
import type { Badge } from "../types";
import "./BadgeUnlockToast.css";

interface Props {
  badges: Badge[];
  onClose: () => void;
}

/**
 * Phase 9.2: a lightweight, auto-dismissing toast shown after a quiz / review
 * submit when at least one badge was just unlocked. Purely cosmetic -- it never
 * blocks the result view. Secrets, once unlocked, are revealed normally here
 * (the backend only blanks them while still locked).
 */
export default function BadgeUnlockToast({ badges, onClose }: Props) {
  useEffect(() => {
    if (!badges.length) return;
    const t = setTimeout(onClose, 5200);
    return () => clearTimeout(t);
  }, [badges, onClose]);

  if (!badges.length) return null;

  return (
    <div className="badge-toast" role="status" aria-live="polite">
      <div className="badge-toast-head">
        <span className="badge-toast-spark">🏅</span> 解锁新徽章！
      </div>
      <ul className="badge-toast-list">
        {badges.map((b) => (
          <li key={b.code} className="badge-toast-item">
            {b.image ? (
              <img src={b.image} alt={b.name} className="badge-toast-img" />
            ) : (
              <span className="badge-toast-img placeholder">?</span>
            )}
            <div className="badge-toast-text">
              <div className="badge-toast-name">{b.name || "神秘徽章"}</div>
              <div className="badge-toast-desc">{b.description}</div>
            </div>
          </li>
        ))}
      </ul>
      <button className="badge-toast-close" onClick={onClose} aria-label="关闭">
        ✕
      </button>
    </div>
  );
}
