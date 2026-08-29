# -*- coding: utf-8 -*-
"""一次性脚本：把 Level 4（执行计划，9 课）合并进 course_seed.json 与 quiz_seed.json，
并幂等地 upsert 进 spark_quest.db 的 course_levels / lessons / quizzes 表。
不修改 Level 0/1/2/3 与已有的 lesson_mastery 进度数据。

运行：cd backend && python seed_level4.py
"""
import sqlite3, json, os

BASE = os.path.dirname(os.path.abspath(__file__))
SEED = os.path.join(BASE, "app", "course_seed.json")
QUIZ = os.path.join(BASE, "app", "quiz_seed.json")
DB = os.path.join(BASE, "spark_quest.db")

LEVEL4 = {
    "title": "Level 4：执行计划",
    "description": "教读者「怎么看懂 Spark 是怎么算的」——从代码到执行计划的映射，以及 Catalyst 在背后做了哪些等价优化。覆盖为什么看计划、逻辑/物理四段、explain 三档、读节点、Catalyst 规则、WholeStageCodegen、窄宽依赖、Job/Stage/Task 层级与综合读图。为 Level 5（分区/Shuffle 调优）→ Level 6（Join）→ Level 7（性能调优）铺垫，本身不抢跑调优。",
    "order_index": 4,
    "lessons": [
        {
            "title": "为什么该看执行计划",
            "slug": "l4-why-explain",
            "description": "建立「执行计划是诊断性能第一视角」的直觉；代码写对 ≠ 跑得快。",
            "objective": "学完本课，你应该能够：用自己的话解释为什么「代码写对 ≠ 跑得快」；建立「执行计划是诊断性能的第一视角」的直觉；说清执行计划描述的是「打算怎么算」而非「真实耗时」；并理解为什么从 Level 0-3 一路写代码，却从不曾真正「看见」Spark 内部怎么算。",
            "estimated_minutes": 12,
            "order_index": 0,
            "prerequisites": "",
            "content": {
                "explanation": "【先用人话理解】\n\n你已经能写 DataFrame / SQL 跑出正确结果了。但「结果对」和「跑得快」是两件事。比如同样一段聚合，写得好 Spark 只读需要的列、尽早过滤；写得不好它老老实实扫描全表、搬运全部字段。问题来了：你怎么知道它实际是怎么算的？答案就是「执行计划」——它是 Spark 在动手前，把你的代码翻译成的「施工说明书」。\n\n【一个直观的心智模型】\n\n把执行计划想成开车时的「导航路线单」。你只说了目的地（一段代码），但真正上路要走哪条路、过几个高架、在哪里并线，是导航（Catalyst 优化大脑）替你算好的「最终路线单」。不懂看路线单，你就永远不知道为什么这次「堵在高速上」（慢），只能干等。执行计划就是 Catalyst 给你的那张单。\n\n⚠️ 比喻的边界（很重要）：\n① 执行计划看不出「运行时」的真实耗时与数据倾斜——那些是 Job 跑起来后的指标（Stage 实跑时间、shuffle 字节数），属于 Level 5/L7 的运行时观测。计划只描述「打算怎么算」。\n② 计划是「静态蓝图」，不是「已经跑过一遍」。同一段代码今天和明天计划可能一样，但真实耗时天差地别（数据量、集群状态不同）。\n③ 看计划不会让代码变快，它只是「诊断工具」——看见问题，再决定要不要改写（调优是 Level 5 之后的事）。\n\n【正式的技术定义】\n\n执行计划（Execution Plan）是 Spark 把用户代码（Transformation/Action）经过 Catalyst 优化后生成的逻辑/物理算子树，描述了「数据从哪读、经过哪些算子、怎么在节点间重分布、最终怎么输出」。可通过 `explain()` 查看。它是理解性能、排查「为什么这么慢」的第一手视角。\n\n【写下代码后，Spark 内部发生了什么】\n\n你写完一段 DataFrame 代码时，Spark 还没算——它只是把你的意图登记成未优化的逻辑计划。当你调用 `explain()`，Spark 会把「经过 Catalyst 四阶段（解析→分析→优化→物理化）」之后的算子树打印出来，但**不会真正执行**数据计算。也就是说，`explain()` 是「在动手前先给你看一眼施工单」，是诊断而非执行。",
                "examples": [
                    {
                        "title": "为什么结果对但可能很慢",
                        "code": "df = spark.read.parquet('sales')\nresult = df.groupBy('city').sum('amount')\nresult.explain()   # 看计划，但不真正算",
                        "note": "explain() 只打印计划，不触发执行；你想验证「它怎么算的」而不是「结果是什么」时，用它。"
                    },
                    {
                        "title": "计划揭示「读多少」",
                        "code": "# 即使你只选两列，要看计划里 Scan 是否做了列裁剪\ndf.select('city', 'amount').filter(df.amount > 0).explain()",
                        "note": "计划里如果 Scan 仍读全列，说明没下推/裁剪，可能白白读了大量不需要的字段。"
                    },
                    {
                        "title": "对比「看起来一样」的两段代码",
                        "code": "# 写法 A\ndf.filter(df.amount > 0).groupBy('city').count()\n# 写法 B\ndf.groupBy('city').count()\n# 两者的计划可能不同——B 没过滤，扫描/计算量更大",
                        "note": "用 explain 对照两段代码的计划，能直观看出「写法差异」如何变成「计算量差异」。"
                    }
                ],
                "key_points": [
                    "「代码写对 ≠ 跑得快」：结果正确不保证性能合理",
                    "执行计划是「Spark 打算怎么算」的施工单，是诊断性能的第一视角",
                    "explain() 只打印计划、不触发执行（惰性窥视）",
                    "计划描述静态蓝图，看不出运行时真实耗时与数据倾斜",
                    "真正调优（改写法/调分区）是 Level 5 之后的事，本课只学会「看」"
                ],
                "common_mistakes": [
                    {
                        "mistake": "以为「结果对了就不需要看计划」。",
                        "why": "结果对不代表性能好，慢查询可能一直潜伏。",
                        "fix": "养成对复杂查询先 explain 看一眼的习惯。"
                    },
                    {
                        "mistake": "把 explain 的输出当成「已经跑过、耗时就是这些」。",
                        "why": "计划里行数/字节是「估计」，不是实测。",
                        "fix": "真实耗时看 Spark UI 的 Stage 实跑，计划只管「打算怎么算」。"
                    },
                    {
                        "mistake": "看到计划有 Exchange（Shuffle）就觉得「写错了」。",
                        "why": "Shuffle 在很多聚合/排序里是正常且必要的。",
                        "fix": "区分「必要 Shuffle」和「本可避免的冗余 Shuffle」，后者才是优化点（Level 5）。"
                    }
                ],
                "review": "从 Level 0 到 Level 3，你已经能用 DataFrame API 和 SQL 写出正确的分析。你也知道 Catalyst 会在背后做优化（谓词下推、列裁剪），但那些优化对你来说是「黑盒」——你从没真正看见过。",
                "problem": "为什么「代码能跑出正确结果」不等于「代码跑得快」？当你怀疑一段聚合特别慢时，第一件该做的事是什么？怎么「看见」Spark 内部到底打算怎么算？",
                "preview": "下集我们正式拆开执行计划的「四段结构」——逻辑计划和物理计划到底差在哪，为什么一个叫「想做什么」、一个叫「怎么用 Spark 算子做」。"
            }
        },
        {
            "title": "逻辑计划 vs 物理计划",
            "slug": "l4-logical-vs-physical",
            "description": "区分 Logical（想做什么）与 Physical（怎么用 Spark 算子做）；理解四段 Parsed→Analyzed→Optimized→Physical。",
            "objective": "学完本课，你应该能够：区分 Logical Plan（「想做什么」）与 Physical Plan（「怎么用 Spark 算子做」）；说出四段 Parsed → Analyzed → Optimized → Physical 各自做了什么；理解 Analyzed 才做类型/表存在性检查（很多报错在这）、Optimized 做等价改写、Physical 才绑定具体实现（如 HashAgg vs SortAgg）。",
            "estimated_minutes": 13,
            "order_index": 1,
            "prerequisites": "",
            "content": {
                "explanation": "【先用人话理解】\n\n执行计划不是「一张图」，而是「几张渐进的图」。最开始是「你想干什么」（逻辑计划），到最后是「具体用哪套零件、哪条流水线干」（物理计划）。中间 Catalyst 不断把模糊的意图变成可执行、且更省的方案。理解这四段，你才算真正「读得懂」计划。\n\n【一个直观的心智模型】\n\n把 Logical Plan 想成「设计师的概念图」——只画「要造一栋带阳台的两层楼」，不规定用什么砖、怎么吊装。Physical Plan 想成「施工队拿到的施工图」——明确用哪种塔吊、混凝土标号、工序顺序。Catalyst 就是那个既画概念图、又出施工图、还在中间做「等价省料」改的总工程师。四段就是：草图（Parsed）→ 审图盖章确认能建（Analyzed）→ 优化改图（Optimized）→ 最终施工图（Physical）。\n\n⚠️ 比喻的边界（很重要）：\n① Analyzed 阶段才做「类型检查 / 表是否存在 / 列是否存在」——你很多 `AnalysisException`（「表不存在」「列不存在」「类型不匹配」）就在这爆出来，而不是在写代码时。这是「fail-fast 推迟到分析阶段」的体现。\n② Optimized 做的是「等价改写」：结果不变，但更省（下推、裁剪、常量折叠）。它不是凭空变快，是聪明地少干活。\n③ Physical 才绑定具体实现：同一个聚合，可能选 HashAggregate 或 SortAggregate；同一个 join，可能选 broadcast 或 sort-merge——但这些「策略选择」是 Physical 阶段，且受后续 Level 5/6 的调优参数影响。\n\n【正式的技术定义】\n\n执行计划分四段：① Parsed Logical Plan（语法解析后的初始逻辑树）；② Analyzed Logical Plan（经 Catalog 解析元数据、校验类型/表/列合法性）；③ Optimized Logical Plan（Catalyst 规则做等价重写，如谓词下推、列裁剪）；④ Physical Plan（选择具体算子实现与执行策略，生成可执行的算子树）。逻辑计划描述「做什么」，物理计划描述「怎么做」。\n\n【写下代码后，Spark 内部发生了什么】\n\n你写 `df.groupBy('city').sum('amount')` 时，Spark 先生成 Parsed 树（未经校验）。Analyzer 接手，去 Catalog 查 `city/amount` 列是否存在、类型是否匹配——这里最容易抛错。接着 Optimizer 套用规则把「先全表扫描再分组」改写成「扫描时只取需要的列」。最后 Planner 选具体物理算子（如 HashAggregate）输出 Physical Plan。你调用 `explain(True)` 就能看到这四段全貌。",
                "examples": [
                    {
                        "title": "触发 Analyzed 报错（表不存在）",
                        "code": "spark.sql('SELECT * FROM not_exist_table').explain()\n# 抛 AnalysisException: Table or view not found",
                        "note": "报错发生在 Analyzed 阶段，不是写代码时——这就是「fail-fast 推迟」。"
                    },
                    {
                        "title": "看四段：explain(True)",
                        "code": "df.groupBy('city').sum('amount').explain(True)\n# 输出 Parsed / Analyzed / Optimized / Physical 四段",
                        "note": "explain(True) ≡ explain('extended')，一次看全四段；默认 explain() 只看 Physical。"
                    },
                    {
                        "title": "Optimized 的等价改写",
                        "code": "# 列裁剪：你只选 city，优化器让 Scan 只读 city 一列\ndf.select('city').filter(df.amount > 0).explain(True)",
                        "note": "在 Optimized 段能看到 Project/Filter 被下推、列被裁剪，逻辑上「读更少」。"
                    }
                ],
                "key_points": [
                    "逻辑计划 = 想做什么；物理计划 = 怎么用 Spark 算子做",
                    "四段：Parsed（解析）→ Analyzed（校验元数据/类型）→ Optimized（等价改写）→ Physical（绑定具体实现）",
                    "报错（表/列/类型不存在）多在 Analyzed 阶段爆出（fail-fast 推迟）",
                    "Optimized 做等价改写（下推/裁剪/常量折叠），结果不变只更省",
                    "Physical 才选具体算子（HashAgg vs SortAgg、join 策略等）"
                ],
                "common_mistakes": [
                    {
                        "mistake": "以为写完代码时就会报「列不存在」。",
                        "why": "校验推迟到 Analyzed。",
                        "fix": "真正触发执行或 explain 时才暴露，所以别以为「没报错=没问题」。"
                    },
                    {
                        "mistake": "混淆 Logical 与 Physical，说「计划就是最终怎么跑」。",
                        "why": "Logical 还没绑定实现。",
                        "fix": "区分「做什么」（逻辑）与「怎么做」（物理），优化看逻辑段、调优看物理段。"
                    },
                    {
                        "mistake": "看到 Optimized 和 Physical 不一样就以为出 bug。",
                        "why": "二者本就该不同（一个是等价改写、一个是具体实现）。",
                        "fix": "理解这是正常演进，不是错误。"
                    }
                ],
                "review": "上一课我们建立了「执行计划是诊断性能第一视角」的直觉，也知道 explain() 能把它打印出来。但打印出来那一大坨，到底是什么？",
                "problem": "为什么执行计划要分「逻辑」和「物理」？Parsed/Analyzed/Optimized/Physical 四段各自干啥？为什么很多「表不存在」的报错要等运行/ explain 才爆出来？",
                "preview": "知道了四段长什么样，下集就学怎么把这张「施工单」真正调出来——explain() / explain(True) / explain(mode=\"formatted\") 三者到底差在哪。"
            }
        },
        {
            "title": "explain() 怎么用",
            "slug": "l4-explain-api",
            "description": "掌握 explain() / explain(True) / explain(mode=\"formatted\") 区别与输出结构。",
            "objective": "学完本课，你应该能够：说清 explain() / explain(True) / explain(mode=\"formatted\") 的区别与输出结构；理解 explain() 本身不触发执行（是惰性窥视）；知道 mode=\"formatted\" 需 Spark 2.3+，explain(True) 等价于 extended。",
            "estimated_minutes": 11,
            "order_index": 2,
            "prerequisites": "",
            "content": {
                "explanation": "【先用人话理解】\n\n执行计划要「调出来」才能看，调它的扳机就是 `explain()`。但它有三个「档位」：简版（默认）、全四段版（True）、树状可读版（formatted）。就像你要查一张施工单，可以只要「最终施工图」（简版），要「从草图到施工图全过程」（True），或要「缩进排好、一眼看清层级」的精装版（formatted）。\n\n【一个直观的心智模型】\n\n把 explain 想成「向工厂要施工排程单」：\n- 默认 `explain()` = 只给你最终施工图（Physical Plan），最常用、最聚焦。\n- `explain(True)` = 把草图、审图、优化图、施工图四张全给你（extended）。\n- `explain(mode=\"formatted\")` = 给一张「缩进树状、节点层级一目了然」的精装施工图，适合人眼扫读。\n\n⚠️ 比喻的边界（很重要）：\n① `explain()` 本身**不触发执行**——它只是「窥视」 Catalyst 已经规划好的计划，数据不会真正算。所以它便宜、安全，可以随便看。\n② `mode=\"formatted\"` 需要 Spark 2.3+（老版本没有这个模式）；现代 Spark 都支持。\n③ `explain(True)` 就是 `explain(\"extended\")` 的快捷写法，二者等价；它多打出的 Parsed/Analyzed/Optimized 三段是「规划过程」，不是「额外干活」。\n\n【正式的技术定义】\n\n`DataFrame.explain()` 打印执行计划。`explain()`（无参）默认打印 Physical Plan；`explain(True)` 或 `explain(\"extended\")` 打印 Parsed/Analyzed/Optimized/Physical 四段；`explain(\"formatted\")` 以缩进树状结构打印（Spark 2.3+），更易读。它是诊断 API，不触发 Action。\n\n【写下代码后，Spark 内部发生了什么】\n\n你调用 `df.explain()`，Spark 走完 Catalyst 的分析与优化（但不会去读数据、不会起 Task），然后把「规划结果」打印到控制台。因为没遇到真正的 Action（如 show/count/write），整条数据流水线不会执行——这正是它「安全可反复看」的原因。",
                "examples": [
                    {
                        "title": "默认简版（仅 Physical）",
                        "code": "df.groupBy('city').count().explain()\n# 输出一段 Physical Plan（带 *(N) 融合标记）",
                        "note": "默认只看最终物理计划，最快聚焦「怎么跑」。"
                    },
                    {
                        "title": "全四段",
                        "code": "df.groupBy('city').count().explain(True)\n# 含 Parsed / Analyzed / Optimized / Physical",
                        "note": "explain(True) ≡ explain('extended')；想看 Catalyst 怎么做优化的用这个。"
                    },
                    {
                        "title": "树状可读版",
                        "code": "df.groupBy('city').count().explain(mode='formatted')\n# 缩进树状，层级清晰",
                        "note": "formatted 适合人眼扫读；Spark 2.3+ 才支持。"
                    }
                ],
                "key_points": [
                    "explain() 默认只打印 Physical Plan",
                    "explain(True) ≡ explain('extended')，打印四段全貌",
                    "explain(mode='formatted') 缩进树状、易读，需 Spark 2.3+",
                    "explain() 不触发执行，是惰性「窥视」，可安全反复看",
                    "真正执行要 show/count/write 等 Action"
                ],
                "common_mistakes": [
                    {
                        "mistake": "调了 explain 还以为「数据算了一遍」。",
                        "why": "explain 不触发 Action。",
                        "fix": "记住它只打印计划；要结果用 show/count。"
                    },
                    {
                        "mistake": "在老 Spark（<2.3）用 mode='formatted' 报错。",
                        "why": "该模式 2.3 才引入。",
                        "fix": "老版本用 explain(True) 看四段即可。"
                    },
                    {
                        "mistake": "只看默认 explain() 就以为「没优化」。",
                        "why": "默认不显示 Optimized 段，优化痕迹看不到。",
                        "fix": "想看 Catalyst 优化了什么，用 explain(True)。"
                    }
                ],
                "review": "上一课我们拆开了「逻辑计划 vs 物理计划」的四段结构，知道 Analyzed 才校验、Optimized 才改写。可那四段到底怎么「调出来」看？",
                "problem": "explain() 默认给你什么？想看完整四段该用哪个档位？树状易读版怎么调？为什么 explain 不会让你的数据真的算一遍？",
                "preview": "调出了计划，下集就学怎么「读」它——Scan / Filter / Project / Aggregate / Exchange 这些节点分别是什么，尤其认出 Exchange 这个「必 Shuffle」的信号。"
            }
        },
        {
            "title": "怎么读执行计划文本",
            "slug": "l4-read-plan",
            "description": "识别 Scan/Filter/Project/Aggregate/Exchange；尤其认出 Exchange = Shuffle 信号。",
            "objective": "学完本课，你应该能够：识别 Scan / Filter / Project / Aggregate / Exchange 节点；尤其认出 Exchange = Shuffle 信号；理解 *(N) 是 Stage 内算子融合标记；并知道计划里的行数/字节是「估计」非真实。",
            "estimated_minutes": 14,
            "order_index": 3,
            "prerequisites": "",
            "content": {
                "explanation": "【先用人话理解】\n\n计划打印出来是一棵「算子树」，每个节点是一个工序。你得学会认这几个常客：哪里进货（Scan）、哪里筛（Filter）、哪里选列（Project）、哪里汇总（Aggregate）、哪里「货在空中飞」（Exchange）。读懂这棵「工厂车间布局图」，你就知道数据走了哪些弯路。\n\n【一个直观的心智模型】\n\n把计划当成「工厂车间布局图」：\n- Scan = 进货口（从文件/表读数据）\n- Filter = 入口筛（拦下不合格行）\n- Project = 选列（只挑要的字段装箱）\n- Aggregate = 水果分拣派对（按 key 分组汇总，复用 L2）\n- Exchange = 货在空中飞（复用 L2/L3 的 Shuffle 信号）——**这就是最该警惕的节点**\n\n⚠️ 比喻的边界（很重要）：\n① Exchange 节点 = 必 Shuffle：数据要序列化、走网络、反序列化，重新按 key 分布。它是性能成本的主要来源之一，看到它就心里有数「这里要花钱」。\n② `*(N)` 是 Stage 内算子融合标记（WholeStageCodegen，下节课讲），表示相邻 N 个算子被融合成一个 Java 方法——不是「第 N 阶段」。\n③ 计划里的行数 / 字节是 Catalyst 的「**估计**」，不是实测；真实量要看 Spark UI 的 Stage 指标。别拿计划数字当真相。\n\n【正式的技术定义】\n\n执行计划由算子节点组成：Scan（数据源读取）、Filter（行过滤）、Project（列投影/表达式）、Aggregate（分组聚合）、Exchange（按 key 重分布 = Shuffle）、Sort（排序）等。`*(N)` 前缀表示 WholeStageCodegen 融合的算子数。Exchange 是宽依赖/Stage 边界的物理信号；计划中的统计量是优化器估计值。\n\n【写下代码后，Spark 内部发生了什么】\n\n当你 print 出计划，每个缩进层级是一个算子在「等上游喂数据」。Spark 从最底层的 Scan 开始读，向上经过 Filter/Project 做本地处理，遇到 Exchange 就把数据按 key 洗牌到别的节点，再向上 Aggregate。读懂这棵树，你就能指着一个 Exchange 说「这里是 Shuffle，是潜在瓶颈」。",
                "examples": [
                    {
                        "title": "认出 Exchange（Shuffle）",
                        "code": "df.groupBy('city').count().explain()\n# 计划里会出现 Exchange 节点（groupBy 必 Shuffle）",
                        "note": "任何 groupBy/distinct/orderBy/join 都会引入 Exchange，认准它就是认准 Shuffle。"
                    },
                    {
                        "title": "认出 Scan / Filter / Project",
                        "code": "df.select('city').filter(df.amount > 0).explain()\n# Scan -> Filter -> Project 链路清晰",
                        "note": "三者顺序体现「先读、再筛、最后选列」的本地流水线。"
                    },
                    {
                        "title": "计划里的估计 vs 真实",
                        "code": "df.groupBy('city').count().explain()\n# 节点旁标注的 sizeInBytes/rows 是估计值",
                        "note": "别把估计行数当真实；真实数据量看 Spark UI 的 Stage 指标（Level 5）。"
                    }
                ],
                "key_points": [
                    "Scan=进货口，Filter=入口筛，Project=选列，Aggregate=分组汇总，Exchange=Shuffle",
                    "Exchange 节点 = 必 Shuffle（序列化+网络+反序列化开销），是性能重点信号",
                    "*(N) 是 Stage 内算子融合标记（WholeStageCodegen），不是阶段编号",
                    "计划里的行数/字节是「估计」值，非真实，真实看 Spark UI",
                    "读懂算子树 = 能指出「数据走了哪些弯路、哪里 Shuffle」"
                ],
                "common_mistakes": [
                    {
                        "mistake": "把 *(N) 当成「第 N 个 Stage」。",
                        "why": "它是融合算子数标记。",
                        "fix": "Stage 由 Exchange 切分，不是 *(N)。"
                    },
                    {
                        "mistake": "看到计划里「行数很大」就恐慌。",
                        "why": "那是估计值，可能严重偏离真实。",
                        "fix": "真实数据量看运行时 Stage 指标。"
                    },
                    {
                        "mistake": "以为没有 Exchange 就一定快。",
                        "why": "没有 Shuffle 不代表没别的瓶颈（扫描量、倾斜）。",
                        "fix": "Exchange 是重点但非唯一，综合看。"
                    }
                ],
                "review": "上一课我们学会了三个 explain 档位，能把计划调出来。可面对那一坨缩进文本，第一眼还是懵——到底看哪里？",
                "problem": "计划文本里 Scan/Filter/Project/Aggregate/Exchange 各代表什么？为什么 Exchange 是最该警惕的节点？*(N) 和计划里的「行数」到底是什么意思？",
                "preview": "认出了 Exchange（Shuffle），下集就讲 Catalyst 在 Optimized 段到底做了哪些「等价省工」的改写——谓词下推、列裁剪、常量折叠都是啥。"
            }
        },
        {
            "title": "Catalyst 优化规则",
            "slug": "l4-catalyst-rules",
            "description": "理解 Optimized 阶段的等价改写：谓词下推、列裁剪、常量折叠、null 传播。",
            "objective": "学完本课，你应该能够：理解 Optimized 阶段的等价改写——谓词下推、列裁剪、常量折叠、null 传播；明白优化是「等价」的（结果不变只更省）；知道优化器非神仙（UDF/复杂嵌套下推不了），且下推能否发生取决于数据源（Parquet 能，csv 有限）。",
            "estimated_minutes": 14,
            "order_index": 4,
            "prerequisites": "",
            "content": {
                "explanation": "【先用人话理解】\n\nCatalyst 在 Optimized 段干的事，本质就是「等价省工」——在不改变结果的前提下，让 Spark 少读、少算、少搬。你不用手动优化，它就自动帮你做了。读懂这几条规则，你看计划时才知道「它为什么这么聪明」。\n\n【一个直观的心智模型】\n\n把 Catalyst 总工想想成做「等价省工」改写：\n- 谓词下推 = 把末端的滤网**瞬移到河口**（复用 L2 select-filter 边界「开天眼」）：本来读完所有列再筛，改成「读的时候就只让合格行进来」。\n- 列裁剪 = 只搬清单上列的箱子：你没选的列，压根不读。\n- 常量折叠 = 先算好 `1+1=2`：编译期能定的值，不拖到运行时算。\n\n⚠️ 比喻的边界（很重要）：\n① 优化是「等价」的：结果和没优化完全一致，只是更省。它不是魔法，不改语义。\n② 优化器非神仙：遇到 UDF（L3 讲的「外聘手艺人」）或复杂嵌套，它「看不懂」内部逻辑，下推/裁剪就失效——所以能不用 UDF 就不用（也呼应 L3 的 L7 伏笔）。\n③ 下推能否真正发生，**取决于数据源**：Parquet 这类列式存储能配合做列裁剪/谓词下推；普通 csv 做不到按列跳过，下推收益有限。\n\n【正式的技术定义】\n\nCatalyst 优化规则是作用于 Analyzed Logical Plan 的一组等价变换，常见包括：Predicate Pushdown（谓词下推，把过滤推到读取端）、Column Pruning（列裁剪，去掉不需要的列）、Constant Folding（常量折叠）、Null Propagation（null 传播）、算子合并等。它们在 Optimized 段输出更精简的等价逻辑计划，降低后续物理执行成本。\n\n【写下代码后，Spark 内部发生了什么】\n\n你写 `df.select('city').filter(df.amount>0)`，Catalyst 在 Optimized 段会把 Filter 下推到 Scan 之前、把 Project 的列裁剪合并进 Scan——最终物理计划「读数据时就已经只取 city、只留 amount>0 的行」。你没写任何优化代码，全部是 Catalyst 自动完成的等价改写。",
                "examples": [
                    {
                        "title": "谓词下推",
                        "code": "df.filter(df.amount > 0).select('city').explain(True)\n# Optimized 段可见 Filter 被下推到 Scan 附近",
                        "note": "即使你先写 filter 后写 select，优化器也会重排，让过滤尽早发生。"
                    },
                    {
                        "title": "列裁剪",
                        "code": "df.select('city', 'amount').filter(df.amount > 0).explain(True)\n# 未选的列不会进入 Scan",
                        "note": "你没选的列，优化器在 Scan 就裁掉，少读少搬。"
                    },
                    {
                        "title": "常量折叠",
                        "code": "from pyspark.sql import functions as F\ndf.withColumn('x', F.lit(1) + F.lit(1)).explain(True)\n# 1+1 在优化期折叠为 2",
                        "note": "编译期能定的表达式被提前算好，不占运行时。"
                    }
                ],
                "key_points": [
                    "优化是「等价改写」，结果不变只更省",
                    "谓词下推：过滤尽早发生（复用 L2「开天眼」）",
                    "列裁剪：没选的列不读",
                    "常量折叠：编译期能定的值提前算好",
                    "UDF/复杂嵌套下推不了；下推收益看数据源（Parquet 强、csv 弱）"
                ],
                "common_mistakes": [
                    {
                        "mistake": "以为「写 filter 顺序」决定性能。",
                        "why": "Catalyst 会重排，顺序不影响最终计划。",
                        "fix": "按可读性写，优化交给 Catalyst。"
                    },
                    {
                        "mistake": "以为所有数据源下推都一样。",
                        "why": "csv 不能按列跳过。",
                        "fix": "重读场景优先 Parquet，下推收益最大。"
                    },
                    {
                        "mistake": "在 UDF 里做过滤指望被下推。",
                        "why": "Catalyst 看不懂 UDF 内部。",
                        "fix": "能用内置函数/SQL 表达的就别用 UDF（呼应 L3）。"
                    }
                ],
                "review": "上两课我们认出了计划里的 Scan/Filter/Project/Exchange，也知道 Optimized 段会做改写。但具体改了什么？为什么同样的代码计划总「更聪明」？",
                "problem": "Catalyst 在 Optimized 段做了哪些等价省工的改写？谓词下推、列裁剪、常量折叠分别是什么？为什么 UDF 会「骗不过」优化器？",
                "preview": "知道了优化器会融合算子、提前算常量，下集就讲 WholeStageCodegen——相邻算子怎么被「焊成一台机器」，以及 Tungsten 这个紧凑零件标准。"
            }
        },
        {
            "title": "WholeStageCodegen 与 Tungsten",
            "slug": "l4-wholestage-codegen",
            "description": "理解相邻算子融合成单个 Java 方法；*(N) 标记含义；codegen 不是全融合。",
            "objective": "学完本课，你应该能够：理解相邻算子融合成单个 Java 方法，避免逐算子虚函数/中间对象开销；说清 *(N) 标记含义；知道 codegen 不是全融合（Exchange 边界会打断）、某些表达式不支持会回退；内存/堆外细节留 L7。",
            "estimated_minutes": 13,
            "order_index": 5,
            "prerequisites": "",
            "content": {
                "explanation": "【先用人话理解】\n\n普通流水线每道工序都是独立工位：上一道算完，打包成对象交给下一道，下一道再拆包——中间反复「打包/拆包」和函数调用有开销。Spark 有个绝活：把相邻几道工序「焊成一台一体化机器」，一次开机连续加工，省掉中间所有交接损耗。这就是 WholeStageCodegen。\n\n【一个直观的心智模型】\n\n- 普通流水线：每工位单独开关、逐件交接（每次交接都有虚函数调用 overhead、产生中间对象）。\n- WholeStageCodegen：把相邻工位「焊成一体化机器」，一次开机连加工，中间不拆不包。\n- Tungsten = 这套机器的「紧凑零件标准」（复用 L2 的 Tungsten 边界：底层二进制紧凑布局，省内存、Cache 友好）。\n\n⚠️ 比喻的边界（很重要）：\n① codegen **不是全融合**：遇到 Exchange（Shuffle）边界，融合必然被打断——因为数据要跨节点重分布，无法在同一个本地机器方法里连续跑。Exchange 是 Stage 边界，也是融合的「断点」。\n② 某些复杂表达式 / 不支持的算子会导致回退（fallback）到逐算子解释执行，融合标记消失。\n③ 内存布局、堆外、编码字节级细节是 Level 7 性能调优的内容，本课只把 Tungsten 当「紧凑零件标准」复用，不深挖。\n\n【正式的技术定义】\n\nWholeStageCodegen（全阶段代码生成）是 Tungsten 执行引擎的特性：将同一个 Stage 内相邻的多个算子（如 Scan+Filter+Project+Aggregate）编译成一个手写的 Java 方法，消除逐算子虚函数调用与中间对象分配，数据以二进制行格式在算子间流转。计划中以 `*(N)` 标记融合的算子数。Exchange 会切断融合。\n\n【写下代码后，Spark 内部发生了什么】\n\n你写 `df.select('city').filter(df.amount>0).groupBy('city').count()`，若这些算子在同一 Stage 内（无 Exchange 隔断），Spark 会把它们生成一个 `*(4)` 的融合方法：数据从 Scan 出来直接在同一个方法里被过滤、投影、聚合，全程不拆成对象。一旦中间出现 Exchange（如 groupBy 的 Shuffle），融合在此断开，后面的算子另起一段。",
                "examples": [
                    {
                        "title": "看 *(N) 融合标记",
                        "code": "df.select('city').filter(df.amount > 0).explain()\n# 节点前缀 *(2) 表示两个算子融合",
                        "note": "*(N) 即 WholeStageCodegen 融合的算子数，越大说明本地融合越充分。"
                    },
                    {
                        "title": "Exchange 打断融合",
                        "code": "df.groupBy('city').count().explain()\n# groupBy 的 Exchange 之后，融合重新从 1 计数",
                        "note": "Shuffle 边界必然切断融合，这是性能与 Stage 划分的关键。"
                    },
                    {
                        "title": "Tungsten 二进制布局（概念）",
                        "code": "# Tungsten 用紧凑二进制行格式，而非 Java 对象\ndf.filter(df.amount > 0).explain()",
                        "note": "本课只把 Tungsten 当「紧凑零件标准」；堆外/编码细节留 Level 7。"
                    }
                ],
                "key_points": [
                    "WholeStageCodegen：相邻算子融合成单个 Java 方法，省虚函数/中间对象开销",
                    "*(N) 标记 = 融合的算子数",
                    "Exchange（Shuffle）边界必然打断融合，是 Stage 边界也是融合断点",
                    "部分复杂表达式不支持会回退到解释执行",
                    "Tungsten = 紧凑二进制零件标准；内存细节留 Level 7"
                ],
                "common_mistakes": [
                    {
                        "mistake": "看到 *(1) 以为「没优化」。",
                        "why": "单算子本身也可能 codegen，只是没融合邻居。",
                        "fix": "看是否受 Exchange 隔断，而非看数字大小。"
                    },
                    {
                        "mistake": "以为所有算子都能无限融合。",
                        "why": "Exchange 必断、部分表达式回退。",
                        "fix": "理解融合有边界。"
                    },
                    {
                        "mistake": "把 Tungsten 当本课深挖对象。",
                        "why": "内存/堆外是 L7 内容。",
                        "fix": "本课只复用「紧凑零件标准」口径。"
                    }
                ],
                "review": "上一课我们讲了 Catalyst 的等价改写（下推/裁剪/折叠）。但光「少读少算」还不够快——Spark 还有一层执行层的加速，藏在计划里的 *(N) 标记里。",
                "problem": "计划里的 *(N) 是什么？为什么相邻算子能被「焊成一台机器」？为什么 Shuffle 会打断这种融合？Tungsten 又是什么角色？",
                "preview": "知道了融合与 Stage 边界，下集就讲「窄依赖 vs 宽依赖」——为什么某些算子在一个 Stage 内、某些必须切开，根源就在依赖类型。"
            }
        },
        {
            "title": "窄依赖 vs 宽依赖",
            "slug": "l4-dependency-narrow-wide",
            "description": "区分 Narrow（无 Shuffle）与 Wide（跨分区重排，必 Shuffle）；理解这是 Stage 边界根源。",
            "objective": "学完本课，你应该能够：区分 Narrow（父→子 1对1/多对1，无 Shuffle）与 Wide（跨分区重排，必 Shuffle）；理解这是 Stage 边界根源；知道窄依赖失败只重算局部分区（恢复便宜）、宽依赖失败要重算整个上游重排（贵）；map/filter/select 窄，groupBy/join/orderBy/distinct 宽。",
            "estimated_minutes": 13,
            "order_index": 6,
            "prerequisites": "",
            "content": {
                "explanation": "【先用人话理解】\n\nRDD 把数据切成很多分区。一个算子处理完，数据怎么流向子算子，决定了「要不要跨节点搬运」。如果子分区只依赖父分区里「同一小撮」，那搬运在车间内部搞定；如果子分区要「凑齐所有节点上同 key 的数据」，那就得把货运到空中重排。前者便宜，后者贵——这就是窄/宽依赖。\n\n【一个直观的心智模型】\n\n- 窄依赖 = 车间内部传递：上游一摞货直接交给同车间的同一个工人，不搬出车间（无 Shuffle）。\n- 宽依赖 = 把货空运到别车间按 key 重排（复用 L2/L3 的 Shuffle=空中飞货）：每个子分区要等「所有上游分区里同 key 的货」到齐。\n- **宽依赖即 Stage 的「断点」**——这正是上一课说的 Exchange 打断融合的根源。\n\n⚠️ 比喻的边界（很重要）：\n① 窄依赖失败，只需重算那个**局部**分区，恢复便宜（血缘短、数据就在本地）。\n② 宽依赖失败，要重算**整个上游重排**——因为下游依赖「全局按 key 汇聚」，上游任何分区丢了都得整体重算，贵。\n③ map/filter/select 是窄；groupBy/join/orderBy/distinct 是宽（其中 groupBy 的「部分聚合」是窄+宽两阶段：本地先聚合是窄，跨节点合并是宽）。\n\n【正式的技术定义】\n\n依赖描述子 RDD 分区对父 RDD 分区的依赖关系。Narrow Dependency（窄依赖）：子分区只依赖父的有限个（通常 1 个或同节点）分区，如 map/filter/select，无 Shuffle。Wide Dependency（宽依赖 / Shuffle Dependency）：子分区依赖父的**所有**分区中同 key 的数据，需跨节点重分布，如 groupBy/join/orderBy/distinct。宽依赖是 Stage 边界与容错成本的分水岭。\n\n【写下代码后，Spark 内部发生了什么】\n\n你写 `df.filter(...).select(...)`（窄），Spark 能在同一个 Stage 内把这几个算子融合连续执行，任何分区失败只在本地重算。你写 `df.groupBy('city').count()`（宽），Spark 必须在 Shuffle 处切一刀分成两个 Stage：Stage1 本地预聚合（窄），Stage2 跨节点合并（宽）。宽依赖这刀，就是 Exchange 节点、也是融合断点。",
                "examples": [
                    {
                        "title": "窄依赖（无 Exchange）",
                        "code": "df.filter(df.amount > 0).select('city').explain()\n# 无 Exchange，整段在同一 Stage",
                        "note": "map/filter/select 都是窄，不产生 Shuffle。"
                    },
                    {
                        "title": "宽依赖（有 Exchange）",
                        "code": "df.groupBy('city').count().explain()\n# 出现 Exchange，Stage 在此切开",
                        "note": "groupBy 必宽，是 Stage 边界。"
                    },
                    {
                        "title": "容错成本差异",
                        "code": "# 窄：某分区丢只重算该分区\n# 宽：上游全重排，代价大\ndf.join(other, 'id').explain()   # join 也是宽依赖",
                        "note": "宽依赖失败恢复贵，这是设计容错与调优时要记牢的。"
                    }
                ],
                "key_points": [
                    "窄依赖：子分区只依赖父局部分区，无 Shuffle（map/filter/select）",
                    "宽依赖：子分区依赖父全部分区同 key 数据，必 Shuffle（groupBy/join/orderBy/distinct）",
                    "宽依赖即 Stage 断点（也是 Exchange / 融合断点）",
                    "窄失败只重算局部分区（便宜）；宽失败重算整个上游重排（贵）",
                    "groupBy 部分聚合是窄+宽两阶段"
                ],
                "common_mistakes": [
                    {
                        "mistake": "以为「有算子就有 Stage 切换」。",
                        "why": "只有宽依赖（Exchange）才切 Stage。",
                        "fix": "窄算子在同一 Stage 融合。"
                    },
                    {
                        "mistake": "把 join 当窄依赖。",
                        "why": "join 按 key 重分布，是宽。",
                        "fix": "记住 join/聚合/排序/去重都是宽。"
                    },
                    {
                        "mistake": "以为宽依赖能「避免失败」。",
                        "why": "它只是必要，但恢复成本高。",
                        "fix": "理解宽依赖的容错代价，调优时尽量减少不必要宽依赖。"
                    }
                ],
                "review": "上一课我们看计划里的 *(N) 融合，发现 Shuffle 会打断融合、切出 Stage。可为什么会切？根源在「依赖类型」——有些算子天生在一个 Stage 内，有些必须跨 Stage。",
                "problem": "窄依赖和宽依赖到底差在哪？为什么宽依赖必然是 Stage 的「断点」？失败恢复时二者成本差多少？哪些算子是宽、哪些是窄？",
                "preview": "知道了依赖决定 Stage 边界，下集就把 Job / Stage / Task 三层模型一次讲清——一次 Action 怎么变成一个 Job、怎么按宽依赖切 Stage、怎么按分区切 Task 并行。"
            }
        },
        {
            "title": "Job / Stage / Task 层级",
            "slug": "l4-job-stage-task",
            "description": "建立「一次 Action=一个 Job；Job 按宽依赖切 Stage；每 Stage 按分区数切 Task 并行」层级模型。",
            "objective": "学完本课，你应该能够：建立「一次 Action=一个 Job；Job 按宽依赖切 Stage；每 Stage 按分区数切 Task 并行」的层级模型；理解 Task 数=该 Stage 分区数，Stage 数=宽依赖数+1，Job 内 Stage 顺序执行、Stage 内 Task 并行；并行度调优留 L5。",
            "estimated_minutes": 13,
            "order_index": 7,
            "prerequisites": "",
            "content": {
                "explanation": "【先用人话理解】\n\nSpark 跑一次，不是「一个整体」在动，而是分了三层：你下一个执行命令（Action）叫一次「出货指令」（Job）；这个指令里被 Shuffle 切成几段连续工序（Stage）；每段工序又因为数据被分了很多分区，分给很多工人各干一份（Task）。理解这三层，你看 Spark UI 才不会迷路。\n\n【一个直观的心智模型】\n\n- Job = 接到「出货指令」（一次 Action，如 `count()`/`show()`/`write`）。\n- Stage = 中间几个「不跨车间的连续工序段」，被 Exchange（宽依赖）切开。\n- Task = 每车间分到的一摞活（每个分区一个 Task，Executor 工人并行干）。\n层级：**Job ⊃ Stage ⊃ Task**。\n\n⚠️ 比喻的边界（很重要）：\n① Task 数 = 该 Stage 的分区数（即并行度）；分区越多 Task 越多，但太多反而调度开销大——并行度调优是 Level 5 的内容。\n② Stage 数 = 宽依赖数 + 1：每多一次 Shuffle 就多切一个 Stage。\n③ Job 内 Stage **顺序**执行（前一个 Stage 的 Shuffle 输出是后一个的输入），但**单个 Stage 内 Task 并行**（多个 Executor 同时干各自分区）。这是「宏观串行、微观并行」。\n\n【正式的技术定义】\n\nSpark 执行层级：一个 Action 触发一个 Job；Job 的 DAG 按宽依赖（Shuffle）切分为多个 Stage（Stage 数 = 宽依赖数 + 1）；每个 Stage 按输出 RDD 的分区数切分为多个 Task（每分区一个），由 Executor 并行执行。Task 是最小执行单元。Job/Stage/Task 是理解 Spark UI 与性能调度的核心模型。\n\n【写下代码后，Spark 内部发生了什么】\n\n你写 `df.groupBy('city').count().show()`：`show()` 是 Action → 触发 1 个 Job。这个 Job 里 groupBy 产生 1 次宽依赖 → 切成 2 个 Stage（Stage0：本地读+预聚合；Stage1：跨节点合并+输出）。假设数据有 200 分区 → 每个 Stage 约 200 个 Task，由集群 Executor 并行执行。你在 Spark UI 看到的，就是这棵 Job→Stage→Task 的树。",
                "examples": [
                    {
                        "title": "一次 Action = 一个 Job",
                        "code": "df.groupBy('city').count().show()   # 触发 1 个 Job",
                        "note": "每遇到一个 Action（show/count/write）就起一个 Job；Transformation 不触发。"
                    },
                    {
                        "title": "宽依赖数 → Stage 数",
                        "code": "# groupBy 一次 Shuffle → 2 个 Stage\ndf.groupBy('city').count().explain()",
                        "note": "计划里 Exchange 的个数 + 1 = Stage 数。"
                    },
                    {
                        "title": "分区数 → Task 数",
                        "code": "df = spark.read.parquet('sales').repartition(200)\ndf.groupBy('city').count().show()\n# 每 Stage 约 200 个 Task",
                        "note": "Task 数由该 Stage 分区数决定，即并行度（调优留 L5）。"
                    }
                ],
                "key_points": [
                    "一次 Action = 一个 Job；Job ⊃ Stage ⊃ Task",
                    "Stage 数 = 宽依赖数 + 1（每多一次 Shuffle 多切一个）",
                    "Task 数 = 该 Stage 分区数（并行度）",
                    "Job 内 Stage 顺序执行；单 Stage 内 Task 并行（宏观串行、微观并行）",
                    "并行度/分区数调优留 Level 5"
                ],
                "common_mistakes": [
                    {
                        "mistake": "以为一个 DataFrame 程序 = 一个 Job。",
                        "why": "几个 Action 就几个 Job。",
                        "fix": "数 Action 数 = Job 数。"
                    },
                    {
                        "mistake": "以为 Stage 内也并行出多个 Stage。",
                        "why": "Stage 间是顺序的，只有 Task 层并行。",
                        "fix": "区分「Stage 顺序」与「Task 并行」。"
                    },
                    {
                        "mistake": "把 Task 数当固定值。",
                        "why": "它等于分区数，可配置。",
                        "fix": "想调并行度改分区数（Level 5）。"
                    }
                ],
                "review": "上一课我们讲了窄/宽依赖，知道宽依赖会把执行切成 Stage。可「Stage」之上、「Stage」之内，Spark 还分了几层？一次点击到底发生了什么？",
                "problem": "Job / Stage / Task 三层到底怎么对应？为什么一次 Action 是一个 Job？Stage 为什么按宽依赖切、Task 为什么按分区切？它们谁串行、谁并行？",
                "preview": "学完三层模型，下集做综合练习——给你一段真实代码，你能独立读出它的计划、数出 Stage、认出 Shuffle、指出至少一处 Catalyst 优化。"
            }
        },
        {
            "title": "综合练习",
            "slug": "l4-comprehensive",
            "description": "给一段真实代码，能读/写出其 explain() 输出，数 Stage、认 Shuffle、指出至少一处 Catalyst 优化。",
            "objective": "学完本课，你应该能够：给一段真实代码，独立读/写出其 explain() 输出，数 Stage、认 Shuffle、指出至少一处 Catalyst 优化；理解计划相同 ≠ 运行时性能相同（倾斜/分区数影响，L5/L7）；综合只验证「读得懂」，不要求调优。",
            "estimated_minutes": 18,
            "order_index": 8,
            "prerequisites": "",
            "content": {
                "explanation": "【先用人话理解】\n\n这是 Level 4 的收束：给你一段真实代码，让你像读「施工排程单」一样，把前面所有工位串成一张完整图——先找 Exchange（断点/Shuffle），再数 Stage，最后找 *(N) 融合与下推标记。它逼你把「看计划」从「看得懂单个节点」升级到「看得懂整张图」。\n\n示例任务：读一段 Parquet，过滤 amount>0，按 city 聚合总销售额，输出。\n目标：独立写出/读出它的 explain() 输出，并指出：① 有几处 Exchange（Shuffle）；② 分成几个 Stage；③ 至少一处 Catalyst 优化（下推/裁剪/融合）。\n\n【一个直观的心智模型】\n\n把这次练习想成「把前面所有工位串成一张完整排程单」：\n1. 先找 **Exchange**（断点 / Shuffle）——它是 Stage 的分界线，也是性能重点信号。\n2. 再数 **Stage**（Exchange 数 + 1）。\n3. 最后找 ***(N)** 融合标记与下推/裁剪痕迹——看 Catalyst 帮你省了什么。\n\n⚠️ 比喻的边界（很重要）：\n① 计划相同 ≠ 运行时性能相同：同样一份计划，数据倾斜、分区数不同，真实耗时天差地别（Level 5/L7 才展开）。\n② 本课综合**只验证「读得懂」**——能指认 Shuffle、数出 Stage、找出优化点，就达标；不要求你改写调优。\n③ `explain()` 不触发执行，所以这套「读图」练习随时可做、零成本。\n\n【正式的技术定义】\n\n综合练习 = 对一段真实 Spark 代码，完整应用 Level 4 所学：调用 `explain()` 得到物理计划；识别 Scan/Filter/Project/Aggregate/Exchange 节点；据 Exchange 数判定 Stage 数；据 *(N) 与 Optimized 段判定 WholeStageCodegen 融合与 Catalyst 优化（谓词下推/列裁剪/常量折叠）。输出一份「读图报告」。\n\n【写下代码后，Spark 内部发生了什么】\n\n你写 `spark.read.parquet('sales').filter(df.amount>0).groupBy('city').sum('amount').explain(True)`：Spark 先生成四段计划；你读 Optimized 段看到 Filter 下推、列裁剪；读 Physical 段看到一处 Exchange（groupBy 的 Shuffle）切出 2 个 Stage，且 Stage 内 *(N) 融合。整条分析，你没执行任何数据，纯粹「读图」。",
                "examples": [
                    {
                        "title": "完整读图练习",
                        "code": "df = spark.read.parquet('sales')\ndf.filter(df.amount > 0).groupBy('city').sum('amount').explain(True)\n# 读图：1 处 Exchange → 2 Stage；Optimized 段有 Filter 下推 + 列裁剪",
                        "note": "独立指认 Shuffle、Stage 数、至少一处优化，即达标。"
                    },
                    {
                        "title": "对照不同写法的计划",
                        "code": "# 写法 A：先 filter 后 groupBy\n# 写法 B：直接 groupBy\n# 用 explain(True) 对比二者 Optimized 段是否一致",
                        "note": "Catalyst 会重排，两种写法可能得到相同优化计划——这正是「读图」的价值。"
                    },
                    {
                        "title": "只验证读懂，不调优",
                        "code": "# 目标不是改快，而是说清「它打算怎么算」\ndf.groupBy('city').count().explain()",
                        "note": "综合练习只验收「读得懂」，调优留给 Level 5/L7。"
                    }
                ],
                "key_points": [
                    "读图三步：找 Exchange（Shuffle）→ 数 Stage（Exchange+1）→ 找 *(N) 融合与下推/裁剪",
                    "能指认 Shuffle、数出 Stage、找出至少一处 Catalyst 优化即达标",
                    "计划相同 ≠ 运行时性能相同（倾斜/分区数影响，L5/L7）",
                    "综合只验证「读得懂」，不要求调优",
                    "explain() 不触发执行，读图练习零成本"
                ],
                "common_mistakes": [
                    {
                        "mistake": "综合练习里急着「改代码调快」。",
                        "why": "本课只验收读得懂。",
                        "fix": "先把图读准，调优是 L5/L7。"
                    },
                    {
                        "mistake": "数 Stage 时漏算「初始 Stage」。",
                        "why": "Stage 数 = Exchange 数 + 1。",
                        "fix": "从 1 开始加。"
                    },
                    {
                        "mistake": "把估计行数当真实性能。",
                        "why": "计划数字是估计。",
                        "fix": "真实耗时看 Spark UI（L5）。"
                    }
                ],
                "review": "从「为什么看计划」到「逻辑/物理四段」、「explain 三档」、「读节点」、「Catalyst 规则」、「codegen」、「窄宽依赖」、「Job/Stage/Task」，Level 4 的零件都齐了。",
                "problem": "能不能不靠提示，独立给一段真实代码读出它的 explain() 输出——数出 Stage、认出 Shuffle、指出至少一处 Catalyst 优化？更重要的是，你能否清晰说出「它打算怎么算」？这正是检验你是否真正串起 Level 4 的标准。",
                "preview": "恭喜你走完 Level 4——你现在能「看见」Spark 内部怎么算、怎么优化。但一个更深的问题浮现：「怎么让它真的算得更快？」那是 Level 5（分区/Shuffle 调优）的主场。去测验检验自己吧。🏁"
            }
        }
    ]
}

LEVEL4_QUIZZES = [
    {"lesson_slug": "l4-why-explain", "questions": [
        {"type": "single_choice", "prompt": "执行计划最准确的定位是？", "options": ["结果正确性的保证书", "Spark 打算怎么算的「施工单」", "运行时真实耗时的记录", "数据倾斜的诊断报告"], "correct_index": 1, "explanation": "执行计划描述的是 Spark「打算怎么算」的算子树，是诊断性能的第一视角，而非结果保证或真实耗时。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "为什么「代码写对」不等于「跑得快」？", "options": ["结果正确不保证性能好，写法影响计算量", "Spark 会故意把正确代码跑慢", "Python 比 Scala 慢", "DataFrame 不支持优化"], "correct_index": 0, "explanation": "结果正确只说明语义对；扫描量、是否下推、是否冗余 Shuffle 等会大幅影响性能，与结果是否正确无关。", "dimension": "why"},
        {"type": "single_choice", "prompt": "调用 explain() 时，Spark 内部发生什么？", "options": ["真正执行数据计算", "只打印计划、不执行数据计算", "启动一个 Job", "把全表读进内存"], "correct_index": 1, "explanation": "explain() 只把 Catalyst 规划好的算子树打印出来，不触发任何 Action，数据不会真正算。", "dimension": "mechanism"},
        {"type": "single_choice", "prompt": "怀疑一段聚合特别慢，第一件该做的事？", "options": ["直接重写代码", "先 explain 看计划，定位 Shuffle/扫描", "无脑加大内存", "重启集群"], "correct_index": 1, "explanation": "先用 explain() 看清它「打算怎么算」，才能判断瓶颈在扫描、Shuffle 还是别的，而不是盲目改。", "dimension": "apply"},
        {"type": "single_choice", "prompt": "关于执行计划与真实耗时，正确的是？", "options": ["计划里的数字就是真实耗时", "计划是静态蓝图，看不出运行时倾斜与真实耗时", "计划越复杂跑得越慢", "计划会实时显示耗时"], "correct_index": 1, "explanation": "计划是静态蓝图，描述「打算怎么算」；真实耗时与运行时指标（如倾斜）要看 Spark UI，计划数字只是估计。", "dimension": "comparison"},
        {"type": "single_choice", "prompt": "执行计划主要帮你诊断什么？", "options": ["数据正确性", "性能（它打算怎么算、哪里 Shuffle）", "网络是否连通", "硬盘剩余空间"], "correct_index": 1, "explanation": "执行计划是性能诊断的第一视角，用于看清计算路径与 Shuffle，而非正确性或基础设施。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "为什么从 Level 0-3 一路写代码却不曾「看见」内部怎么算？", "options": ["因为 Catalyst 的优化是黑盒，需 explain 才可见", "因为 Spark 不支持查看", "因为没装插件", "因为代码太简单"], "correct_index": 0, "explanation": "Catalyst 的优化（下推、裁剪等）在背后自动发生，不主动打印；只有调用 explain() 才能看见这份「施工单」。", "dimension": "why"},
        {"type": "single_choice", "prompt": "explain() 是否会触发 Shuffle？", "options": ["会", "不会，它不执行", "视数据量而定", "总是触发"], "correct_index": 1, "explanation": "explain() 不触发执行，自然也不会触发 Shuffle——它只是惰性窥视规划结果。", "dimension": "mechanism"},
        {"type": "single_choice", "prompt": "想「看计划但不让数据真的算」，应该用？", "options": ["show()", "explain()", "count()", "write()"], "correct_index": 1, "explanation": "explain() 不触发 Action，是零成本看计划的工具；show/count/write 都是 Action 会真执行。", "dimension": "apply"},
        {"type": "single_choice", "prompt": "执行计划与 Spark UI 运行时指标的关系是？", "options": ["二者完全一样", "计划是静态蓝图，UI 是运行时实测", "计划比 UI 更准", "UI 没有用处"], "correct_index": 1, "explanation": "计划描述「打算怎么算」（静态），UI 展示「实际跑成什么样」（动态，含真实耗时/字节），两者互补。", "dimension": "comparison"}
    ]},
    {"lesson_slug": "l4-logical-vs-physical", "questions": [
        {"type": "single_choice", "prompt": "逻辑计划（Logical Plan）描述的是？", "options": ["具体用哪个算子实现", "想做什么（语义）", "运行时真实耗时", "网络拓扑"], "correct_index": 1, "explanation": "逻辑计划描述「做什么」，是与具体执行实现无关的操作语义树。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "物理计划（Physical Plan）描述的是？", "options": ["想做什么", "具体用什么算子实现、怎么做", "表是否存在", "列的类型"], "correct_index": 1, "explanation": "物理计划绑定具体实现，如选 HashAggregate 还是 SortAggregate、走 broadcast 还是 sort-merge join。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "为什么执行计划要分逻辑和物理？", "options": ["因为 Catalyst 要先明确意图（逻辑），再绑定具体实现（物理）", "历史遗留，没有原因", "为了让 SQL 更慢", "为了兼容 Hive"], "correct_index": 0, "explanation": "先有与实现无关的语义（逻辑），再经优化、选实现（物理），分层让优化与执行策略解耦。", "dimension": "why"},
        {"type": "single_choice", "prompt": "哪个阶段做类型 / 表 / 列存在性检查？", "options": ["Parsed", "Analyzed", "Optimized", "Physical"], "correct_index": 1, "explanation": "Analyzed 阶段由 Analyzer 借助 Catalog 校验元数据，很多「表/列不存在」「类型不匹配」在此爆出。", "dimension": "mechanism"},
        {"type": "single_choice", "prompt": "哪个阶段做等价改写（下推 / 裁剪 / 常量折叠）？", "options": ["Parsed", "Analyzed", "Optimized", "Physical"], "correct_index": 2, "explanation": "Optimizer 在 Optimized 阶段套用规则做等价重写，降低后续执行成本。", "dimension": "mechanism"},
        {"type": "single_choice", "prompt": "想看完整四段（Parsed/Analyzed/Optimized/Physical），用？", "options": ["explain()", "explain(True)", "show()", "count()"], "correct_index": 1, "explanation": "explain(True) 等价于 explain('extended')，会打印全部四段逻辑/物理计划。", "dimension": "apply"},
        {"type": "single_choice", "prompt": "Analyzed 阶段抛出的常见错误类型是？", "options": ["SyntaxError", "AnalysisException（表或列不存在等）", "OutOfMemoryError", "NetworkError"], "correct_index": 1, "explanation": "表/列不存在、类型不匹配等元数据校验失败，会抛 AnalysisException，发生在 Analyzed 阶段。", "dimension": "comparison"},
        {"type": "single_choice", "prompt": "Optimized 阶段「等价改写」的前提是？", "options": ["结果不变、只更省", "结果会变得更快", "随机挑选算子", "必须改变语义"], "correct_index": 0, "explanation": "优化的铁律是等价：输出结果与未优化一致，只是少读少算更省。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "Physical 阶段才绑定什么？", "options": ["具体算子实现（如 HashAgg vs SortAgg）", "表名", "列名", "SQL 语法"], "correct_index": 0, "explanation": "逻辑计划还停留在语义层；到 Physical 才选具体算子实现与执行策略。", "dimension": "mechanism"},
        {"type": "single_choice", "prompt": "关于「逻辑计划 vs 物理计划」，正确的是？", "options": ["逻辑计划已经绑定具体实现", "逻辑=做什么，物理=怎么做", "物理计划不存在", "二者毫无关系"], "correct_index": 1, "explanation": "逻辑计划描述意图（做什么），物理计划描述落地方式（怎么做），是同一计算的两种粒度。", "dimension": "comparison"}
    ]},
    {"lesson_slug": "l4-explain-api", "questions": [
        {"type": "single_choice", "prompt": "默认 explain()（无参）打印什么？", "options": ["四段全部", "仅 Physical Plan", "仅 Parsed", "运行时指标"], "correct_index": 1, "explanation": "explain() 无参默认只打印 Physical Plan，最聚焦「最终怎么跑」。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "想看 Parsed/Analyzed/Optimized/Physical 四段，用？", "options": ["explain()", "explain(True)", "explain(False)", "show()"], "correct_index": 1, "explanation": "explain(True) 打印完整四段；想看 Catalyst 怎么优化就用它。", "dimension": "apply"},
        {"type": "single_choice", "prompt": "explain(True) 等价于？", "options": ["explain('extended')", "explain('formatted')", "show()", "count()"], "correct_index": 0, "explanation": "explain(True) 是 explain('extended') 的快捷写法，二者都打印四段。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "缩进树状、最易人眼扫读的版本用？", "options": ["explain()", "explain(mode='formatted')", "explain(True)", "print()"], "correct_index": 1, "explanation": "explain(mode='formatted') 以缩进树状结构打印，层级清晰，适合读图。", "dimension": "apply"},
        {"type": "single_choice", "prompt": "为什么 explain() 可以安全反复调用？", "options": ["它不触发执行，只是惰性窥视", "因为它运行极快", "因为它有缓存", "因为它只读内存"], "correct_index": 0, "explanation": "explain() 不触发任何 Action，只打印规划结果，所以反复看零成本、零副作用。", "dimension": "why"},
        {"type": "single_choice", "prompt": "explain() 会触发真正的数据计算吗？", "options": ["会", "不会", "有时", "总是"], "correct_index": 1, "explanation": "explain() 是诊断 API，不触发 Action，数据不会被真正计算。", "dimension": "mechanism"},
        {"type": "single_choice", "prompt": "mode='formatted' 需要什么版本支持？", "options": ["Spark 1.x", "Spark 2.3+", "Python 3.0+", "无要求"], "correct_index": 1, "explanation": "formatted 模式在 Spark 2.3 才引入；老版本只能用 explain(True) 看四段。", "dimension": "comparison"},
        {"type": "single_choice", "prompt": "真正会触发数据执行的是？", "options": ["explain()", "show()", "print()", "type()"], "correct_index": 1, "explanation": "show() 是 Action，会真正触发作业；explain 不会。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "只想看「最终怎么跑」（最聚焦），用？", "options": ["explain()", "explain(True)", "explain('formatted')", "无此档位"], "correct_index": 0, "explanation": "默认 explain() 只看 Physical Plan，最适合快速聚焦最终执行方式。", "dimension": "apply"},
        {"type": "single_choice", "prompt": "关于 explain(True) 多打出的三段，正确的是？", "options": ["那是额外干活产生的", "是规划过程，不是额外执行", "是真实耗时", "没有用处"], "correct_index": 1, "explanation": "Parsed/Analyzed/Optimized 是 Catalyst 的规划产物，打印它们不触发任何数据执行。", "dimension": "comparison"}
    ]},
    {"lesson_slug": "l4-read-plan", "questions": [
        {"type": "single_choice", "prompt": "执行计划里 Scan 节点代表？", "options": ["进货口（从数据源读取）", "过滤行", "选列", "分组汇总"], "correct_index": 0, "explanation": "Scan 是数据源读取节点，对应「进货口」。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "Filter 节点代表？", "options": ["进货", "入口筛（按条件过滤行）", "选列", "汇总"], "correct_index": 1, "explanation": "Filter 对行做条件过滤，对应流水线入口的筛子。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "Exchange 节点代表？", "options": ["读取数据", "过滤", "Shuffle（货在空中飞，按 key 重分布）", "选列"], "correct_index": 2, "explanation": "Exchange 即 Shuffle，数据按 key 跨节点重分布，是性能重点信号。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "为什么 Exchange 是最该警惕的节点？", "options": ["它必触发 Shuffle（序列化+网络+反序列化开销）", "它不干活", "它慢是因为语法", "它会报错"], "correct_index": 0, "explanation": "Exchange = Shuffle，涉及序列化、网络传输与反序列化，是主要性能成本来源之一。", "dimension": "why"},
        {"type": "single_choice", "prompt": "计划中的 *(N) 标记表示？", "options": ["第 N 个 Stage", "WholeStageCodegen 融合的算子数", "行数", "分区数"], "correct_index": 1, "explanation": "*(N) 表示 N 个相邻算子被融合成单个方法，不是阶段编号。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "计划里标注的行数 / 字节是？", "options": ["真实实测值", "优化器的估计值", "用户手动设定", "网络带宽"], "correct_index": 1, "explanation": "计划中的统计量是 Catalyst 的估计，非实测；真实量看 Spark UI。", "dimension": "mechanism"},
        {"type": "single_choice", "prompt": "想一眼看出「哪里发生了 Shuffle」，看计划里哪个节点？", "options": ["Scan", "Exchange", "Aggregate", "Project"], "correct_index": 1, "explanation": "Exchange 就是 Shuffle 的物理信号，认准它就能定位跨节点重分布。", "dimension": "apply"},
        {"type": "single_choice", "prompt": "关于 Aggregate 节点，正确的是？", "options": ["它是分组汇总（复用 L2 水果分拣派对）", "它是读数据", "它不消耗资源", "它不产生 Shuffle"], "correct_index": 0, "explanation": "Aggregate 对应 groupBy 聚合，复用「水果分拣派对」隐喻；聚合通常伴随 Shuffle。", "dimension": "comparison"},
        {"type": "single_choice", "prompt": "Project 节点代表？", "options": ["选列（投影）", "过滤行", "汇总", "读取"], "correct_index": 0, "explanation": "Project 做列投影/表达式计算，对应「只挑要的字段装箱」。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "计划文本里的「估计行数」该怎么对待？", "options": ["当作真相", "当作估计，真实看 Spark UI", "直接忽略", "当作错误信息"], "correct_index": 1, "explanation": "那是优化器估计值，可能严重偏离真实；性能判断以运行时指标为准。", "dimension": "comparison"}
    ]},
    {"lesson_slug": "l4-catalyst-rules", "questions": [
        {"type": "single_choice", "prompt": "谓词下推（Predicate Pushdown）是？", "options": ["把过滤尽早推到读取端", "把列裁掉", "常量折叠", "排序"], "correct_index": 0, "explanation": "谓词下推让过滤在读取端尽早发生，减少后续处理的数据量（复用 L2「开天眼」）。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "列裁剪（Column Pruning）是？", "options": ["过滤行", "只保留需要的列、不读其余列", "常量折叠", "去重"], "correct_index": 1, "explanation": "列裁剪去掉不需要的列，未选的列根本不进入 Scan，少读少搬。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "常量折叠（Constant Folding）是？", "options": ["编译期把 1+1 算成 2", "谓词下推", "列裁剪", "排序"], "correct_index": 0, "explanation": "常量折叠在优化期就把能确定的表达式算好，不拖到运行时。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "为什么 Catalyst 的优化是「等价」的？", "options": ["结果不变，只更省", "结果会变快", "随机选择算子", "必须改变语义"], "correct_index": 0, "explanation": "优化规则保证输出结果与未优化一致，只是减少计算量。", "dimension": "why"},
        {"type": "single_choice", "prompt": "哪种情况会让 Catalyst 的下推 / 裁剪失效？", "options": ["用内置函数", "用 UDF 或复杂嵌套", "用 SQL", "用 select"], "correct_index": 1, "explanation": "Catalyst 看不懂 UDF 内部逻辑，无法下推/裁剪，所以能不用 UDF 就不用（呼应 L3）。", "dimension": "mechanism"},
        {"type": "single_choice", "prompt": "重读场景想最大化下推收益，优先用哪种格式？", "options": ["csv", "Parquet（列式存储）", "纯文本 txt", "无所谓"], "correct_index": 1, "explanation": "Parquet 列式存储能配合做列裁剪/谓词下推；csv 不能按列跳过，收益有限。", "dimension": "apply"},
        {"type": "single_choice", "prompt": "关于优化器，正确的是？", "options": ["它是神仙，什么都能优化", "它看不懂 UDF 内部逻辑", "它会改变计算结果", "它不进行任何优化"], "correct_index": 1, "explanation": "优化器强大但有边界：遇到 UDF/复杂嵌套就无能为力，无法下推。", "dimension": "comparison"},
        {"type": "single_choice", "prompt": "null 传播（Null Propagation）属于哪类规则？", "options": ["Catalyst 等价改写规则", "网络传输规则", "存储格式规则", "与优化无关"], "correct_index": 0, "explanation": "null 传播是 Catalyst 在 Optimized 阶段做的一种等价简化规则。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "为什么普通 csv 的下推收益有限？", "options": ["它不能按列跳过", "它读取更快", "它更智能", "它自动压缩"], "correct_index": 0, "explanation": "csv 是行式文本，无法像列式存储那样跳过不需要的列，下推/裁剪收益受限。", "dimension": "why"},
        {"type": "single_choice", "prompt": "你先写 filter 后写 select，优化器最终会？", "options": ["严格按你写的顺序执行", "重排让过滤尽早、列裁剪合并进 Scan", "直接报错", "忽略你的写法"], "correct_index": 1, "explanation": "Catalyst 会重排算子，让过滤下推、列裁剪合并进 Scan，顺序由优化器决定。", "dimension": "mechanism"}
    ]},
    {"lesson_slug": "l4-wholestage-codegen", "questions": [
        {"type": "single_choice", "prompt": "WholeStageCodegen 是？", "options": ["把相邻算子融合成单个 Java 方法", "一种存储格式", "一种网络协议", "一种 UDF"], "correct_index": 0, "explanation": "WholeStageCodegen 将同 Stage 内相邻算子编译成一个手写 Java 方法，消除逐算子开销。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "为什么要做 codegen 融合？", "options": ["省掉逐算子的虚函数调用与中间对象分配", "它其实更慢", "它会改变结果", "它是强制要求"], "correct_index": 0, "explanation": "融合消除了逐算子虚函数调用与中间对象，数据以二进制行格式在算子间流转，更快。", "dimension": "why"},
        {"type": "single_choice", "prompt": "计划中的 *(N) 标记表示？", "options": ["融合的算子数", "第 N 个 Stage", "行数", "分区数"], "correct_index": 0, "explanation": "*(N) 即 WholeStageCodegen 融合的算子个数。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "什么会打断 codegen 融合？", "options": ["Exchange（Shuffle）边界", "select", "filter", "Project"], "correct_index": 0, "explanation": "Exchange 处数据要跨节点重分布，无法在同一个本地方法里连续跑，融合必然断开。", "dimension": "mechanism"},
        {"type": "single_choice", "prompt": "关于融合与 Stage，正确的是？", "options": ["Exchange 切断融合，也是 Stage 边界", "融合可以无限延续", "Exchange 不影响融合", "Stage 没有边界"], "correct_index": 0, "explanation": "Exchange 既是融合断点，也是 Stage 的切分点，二者一致。", "dimension": "comparison"},
        {"type": "single_choice", "prompt": "Tungsten 在本课的角色是？", "options": ["紧凑二进制零件标准", "一种数据库", "网络层", "AI 模型"], "correct_index": 0, "explanation": "Tungsten 是底层紧凑二进制执行标准（复用 L2 边界），内存/堆外细节留 L7。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "为什么某些表达式会「回退」（fallback）？", "options": ["不支持 codegen 的表达式回退到解释执行", "它其实更快", "它会报错", "它被忽略"], "correct_index": 0, "explanation": "部分复杂/不支持的表达式无法编译进融合方法，会回退到逐算子解释执行。", "dimension": "why"},
        {"type": "single_choice", "prompt": "内存布局、堆外、编码字节级细节属于？", "options": ["本课深挖内容", "Level 7 性能调优", "Level 0 内容", "与 Spark 无关"], "correct_index": 1, "explanation": "那些是 Level 7 性能调优的主题，本课只把 Tungsten 当「紧凑零件标准」复用。", "dimension": "comparison"},
        {"type": "single_choice", "prompt": "看到 *(4) 说明？", "options": ["有 4 个 Stage", "有 4 个算子被融合", "有 4 行数据", "有 4 个分区"], "correct_index": 1, "explanation": "*(N) 的 N 是融合的算子数，不是 Stage/行/分区数。", "dimension": "apply"},
        {"type": "single_choice", "prompt": "groupBy 的 Exchange 之后，*(N) 会？", "options": ["继续累加", "重新从 1 计数", "直接消失", "保持不变"], "correct_index": 1, "explanation": "Shuffle 切断融合，Exchange 之后的算子重新从 1 开始计数融合。", "dimension": "mechanism"}
    ]},
    {"lesson_slug": "l4-dependency-narrow-wide", "questions": [
        {"type": "single_choice", "prompt": "窄依赖（Narrow Dependency）是？", "options": ["子分区只依赖父局部分区，无 Shuffle", "子分区依赖父全部分区", "必然 Shuffle", "跨节点重排"], "correct_index": 0, "explanation": "窄依赖中每个子分区只依赖父的有限个分区，无需跨节点搬数据。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "宽依赖（Wide Dependency）是？", "options": ["子分区依赖父全部分区中同 key 的数据，必 Shuffle", "无 Shuffle", "纯本地", "只是 select"], "correct_index": 0, "explanation": "宽依赖需要把同 key 的数据汇聚，必然触发跨节点重分布（Shuffle）。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "为什么说宽依赖是 Stage 的「断点」？", "options": ["因为它触发 Exchange，把执行切成不同 Stage", "因为它跑得更快", "因为它无 Shuffle", "因为它纯本地"], "correct_index": 0, "explanation": "宽依赖处的 Shuffle（Exchange）就是 Stage 的切分线，也是融合断点。", "dimension": "why"},
        {"type": "single_choice", "prompt": "窄依赖失败时的恢复成本？", "options": ["只重算那个局部分区（便宜）", "重算整个上游重排（贵）", "无法恢复", "全部重来"], "correct_index": 0, "explanation": "窄依赖血缘短、数据在本地，某个分区丢了只需重算局部。", "dimension": "mechanism"},
        {"type": "single_choice", "prompt": "宽依赖失败时的恢复成本？", "options": ["只重算局部", "重算整个上游重排（贵）", "无需恢复", "和窄依赖一样"], "correct_index": 1, "explanation": "宽依赖下游依赖全局按 key 汇聚，上游任何分区丢失都要整体重算，代价大。", "dimension": "mechanism"},
        {"type": "single_choice", "prompt": "以下哪组算子都是窄依赖？", "options": ["map / filter / select", "groupBy / join / orderBy", "union / distinct / join", "groupBy / select"], "correct_index": 0, "explanation": "map/filter/select 都只做本地转换，无 Shuffle，是窄依赖。", "dimension": "apply"},
        {"type": "single_choice", "prompt": "下列哪个是宽依赖（必 Shuffle）？", "options": ["filter", "select", "map", "groupBy"], "correct_index": 3, "explanation": "groupBy 需按 key 重分布，是宽依赖；map/filter/select 是窄。", "dimension": "apply"},
        {"type": "single_choice", "prompt": "groupBy 的「部分聚合」属于？", "options": ["纯窄依赖", "纯宽依赖", "窄+宽两阶段", "无依赖"], "correct_index": 2, "explanation": "groupBy 先本地预聚合（窄），再跨节点合并（宽），是两阶段。", "dimension": "comparison"},
        {"type": "single_choice", "prompt": "决定 Stage 边界的是？", "options": ["宽依赖（Exchange）", "窄依赖", "select", "Project"], "correct_index": 0, "explanation": "只有宽依赖（Shuffle）才会把执行切成不同 Stage。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "关于窄/宽依赖的容错，正确的是？", "options": ["二者恢复成本一样", "窄依赖便宜、宽依赖贵", "宽依赖更便宜", "二者都很贵"], "correct_index": 1, "explanation": "窄依赖局部重算即可，宽依赖要整体重排，容错成本差异明显。", "dimension": "comparison"}
    ]},
    {"lesson_slug": "l4-job-stage-task", "questions": [
        {"type": "single_choice", "prompt": "一次 Action（如 show/count/write）触发？", "options": ["一个 Job", "一个 Stage", "一个 Task", "什么都不触发"], "correct_index": 0, "explanation": "每个 Action 对应一个 Job；Transformation 不会触发 Job。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "Stage 数等于？", "options": ["宽依赖数 + 1", "分区数", "Task 数", "Action 数"], "correct_index": 0, "explanation": "每多一次 Shuffle（宽依赖）就多切一个 Stage，所以 Stage 数 = 宽依赖数 + 1。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "Task 数等于？", "options": ["该 Stage 的分区数（并行度）", "Stage 数", "Job 数", "宽依赖数"], "correct_index": 0, "explanation": "每个分区对应一个 Task，所以 Task 数 = 该 Stage 输出 RDD 的分区数。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "为什么 Job 内的 Stage 是顺序执行的？", "options": ["后一个 Stage 依赖前一个 Stage 的 Shuffle 输出", "因为 Spark 不支持并行", "因为随机", "没有原因"], "correct_index": 0, "explanation": "Stage 间有数据依赖（Shuffle 输出），必须前一个算完下一个才能开始。", "dimension": "why"},
        {"type": "single_choice", "prompt": "单个 Stage 内的 Task 是？", "options": ["顺序执行", "并行执行（多 Executor 各干一个分区）", "不执行", "串行排队"], "correct_index": 1, "explanation": "同一 Stage 内各分区 Task 由集群 Executor 并行执行，这是「微观并行」。", "dimension": "mechanism"},
        {"type": "single_choice", "prompt": "想调整并行度（留给 Level 5），应改？", "options": ["分区数", "Stage 数", "Job 数", "Action 数"], "correct_index": 0, "explanation": "Task 数由分区数决定，所以并行度调优本质是调分区数（Level 5 展开）。", "dimension": "apply"},
        {"type": "single_choice", "prompt": "层级关系正确的是？", "options": ["Job ⊃ Stage ⊃ Task", "Task ⊃ Stage ⊃ Job", "Stage ⊃ Job ⊃ Task", "三者无关系"], "correct_index": 0, "explanation": "一个 Job 包含多个 Stage，一个 Stage 包含多个 Task，层级嵌套。", "dimension": "comparison"},
        {"type": "single_choice", "prompt": "Spark 的最小执行单元是？", "options": ["Job", "Stage", "Task", "Action"], "correct_index": 2, "explanation": "Task 是调度与执行的最小单位，运行在 Executor 上处理单个分区。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "一段 groupBy(...).show() 通常产生几个 Job？", "options": ["0", "1（一个 Action）", "2", "3"], "correct_index": 1, "explanation": "show() 是一个 Action，触发恰好一个 Job。", "dimension": "mechanism"},
        {"type": "single_choice", "prompt": "关于并行模型，正确的是？", "options": ["宏观串行、微观并行", "全部串行", "全部并行", "没有并行"], "correct_index": 0, "explanation": "Job 内 Stage 顺序（宏观串行），单 Stage 内 Task 并行（微观并行）。", "dimension": "comparison"}
    ]},
    {"lesson_slug": "l4-comprehensive", "questions": [
        {"type": "single_choice", "prompt": "综合读图的第一步是？", "options": ["找 Exchange（Shuffle）", "数 Task", "打开 Spark UI", "改代码"], "correct_index": 0, "explanation": "先找 Exchange 定位 Shuffle 与 Stage 边界，是读图的起点。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "数 Stage 的公式是？", "options": ["Exchange 数 + 1", "分区数", "Task 数", "Action 数"], "correct_index": 0, "explanation": "Stage 数 = 宽依赖（Exchange）数 + 1。", "dimension": "apply"},
        {"type": "single_choice", "prompt": "一段 groupBy 聚合代码通常有几处 Exchange？", "options": ["0", "1（聚合必 Shuffle）", "2", "3"], "correct_index": 1, "explanation": "groupBy 需按 key 重分布，产生 1 次 Shuffle（Exchange）。", "dimension": "mechanism"},
        {"type": "single_choice", "prompt": "指认「至少一处 Catalyst 优化」应看哪段？", "options": ["Physical 段", "Optimized 段的下推/裁剪痕迹", "Spark UI", "运行日志"], "correct_index": 1, "explanation": "Optimized 段集中体现谓词下推、列裁剪等等价改写。", "dimension": "apply"},
        {"type": "single_choice", "prompt": "为什么「计划相同 ≠ 运行时性能相同」？", "options": ["数据倾斜、分区数等运行时因素影响真实耗时", "计划本身有错", "两者毫无关系", "Spark 会随机变慢"], "correct_index": 0, "explanation": "同样计划在不同数据分布/分区数下真实耗时差异大，倾斜等是运行时因素（L5/L7）。", "dimension": "why"},
        {"type": "single_choice", "prompt": "Level 4 综合练习的达标标准是？", "options": ["把代码改快", "读懂：认 Shuffle、数 Stage、找优化点", "完全重写", "立即调优"], "correct_index": 1, "explanation": "综合只验收「读得懂」，不要求改写或调优。", "dimension": "comparison"},
        {"type": "single_choice", "prompt": "explain() 在综合练习中的角色是？", "options": ["触发执行", "零成本的读图工具", "修改数据", "没有作用"], "correct_index": 1, "explanation": "explain() 不执行，是随时可做、零成本的读图手段。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "对照两种写法，若 Optimized 段一致说明？", "options": ["Catalyst 重排后二者等价", "结果一定不同", "会报错", "毫无意义"], "correct_index": 0, "explanation": "优化器会把不同写法重排成等价计划，这正是读图能帮你判断「写法差异是否影响性能」的价值。", "dimension": "mechanism"},
        {"type": "single_choice", "prompt": "读图时 *(N) 告诉你？", "options": ["融合的算子数", "Stage 数", "行数", "分区数"], "correct_index": 0, "explanation": "*(N) 表示本地融合的算子个数，是 WholeStageCodegen 的标志。", "dimension": "mechanism"},
        {"type": "single_choice", "prompt": "关于综合练习与调优，正确的是？", "options": ["综合只验读懂，调优留 L5/L7", "必须当场调优", "不用读图", "读图毫无用处"], "correct_index": 0, "explanation": "本课目标是「看得懂计划」，真正的调优在 Level 5（分区/Shuffle）与 Level 7（性能）展开。", "dimension": "comparison"}
    ]}
]


def upsert():
    # 1) 合并进 course_seed.json
    with open(SEED, encoding="utf-8") as f:
        data = json.load(f)
    exists = any(lv.get("order_index") == 4 for lv in data["levels"])
    if not exists:
        data["levels"].append(LEVEL4)
        with open(SEED, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print("已写入 course_seed.json（Level 4）")
    else:
        print("course_seed.json 已存在 Level 4，跳过 JSON 写入")

    # 2) 合并进 quiz_seed.json
    with open(QUIZ, encoding="utf-8") as f:
        qdata = json.load(f)
    qentries = qdata.setdefault("quizzes", [])
    existing = {e["lesson_slug"] for e in qentries}
    added_q = 0
    for entry in LEVEL4_QUIZZES:
        if entry["lesson_slug"] in existing:
            continue
        qentries.append(entry)
        existing.add(entry["lesson_slug"])
        added_q += 1
    if added_q:
        with open(QUIZ, "w", encoding="utf-8") as f:
            json.dump(qdata, f, ensure_ascii=False, indent=2)
        print(f"已写入 quiz_seed.json（新增 {added_q} 个 lesson 的题库）")
    else:
        print("quiz_seed.json 已包含 Level 4 题库，跳过")

    # 3) upsert 进数据库
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT id,title FROM course_levels WHERE order_index=4")
    row = cur.fetchone()
    if row:
        level_id = row[0]
        print(f"Level 4 已存在于 DB (id={level_id})，仅补充缺失 lesson")
    else:
        cur.execute(
            "INSERT INTO course_levels (title, description, order_index, status) VALUES (?,?,?,?)",
            (LEVEL4["title"], LEVEL4["description"], LEVEL4["order_index"], "active"))
        level_id = cur.lastrowid
        print(f"已插入 Level 4 (id={level_id})")

    inserted_lessons = 0
    for ls in LEVEL4["lessons"]:
        cur.execute("SELECT id FROM lessons WHERE slug=?", (ls["slug"],))
        if cur.fetchone():
            continue
        cur.execute(
            """INSERT INTO lessons (level_id, title, slug, description, objective,
               estimated_minutes, order_index, prerequisites, content)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (level_id, ls["title"], ls["slug"], ls.get("description",""), ls.get("objective",""),
             ls.get("estimated_minutes",15), ls["order_index"], ls.get("prerequisites",""),
             json.dumps(ls["content"], ensure_ascii=False)))
        inserted_lessons += 1
    print(f"新增 lesson 数：{inserted_lessons}")

    # 4) upsert quizzes
    inserted_q = 0
    for entry in LEVEL4_QUIZZES:
        cur.execute("SELECT id FROM lessons WHERE slug=?", (entry["lesson_slug"],))
        lr = cur.fetchone()
        if not lr:
            print(f"警告：quiz 找不到 lesson {entry['lesson_slug']}，跳过")
            continue
        lesson_id = lr[0]
        cur.execute("SELECT COUNT(*) FROM quizzes WHERE lesson_id=?", (lesson_id,))
        if cur.fetchone()[0]:
            continue
        for i, q in enumerate(entry["questions"]):
            cur.execute(
                """INSERT INTO quizzes (lesson_id, type, prompt, options, correct_index,
                   explanation, order_index, dimension)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (lesson_id, q.get("type","single_choice"), q["prompt"],
                 json.dumps(q["options"], ensure_ascii=False), q["correct_index"],
                 q.get("explanation",""), i, q.get("dimension")))
            inserted_q += 1
    conn.commit()
    conn.close()
    print(f"新增 quiz 题数：{inserted_q}")


if __name__ == "__main__":
    upsert()
