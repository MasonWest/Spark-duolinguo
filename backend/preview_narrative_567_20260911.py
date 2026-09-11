# -*- coding: utf-8 -*-
"""生成 Level 5 / 6 / 7 三段文案（上一课回顾 / 本课要解决的问题 / 下一课伏笔）的静态预览页。

渲染规则对齐前端 components/RichText.tsx：
- \\n\\n+ 切分段落
- `· ` 开头且 >=2 行 → 无序列表
- **x** → 粗体、`x` → 行内 code

用法：python preview_narrative_567_20260911.py
"""
import html
import json
import re
import sqlite3

DB = "spark_quest.db"
OUT = "_l567_narrative_preview.html"


def inline(t: str) -> str:
    t = html.escape(t)
    t = re.sub(r"`([^`]+)`", r'<code class="ic">\1</code>', t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", t)
    return t


def block(t: str) -> str:
    lines = [l.rstrip() for l in t.split("\n")]
    dot = lambda s: s.lstrip().startswith("· ")
    if sum(1 for l in lines if dot(l)) >= 2:
        out, prose, i = [], [], 0

        def flush():
            if prose:
                out.append(f'<p class="para">{inline("".join(prose))}</p>')
                prose.clear()

        while i < len(lines):
            if dot(lines[i]):
                flush()
                items = []
                while i < len(lines) and dot(lines[i]):
                    items.append(re.sub(r"^\s*·\s*", "", lines[i]))
                    i += 1
                out.append(
                    '<ul class="rich-list">'
                    + "".join(f"<li>{inline(x)}</li>" for x in items)
                    + "</ul>"
                )
            else:
                prose.append(lines[i])
                i += 1
        flush()
        return "".join(out)
    return f'<p class="para">{inline(t)}</p>'


def richtext(t: str) -> str:
    paras = [p.strip() for p in re.split(r"\n\n+", t) if p.strip()]
    return "".join(block(p) for p in paras)


def main():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute(
        "select cl.order_index, l.title, l.order_index, l.content "
        "from lessons l join course_levels cl on cl.id = l.level_id "
        "where cl.order_index in (5,6,7) order by cl.order_index, l.order_index"
    )
    rows = cur.fetchall()
    conn.close()

    cards = []
    for lv, title, oi, raw in rows:
        d = json.loads(raw)
        cards.append(f"""
    <section class="lesson">
      <h2 class="lt">L{lv}-{oi + 1} · {html.escape(title)}</h2>
      <div class="grid">
        <div class="card c-review">
          <h3>🔗 上一课回顾</h3>
          <div class="rich-text">{richtext(d.get('review', ''))}</div>
        </div>
        <div class="card c-problem">
          <h3>❓ 本课要解决的问题</h3>
          <div class="rich-text">{richtext(d.get('problem', ''))}</div>
        </div>
        <div class="card c-preview">
          <h3>🔭 下一课伏笔</h3>
          <div class="rich-text">{richtext(d.get('preview', ''))}</div>
        </div>
      </div>
    </section>""")

    page = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>Level 5 / 6 / 7 三段文案预览</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{ margin:0; padding:32px 28px 60px; background:#f6f8fb; color:#1f2937;
         font-family:-apple-system,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif; }}
  h1 {{ font-size:22px; margin:0 0 4px; }}
  .sub {{ color:#6b7280; font-size:13px; margin-bottom:26px; }}
  .lesson {{ margin-bottom:34px; }}
  .lt {{ font-size:16px; margin:0 0 12px; color:#1e3a8a; }}
  .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(320px,1fr)); gap:14px; }}
  .card {{ background:#fff; border:1px solid #e5e7eb; border-radius:14px; padding:16px 18px;
           box-shadow:0 1px 3px rgba(16,24,40,.04); }}
  .card h3 {{ font-size:14px; margin:0 0 10px; }}
  .c-review h3 {{ color:#0e7490; }} .c-problem h3 {{ color:#b45309; }} .c-preview h3 {{ color:#6d28d9; }}
  .rich-text {{ font-size:15px; }}
  .para {{ margin:0 0 10px; line-height:1.85; }}
  .para:last-child {{ margin-bottom:0; }}
  .rich-list {{ margin:8px 0 12px; padding-left:22px; line-height:1.8; }}
  .ic {{ font-family:Consolas,monospace; background:#f1f5f9; color:#be123c;
         padding:1px 6px; border-radius:5px; font-size:.9em; }}
  strong {{ color:#111827; }}
</style></head><body>
  <h1>Level 5 / 6 / 7 · 「上一课回顾 / 本课要解决的问题 / 下一课伏笔」预览</h1>
  <div class="sub">渲染规则对齐前端 RichText 组件（\\n\\n 分段 · · 列表 · **粗体** · `code`）· 共 {len(rows)} 课 / {len(rows)*3} 段</div>
  {''.join(cards)}
</body></html>"""
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(page)
    print("written:", OUT, "|", len(rows), "lessons")


if __name__ == "__main__":
    main()
