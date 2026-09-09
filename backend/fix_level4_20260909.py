# -*- coding: utf-8 -*-
"""Level 4 课文技术修复脚本（2026-09-09）

依据《Spark Quest Level 4 全面技术审查报告（2026-09-09）》落地：
  P0  *(N) = codegen stage 编号（非融合算子数）
  P1  formatted 3.0+ / join 非必宽依赖 / groupBy 非必 Shuffle /
      repartition 示例 Stage 数 / Action≠恰好一个 Job / Stage 非必然串行
  P2  三个错误示例 / UDF 因果 / 等价改写边界 / 容错表述 / Stage 公式 / 列裁剪
  P3  AQE 版本提示 / FileScan 不带 * / codegen 版本 / 五种 explain 模式 / Tungsten 重定义

用法：
  python fix_level4_20260909.py --lessons          # 修复 9 课课文
  python fix_level4_20260909.py --verify           # 关键词扫描 + 完整性检查
"""

import json
import sqlite3
import sys
from pathlib import Path

DB = Path(__file__).resolve().parent / "spark_quest.db"
LEVEL_ORDER = 4

# ---------------------------------------------------------------------------
# 一、整字段重写（用于改动过大的字段）
# ---------------------------------------------------------------------------
LESSON_SETS: dict[int, dict] = {
    # ---------------- L4-6 WholeStageCodegen 与 Tungsten（P0 重灾区） --------
    36: {
        "explanation": """【先用人话理解】

普通流水线每道工序都是独立工位：上一道算完，把行交给下一道，下一道再处理——每道工序之间都有一次「函数调用 + 中间行交接」的开销（Spark 里这叫 Volcano / iterator 模型）。Spark 有个绝活：把一段可以连续执行的算子流水线**生成 Java 代码并编译执行**，让它们在同一份生成的代码里连续加工，省掉中间大部分交接损耗。这就是 WholeStageCodegen。

【一个直观的心智模型】

- 普通流水线：每工位单独开关、逐件交接（每次交接都是一次虚函数调用 + 中间行的传递）。
- WholeStageCodegen：Spark 把一段连续的算子流水线生成 Java 代码并编译执行，让它们在同一份生成代码里连续加工。
- Tungsten = Spark 为提高 CPU / 内存效率而做的一整套底层执行优化方向（紧凑二进制内存表示 + cache 感知算法 + **代码生成**）。注意：**WholeStageCodegen 本身就是 Tungsten 的一部分**，不是「另一个用到了 Tungsten 格式的特性」。

⚠️ 比喻的边界（很重要）：
① codegen **不是全融合**：遇到 Exchange（Shuffle）边界，连续的代码生成必然被打断——因为数据要跨节点重分布，无法在同一段本地生成代码里连续跑。Exchange 是 Stage 边界，也是融合的「断点」。此外，不支持 codegen 的算子/表达式（例如 Python UDF）也会打断它——这也是 UDF 性能开销的重要来源之一。
② 不适用 WholeStageCodegen 的部分，会以传统的**逐算子 iterator / Volcano 方式**执行（**不是「解释执行」**——Spark 没有解释器，只是走回归常的迭代器模型）。
③ 计划里的 `*(N)` 是 **codegen stage 的编号**，不是「融合了几个算子」，也不是「第 N 个 Stage」。同一个 codegen stage 里的每个算子都带**相同**的 `*(N)`。
④ ⚠️ 版本提示：Spark 3.2+ 默认开启 Adaptive Query Execution（AQE）。开启 AQE 时 `explain()` 可能显示 `AdaptiveSparkPlan isFinalPlan=false`，你看到的是**初始计划**、且**看不到 `*(N)`**（代码生成折叠还没发生）。想看本课这种经典输出，先 `spark.conf.set("spark.sql.adaptive.enabled", "false")`；要看最终实际执行的计划，去 Spark UI 的 SQL 详情页。
⑤ 内存布局、堆外、UnsafeRow 字节级细节是 Level 7 性能调优的内容，本课只把 Tungsten 当「底层执行优化方向」复用，不深挖。

【正式的技术定义】

WholeStageCodegen（全阶段代码生成）是 Project Tungsten 中「代码生成」这一支的产物：Spark 把一段可以连续 codegen 的物理算子流水线（如 Scan+Filter+Project+Aggregate）生成 Java 代码并编译执行，以减少逐算子调用以及中间对象/数据转换带来的开销，数据在算子间以紧凑的二进制行格式流转。计划中，属于同一个 codegen stage 的每个算子都会被标上相同的 `*(N)`，**N 是 codegen stage 的编号（codegenStageId），不是算子个数**。Exchange 会切断连续的代码生成。

【写下代码后，Spark 内部发生了什么】

你写 `df.select('city', 'amount').filter(df.amount > 0).groupBy('city').count()`，这些算子会被 `CollapseCodegenStages` 折叠成若干个 codegen stage：数据在生成的代码里连续地被过滤、投影、聚合，中间不再逐算子交接待处理的行。一旦中间出现 Exchange（groupBy 的 Shuffle），连续的代码生成在此断开，Exchange 之后的算子另起一个新的 codegen stage。注意：**新 stage 的编号会继续递增，不会回到 1。**""",
        "examples": [
            {
                "title": "真实计划长什么样（重点）",
                "code": "df = spark.read.parquet('sales')\ndf.filter(df.amount > 0).groupBy('city').sum('amount').explain()\n# 典型输出（Spark 3.x，已关闭 AQE）：\n# *(3) HashAggregate(keys=[city#10], functions=[sum(amount#11)])\n# +- Exchange hashpartitioning(city#10, 200)\n#    +- *(2) HashAggregate(keys=[city#10], functions=[partial_sum(amount#11)])\n#       +- *(2) Project [city#10, amount#11]\n#          +- *(2) Filter (isnotnull(amount#11) AND (amount#11 > 0))\n#             +- *(1) ColumnarToRow\n#                +- FileScan parquet [city#10, amount#11]",
                "note": "怎么读：*(3) 是 codegen stage 3 的编号（并不代表 3 个算子）；三个 *(2) 说明 Filter / Project / HashAggregate 属于同一个 codegen stage（这个 stage 融合了 3 个算子）；Exchange 没有星号，它是 Shuffle，也是 codegen 断点；FileScan parquet 不带 *(N) 同样正常——Spark 3.x 默认开启 Parquet 向量化读取，FileScan 输出 ColumnarBatch，行式 codegen 从 ColumnarToRow 才开始。",
            },
            {
                "title": "数「不同 N 的个数」= codegen stage 数",
                "code": "# 接上例：出现了 *(1) / *(2) / *(3) 三种编号\n# => 这条计划里共有 3 个 codegen stage\n# 数「同一个 N 出现几次」= 该 stage 融合了几个算子\n# => *(2) 出现 3 次，说明 stage 2 里融合了 3 个算子",
                "note": "这两种数法才可靠；直接把 N 当成算子数是错的（*(3) 下面只有 1 个算子，*(2) 下面却有 3 个）。",
            },
            {
                "title": "codegen 的断点",
                "code": "df.groupBy('city').count().explain()\n# Exchange 之后不会出现 *(1)，而是出现更大的编号",
                "note": "Exchange（Shuffle）会切断 codegen；Python UDF、部分不支持的表达式也会切断它。被切断的部分走传统的逐算子 iterator 方式执行，而不是「解释执行」。",
            },
            {
                "title": "explain(mode='codegen') 直接看生成的代码",
                "code": "df.filter(df.amount > 0).groupBy('city').count().explain(mode='codegen')\n# 直接打印 Spark 生成的 Java 代码（Spark 3.0+）",
                "note": "这是理解「融合」最直观的工具：生成的代码按 codegen stage 分段，每一段正好对应一个 WholeStageCodegen。",
            },
        ],
        "key_points": [
            "WholeStageCodegen：把一段连续的算子流水线生成 Java 代码并编译执行，减少逐算子调用与中间数据转换开销",
            "*(N) 的 N = codegen stage 编号；同编号 = 同 stage，数「同编号行数」= 算子数，数「不同编号个数」= codegen stage 数",
            "Exchange（Shuffle）切断 codegen；Python UDF、不支持的表达式也会切断（回退为逐算子 iterator 执行）",
            "编号在一个查询内从 1 递增，Exchange 之后继续递增，不会回到 1",
            "Tungsten = 紧凑二进制内存表示 + cache 感知算法 + 代码生成；WholeStageCodegen 属于其中的代码生成部分，内存细节留 Level 7",
        ],
        "common_mistakes": [
            {
                "mistake": "把 *(N) 的 N 当成「融合了几个算子」。",
                "why": "N 是 codegen stage 的编号（codegenStageId），与算子个数无关。",
                "fix": "数「相同 N 出现几次」才是该 stage 的算子数；数「有几种不同的 N」才是 codegen stage 数。",
            },
            {
                "mistake": "以为所有算子都能无限融合，或以为 Exchange 之后编号会回到 1。",
                "why": "Exchange 必断、Python UDF 也会断；编号在整个查询内只增不重置。",
                "fix": "理解融合有边界；看到 Shuffle 之后的编号更大是正常的。",
            },
            {
                "mistake": "看到 FileScan 不带 *(N) 就以为「这里没做 codegen」。",
                "why": "Spark 3.x 的 Parquet 向量化读取输出 ColumnarBatch，codegen 从 ColumnarToRow 开始，FileScan 本就不带编号。",
                "fix": "看 ColumnarToRow 及其之上的算子有没有编号。",
            },
            {
                "mistake": "把 Tungsten 只当成「紧凑二进制格式」。",
                "why": "Tungsten 是包含内存表示、cache 感知算法与代码生成的一整套方向，WholeStageCodegen 本身就是其中一支。",
                "fix": "记住 codegen ⊂ Tungsten，不是两套并列的东西。",
            },
        ],
    },
}

# ---------------------------------------------------------------------------
# 二、局部替换（old -> new），每个 old 必须命中，否则脚本中止
# ---------------------------------------------------------------------------
LESSON_SUBS: dict[int, list[tuple[str, str]]] = {
    # ---------------- L4-1 ----------------
    31: [
        (
            "当你调用 `explain()`，Spark 会把「经过 Catalyst 四阶段（解析→分析→优化→物理化）」之后的算子树打印出来",
            "当你调用 `explain()`，Spark 会先把 Catalyst 四阶段（解析→分析→优化→物理化）全部走完，然后默认只把**最终物理计划**打印出来（想看前三段要用 `explain(True)`，下一课讲）",
        ),
    ],
    # ---------------- L4-2 ----------------
    32: [
        (
            "df.select('city').filter(df.amount > 0).explain(True)",
            "df.select('city', 'amount').filter(df.amount > 0).explain(True)",
        ),
        (
            "在 Optimized 段能看到 Project/Filter 被下推、列被裁剪，逻辑上「读更少」。",
            "在 Optimized 段能看到 Filter 被下推到 Scan 附近、未用到的列被裁掉（Scan 的 ReadSchema 里只保留 city/amount）。",
        ),
    ],
    # ---------------- L4-3 ----------------
    33: [
        (
            "② `mode=\"formatted\"` 需要 Spark 2.3+（老版本没有这个模式）；现代 Spark 都支持。",
            "② `mode=\"formatted\"` 需要 **Spark 3.0+**（老版本没有这个模式）。⚠️ 别把两个版本号记混：**`*(N)` 编号是 Spark 2.3 引入的（SPARK-23032），formatted 模式是 Spark 3.0 引入的（SPARK-27395）**。",
        ),
        (
            "`DataFrame.explain()` 打印执行计划。`explain()`（无参）默认打印 Physical Plan；`explain(True)` 或 `explain(\"extended\")` 打印 Parsed/Analyzed/Optimized/Physical 四段；`explain(\"formatted\")` 以缩进树状结构打印（Spark 2.3+），更易读。它是诊断 API，不触发 Action。",
            "`DataFrame.explain()` 打印执行计划。Spark 3.0+ 共支持五种模式：`simple`（默认，仅物理计划）、`extended`（四段全貌）、`codegen`（打印生成的 Java 代码）、`cost`（逻辑计划 + 统计量）、`formatted`（缩进树状 + 节点详情）。`explain()` 无参 ≡ `simple`；`explain(True)` ≡ `explain(\"extended\")`；`explain(\"formatted\")` 以缩进树状结构打印（**Spark 3.0+**），最易读。它是诊断 API，不触发 Action。",
        ),
        (
            "explain(mode='formatted') 缩进树状、易读，需 Spark 2.3+",
            "explain(mode='formatted') 缩进树状、易读，需 Spark 3.0+",
        ),
        (
            "在老 Spark（<2.3）用 mode='formatted' 报错。",
            "在老 Spark（<3.0）用 mode='formatted' 报错。",
        ),
        (
            "该模式 2.3 才引入。",
            "该模式 3.0 才引入（SPARK-27395）；`*(N)` 编号才是 2.3 引入的（SPARK-23032），别混。",
        ),
        (
            "真正执行要 show/count/write 等 Action",
            "真正执行要 show/count/write 等 Action\nSpark 3.0+ 共五种模式：simple / extended / codegen / cost / formatted；`explain(mode=\"codegen\")` 能直接看生成的 Java 代码，是理解 WholeStageCodegen 最直观的工具",
        ),
        (
            "③ `explain(True)` 就是 `explain(\"extended\")` 的快捷写法，二者等价；它多打出的 Parsed/Analyzed/Optimized 三段是「规划过程」，不是「额外干活」。",
            "③ `explain(True)` 就是 `explain(\"extended\")` 的快捷写法，二者等价；它多打出的 Parsed/Analyzed/Optimized 三段是「规划过程」，不是「额外干活」。\n④ ⚠️ 版本提示：Spark 3.2+ 默认开启 Adaptive Query Execution（AQE）。开启 AQE 时 `explain()` 可能显示 `AdaptiveSparkPlan isFinalPlan=false`，你看到的是**初始计划**，运行过程中 Spark 会根据运行时统计信息调整它（比如把 sort-merge join 改成 broadcast join、合并 shuffle 分区）。想看本课这种经典输出，可先 `spark.conf.set(\"spark.sql.adaptive.enabled\", \"false\")`；想看最终实际执行的计划，去 Spark UI 的 SQL 详情页。",
        ),
        (
            "执行计划要「调出来」才能看，调它的扳机就是 `explain()`。但它有三个「档位」：简版（默认）、全四段版（True）、树状可读版（formatted）。",
            "执行计划要「调出来」才能看，调它的扳机就是 `explain()`。它有好几个「档位」：简版（默认）、全四段版（True）、树状可读版（formatted），以及能直接看生成代码的 codegen 版。",
        ),
    ],
    # ---------------- L4-4 ----------------
    34: [
        (
            "① Exchange 节点 = 必 Shuffle：数据要序列化、走网络、反序列化，重新按 key 分布。它是性能成本的主要来源之一，看到它就心里有数「这里要花钱」。",
            "① Exchange 节点 = 一次 Shuffle：数据要序列化、走网络、反序列化，重新按 key 分布。它是性能成本的主要来源之一，看到它就心里有数「这里要花钱」。（出现 Exchange 就一定有 Shuffle；但反过来，不是所有聚合/join 都必然产生 Exchange，见本课 key_points。）",
        ),
        (
            "② `*(N)` 是 Stage 内算子融合标记（WholeStageCodegen，下节课讲），表示相邻 N 个算子被融合成一个 Java 方法——不是「第 N 阶段」。",
            "② `*(N)` 中的 N 是 **codegen stage 的编号**（WholeStageCodegen，下节课细讲），不是「融合了几个算子」，也不是「第 N 个 Stage」。同一个 codegen stage 里的每个算子都带**相同**的 `*(N)`：想数「这个 stage 融合了几个算子」要数**相同 N 的行数**，想数「有几个 codegen stage」要数**不同 N 的个数**。N 从 1 开始递增，遇到 Exchange 也不会归零。",
        ),
        (
            "`*(N)` 前缀表示 WholeStageCodegen 融合的算子数。",
            "`*(N)` 前缀里的 N 是 codegen stage 的编号（codegenStageId），带相同编号的算子属于同一个 WholeStageCodegen stage。",
        ),
        (
            "Exchange 节点 = 必 Shuffle（序列化+网络+反序列化开销），是性能重点信号",
            "Exchange 节点 = 一次 Shuffle（序列化+网络+反序列化开销），是性能重点信号",
        ),
        (
            "*(N) 是 Stage 内算子融合标记（WholeStageCodegen），不是阶段编号",
            "*(N) 的 N 是 codegen stage 编号；同编号 = 同 stage，数「同编号行数」才知道融合了几算子",
        ),
        (
            "读懂算子树 = 能指出「数据走了哪些弯路、哪里 Shuffle」",
            "读懂算子树 = 能指出「数据走了哪些弯路、哪里 Shuffle」\n但 Exchange 并非必然出现：groupBy/orderBy/distinct 通常有，上游已按 key 分区时可省略；broadcast join 不产生 ShuffleExchange",
        ),
        (
            "任何 groupBy/distinct/orderBy/join 都会引入 Exchange，认准它就是认准 Shuffle。",
            "groupBy / distinct / orderBy 与 shuffle-based join（sort-merge、shuffle-hash）通常会引入 Exchange；但 broadcast join 不产生 ShuffleExchange，上游已按该 key 分区的聚合也可能省掉 Exchange。",
        ),
        (
            "df.select('city').filter(df.amount > 0).explain()",
            "df.select('city', 'amount').filter(df.amount > 0).explain()",
        ),
        (
            "把 *(N) 当成「第 N 个 Stage」。",
            "把 *(N) 的 N 当成「融合的算子数」或「第 N 个 Stage」。",
        ),
        (
            "它是融合算子数标记。",
            "N 是 codegen stage 的编号，与算子个数无关；Shuffle 的 Stage 又是另一套编号。",
        ),
        (
            "Stage 由 Exchange 切分，不是 *(N)。",
            "Stage 由 Exchange 切分；*(N) 是 codegen stage 编号——数同编号行数才是算子数，数不同编号个数才是 codegen stage 数。",
        ),
    ],
    # ---------------- L4-5 ----------------
    35: [
        (
            "① 优化是「等价」的：结果和没优化完全一致，只是更省。它不是魔法，不改语义。",
            "① 优化是「等价」的：对**确定性**表达式，改写后语义与未优化时一致，只是更省。它不是魔法，不改语义。",
        ),
        (
            "② 优化器非神仙：遇到 UDF（L3 讲的「外聘手艺人」）或复杂嵌套，它「看不懂」内部逻辑，下推/裁剪就失效——所以能不用 UDF 就不用（也呼应 L3 的 L7 伏笔）。",
            "② 优化器非神仙：过滤条件如果**依赖 UDF 的输出值**，就**不能**被移动到 UDF 计算之前，自然也推不到 Scan 端——这不是「优化器看不懂 UDF」，而是**表达式的数据依赖顺序决定的**。列裁剪仍然会发生，只是 UDF 依赖的那些列必须保留。所以能不用 UDF 就不用（也呼应 L3 的 L7 伏笔）。",
        ),
        (
            "③ 下推能否真正发生，**取决于数据源**：Parquet 这类列式存储能配合做列裁剪/谓词下推；普通 csv 做不到按列跳过，下推收益有限。",
            "③ 下推/裁剪**真正能省下多少，取决于数据源**：Parquet/ORC 这类列式存储能配合做列裁剪/谓词下推，真正跳过不需要的列数据；普通 csv/json 是行式文本，做不到按列跳过（整行仍要读进来解析），下推收益有限。\n④ 「等价」也有边界：非确定性表达式（如 `rand()`、`current_timestamp()`、`monotonically_increasing_id()`）不会被随意折叠或重排——否则同一条查询两次跑出来的结果会不一样。别把「等价改写」理解成「任何表达式都能随便挪」。",
        ),
        (
            "优化是「等价改写」，结果不变只更省",
            "优化是「等价改写」：对确定性表达式语义不变、只更省（非确定性表达式除外）",
        ),
        (
            "UDF/复杂嵌套下推不了；下推收益看数据源（Parquet 强、csv 弱）",
            "含 UDF 的过滤条件无法下推（依赖顺序不允许），UDF 依赖的列仍会保留；下推收益看数据源（Parquet 强、csv 弱）",
        ),
        (
            "Catalyst 看不懂 UDF 内部。",
            "过滤条件依赖 UDF 的输出值，顺序上必须先算 UDF 才能过滤，推不到数据源端。",
        ),
        (
            "你没选的列，优化器在 Scan 就裁掉，少读少搬。",
            "你没选的列不会出现在 Scan 的 ReadSchema / 输出中；Parquet/ORC 这类列式格式能真正跳过这些列的数据，csv/json 这类行式文件仍要整行读取解析（省的是内存与后续搬运，不是 IO）。",
        ),
    ],
    # ---------------- L4-6（整字段已重写，这里只改 problem） ----------------
    36: [
        (
            "计划里的 *(N) 是什么？为什么相邻算子能被「焊成一台机器」？为什么 Shuffle 会打断这种融合？Tungsten 又是什么角色？",
            "计划里的 *(N) 到底是什么编号？为什么相邻的算子能被生成到同一段代码里？为什么 Shuffle 会打断这种融合？Tungsten 又是什么角色？",
        ),
    ],
    # ---------------- L4-7 ----------------
    37: [
        (
            "① 窄依赖失败，只需重算那个**局部**分区，恢复便宜（血缘短、数据就在本地）。",
            "① 窄依赖失败，通常只需沿本地依赖链重算受影响的分区（不一定只有一个，但都在本地/局部），恢复便宜。",
        ),
        (
            "② 宽依赖失败，要重算**整个上游重排**——因为下游依赖「全局按 key 汇聚」，上游任何分区丢了都得整体重算，贵。",
            "② 宽依赖失败，恢复成本通常明显更高：Shuffle 输出丢失时，可能需要重新执行相关的上游 map task，而不像窄依赖那样只重算少数本地分区。（早期 RDD 论文说「上游任何分区丢失都要整体重算」，那是更保守的表述；现代 Spark 有 shuffle 文件与 External Shuffle Service，实际只重跑真正失败的那部分。）",
        ),
        (
            "③ map/filter/select 是窄；groupBy/join/orderBy/distinct 是宽（其中 groupBy 的「部分聚合」是窄+宽两阶段：本地先聚合是窄，跨节点合并是宽）。",
            "③ map/filter/select 是窄；groupBy/orderBy/distinct 和 **shuffle-based join** 是宽（其中 groupBy 的「部分聚合」是窄+宽两阶段：本地先聚合是窄，跨节点合并是宽）。但 **broadcast join 不 Shuffle，是宽依赖里最重要的例外**；`coalesce`（不 shuffle 的合并分区）也是窄。",
        ),
        (
            "如 groupBy/join/orderBy/distinct。宽依赖是 Stage 边界与容错成本的分水岭。",
            "如 groupBy/orderBy/distinct，以及 **shuffle-based join**（sort-merge join、shuffle-hash join）。**Broadcast join 是重要例外：它靠广播小表避免 Shuffle，不产生 ShuffleExchange，也不产生 Stage 边界**（Level 6 会细讲）。另外，若上游数据已满足所需分区（例如已经按该 key 分过区），groupBy 也可以省掉 Exchange。宽依赖是 Stage 边界与容错成本的分水岭。",
        ),
        (
            "宽依赖：子分区依赖父全部分区同 key 数据，必 Shuffle（groupBy/join/orderBy/distinct）",
            "宽依赖：子分区依赖父多个/全部分区的同 key 数据，需 Shuffle（groupBy/orderBy/distinct、shuffle-based join）",
        ),
        (
            "窄失败只重算局部分区（便宜）；宽失败重算整个上游重排（贵）",
            "窄失败沿本地依赖链重算受影响分区（便宜）；宽失败可能要重跑相关上游 map task（贵）\n例外：broadcast join 不 Shuffle、不切 Stage；groupBy 在上游已按该 key 分区时可省掉 Exchange",
        ),
        (
            "把 join 当窄依赖。",
            "以为 join 一定都是宽依赖。",
        ),
        (
            "join 按 key 重分布，是宽。",
            "shuffle-based join（sort-merge / shuffle-hash）按 key 重分布才是宽；broadcast join 广播小表，大表侧不重分布，没有 ShuffleExchange。",
        ),
        (
            "记住 join/聚合/排序/去重都是宽。",
            "记住「聚合/排序/去重是宽，join 要看策略」——broadcast 是例外（Level 6 细讲）。",
        ),
        (
            "# 窄：某分区丢只重算该分区\n# 宽：上游全重排，代价大\ndf.join(other, 'id').explain()   # join 也是宽依赖",
            "# 窄：沿本地依赖链重算受影响的分区\n# 宽：Shuffle 输出丢失时可能要重新执行相关上游 map task，代价更大\ndf.join(other, 'id').explain()   # 走 sort-merge 时是宽依赖；若小表被广播则是 broadcast join，没有 ShuffleExchange",
        ),
        (
            "宽依赖失败恢复贵，这是设计容错与调优时要记牢的。",
            "宽依赖的恢复成本通常更高，这是设计容错与调优时要记牢的。",
        ),
    ],
    # ---------------- L4-8 ----------------
    38: [
        (
            "- Job = 接到「出货指令」（一次 Action，如 `count()`/`show()`/`write`）。",
            "- Job = 接到「出货指令」（一次 Action，如 `count()`/`show()`/`write`；`show`/`take` 这类带 limit 的可能分多轮起多个 Job）。",
        ),
        (
            "② Stage 数 = 宽依赖数 + 1：每多一次 Shuffle 就多切一个 Stage。",
            "② 对**单条线性依赖链**，可以用「Shuffle 边界数 + 1」快速估算 Stage 数；遇到多分支 / Union / 多数据源这类 DAG 结构，要按实际依赖关系数，别硬套公式。",
        ),
        (
            "③ Job 内 Stage **顺序**执行（前一个 Stage 的 Shuffle 输出是后一个的输入），但**单个 Stage 内 Task 并行**（多个 Executor 同时干各自分区）。这是「宏观串行、微观并行」。",
            "③ Stage 按依赖关系组成 DAG：**有依赖的 Stage 必须等父 Stage 完成**（前一个 Stage 的 Shuffle 输出是后一个的输入），**没有依赖关系的 Stage 可以并行提交执行**；**单个 Stage 内 Task 并行**（多个 Executor 同时干各自分区）。简单说：依赖处串行、无依赖可并行、Stage 内 Task 并行。",
        ),
        (
            "Spark 执行层级：一个 Action 触发一个 Job；Job 的 DAG 按宽依赖（Shuffle）切分为多个 Stage（Stage 数 = 宽依赖数 + 1）；每个 Stage 按输出 RDD 的分区数切分为多个 Task（每分区一个），由 Executor 并行执行。Task 是最小执行单元。",
            "Spark 执行层级：一个 Action 通常触发一个 Job（`take`/`show` 这类带 limit 的 Action 可能多轮提交多个 Job）；Job 的 DAG 按宽依赖（Shuffle）切分为多个 Stage（单条线性链上可用「Shuffle 边界数 + 1」快速估算）；每个 Stage 按输出 RDD 的分区数切分为多个 Task（每分区一个），由 Executor 并行执行。Task 是最小执行单元。",
        ),
        (
            "`show()` 是 Action → 触发 1 个 Job。",
            "`show()` 是 Action → 通常触发 1 个 Job（底层是 `take`，数据不够时可能分多轮提交多个 Job）。",
        ),
        (
            "一次 Action = 一个 Job；Job ⊃ Stage ⊃ Task",
            "通常一次 Action = 一个 Job（take/show 可能多个）；Job ⊃ Stage ⊃ Task",
        ),
        (
            "Stage 数 = 宽依赖数 + 1（每多一次 Shuffle 多切一个）",
            "单条线性链：Stage 数 ≈ Shuffle 边界数 + 1；多分支 DAG 要按实际依赖关系数",
        ),
        (
            "Job 内 Stage 顺序执行；单 Stage 内 Task 并行（宏观串行、微观并行）",
            "Stage 按依赖 DAG 执行：有依赖的串行、无依赖的可并行；单 Stage 内 Task 并行",
        ),
        (
            "每遇到一个 Action（show/count/write）就起一个 Job；Transformation 不触发。",
            "通常每遇到一个 Action（show/count/write）就起一个 Job；Transformation 不触发。注意 show() 底层是 take，数据不够时可能分多轮、产生多个 Job。",
        ),
        (
            "计划里 Exchange 的个数 + 1 = Stage 数。",
            "单条线性链上：Exchange 个数 + 1 = Stage 数。多分支 / Union 的计划要按 DAG 数，不能套这个公式。",
        ),
        (
            "df = spark.read.parquet('sales').repartition(200)\ndf.groupBy('city').count().show()\n# 每 Stage 约 200 个 Task",
            "df = spark.read.parquet('sales').repartition(200)\ndf.groupBy('city').count().show()\n# 注意：repartition(200) 自己就是一次 Exchange（RoundRobinPartitioning）\n# 再叠加 groupBy 的 Exchange（hashpartitioning）\n# => 一共 2 个 Shuffle 边界、3 个 Stage",
        ),
        (
            "Task 数由该 Stage 分区数决定，即并行度（调优留 L5）。",
            "别漏数 repartition：它自身也算一次 Shuffle。Task 数由该 Stage 分区数决定，即并行度（调优留 L5）。",
        ),
        (
            "几个 Action 就几个 Job。",
            "通常几个 Action 就几个 Job。",
        ),
        (
            "数 Action 数 = Job 数。",
            "数 Action 数 ≈ Job 数；show/take 可能因分批而多出几个。",
        ),
        (
            "以为 Stage 内也并行出多个 Stage。",
            "以为一个 Job 里的 Stage 只能一个接一个串行。",
        ),
        (
            "Stage 间是顺序的，只有 Task 层并行。",
            "有依赖的才需要等；没有依赖关系的 Stage 可以并行提交。",
        ),
        (
            "区分「Stage 顺序」与「Task 并行」。",
            "区分「依赖导致的串行」与「无依赖的并行」；真正的并行主力在 Task 层。",
        ),
    ],
    # ---------------- L4-9 ----------------
    39: [
        (
            "3. 最后找 ***(N)** 融合标记与下推/裁剪痕迹——看 Catalyst 帮你省了什么。",
            "3. 最后看 ***(N)** 编号与下推/裁剪痕迹——数「有几种不同的 N」= codegen stage 数，数「同一个 N 出现几次」= 该 stage 融合了几个算子。",
        ),
        (
            "据 *(N) 与 Optimized 段判定 WholeStageCodegen 融合与 Catalyst 优化（谓词下推/列裁剪/常量折叠）。",
            "据 *(N) 判定 WholeStageCodegen 的 codegen stage 划分（N 是编号不是算子数），并结合 Optimized 段判定 Catalyst 优化（谓词下推/列裁剪/常量折叠）。",
        ),
        (
            "读图三步：找 Exchange（Shuffle）→ 数 Stage（Exchange+1）→ 找 *(N) 融合与下推/裁剪",
            "读图三步：找 Exchange（Shuffle）→ 数 Stage（单条线性链：Exchange 数 + 1）→ 看 *(N) 编号（数「不同 N 的个数」= codegen stage 数）与下推/裁剪",
        ),
        (
            "数 Stage 时漏算「初始 Stage」。",
            "数 Stage 时漏算「初始 Stage」，或拿公式去套多分支计划。",
        ),
        (
            "Stage 数 = Exchange 数 + 1。",
            "单条线性链才是 Exchange 数 + 1；多分支 DAG 要按依赖关系数。",
        ),
        (
            "从 1 开始加。",
            "先确认是不是线性链，再决定用不用这个公式。",
        ),
        (
            "③ `explain()` 不触发执行，所以这套「读图」练习随时可做、零成本。",
            "③ `explain()` 不触发执行，所以这套「读图」练习随时可做、零成本。\n④ ⚠️ Spark 3.2+ 默认开启 AQE：`explain()` 看到的是**初始计划**（可能显示 `AdaptiveSparkPlan isFinalPlan=false`），运行时可能被调整；要确认「实际怎么跑」，请结合 Spark UI 的 SQL 详情页。",
        ),
    ],
}

# ---------------------------------------------------------------------------
# 三、关键词扫描（修复后不应再出现的语义）
# ---------------------------------------------------------------------------
BANNED_PATTERNS = [
    "融合的算子数",
    "标记融合的算子数",
    "融合算子数",
    "重新从 1 计数",
    "重新从 1 开始计数",
    "重新从1",
    "必 Shuffle",
    "必shuffle",
    "必然 Shuffle",
    "必然产生 Exchange",
    "join 必",
    "一定是宽依赖",
    "都是宽依赖",
    "一个 Action 触发一个 Job",
    "一次 Action = 一个 Job",
    "Stage 顺序执行",
    "宏观串行",
    "Catalyst 看不懂",
    "根本不进入 Scan",
    "根本不会进入 Scan",
    "Tungsten = 紧凑二进制零件标准",
    "紧凑零件标准",
    "解释执行",
    "手写的 Java 方法",
    "全程不拆成对象",
    "Spark 2.3+",
    "2.3+",
]

# 允许出现的新表述（用于排除误报）
ALLOWED_CONTEXT = [
    "2.3 引入",
    "2.3 才引入",
    "SPARK-23032",
    "不是「解释执行」",
    "而不是「解释执行」",
]


def walk_replace(obj, pairs, stats):
    if isinstance(obj, str):
        s = obj
        for old, new in pairs:
            if old in s:
                stats[old] = stats.get(old, 0) + 1
                s = s.replace(old, new)
        return s
    if isinstance(obj, list):
        return [walk_replace(x, pairs, stats) for x in obj]
    if isinstance(obj, dict):
        return {k: walk_replace(v, pairs, stats) for k, v in obj.items()}
    return obj


def do_lessons() -> None:
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT id FROM course_levels WHERE order_index=?", (LEVEL_ORDER,))
    level_id = cur.fetchone()[0]
    cur.execute(
        "SELECT id, title, content FROM lessons WHERE level_id=? ORDER BY order_index",
        (level_id,),
    )
    lessons = cur.fetchall()
    print(f"Level 4 lessons: {len(lessons)}")

    for lid, title, raw in lessons:
        content = json.loads(raw)
        changed = False

        # 1) 整字段重写
        for field, value in LESSON_SETS.get(lid, {}).items():
            if field not in content:
                raise SystemExit(f"[FAIL] lesson {lid} 缺少字段 {field}")
            content[field] = value
            changed = True

        # 2) 局部替换
        pairs = LESSON_SUBS.get(lid, [])
        if pairs:
            stats: dict[str, int] = {}
            content = walk_replace(content, pairs, stats)
            missing = [p[0] for p in pairs if p[0] not in stats]
            if missing:
                for m in missing:
                    print(f"[FAIL] lesson {lid} ({title}) 未命中:\n    {m!r}")
                raise SystemExit("中止：存在未命中的替换，请核对原文")
            changed = True

        if changed:
            cur.execute(
                "UPDATE lessons SET content=? WHERE id=?",
                (json.dumps(content, ensure_ascii=False), lid),
            )
            print(f"  updated lesson {lid}: {title}")

    conn.commit()
    conn.close()
    print("[OK] lessons written to DB")


def do_verify() -> None:
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT id FROM course_levels WHERE order_index=?", (LEVEL_ORDER,))
    level_id = cur.fetchone()[0]

    # 完整性
    cur.execute("SELECT COUNT(*) FROM lessons WHERE level_id=?", (level_id,))
    n_lessons = cur.fetchone()[0]
    cur.execute(
        "SELECT COUNT(*) FROM quizzes q JOIN lessons l ON l.id=q.lesson_id WHERE l.level_id=?",
        (level_id,),
    )
    n_quiz = cur.fetchone()[0]
    cur.execute(
        "SELECT COUNT(*) FROM quizzes q LEFT JOIN lessons l ON l.id=q.lesson_id WHERE l.id IS NULL"
    )
    orphan = cur.fetchone()[0]
    cur.execute(
        "SELECT lesson_id, COUNT(*) FROM quizzes WHERE lesson_id IN "
        "(SELECT id FROM lessons WHERE level_id=?) GROUP BY lesson_id HAVING COUNT(*)<>10",
        (level_id,),
    )
    bad_lessons = cur.fetchall()
    cur.execute(
        "SELECT lesson_id, prompt, COUNT(*) c FROM quizzes WHERE lesson_id IN "
        "(SELECT id FROM lessons WHERE level_id=?) GROUP BY lesson_id, prompt HAVING c>1",
        (level_id,),
    )
    dup = cur.fetchall()

    print(f"lessons={n_lessons} (expect 9)")
    print(f"quizzes={n_quiz} (expect 90)")
    print(f"orphan quizzes (whole DB)={orphan} (expect 0)")
    print(f"lessons with !=10 quizzes: {bad_lessons} (expect [])")
    print(f"duplicate prompts in L4: {dup} (expect [])")

    # 关键词扫描
    cur.execute(
        "SELECT l.id, l.title, l.content FROM lessons l WHERE l.level_id=? ORDER BY l.order_index",
        (level_id,),
    )
    hits = []
    for lid, title, raw in cur.fetchall():
        blob = raw
        for pat in BANNED_PATTERNS:
            idx = 0
            while True:
                idx = blob.find(pat, idx)
                if idx < 0:
                    break
                snippet = blob[max(0, idx - 60) : idx + len(pat) + 60]
                if not any(a in snippet for a in ALLOWED_CONTEXT):
                    hits.append((lid, title, pat, snippet.replace("\n", " ")))
                idx += len(pat)
    cur.execute(
        "SELECT q.id, q.prompt, q.options, q.explanation FROM quizzes q "
        "JOIN lessons l ON l.id=q.lesson_id WHERE l.level_id=?",
        (level_id,),
    )
    for qid, prompt, options, exp in cur.fetchall():
        blob = f"{prompt} {options} {exp}"
        for pat in BANNED_PATTERNS:
            idx = 0
            while True:
                idx = blob.find(pat, idx)
                if idx < 0:
                    break
                snippet = blob[max(0, idx - 60) : idx + len(pat) + 60]
                if not any(a in snippet for a in ALLOWED_CONTEXT):
                    hits.append((f"quiz {qid}", "", pat, snippet.replace("\n", " ")))
                idx += len(pat)

    if hits:
        print(f"\n[SCAN] {len(hits)} hit(s):")
        for h in hits:
            print(f"  - {h[0]} {h[1]} :: '{h[2]}' :: ...{h[3]}...")
    else:
        print("\n[SCAN] clean: no banned semantics left in Level 4")

    # 示例检查
    cur.execute(
        "SELECT l.id, l.title, l.content FROM lessons l WHERE l.level_id=? ORDER BY l.order_index",
        (level_id,),
    )
    bad_example = []
    for lid, title, raw in cur.fetchall():
        content = json.loads(raw)
        for ex in content.get("examples", []):
            code = ex.get("code", "")
            if "select('city')" in code.replace('"', "'") and "filter(df.amount" in code:
                bad_example.append((lid, ex.get("title"), code))
    print(f"\n[EXAMPLE] risky select/filter examples: {bad_example}")
    conn.close()


# ---------------------------------------------------------------------------
# 四、题库修复：qid -> (prompt, options, correct_index, explanation)
#     题干 / 选项 / 正确答案 / 解析 四者保持一致
# ---------------------------------------------------------------------------
QUIZ_FIXES: dict[int, tuple[str, list[str], int, str]] = {
    # ---------------- P0: *(N) ----------------
    379: (
        "计划里的 `*(N)` 中的 N 指的是什么？",
        [
            "该算子在计划树中的行号",
            "该 codegen stage 融合了 N 个算子",
            "WholeStageCodegen 的 codegen stage 编号（codegenStageId）",
            "该算子所属的第 N 个 Stage",
        ],
        2,
        "N 是 codegen stage 的编号，既不是「融合了几个算子」，也不是 Stage 编号。同一个 codegen stage 里的每个算子都会带上相同的 `*(N)`。",
    ),
    397: (
        "想知道「某个 codegen stage 里到底融合了几个物理算子」，正确的数法是？",
        [
            "直接看 N 的大小：*(3) 就是融合了 3 个算子",
            "数计划中带相同 `*(N)` 编号的算子有几行",
            "数整条计划里一共出现了几种不同的 N",
            "数 `*(N)` 前面的缩进层级",
        ],
        1,
        "N 只是 codegen stage 的编号，与算子个数无关（*(3) 下面可能只有 1 个算子，*(2) 下面可能有 3 个）。同一个 stage 里的每个算子都带相同编号，所以「数同编号的行数」才是算子数；「数不同编号的个数」是 codegen stage 数。",
    ),
    403: (
        "怎样判断一个 WholeStageCodegen stage 里包含几个物理算子？",
        [
            "看 `*(N)` 里的 N 是几：*(4) 就有 4 个",
            "统计计划中带有相同 `*(N)` 编号的算子有几行",
            "统计整条计划里出现了几种不同的 N",
            "数 Exchange 节点的个数",
        ],
        1,
        "N 是 codegen stage 的编号；同一个 stage 的每个算子都带相同编号，所以「数相同编号的行数」才是该 stage 的算子数。选项 C 数出来的是 codegen stage 的个数，是另一回事。",
    ),
    404: (
        "一次 groupBy 的 Exchange 之后，后面的算子如果出现 `*(N)`，这个 N 会怎样？",
        [
            "继续递增（不会回到 1）",
            "重新从 1 开始计数",
            "变成 `*(0)`",
            "与 Shuffle 之前的编号保持相同",
        ],
        0,
        "Exchange 会切断连续的代码生成、开启一个新的 codegen stage，但编号是在整个查询内从 1 开始递增分配的，不会归零。所以 Shuffle 之后看到的是更大的编号。",
    ),
    433: (
        "综合读图时，计划里的 `*(N)` 能告诉你什么？",
        [
            "这是第 N 个 codegen stage，带相同编号的算子属于同一段 WholeStageCodegen",
            "这个 stage 刚好融合了 N 个算子",
            "这里发生了 N 次 Shuffle",
            "这个算子处理了 N 行数据",
        ],
        0,
        "N 是 codegen stage 编号。要数「融合了几个算子」得数相同编号的行数；要数「有几个 codegen stage」得数不同编号的个数。它既不表示 Shuffle 次数，也不表示行数。",
    ),
    # ---------------- P1-1 formatted 版本 ----------------
    371: (
        "`explain(mode=\"formatted\")` 从哪个版本才开始支持？",
        [
            "Spark 2.0+",
            "Spark 2.3+",
            "Spark 3.0+",
            "没有版本要求",
        ],
        2,
        "formatted 模式由 SPARK-27395 在 Spark 3.0 引入。别和 `*(N)` 编号搞混——那个是 SPARK-23032、Spark 2.3 引入的。",
    ),
    # ---------------- P1-2 / P1-3 宽依赖与 Shuffle ----------------
    406: (
        "关于宽依赖（Shuffle Dependency），下列说法正确的是？",
        [
            "任何 join 都必然是宽依赖",
            "子分区需要来自父多个/全部分区的同 key 数据，通常需要 Shuffle；但 broadcast join 不产生 ShuffleExchange",
            "groupBy 无论上游怎么分区，都一定会插入 Exchange",
            "宽依赖不会产生 Stage 边界",
        ],
        1,
        "宽依赖的核心是「子分区要汇聚上游多个分区的相同 key」，典型如 groupBy/orderBy/distinct 与 shuffle-based join（sort-merge、shuffle-hash）。两个重要例外：broadcast join 靠广播小表避免 Shuffle；上游已按该 key 分区时 groupBy 可以省掉 Exchange。",
    ),
    411: (
        "下列算子中，通常情况下属于宽依赖（会引入 Shuffle）的是？",
        ["filter", "select", "map", "groupBy"],
        3,
        "map/filter/select 都是窄依赖（本地转换，无 Shuffle）。groupBy 需要按 key 重分布，通常会插入 Exchange——但若上游数据已按该 key 分区，这次 Exchange 也可以被省掉，所以是「通常」而非「必然」。",
    ),
    427: (
        "一段简单的 `df.groupBy('city').count()` 通常会在计划里产生几处 Exchange？",
        [
            "0，聚合不需要 Shuffle",
            "1（把相同 key 汇聚到一起需要一次 Shuffle）",
            "2",
            "3",
        ],
        1,
        "groupBy 需要把相同 key 汇聚到一起，通常会插入 1 次 Exchange。但这是「通常」不是「必然」：如果上游已经按 city 分好区（比如前面刚 repartition('city')，或读的是按 city 分桶的表），这次 Exchange 就可以省掉。",
    ),
    # ---------------- P1-5 / P1-6 Job 与 Stage ----------------
    415: (
        "关于 Action 与 Job 的对应关系，正确的是？",
        [
            "通常一个 Action 对应一个 Job",
            "一次 Action 永远恰好对应一个 Job，没有例外",
            "一个 DataFrame 程序永远只有一个 Job",
            "Action 不会触发 Job",
        ],
        0,
        "通常一个 Action 起一个 Job，count/write 是稳定的一个；但 `take`/`show` 这类带 limit 的 Action 会先试跑部分分区、行数不够再扩大范围，可能分多轮提交多个 Job。所以「Action 数 ≈ Job 数」是估算，不是绝对定律。",
    ),
    423: (
        "执行一段 `df.groupBy('city').count().show()`，通常会产生几个 Job？",
        [
            "0，show 不触发作业",
            "通常 1 个（show 是 Action），但 show 底层是 take，数据不足时可能分多轮产生多个",
            "固定 2 个",
            "有几个分区就有几个",
        ],
        1,
        "show() 是 Action，通常会触发 1 个 Job。但 show 底层是 take(21)，Spark 会先跑一部分分区、行数不够再扩大范围重跑，所以数据很少或分布特殊时，Spark UI 上可能看到 2~3 个 Job，这是正常现象而不是重复计算。",
    ),
    418: (
        "一个 Job 里的多个 Stage 是如何执行的？",
        [
            "有依赖关系的 Stage 必须等父 Stage 完成，没有依赖关系的 Stage 可以并行提交",
            "所有 Stage 一律严格串行，不可能并行",
            "所有 Stage 一律同时并行",
            "由 Stage 编号的奇偶决定",
        ],
        0,
        "Stage 之间靠依赖关系组成 DAG：前一个 Stage 的 Shuffle 输出是后一个的输入，这种必须串行；但互不依赖的分支（比如 union 的两侧、broadcast 的构建侧与探测侧）会被同时提交执行。真正的并行主力在 Task 层。",
    ),
    424: (
        "关于 Spark 的并行模型，正确的是？",
        [
            "有依赖处串行、无依赖可并行，单个 Stage 内的 Task 并行执行",
            "宏观串行、微观并行（所有 Stage 必然串行）",
            "全部串行，没有并行",
            "全部并行，Stage 之间也不等待",
        ],
        0,
        "Stage 按依赖 DAG 执行：有依赖的要等父 Stage，无依赖的可以并行提交；单个 Stage 内的 Task 由多个 Executor 并行处理各自分区。把「宏观串行」当成绝对规律，会误判多分支计划。",
    ),
    # ---------------- P2-4 容错 ----------------
    408: (
        "窄依赖失败时的恢复成本，准确的描述是？",
        [
            "只需重算那一个分区，且永远只有一个",
            "通常沿本地依赖链重算受影响的分区（可能不止一个），整体代价较低",
            "必须重跑整个 Stage 的所有 Task",
            "与宽依赖代价相同",
        ],
        1,
        "窄依赖的重算局限在本地、局部的依赖链上，所以便宜；但「受影响的分区」不一定只有一个——需要沿依赖链把缺失的祖先分区一起算回来，只是这些计算都发生在局部，不涉及跨节点 Shuffle。",
    ),
    409: (
        "宽依赖（Shuffle 依赖）失败时的恢复成本，准确的描述是？",
        [
            "和窄依赖完全一样",
            "通常更高：Shuffle 输出丢失时可能需要重新执行相关的上游 map task，而不是只重算少数本地分区",
            "一定比窄依赖便宜",
            "无法恢复，只能整个作业重跑",
        ],
        1,
        "宽依赖的恢复成本通常明显高于窄依赖——Shuffle 输出不可用时，要回到上游 map 端重跑相关任务。（早期 RDD 论文的表述是「上游任何分区丢失都要整体重算」，那更保守；现代 Spark 有 shuffle 文件与 External Shuffle Service，实际只重跑失败的那部分。）",
    ),
    414: (
        "关于窄依赖与宽依赖的容错成本，正确的是？",
        [
            "二者恢复成本一样",
            "窄依赖通常只需沿本地依赖链重算受影响分区（便宜）；宽依赖可能要重跑相关上游 map task（更贵）",
            "宽依赖更便宜，因为它有 Shuffle 文件",
            "窄依赖无法恢复",
        ],
        1,
        "恢复成本的差异是相对的：窄依赖的重算局限在本地/局部依赖链上；宽依赖一旦 Shuffle 输出不可用，就要回到上游 map 端重跑，代价明显更大。这也是调优时尽量减少不必要宽依赖的理由。",
    ),
    # ---------------- P2-5 Stage 数公式 ----------------
    416: (
        "关于「Stage 数 = Shuffle 边界数 + 1」这个算法，正确的是？",
        [
            "它是普遍公式，任何计划都能用",
            "它只适合快速估算单条线性依赖链；多分支、Union、多数据源的 DAG 要按实际依赖关系数",
            "它算的是 Task 数",
            "它只在关闭 AQE 时才成立",
        ],
        1,
        "线性链上（读 → shuffle → shuffle → 输出）用它估算很方便。但遇到多分支（例如 union 两个各自先聚合的分支），每次 Shuffle 都会各自切出 Stage，总数不等于「Shuffle 数 + 1」，必须看 DAG。",
    ),
    426: (
        "综合读图时，估算 Stage 数的正确做法是？",
        [
            "一律用「Exchange 数 + 1」",
            "先确认是不是单条线性链：是，才用「Exchange 数 + 1」估算；多分支 DAG 要按依赖关系逐个 Stage 数",
            "用 Task 数除以分区数",
            "数 Scan 节点的个数",
        ],
        1,
        "线性链可以用这个口诀；多分支、Union、多数据源的计划要按 DAG 数，硬套公式会漏算 Stage。",
    ),
    # ---------------- P2-2 / P2-3 / P2-6 Catalyst ----------------
    386: (
        "列裁剪（Column Pruning）的效果，准确的描述是？",
        [
            "过滤掉不需要的行",
            "未被上层需要的列不会出现在 Scan 的 ReadSchema / 输出中；Parquet/ORC 等列式格式能进一步跳过这些列的数据",
            "在任何存储格式下都能等量减少磁盘 IO",
            "把所有列合并成一列",
        ],
        1,
        "列裁剪让不需要的列不进入 Scan 的 ReadSchema 与输出。收益大小取决于存储格式：Parquet/ORC 这类列式格式能真正跳过不需要的列数据（连 IO 一起省）；CSV/JSON 这类行式文本仍需要读取并解析整行，省的是内存与后续搬运，不是 IO。",
    ),
    389: (
        "为什么「在 UDF 里做过滤」、指望它被下推到数据源，往往会落空？",
        [
            "因为 Catalyst 看不懂 UDF 内部逻辑，所以放弃优化",
            "因为过滤条件依赖 UDF 的输出值，表达式的数据依赖顺序不允许把它移动到 UDF 计算之前",
            "因为 UDF 只能用在 SQL 里，不能用在 DataFrame 上",
            "因为谓词下推只对 Parquet 生效",
        ],
        1,
        "关键不是「优化器看不懂」，而是依赖顺序：必须先把 UDF 的值算出来，才能判断过滤条件成不成立，所以这个 Filter 无法被推到 UDF 之前、更不可能推到 Scan 端。注意列裁剪仍然会发生，只是 UDF 依赖的那些列会被保留。",
    ),
    391: (
        "关于 Catalyst 优化器的边界，正确的是？",
        [
            "它是神仙，什么都能优化",
            "含 UDF 的过滤条件因依赖顺序无法下推；但 UDF 依赖的列仍会被保留，列裁剪并未失效",
            "它会改变计算结果",
            "它只优化 SQL，不优化 DataFrame",
        ],
        1,
        "优化器强大但有边界：过滤条件依赖 UDF 输出时，顺序上不可能上推；但列裁剪照常进行，只是必须保留 UDF 引用到的列。另外 Python UDF 还会打断 WholeStageCodegen，这是它额外的性能开销来源。",
    ),
    362: (
        "Optimized 阶段「等价改写」的前提，准确的说法是？",
        [
            "对确定性表达式保持语义不变、只更省",
            "任何表达式都能任意折叠和重排，结果一定一致",
            "必须改变语义才能提速",
            "只看写法顺序，不看表达式性质",
        ],
        0,
        "等价是有前提的：确定性表达式才能在保证语义不变的前提下改写；非确定性表达式（如 rand()、current_timestamp()、monotonically_increasing_id()）会被特殊处理，不能被随意折叠或重排，否则结果会变。",
    ),
    388: (
        "为什么我们说 Catalyst 的优化是「等价」的？",
        [
            "对确定性表达式，改写后语义与未优化时一致，只是少读少算",
            "因为它保证任何情况下结果逐位一致，包括 rand() 这类表达式",
            "因为它会先跑一遍对比结果",
            "因为它不允许改变算子顺序",
        ],
        0,
        "等价指的是「确定性表达式下语义不变」。非确定性表达式（rand()、current_timestamp() 等）不在这个保证范围内——它们不能被简单地折叠或重排，否则同一条查询两次跑出来的结果会不一样。",
    ),
}


def do_quizzes() -> None:
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT id FROM course_levels WHERE order_index=?", (LEVEL_ORDER,))
    level_id = cur.fetchone()[0]

    for qid, (prompt, options, ci, exp) in QUIZ_FIXES.items():
        cur.execute(
            "SELECT q.id, l.level_id FROM quizzes q JOIN lessons l ON l.id=q.lesson_id WHERE q.id=?",
            (qid,),
        )
        row = cur.fetchone()
        if row is None:
            raise SystemExit(f"[FAIL] quiz {qid} 不存在")
        if row[1] != level_id:
            raise SystemExit(f"[FAIL] quiz {qid} 不属于 Level 4")
        if not (0 <= ci < len(options)):
            raise SystemExit(f"[FAIL] quiz {qid} correct_index 越界")
        old = cur.execute("SELECT correct_index FROM quizzes WHERE id=?", (qid,)).fetchone()[0]
        cur.execute(
            "UPDATE quizzes SET prompt=?, options=?, correct_index=?, explanation=? WHERE id=?",
            (prompt, json.dumps(options, ensure_ascii=False), ci, exp, qid),
        )
        flag = "" if old == ci else f"  (correct_index {old} -> {ci})"
        print(f"  updated quiz {qid}{flag}")

    conn.commit()
    conn.close()
    print(f"[OK] {len(QUIZ_FIXES)} quizzes written to DB")


def do_quiz_dist() -> None:
    """检查每课正确答案位置分布，避免答案挤在同一选项。"""
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT id FROM course_levels WHERE order_index=?", (LEVEL_ORDER,))
    level_id = cur.fetchone()[0]
    cur.execute(
        "SELECT l.id, l.title, q.correct_index FROM quizzes q JOIN lessons l ON l.id=q.lesson_id "
        "WHERE l.level_id=? ORDER BY l.order_index, q.order_index",
        (level_id,),
    )
    dist: dict[int, dict[int, int]] = {}
    for lid, title, ci in cur.fetchall():
        dist.setdefault(lid, {}).setdefault(ci, 0)
        dist[lid][ci] += 1
    cur.execute(
        "SELECT l.id, l.title FROM lessons l WHERE l.level_id=? ORDER BY l.order_index",
        (level_id,),
    )
    titles = dict(cur.fetchall())
    for lid in sorted(dist):
        d = {k: dist[lid].get(k, 0) for k in range(4)}
        warn = "  <-- 失衡" if max(d.values()) >= 6 or min(d.values()) == 0 else ""
        print(f"  lesson {lid} {titles[lid]}: A={d[0]} B={d[1]} C={d[2]} D={d[3]}{warn}")
    conn.close()


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "--verify"
    if arg == "--lessons":
        do_lessons()
    elif arg == "--quizzes":
        do_quizzes()
    elif arg == "--dist":
        do_quiz_dist()
    elif arg == "--verify":
        do_verify()
    else:
        print(__doc__)
