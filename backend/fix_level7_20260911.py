# -*- coding: utf-8 -*-
"""Level 7（性能调优）技术审查修复。

审查结论：L7 无 L4 那种「把定义说反」级别的 P0 错误，整体质量好于 L5。
主要缺口是**版本事实**——AQE 自 Spark 3.2.0 起默认开启这件事全课没讲，
导致第 4/5/6/7 课的「调旋钮 / 开 AQE」都与 3.x 现实脱节。

修复项：
P1-1 乱码 2 处（U+FFFD）：L7-4 / L7-9 的 example note
P1-2 AQE 默认开启的版本事实缺失（L7-4/6/7/9 + 题库）
P1-3 绝对化「慢几个数量级」（L7-4 note + q646）
P2   内存借用「反之亦然」不准确（实为不对称）；「200 列里的 200 列」表述不通；
     中英混用「memory」；Parquet 读取路径（向量化 → ColumnarBatch → UnsafeRow）
P3   补 Reserved 300MB / fraction 0.6 / 广播阈值默认 10MB

来源（已核对官方文档）：
- AQE 默认启用自 3.2.0（"enabled by default since Apache Spark 3.2.0"）
- skewJoin.enabled / coalescePartitions.enabled 默认 true（3.0.0）
- advisoryPartitionSizeInBytes 默认 64MB；autoBroadcastJoinThreshold 默认 10MB
- Reserved Memory 固定 300MB；spark.memory.fraction 默认 0.6、storageFraction 0.5
- 借用不对称：Execution 可驱逐 Storage，反向不可

注意：lessons.content 的 key_points 是**纯字符串列表**（无 `- ` 前缀），
新增条目走 KP_APPEND，不要写成带前缀的字符串替换。

用法：python fix_level7_20260911.py --dry | --apply
"""
import json
import sqlite3
import sys
from pathlib import Path

DB = Path(__file__).resolve().parent / "spark_quest.db"

# (lesson_id, field, old, new) —— 字符串替换（幂等）
EDITS = []


def E(lid, field, old, new):
    EDITS.append((lid, field, old, new))


# ---------- L7-1 [58] ----------
E(58, "examples",
  "# 作业慢的真实原因：读了 200 列里的 200 列、没做分区裁剪",
  "# 作业慢的真实原因：200 列一列没裁、全读了，也没做分区裁剪")

# ---------- L7-2 [59] ----------
E(59, "explanation",
  "数据一多，这些「包装」吃掉的 memory 比数据本身还多",
  "数据一多，这些「包装」吃掉的内存比数据本身还多")

E(59, "explanation",
  "你写 `df = spark.read.parquet('sales')`：Parquet 读出的数据被直接组织成 Tungsten 的紧凑二进制行，在 Executor 内存里连续排列。",
  "你写 `df = spark.read.parquet('sales')`：Spark 3.x 默认启用 Parquet 向量化读取，数据先按批（ColumnarBatch）读入，再转成 Tungsten 的紧凑二进制行（UnsafeRow），在 Executor 内存里连续排列。")

# ---------- L7-3 [60] ----------
E(60, "explanation",
  "- **Reserved Memory**：系统保留（固定量）。",
  "- **Reserved Memory**：系统保留，固定 300MB（不可配置）。")

E(60, "explanation",
  "统一内存管理（Unified Memory Manager）下，Execution 与 Storage 之间可互相借用：Storage 空间可被执行内存挤占（缓存按策略逐出或落盘），反之亦然。堆外内存（off-heap）由 Spark 自行管理、不受 GC 管辖，需单独估量。",
  """统一内存管理（Unified Memory Manager）下，Execution 与 Storage 共享同一区域，空闲部分可互相借用——但**这种借用是不对称的**：Execution 紧张时可以直接驱逐 Storage（缓存被逐出或落盘），而 Storage 只能等 Execution 释放，无法反向驱逐。堆外内存（off-heap）由 Spark 自行管理、不受 GC 管辖，需单独估量。

堆内存的具体划分（Spark 3.x 默认值）：`Reserved` 固定 **300MB**；其余按 `spark.memory.fraction`（默认 0.6）划给 Execution + Storage 统一区，其中按 `spark.memory.storageFraction`（默认 0.5）分给 Storage；剩余约 40% 是 User Memory。**注意 User Memory 不参与借用**——这正是「容器里明明还有内存、任务却报 OOM」的一大来源。""")

# ---------- L7-4 [61] ----------
E(61, "examples",
  "复\ufffd\ufffd L5：spill 意味着内存放不下、落到磁盘，I/O 慢几个数量级。",
  "复用 L5：spill 意味着内存放不下、落到磁盘；磁盘 I/O 通常比内存慢 1~2 个数量级。")

E(61, "explanation",
  "④ 分区数不是越多越并行：集群核数才是并行上限，车道再多、工人只有 8 个，也只能同时开 8 条（复用 L5 分区与并行度）。",
  """④ 分区数不是越多越并行：集群核数才是并行上限，车道再多、工人只有 8 个，也只能同时开 8 条（复用 L5 分区与并行度）。
⑤ ⚠️ **版本提示**：Spark 3.2+ 默认开启 AQE。开启时本参数是 shuffle 后的**初始**分区数（上界），运行时 AQE 会按真实数据量合并掉一部分——你设 400，实际可能只跑出几十个 Task。做教学演示想看到「经典」行为，可显式 `spark.conf.set('spark.sql.adaptive.enabled','false')`（第 6 课展开）。""")

# ---------- L7-5 [62] ----------
E(62, "explanation",
  "判断依据是该侧数据的**统计大小估计**。",
  "判断依据是该侧数据的**统计大小估计**（Spark 3.x 的默认阈值为 10MB）。")

E(62, "explanation",
  "④ 具体配多少字节、怎么配，没有通用答案——取决于 Executor 内存与并发作业数，别抄别人的配置。",
  """④ 具体配多少字节、怎么配，没有通用答案——取决于 Executor 内存与并发作业数，别抄别人的配置。
⑤ ⚠️ Spark 3.2+ 默认开启 AQE，运行时会根据真实大小把 Sort-Merge Join 改成 Broadcast Hash Join——所以静态 `explain` 里看到的 SortMergeJoin 未必是最终执行的策略（第 6 课展开）。""")

# ---------- L7-6 [63] ----------
E(63, "explanation",
  "① AQE 的观察点是 **Shuffle**：它要等 shuffle 写出后才知道每个分区真实多大。没有 shuffle 的地方，它看不到真相。",
  """⓪ ⚠️ **版本提示（重要）**：AQE **自 Spark 3.2.0 起默认开启**（三大能力自 3.0 引入；3.0 / 3.1 需手动打开总开关）。所以在较新的 Spark 上，你多半不需要「开启」它，而是要**确认它的效果**——直接做后面的验证即可。
① AQE 的观察点是 **Shuffle**：它要等 shuffle 写出后才知道每个分区真实多大。没有 shuffle 的地方，它看不到真相。""")

E(63, "examples",
  "开启 AQE（概念验证，具体开关以实际版本为准）",
  "确认 AQE 状态（Spark 3.2+ 默认已开启）")

E(63, "examples",
  "spark.conf.set('spark.sql.adaptive.enabled', 'true')\nbig.join(dim, 'city_id').groupBy('k').count().show()\n# 再看 Spark UI：实际执行图可能与静态 explain 不同",
  "print(spark.conf.get('spark.sql.adaptive.enabled'))   # 3.2+ 默认为 true\nbig.join(dim, 'city_id').groupBy('k').count().show()\n# 再看 Spark UI：实际执行图可能与静态 explain 不同")

E(63, "examples",
  "开了 AQE 就别只信 explain 的静态计划，要看 UI 里的真实执行图。",
  "3.0 / 3.1 需要手动开启，3.2+ 默认已开——重点是确认它生效，而不是「打开」它。开了它就别只信 explain 的静态计划，要看 UI 里的真实执行图。")

E(63, "explanation",
  "开启 AQE 后，静态 `explain()` 结果可能与实际执行计划不同，应以 Spark UI 的实际执行图为准。",
  """开启 AQE 后，静态 `explain()` 结果可能与实际执行计划不同，应以 Spark UI 的实际执行图为准。

**版本事实**：三大能力（合并分区 / 切换 JOIN 策略 / 倾斜处理）自 Spark 3.0 引入；总开关 `spark.sql.adaptive.enabled` **自 3.2.0 起默认为 true**；子开关 `spark.sql.adaptive.coalescePartitions.enabled`（合并分区）与 `spark.sql.adaptive.skewJoin.enabled`（倾斜处理）默认同样为 true（自 3.0.0）。""")

# ---------- L7-7 [64] ----------
E(64, "explanation",
  "1. **让系统自动分流（AQE）**：开自动倾斜处理，让 Spark 自己把堵死的车道拆成几条匝道——最省事，优先试；",
  "1. **让系统自动分流（AQE）**：让 Spark 自己把堵死的车道拆成几条匝道——**注意 AQE 的倾斜处理自 Spark 3.0 起默认开启**，所以这一步通常是「先确认它有没有生效」（看 Spark UI 里那个巨大分区有没有被拆开），而不是「去打开它」；最省事，优先试；")

E(64, "explanation",
  "④ 具体的倾斜开关与其参数配方不在本课范围（不同版本支持不同），本课给的是**手段与优先级**。",
  """④ 具体的倾斜开关与其参数配方不在本课范围（不同版本支持不同），本课给的是**手段与优先级**。但有一条版本事实必须知道：`spark.sql.adaptive.skewJoin.enabled` 默认 **true**（自 Spark 3.0），所以在 Spark 3.x 上「先看 AQE 有没有兜住」才是第一步，手工加盐往往是后面才需要考虑的。""")

E(64, "examples",
  "最省事的一招，先试它；不行再上重手段。",
  "最省事的一招：先确认它有没有生效（AQE 倾斜处理自 3.0 起默认开启）；不行再上重手段。")

E(64, "key_points",
  "手段优先级：AQE 自动处理 → 隔离大 key → salting 加盐 → 广播绕过 → 过滤异常 key",
  "手段优先级：AQE 自动处理（3.0+ 默认已开，先确认是否生效）→ 隔离大 key → salting 加盐 → 广播绕过 → 过滤异常 key")

# ---------- L7-9 [66] ----------
E(66, "examples",
  "旋钮是最后一道工序；开了 AQE 记得以 UI 的实\ufffd\ufffd\ufffd执行图为准，而不是静态 explain。",
  "旋钮是最后一道工序；AQE 自 3.2+ 默认开启，记得以 UI 的实际执行图为准，而不是静态 explain。")

E(66, "explanation",
  "   - **调旋钮**：shuffle 分区数（第 4 课）、开 AQE（第 6 课）；",
  "   - **调旋钮**：shuffle 分区数（第 4 课）、确认 AQE 效果（第 6 课）；")

# ---------- key_points 追加（list 元素级操作，不走字符串替换）----------
# (lesson_id, 定位用的既有关键点原文, 追加的新条目)
KP_APPEND = [
    (61, "并行上限是集群核数，分区再多也开不出更多并行",
         "⚠️ Spark 3.2+ 默认开启 AQE：本参数只是初始分区数（上界），运行时会被动态合并（第 6 课）"),
    (63, "不是万能药：修不了「读太多」，具体开关配置以实际版本为准",
         "⚠️ AQE 自 Spark 3.2.0 起默认开启（三大能力自 3.0）；3.x 上通常是「确认它是否生效」而非「打开它」"),
]

# ============ 题库（改解析，不动 correct_index）============
QUIZ_EDITS = [
    (646, "复用 L5：内存放不下就 spill，磁盘 I/O 比内存慢几个数量级。",
          "复用 L5：内存放不下就 spill；磁盘 I/O 通常比内存慢 1~2 个数量级。"),
    (650, "默认值是「能跑起来」的起点，不是「跑得快」的保证。",
          "默认值是「能跑起来」的起点，不是「跑得快」的保证。另外注意：Spark 3.2+ 默认开启 AQE 时，它只是初始分区数（上界），运行时会被按真实数据量合并。"),
    (666, "这正是 L6 第 6 课「估计会误判」的兜底方案。",
          "这正是 L6 第 6 课「估计会误判」的兜底方案。版本事实：AQE 自 Spark 3.2.0 起默认开启，所以在较新的 Spark 上通常不需要手动打开它。"),
    (674, "AQE 不替代「少读少传少算」，它是在此之上的运行时增强。",
          "AQE 不替代「少读少传少算」，它是在此之上的运行时增强；且自 Spark 3.2.0 起默认开启，手动调参与它不是二选一的关系。"),
    (684, "按代价从低到高推进：AQE → 隔离大 key → 加盐 → 广播绕过 → 过滤异常 key。",
          "按代价从低到高推进：AQE → 隔离大 key → 加盐 → 广播绕过 → 过滤异常 key。其中 AQE 的倾斜处理（skewJoin.enabled）自 Spark 3.0 起默认开启，所以第一步是确认它有没有生效，而不是先去打开它。"),
]


def replace_in_content(d, old, new):
    """在整个 content 字典里做字符串替换（覆盖 str / list[str] / list[dict]）。
    返回替换命中次数。"""
    n = 0

    def walk(obj):
        nonlocal n
        if isinstance(obj, str):
            if old in obj:
                n += obj.count(old)
                return obj.replace(old, new)
            return obj
        if isinstance(obj, list):
            return [walk(x) for x in obj]
        if isinstance(obj, dict):
            return {k: walk(v) for k, v in obj.items()}
        return obj

    for k in list(d.keys()):
        d[k] = walk(d[k])
    return n


def main():
    apply = "--apply" in sys.argv
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    print("=== 课文修复（字符串替换）===")
    per_lesson = {}
    for lid, field, old, new in EDITS:
        per_lesson.setdefault(lid, []).append((field, old, new))

    for lid in sorted(per_lesson):
        cur.execute("select title, content from lessons where id=?", (lid,))
        row = cur.fetchone()
        if not row:
            print(f"  !! lesson {lid} 不存在")
            continue
        title, raw = row
        d = json.loads(raw)
        hit = miss = 0
        for field, old, new in per_lesson[lid]:
            c = replace_in_content(d, old, new)
            if c:
                hit += 1
            else:
                miss += 1
                print(f"  [SKIP·可能已应用] [{lid}] {old[:40]}...")
        if apply and hit:
            cur.execute("update lessons set content=? where id=?",
                        (json.dumps(d, ensure_ascii=False), lid))
        print(f"  [{lid}] {title}: 命中 {hit} / 跳过 {miss}")

    print("\n=== key_points 追加 ===")
    kp_by_lesson = {}
    for lid, anchor, new_kp in KP_APPEND:
        kp_by_lesson.setdefault(lid, []).append((anchor, new_kp))
    for lid in sorted(kp_by_lesson):
        cur.execute("select content from lessons where id=?", (lid,))
        d = json.loads(cur.fetchone()[0])
        kps = d.get("key_points") or []
        for anchor, new_kp in kp_by_lesson[lid]:
            if new_kp in kps:
                print(f"  [SKIP·已存在] [{lid}] {new_kp[:34]}...")
                continue
            if anchor in kps:
                kps.insert(kps.index(anchor) + 1, new_kp)
                print(f"  [{lid}] 已追加: {new_kp[:40]}...")
            else:
                kps.append(new_kp)
                print(f"  [{lid}] 锚点未命中，追加到末尾: {new_kp[:34]}...")
        d["key_points"] = kps
        if apply:
            cur.execute("update lessons set content=? where id=?",
                        (json.dumps(d, ensure_ascii=False), lid))

    print("\n=== 题库修复（只改解析）===")
    for qid, old, new in QUIZ_EDITS:
        cur.execute("select prompt, explanation from quizzes where id=?", (qid,))
        row = cur.fetchone()
        if not row:
            print(f"  !! quiz {qid} 不存在")
            continue
        prompt, exp = row
        if old in (exp or ""):
            if apply:
                cur.execute("update quizzes set explanation=? where id=?",
                            ((exp or "").replace(old, new), qid))
            print(f"  [q{qid}] 解析已更新 | {prompt[:34]}")
        else:
            print(f"  [SKIP·可能已应用] q{qid}")

    if apply:
        conn.commit()
        print("\n已提交写入。")
    else:
        print("\n[DRY-RUN] 未写入。加 --apply 生效。")
    conn.close()


if __name__ == "__main__":
    main()
