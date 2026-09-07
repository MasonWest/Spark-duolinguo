import type { Lesson } from "../../types";
import { segmentPath, type MapNode } from "./mapLayout";

interface Props {
  nodes: MapNode[];
  lessons: Lesson[];
  width: number;
  height: number;
}

/**
 * 区域内部的道路。
 *
 * 一段一课：段 i 连接第 i 课与第 i+1 课的节点。第 i 课 mastered 就把这段点亮 ——
 * 「走过的路被点亮」是完成感的核心载体，比单点打勾强得多。
 *
 * 路径形状全部由 segmentPath() 依节点坐标算出，不依赖任何图片。
 */
export default function LessonPath({ nodes, lessons, width, height }: Props) {
  return (
    <svg
      className="lesson-path"
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      aria-hidden="true"
      focusable="false"
    >
      {nodes.slice(0, -1).map((n, i) => {
        const lit = lessons[i]?.status === "mastered";
        return (
          <path
            key={i}
            d={segmentPath(n, nodes[i + 1])}
            className={lit ? "seg seg-lit" : "seg seg-dim"}
          />
        );
      })}
    </svg>
  );
}
