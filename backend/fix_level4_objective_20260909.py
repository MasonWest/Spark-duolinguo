"""Level 4 「学完后，你应该能回答」(lessons.objective) 修复 2026-09-09

背景：上一轮修复只改了 content JSON 的七键与 quizzes，漏了 lessons.objective 这个独立列
（前端 LessonPage.tsx 渲染为「🎯 学完后，你应该能回答」）。里面残留的错误表述与
审查报告 P0/P1/P2/P3 完全同源，必须一并清掉。

原则：
- 只改 Level 4 的 9 条 objective，不动 description / 其它 Level
- 逐条整字段覆盖（不是模糊替换），用 (id, title) 双重校验，防止改错课
- 改完打印全文供人工核对

用法：python fix_level4_objective_20260909.py [--apply]   # 默认 dry-run
"""

import shutil
import sqlite3
import sys

DB = "spark_quest.db"
LEVEL_ORDER_INDEX = 4

# (lesson_id, title 关键字, 新 objective)
NEW = [
    (
        31,
        "为什么该看执行计划",
        "学完本课，你应该能够：用自己的话解释为什么「代码写对 ≠ 跑得快」；"
        "建立「执行计划是诊断性能的第一视角」的直觉；"
        "说清执行计划描述的是「打算怎么算」而非「真实耗时」；"
        "并理解为什么从 Level 0-3 一路写代码，却从不曾真正「看见」Spark 内部怎么算。",
    ),
    (
        32,
        "逻辑计划 vs 物理计划",
        "学完本课，你应该能够：区分 Logical Plan（「想做什么」）与 Physical Plan（「怎么用 Spark 算子做」）；"
        "说出四段 Parsed → Analyzed → Optimized → Physical 各自做了什么；"
        "理解 Analyzed 才做类型/表/列存在性检查（很多报错在这）、Optimized 做等价改写、"
        "Physical 才绑定具体实现（如 HashAgg vs SortAgg、SortMergeJoin vs BroadcastHashJoin）；"
        "并知道 join 策略是到 Physical 阶段才定的，所以「join 一定有 Shuffle」并不成立（Broadcast Join 详见 Level 6）。",
    ),
    (
        33,
        "explain() 怎么用",
        "学完本课，你应该能够：说清 explain() / explain(True) / explain(mode=\"formatted\") 的区别与输出结构；"
        "理解 explain() 本身不触发执行（是惰性窥视）；"
        "知道 Spark 3.0+ 共五种模式（simple / extended / codegen / cost / formatted）、"
        "mode=\"formatted\" 需 Spark 3.0+（不是 2.3+）、explain(True) 等价于 extended、"
        "而 mode=\"codegen\" 能直接看生成的 Java 代码；"
        "并知道 Spark 3.2+ 默认开启 AQE 时 explain() 看到的只是初始计划"
        "（常显示 AdaptiveSparkPlan isFinalPlan=false），想稳定复现经典输出需先 "
        "spark.conf.set(\"spark.sql.adaptive.enabled\", \"false\")。",
    ),
    (
        34,
        "怎么读执行计划文本",
        "学完本课，你应该能够：识别 Scan / Filter / Project / Aggregate / Exchange 节点；"
        "尤其认出 Exchange = Shuffle 信号，但也知道它并非必然出现"
        "（Broadcast Join 不产生 ShuffleExchange、上游已按该 key 分区时 groupBy 可省掉 Exchange）；"
        "读对 *(N)——N 是 codegen stage 的编号，不是融合算子的数量："
        "数「带相同 N 的行数」才知道这个 stage 融合了多少算子，数「不同 N 的个数」才知道有几个 codegen stage；"
        "并知道计划里的行数/字节是「估计」而非真实值。",
    ),
    (
        35,
        "Catalyst 优化规则",
        "学完本课，你应该能够：理解 Optimized 阶段的等价改写——谓词下推、列裁剪、常量折叠、null 传播；"
        "明白对确定性表达式而言优化是「等价」的（语义不变、只更省），"
        "而 rand() / current_timestamp() 这类非确定性表达式不能想当然地折叠或重排；"
        "知道优化器的边界在哪：含 UDF 的过滤条件依赖 UDF 的输出值，因此无法被移到 UDF 之前"
        "（这不是「优化器看不懂」，而是由表达式的数据依赖顺序决定的），"
        "不过列裁剪仍会发生，只是 UDF 依赖的列必须保留；"
        "并知道收益取决于数据源——下推对 Parquet 效果明显、csv 有限，"
        "列裁剪在 Parquet/ORC 上能跳过整列数据，而 csv 等行式文本通常仍需读取并解析整行。",
    ),
    (
        36,
        "WholeStageCodegen 与 Tungsten",
        "学完本课，你应该能够：说清 WholeStageCodegen 把一段可以连续 codegen 的物理算子流水线"
        "生成 Java 代码并编译执行，以减少逐算子调用以及中间对象/数据转换的开销；"
        "读对 *(N)——N 是 codegen stage 的编号：数「同编号的行数」= 该 stage 融合的算子数，"
        "数「不同编号的个数」= 这条查询有几个 codegen stage，Exchange 之后编号继续递增、不会重新从 1 开始；"
        "知道 Exchange 会切断 codegen 流水线，不支持 codegen 的表达式或 Python UDF 会回退为"
        "逐算子 iterator（Volcano 式）执行——Spark 并没有一个「解释器」；"
        "并知道 WholeStageCodegen 属于 Project Tungsten 的代码生成部分，Tungsten 还包括紧凑的二进制内存表示"
        "与 cache-aware 的算法数据结构，那些内存/堆外细节留到 Level 7。",
    ),
    (
        37,
        "窄依赖 vs 宽依赖",
        "学完本课，你应该能够：区分 Narrow（父分区→子分区 1对1/多对1，无 Shuffle）与 "
        "Wide（子分区依赖父多个甚至全部分区的同 key 数据，通常需要 Shuffle）；"
        "理解这是 Stage 边界的根源；"
        "知道 shuffle-based join（sort-merge / shuffle-hash）属于宽依赖，"
        "但 Broadcast Join 是重要例外——它不 Shuffle、不切 Stage；"
        "容错上：窄依赖通常只需沿本地依赖链重算受影响的分区（便宜），"
        "宽依赖的 Shuffle 输出丢失时可能要重新跑相关的上游 map task（贵）；"
        "map / filter / select 是窄依赖，groupBy / orderBy / distinct 与 shuffle-based join 是宽依赖。",
    ),
    (
        38,
        "Job / Stage / Task 层级",
        "学完本课，你应该能够：建立「通常一次 Action = 一个 Job（take / show 这类带限制语义的可能触发多个）；"
        "Job 按宽依赖切 Stage；每个 Stage 按分区数切 Task 并行」的层级模型；"
        "理解 Task 数 = 该 Stage 的分区数；"
        "单条线性依赖链可以用「Shuffle 边界数 + 1」快速估算 Stage 数，"
        "遇到多分支 / Union / 多数据源的 DAG 则要按实际依赖关系判断，不能套公式；"
        "Stage 按依赖 DAG 执行——有依赖的必须等父 Stage、无依赖的可以并行提交，"
        "单个 Stage 内的 Task 通常并行执行；并行度调优留 Level 5。",
    ),
    (
        39,
        "综合练习",
        "学完本课，你应该能够：给一段真实代码，独立读/写出它的 explain() 输出，"
        "数 Stage（单条线性链用 Shuffle 边界数 + 1，多分支按实际依赖数）、认出 Shuffle、"
        "指出至少一处 Catalyst 优化；"
        "理解计划相同 ≠ 运行时性能相同（数据倾斜 / 分区数都会影响，Level 5 / Level 7 展开）；"
        "知道 Spark 3.2+ 默认开启 AQE 时 explain() 只是初始计划，最终执行计划要结合 Spark UI 看；"
        "综合练习只验证「读得懂」，不要求你会调优。",
    ),
]


def main(apply: bool):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute(
        "select id, title, objective from lessons "
        "where level_id = (select id from course_levels where order_index = ?) "
        "order by order_index",
        (LEVEL_ORDER_INDEX,),
    )
    rows = cur.fetchall()
    if len(rows) != 9:
        print(f"[ABORT] Level 4 课程数 = {len(rows)}，期望 9")
        return 1

    by_id = {r[0]: r for r in rows}
    for lid, kw, _ in NEW:
        if lid not in by_id:
            print(f"[ABORT] lesson id {lid} 不在 Level 4")
            return 1
        if kw not in by_id[lid][1]:
            print(f"[ABORT] lesson {lid} 标题「{by_id[lid][1]}」不含关键字「{kw}」")
            return 1

    for lid, kw, text in NEW:
        old = by_id[lid][2]
        changed = old != text
        print(f"--- [{lid}] {by_id[lid][1]}  {'CHANGED' if changed else 'unchanged'}")
        if changed:
            if apply:
                cur.execute("update lessons set objective=? where id=?", (text, lid))
        print("   NEW:", text[:90], "…")

    if apply:
        conn.commit()
        print("\n已写入真库。")
    else:
        print("\ndry-run，未写入。加 --apply 执行。")
    conn.close()
    return 0


if __name__ == "__main__":
    if "--apply" in sys.argv:
        shutil.copy(DB, DB + ".bak_before_objective_20260909")
        print("已备份:", DB + ".bak_before_objective_20260909")
    sys.exit(main("--apply" in sys.argv))
