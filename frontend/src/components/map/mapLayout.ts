// Course Map v1.1 — 纯函数布局算法
//
// 设计约束（v1.1 硬约束）：
//   · 课程结构必须由数据动态渲染，不能依赖任何固定背景图片
//   · 输入只有「课程数量」，加课/删课自动适配，零硬编码坐标
//
// 本文件不含任何 React / DOM 依赖，可独立单测。

import type { Level } from "../../types";

export interface MapNode {
  x: number;
  y: number;
}

export interface LayoutOptions {
  /** 可用内容宽度（px），节点在此宽度内居中摆动 */
  width: number;
  /**
   * 垂直步长（两节点中心距）。默认 96，保证当前节点放大到 58 时，
   * 上一节点的两行标题不会与下一节点的 orb 顶重叠。
   */
  stepY?: number;
  /** 第一个节点中心距区域顶部的距离 */
  startY?: number;
  /** 区域底部留白 */
  paddingBottom?: number;
  /** 水平摆动幅度系数，窄屏传 0.6 */
  amplitude?: number;
}

/**
 * 水平偏移表（循环使用）。
 *
 * 为什么用预设表而不是 sin()：
 *   · 确定性 —— 同样的 count 永远得到同样的形状，可快照单测
 *   · 可控 —— 不会出现 sin 在极端相位产生的贴边或过冲
 *   · 可调 —— 想改风格只改这张表
 */
const OFFSET_CYCLE = [0, 58, 78, 58, 0, -58, -78, -58];

/** 窄屏判定阈值：低于此宽度时收窄摆动，避免节点与标题溢出 */
export const NARROW_WIDTH = 420;

export function layoutRegion(count: number, opts: LayoutOptions): MapNode[] {
  const { width, stepY = 96, startY = 56, amplitude = 1 } = opts;
  const cx = width / 2;
  const nodes: MapNode[] = [];
  for (let i = 0; i < count; i++) {
    const off = OFFSET_CYCLE[i % OFFSET_CYCLE.length] * amplitude;
    nodes.push({ x: cx + off, y: startY + i * stepY });
  }
  return nodes;
}

/** 区域内容总高：由课程数推导，不写死 */
export function regionHeight(
  count: number,
  opts: Pick<LayoutOptions, "stepY" | "startY" | "paddingBottom"> = {}
): number {
  const { stepY = 96, startY = 56, paddingBottom = 56 } = opts;
  if (count <= 0) return startY + paddingBottom;
  return startY + (count - 1) * stepY + paddingBottom;
}

/**
 * 生成两节点之间的道路段（S 曲线）。
 *
 * 用三次贝塞尔，控制点取垂直中点，使路径在节点处垂直出入，
 * 视觉上像一条连续蜿蜒的小路而不是折线。
 */
export function segmentPath(a: MapNode, b: MapNode): string {
  const my = (a.y + b.y) / 2;
  return `M ${a.x} ${a.y} C ${a.x} ${my}, ${b.x} ${my}, ${b.x} ${b.y}`;
}

/**
 * 区域三档视觉：时间的叙事。
 *   past    走过的路   —— 已通关，视觉沉淀
 *   present 我在这里   —— 进行中 / 可开始，全饱和聚焦
 *   future  前方未知   —— 未解锁，低对比朦胧
 *
 * 档位只用于「增强层」。状态信息永远由徽章文字 + 节点色 + 道路虚实承载，
 * 因此禁用全部滤镜后三档仍可 100% 判别（见验收项 4）。
 */
export type RegionTone = "past" | "present" | "future";

export function regionTone(level: Pick<Level, "status">): RegionTone {
  if (level.status === "completed") return "past";
  if (level.status === "locked") return "future";
  return "present";
}

export const REGION_TONE_LABEL: Record<RegionTone, string> = {
  past: "过去",
  present: "现在",
  future: "未来",
};
