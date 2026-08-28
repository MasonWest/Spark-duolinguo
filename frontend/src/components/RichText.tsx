import type { ReactNode } from "react";
import { Fragment } from "react";
import "./RichText.css";

// 行内解析：code（`x`）与 bold（**x**）。数据均为自有种子内容，无 XSS 风险。
function renderInline(text: string): ReactNode[] {
  const nodes: ReactNode[] = [];
  const parts = text.split(/(`[^`]+`)/g);
  for (const part of parts) {
    if (part.length > 1 && part.startsWith("`") && part.endsWith("`")) {
      nodes.push(
        <code key={nodes.length} className="inline-code">
          {part.slice(1, -1)}
        </code>
      );
      continue;
    }
    const bparts = part.split(/(\*\*[^*]+\*\*)/g);
    for (const bp of bparts) {
      if (bp.length > 2 && bp.startsWith("**") && bp.endsWith("**")) {
        nodes.push(<strong key={nodes.length}>{bp.slice(2, -2)}</strong>);
      } else if (bp.length > 0) {
        nodes.push(<Fragment key={nodes.length}>{bp}</Fragment>);
      }
    }
  }
  return nodes;
}

const CIRCLED_RE = /[①-⑳]/g;

// 单个文本块：① ② ③ 有序枚举 / · 项目符号枚举（按行识别，支持与正文混排）/ 普通段落。
// 返回 ReactNode[]（可能含多个元素：正文段 + 列表）。
function renderBlock(text: string, key: string): ReactNode[] {
  const circled = text.match(CIRCLED_RE);
  if (circled && circled.length >= 2) {
    const positions: number[] = [];
    for (const m of text.matchAll(CIRCLED_RE)) positions.push(m.index ?? 0);
    const lead = text.slice(0, positions[0]).trim();
    const items: string[] = [];
    for (let i = 0; i < positions.length; i++) {
      const start = positions[i] + 1;
      const end = i + 1 < positions.length ? positions[i + 1] : text.length;
      let seg = text.slice(start, end).trim();
      seg = seg.replace(/^[；、)\s]+/, "").replace(/[；、]+$/, "");
      if (seg) items.push(seg);
    }
    const out: ReactNode[] = [];
    if (lead) {
      out.push(
        <p key={`${key}-l`} className="para">
          {renderInline(lead)}
        </p>
      );
    }
    out.push(
      <ol key={`${key}-ol`} className="rich-list">
        {items.map((it, i) => (
          <li key={i}>{renderInline(it)}</li>
        ))}
      </ol>
    );
    return out;
  }

  // · 项目符号列举：按行识别（数据常用单个换行分隔，并与正文混排）
  const isDot = (l: string) => l.trimStart().startsWith("· ");
  const lines = text.split("\n").map((l) => l.replace(/\s+$/, ""));
  if (lines.filter(isDot).length >= 2) {
    const out: ReactNode[] = [];
    let prose: string[] = [];
    const flush = () => {
      if (prose.length) {
        out.push(
          <p key={`${key}-p${out.length}`} className="para">
            {renderInline(prose.join(""))}
          </p>
        );
        prose = [];
      }
    };
    let i = 0;
    while (i < lines.length) {
      if (isDot(lines[i])) {
        flush();
        const items: string[] = [];
        while (i < lines.length && isDot(lines[i])) {
          items.push(lines[i].replace(/^\s*·\s*/, ""));
          i++;
        }
        out.push(
          <ul key={`${key}-ul${out.length}`} className="rich-list rich-list-ul">
            {items.map((it, j) => (
              <li key={j}>{renderInline(it)}</li>
            ))}
          </ul>
        );
      } else {
        prose.push(lines[i]);
        i++;
      }
    }
    flush();
    return out;
  }

  return [<p key={key} className="para">{renderInline(text)}</p>];
}

// 判断 s[idx] 处的【...】是否为「小节标题」，而非行内【】强调。
function isHeaderBracket(s: string, idx: number): boolean {
  const m = /【([^】]+)】/.exec(s.slice(idx));
  if (!m) return false;
  const after = s.slice(idx + m[0].length);
  const before = s.slice(0, idx);
  if (before.trim().length === 0) return true;
  if (after.startsWith("\n")) return true;
  const at = after.trim();
  return at.length === 0 || at.startsWith("【");
}

function firstHeaderIndex(s: string): number {
  let idx = s.indexOf("【");
  while (idx >= 0) {
    if (isHeaderBracket(s, idx)) return idx;
    idx = s.indexOf("【", idx + 1);
  }
  return -1;
}

type Seg = { subhead: string } | { body: string };

// 解析一个段落块，支持「【标题】」与正文粘连（部分课程未用空行分隔小节）。
function parseBlock(p: string): Seg[] {
  const m = /^【([^】]+)】\s*([\s\S]*)$/.exec(p);
  if (m) {
    const segs: Seg[] = [{ subhead: m[1] }];
    const rest = m[2].trim();
    if (rest) segs.push(...parseBlock(rest));
    return segs;
  }
  const idx = firstHeaderIndex(p);
  if (idx >= 0) {
    const before = p.slice(0, idx).trim();
    const segs: Seg[] = [];
    if (before) segs.push({ body: before });
    segs.push(...parseBlock(p.slice(idx)));
    return segs;
  }
  return [{ body: p }];
}

export default function RichText({ text }: { text: string }) {
  if (!text || !text.trim()) return null;
  const paras = text
    .split(/\n\n+/)
    .map((s) => s.trim())
    .filter(Boolean);

  const out: ReactNode[] = [];
  let k = 0;
  let i = 0;
  while (i < paras.length) {
    const p = paras[i];

    // ⚠️ 警示块：标题段 + 后续非结构段作为正文
    if (p.startsWith("⚠️")) {
      const body: ReactNode[] = [];
      i++;
      while (
        i < paras.length &&
        !paras[i].startsWith("⚠️") &&
        !/^【/.test(paras[i])
      ) {
        body.push(renderBlock(paras[i], `w${k++}`));
        i++;
      }
      out.push(
        <div key={`warn${k++}`} className="rich-warning">
          <p className="rich-warning-title">{renderInline(p)}</p>
          {body}
        </div>
      );
      continue;
    }

    for (const seg of parseBlock(p)) {
      if ("subhead" in seg) {
        out.push(
          <h4 key={`h${k++}`} className="rich-subhead">
            {seg.subhead}
          </h4>
        );
      } else {
        out.push(renderBlock(seg.body, `b${k++}`));
      }
    }
    i++;
  }

  return <div className="rich-text">{out}</div>;
}
