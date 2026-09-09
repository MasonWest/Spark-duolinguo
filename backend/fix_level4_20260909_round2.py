# -*- coding: utf-8 -*-
"""Level 4 修复第二轮（2026-09-09）

第一轮遗漏项，由关键词扫描暴露：
- L4-3 preview 的「必 Shuffle」、examples note 的「Spark 2.3+」
- L4-4 examples code 注释里的「groupBy 必 Shuffle」
- L4-5 preview 的「Tungsten 这个紧凑零件标准」
- L4-8 examples 的「一次 Action = 一个 Job」标题与注释
- q400 / q401 / q402 / q405：Tungsten 定义、「回退到解释执行」
"""

import fix_level4_20260909 as f

f.LESSON_SUBS = {
    33: [
        (
            "尤其认出 Exchange 这个「必 Shuffle」的信号。",
            "尤其认出 Exchange 这个 Shuffle 信号。",
        ),
        (
            "formatted 适合人眼扫读；Spark 2.3+ 才支持。",
            "formatted 适合人眼扫读；Spark 3.0+ 才支持（SPARK-27395）。",
        ),
    ],
    34: [
        (
            "# 计划里会出现 Exchange 节点（groupBy 必 Shuffle）",
            "# 计划里通常会出现 Exchange 节点（groupBy 按 key 重分布）",
        ),
    ],
    35: [
        (
            "下集就讲 WholeStageCodegen——相邻算子怎么被「焊成一台机器」，以及 Tungsten 这个紧凑零件标准。",
            "下集就讲 WholeStageCodegen——相邻的算子怎么被生成到同一段代码里，以及 Tungsten 这套底层执行优化方向（WholeStageCodegen 正是其中一支）。",
        ),
    ],
    38: [
        (
            "一次 Action = 一个 Job",
            "通常一次 Action = 一个 Job",
        ),
        (
            "df.groupBy('city').count().show()   # 触发 1 个 Job",
            "df.groupBy('city').count().show()   # 通常触发 1 个 Job",
        ),
    ],
}

f.QUIZ_FIXES = {
    400: (
        "Project Tungsten 是什么？",
        [
            "一种文件存储格式",
            "Spark 的底层执行优化方向：紧凑二进制内存表示 + cache 感知算法 + 代码生成，WholeStageCodegen 属于其中的代码生成部分",
            "一种网络传输协议",
            "一种用户自定义函数",
        ],
        1,
        "Tungsten 不是单一技术，而是一整套方向：紧凑/二进制的内存表示、cache 感知的算法与数据结构，以及代码生成。本课的 WholeStageCodegen 正是第三支。UnsafeRow、堆外内存这些字节级细节留到 Level 7。",
    ),
    401: (
        "为什么有些算子 / 表达式会「回退」（fallback）？",
        [
            "它们走回传统的逐算子 iterator / Volcano 方式执行，不再享受 codegen 融合",
            "它们会直接报错",
            "它们会被优化器删掉",
            "它们会自动改成广播",
        ],
        0,
        "不支持 codegen 的算子/表达式（例如 Python UDF）会让连续的代码生成断开，那部分就走回传统的逐算子 iterator（Volcano）方式执行。注意这不是「解释执行」——Spark 没有解释器，只是不再使用生成的融合代码。",
    ),
    402: (
        "关于 Tungsten，正确的说法是？",
        [
            "它就是「紧凑二进制格式」的别名",
            "它包含紧凑二进制内存表示、cache 感知算法与代码生成三部分，WholeStageCodegen 属于其中的代码生成",
            "它是一种存储格式",
            "它只和 Shuffle 有关",
        ],
        1,
        "Tungsten 是三个方向合起来的总称，不是单指二进制格式。UnsafeRow、堆外内存、编码这些字节级细节属于 Level 7 性能调优，本课只把它当「底层执行优化方向」复用。",
    ),
    405: (
        "窄依赖（Narrow Dependency）是？",
        [
            "子分区只依赖父的有限个（通常 1 个）分区，无需跨节点搬数据",
            "子分区依赖父的全部分区",
            "需要跨节点 Shuffle 才能算出结果",
            "必然触发跨节点重排",
        ],
        0,
        "窄依赖中每个子分区只依赖父的少量分区（典型是 1 个），计算可以留在本地完成，不需要 Shuffle。",
    ),
}

if __name__ == "__main__":
    print("=== round2: lessons ===")
    f.do_lessons()
    print("=== round2: quizzes ===")
    f.do_quizzes()

    # 扩展扫描词后复验
    f.BANNED_PATTERNS += [
        "零件标准",
        "紧凑二进制执行标准",
        "回退到解释执行",
    ]
    print("=== verify ===")
    f.do_verify()
