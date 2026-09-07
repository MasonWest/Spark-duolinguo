import type { Level } from "../../types";
import { regionTone } from "./mapLayout";

interface Props {
  levels: Level[];
  onJump: (levelId: number) => void;
}

/** 去掉「Level N：」前缀，导航胶囊只留区域名 */
function shortTitle(title: string): string {
  return title.replace(/^Level\s*\d+\s*[：:]\s*/, "").trim() || title;
}

/**
 * 区域导航胶囊。
 *
 * 解决 UX Audit 里的 Q1「我现在在哪里」—— 一眼看到 8 个区域、当前在哪、
 * 想回看随时跳转。
 */
export default function RegionNav({ levels, onJump }: Props) {
  return (
    <nav className="region-nav" aria-label="课程区域导航">
      {levels.map((l, i) => {
        const tone = regionTone(l);
        const cls = [
          tone === "present" ? "is-current" : "",
          tone === "past" ? "is-done" : "",
        ]
          .filter(Boolean)
          .join(" ");
        return (
          <button
            key={l.id}
            type="button"
            className={cls}
            onClick={() => onJump(l.id)}
            aria-current={tone === "present" ? "true" : undefined}
            title={`${l.title}（${l.completed_count} / ${l.total_count}）`}
          >
            {i + 1}. {shortTitle(l.title)}
          </button>
        );
      })}
    </nav>
  );
}
