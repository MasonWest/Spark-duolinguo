# -*- coding: utf-8 -*-
"""Level 5 / Level 6 技术审查修复（2026-09-10）

用法：
  python fix_level56_20260910.py --dry     # 只报命中，不写库
  python fix_level56_20260910.py --apply   # 写入真库

修复按四个维度：技术事实 / 示例真实性 / 概念边界 / 版本敏感性。
所有替换都是「精确字符串 → 新字符串」，命中数为 0 会明确报错，不会静默跳过。
"""
import sqlite3
import sys

DB = "spark_quest.db"

# ---------------------------------------------------------------- 课文替换
# {lesson_id: [(old, new), ...]}   —— 递归作用于 content JSON 的每个字符串叶子
LESSON_PATCHES = {
    # ---------------- L5-1 分区是什么 ----------------
    40: [
        (
            "③ HDFS block 与分区不是 1:1：Spark 默认按 block 数给初始分区，但 repartition / 不同输入格式会改变它，别把「block 数」当成「分区数」。",
            "③ HDFS block 与分区不是 1:1：读文件时的初始分区数由**实现**决定——DataFrame 读取看 `spark.sql.files.maxPartitionBytes`（默认 128MB）与文件是否可切分；RDD（`sc.textFile`）看 InputFormat 的 split 划分（默认大小接近 HDFS block）。它「常常正好接近 block 数」只是巧合，不是规则；repartition / 不同输入格式都会改变它。别把「block 数」当成「分区数」。",
        ),
        (
            "你写 `df = spark.read.parquet('sales')`，Spark 先按文件物理布局（block / 文件数）算出初始分区数——假设 128 个。",
            "你写 `df = spark.read.parquet('sales')`，Spark 先按文件大小与 `spark.sql.files.maxPartitionBytes`（默认 128MB）算出初始分区数——假设 128 个。",
        ),
        (
            "初始值通常来自输入文件的 block 数。",
            "初始值来自「怎么读」：DataFrame 按 `spark.sql.files.maxPartitionBytes`（默认 128MB）切，恰好常与 block 数接近，但两者不是一回事。",
        ),
        (
            "分区数 = 并行 Task 数 = 理论并行度（复用 L4 Job/Stage/Task）",
            "分区数 = 并行 Task 数 = 理论并行度（实际并发上限还受集群可用 core 数限制；复用 L4 Job/Stage/Task）",
        ),
    ],
    # ---------------- L5-2 分区数与并行度 ----------------
    41: [
        (
            "并行度（Parallelism）指同时执行的 Task 数量，在 Spark 中等于该 Stage 的分区数。",
            "并行度（Parallelism）指同时执行的 Task 数量。在 Spark 中它**理论上**等于该 Stage 的分区数，但实际能同时跑多少还受集群可用 core 数限制——分区数多于 core 数时，多出来的 Task 要排队等核。",
        ),
        (
            "② 默认分区数有来源（如读文件按 block、shuffle 按 spark.sql.shuffle.partitions 默认 200），但这些默认值未必适合你的数据，本课点到为止。",
            "② 默认分区数有来源（如读文件按 `spark.sql.files.maxPartitionBytes`、shuffle 按 `spark.sql.shuffle.partitions` 默认 200），但这些默认值未必适合你的数据，本课点到为止。",
        ),
        (
            "③ 分区数与「结果正确性」无关，只与「快慢」有关；别为了「算对」去纠结分区数。",
            "③ 分区数与「结果正确性」无关，只与「快慢」有关；别为了「算对」去纠结分区数。\n④ ⚠️ **版本提示**：Spark 3.2+ 默认开启 AQE，`spark.sql.shuffle.partitions`（默认 200）只是 shuffle 后的**初始**分区数——运行时 AQE 会按真实数据量把小分区合并掉，所以「200」是初始上界，不一定是最终分区数；`explain()` 也会因此显示 `AdaptiveSparkPlan isFinalPlan=false`。",
        ),
        (
            "分区数 = 并行 Task 数 = 理论并行度",
            "分区数 = 并行 Task 数 = 理论并行度（实际并发还受可用 core 数限制）",
        ),
        (
            "shuffle 类操作默认按这个值定分区数；它只是默认值，调优留 Level 7。",
            "shuffle 类操作默认按这个值定**初始**分区数；它只是默认值，且 Spark 3.2+ 的 AQE 会在运行时再合并，调优留 Level 7。",
        ),
    ],
    # ---------------- L5-3 Shuffle 是什么 ----------------
    42: [
        (
            "① Shuffle 不是「错误」，而是宽依赖（Wide Dependency）的必然代价——只要计算需要「全局按 key 汇聚」，它就必须发生，躲不掉（除非本就无需汇聚）。",
            "① Shuffle 不是「错误」，而是宽依赖（Wide Dependency）的**通常**代价——需要「全局按 key 汇聚」时通常必须发生。但有两个重要例外：上游**已经**按该 key 分好区（如刚 `repartition('city')`），可以省掉 Exchange；JOIN 走 Broadcast Join 时小表侧也不产生 ShuffleExchange（Level 6 展开）。",
        ),
        (
            "Shuffle 是 Spark 在执行宽依赖算子时，将各分区数据按 key 重新哈希/排序并跨节点传输、再在目标节点重新分区的物理过程。它是宽依赖（如 groupBy / join / orderBy / distinct）的物化，对应执行计划里的 Exchange 节点。",
            "Shuffle 是 Spark 在执行宽依赖算子时，将各分区数据按 key 重新哈希/排序并跨节点传输、再在目标节点重新分区的物理过程。它是宽依赖的物化，对应执行计划里的 Exchange 节点。典型例子有 groupBy / orderBy / distinct，以及 **shuffle-based 的 join**（Sort Merge Join / Shuffle Hash Join）；Broadcast Join 不产生 ShuffleExchange，不属于宽依赖（Level 6）。此外，若上游已按该 key 分区，这些操作也可以不插入 Exchange。",
        ),
        (
            "知道 Shuffle 不是「错误」而是宽依赖的必然代价；",
            "知道 Shuffle 不是「错误」而是宽依赖的通常代价（上游已按该 key 分区、或走 Broadcast Join 时可省）；",
        ),
        (
            "Shuffle 不是错误，是宽依赖的必然代价（躲不掉）",
            "Shuffle 不是错误，是宽依赖的通常代价；上游已按该 key 分区或走 Broadcast Join 时可省",
        ),
    ],
    # ---------------- L5-4 Shuffle 为什么贵 ----------------
    43: [
        (
            "② 当内存放不下中间结果，Spark 会把数据 spill 到磁盘，磁盘 I/O 比内存慢几个数量级，进一步放大代价。",
            "② 当内存放不下中间结果，Spark 会把数据 spill 到磁盘；磁盘（尤其随机 I/O）通常比内存慢 1~2 个数量级，进一步放大代价。",
        ),
        (
            "内存不足会 spill 到磁盘，I/O 慢几个数量级",
            "内存不足会 spill 到磁盘，I/O 通常比内存慢 1~2 个数量级",
        ),
    ],
    # ---------------- L5-5 窄/宽依赖在分区层面的含义 ----------------
    44: [
        (
            "宽依赖父分区数据发往多个子分区（必 Shuffle）；理解「Stage 边界 = Shuffle 发生的切口」",
            "宽依赖父分区数据发往多个子分区（通常需要 Shuffle；上游已按该 key 分区时可省，Broadcast Join 不属于宽依赖）；理解「Stage 边界 = Shuffle 发生的切口」",
        ),
        (
            "Narrow Dependency 中每个子分区只由有限个（通常 1 个或同节点）父分区计算得到，无需跨节点重排；Wide Dependency 中每个子分区依赖所有父分区中同 key 的数据，必须跨节点重分布（Shuffle）。宽依赖处即 Stage 边界，也是融合（WholeStageCodegen）的断点。",
            "Narrow Dependency 中每个子分区只由**有限个**（通常 1 个）父分区计算得到，无需跨节点重排——注意窄依赖并不要求父子在同一节点，它强调的是「依赖的父分区数量有界」。Wide Dependency 中每个子分区依赖所有父分区中同 key 的数据，通常需要跨节点重分布（Shuffle）——除非上游已经按同一 key 分好区，此时可省掉 Exchange。宽依赖处即 Stage 边界，也是融合（WholeStageCodegen）的断点。补充：Broadcast Join 的小表侧只是被广播分发，并不满足「子分区依赖所有父分区同 key 数据」的定义，它**不是**宽依赖。",
        ),
        (
            "② 宽依赖处必切 Stage，是因为子分区要等「所有上游同 key 货到齐」才能算，天然跨节点，无法留在同一段连续工序里。",
            "② 宽依赖处通常会切 Stage，是因为子分区要等「所有上游同 key 货到齐」才能算，天然跨节点，无法留在同一段连续工序里。注意前提是「真的需要重分布」：上游已按该 key 分区时不插 Exchange，也就不切 Stage；Broadcast Join 同理。",
        ),
        (
            "宽依赖：子分区依赖父全部分区同 key 数据，必 Shuffle（空中飞货）",
            "宽依赖：子分区依赖父全部分区同 key 数据，通常需 Shuffle（上游已按该 key 分区时可省；Broadcast Join 不属于宽依赖）",
        ),
        (
            "宽依赖中父分区数据发往多个子分区，必 Shuffle。",
            "宽依赖中父分区数据发往多个子分区，通常需 Shuffle（上游已按该 key 分区时可省）。",
        ),
    ],
    # ---------------- L5-6 哪些操作会触发 Shuffle ----------------
    45: [
        (
            "① 区分「一定 Shuffle」与「可能 Shuffle」：groupBy / distinct / orderBy / sort / join / repartition 通常一定 Shuffle；而像 `union`（同 schema 简单拼接）一般不 Shuffle；某些 `reduceByKey` 在已按相同 key 分区时仍可能仍需跨节点合并（取决于上游分区）。",
            "① 区分「通常一定 Shuffle」与「通常不 Shuffle」：`repartition` 一定 Shuffle（它就是强制重分布）；groupBy / distinct / orderBy / sort 通常需要 Shuffle，但**上游已按目标 key / 排序键分区时可省**；`join` 要看策略——sort-merge / shuffle-hash 需要，Broadcast Join 不需要（Level 6）；`union`（同 schema 简单拼接）一般不 Shuffle；`sortWithinPartitions` **不 Shuffle**（它只在各分区内部排序）；`reduceByKey` 若上游已按相同 key 且相同分区数分区，可只做本地聚合、完全不 Shuffle。",
        ),
        (
            "触发 Shuffle 的算子通常需要跨分区按 key 重分布或全局排序：groupBy / groupByKey / reduceByKey / aggregateByKey（按 key）、join / cogroup（按 key 对齐）、distinct / dropDuplicates（按整行或列去重需重排）、orderBy / sort / sortWithinPartitions（全局有序需重排）、repartition（强制重分布）。是否实际 Shuffle 取决于上游是否已是目标分区分布。",
            "触发 Shuffle 的算子通常需要跨分区按 key 重分布或全局排序：groupBy / groupByKey / reduceByKey / aggregateByKey（按 key）、join / cogroup（按 key 对齐；Broadcast Join 例外）、distinct / dropDuplicates（按整行或列去重需重排）、orderBy / sort（全局有序需重排）、repartition（强制重分布）。**注意 `sortWithinPartitions` 不在此列**——它只在每个分区内部排序、不跨节点重排，因此不 Shuffle。是否实际 Shuffle 最终取决于上游是否已是目标分区分布：上游已按相同 key 分好区时，groupBy / reduceByKey 等都可以不插 Exchange。",
        ),
        (
            "一定/通常 Shuffle：groupBy / distinct / orderBy / sort / join / repartition",
            "通常 Shuffle：groupBy / distinct / orderBy / sort / shuffle-based join / repartition；不 Shuffle：sortWithinPartitions、union、Broadcast Join 的大表侧",
        ),
        (
            "知道 join 只点出「是宽依赖、会 Shuffle」，深类型（broadcast/sort-merge 怎么选）留 Level 6；",
            "知道 join 通常要按 key 重分布、但 Broadcast Join 可免，深类型（broadcast / sort-merge 怎么选）留 Level 6；",
        ),
        (
            "join 深类型（broadcast 等）留 Level 6，本课只点「会 Shuffle」",
            "join 深类型（broadcast 等）留 Level 6；本课只点「shuffle-based join 需按 key 重分布，Broadcast Join 例外」",
        ),
    ],
    # ---------------- L5-7 reduceByKey vs groupByKey ----------------
    46: [
        (
            "① combine 有前提：聚合函数必须是可交换、可结合的（如 sum/ min/ max），否则本地先聚合会算错；groupBy 的「分组后随便处理」没有这个限制。",
            "① combine 有前提：聚合函数必须是**可结合的**（associative，如 sum / min / max；它们通常同时也满足可交换），否则本地先聚合会算错；groupBy 的「分组后随便处理」没有这个限制。",
        ),
        (
            "③ 即便省了 Shuffle 量，reduceByKey 仍有一次 Shuffle（只是传输量小）；它优化的是「传输体积」，不是「消除 Shuffle」。",
            "③ 即便省了传输量，reduceByKey 通常仍有一次 Shuffle（只是传输量小）；它优化的是「传输体积」，不是「消除 Shuffle」。唯一例外是上游已按相同 key 且相同分区数分区——那时它只做本地聚合，一次 Shuffle 都没有。",
        ),
        (
            "combine 要求聚合函数可交换、可结合（sum/min/max）",
            "combine 要求聚合函数可结合（sum/min/max，通常同时可交换）",
        ),
        (
            "reduceByKey 优化的是「Shuffle 传输体积」，不是消除 Shuffle",
            "reduceByKey 优化的是「Shuffle 传输体积」，不是消除 Shuffle（除非上游已按同 key、同分区数分好区）",
        ),
    ],
    # ---------------- L5-8 repartition vs coalesce ----------------
    47: [
        (
            "- repartition = 把所有托盘推倒重排（必空中飞货）：能增能减，但每次都付一次 Shuffle。",
            "- repartition = 把所有托盘推倒、按人头**轮流重新发牌**（必空中飞货）：能增能减，但每次都付一次 Shuffle。注意它是「轮流发」不是「按 key 归堆」，所以同 key 未必同托盘。",
        ),
        (
            "repartition(n) 通过对数据做 hash 重分布把分区数改为 n，**一定触发 Shuffle**，可增可减。",
            "repartition(n) 用 **round-robin（轮询）**方式把数据均匀打散到 n 个分区，**一定触发 Shuffle**，可增可减。注意它不保证同一个 key 落进同一个分区；想要按某列哈希分区得写 `repartition(n, col)`。",
        ),
        (
            "② coalesce 默认 shuffle=False，只在同节点内合并相邻分区；若跨节点合并仍可能移动数据，想要强制不跨节点可传 shuffle=False 并依赖同节点布局（通常无需显式）。",
            "② coalesce 默认 shuffle=False：Spark 会**尽量**把同一 Executor 上的分区并到一起，但并不保证——跨节点合并时仍会通过 block 传输拉取数据（这不是一次 Shuffle stage，但仍然要搬数据）。所以它并非绝对零移动，结果是「省掉一次 Shuffle，可能换来分区大小不均」。",
        ),
        (
            "二者都返回新 DataFrame，原 DataFrame 不变（不可变语义）。",
            "二者都返回新 DataFrame，原 DataFrame 不变（不可变语义）。顺带说清一个常见误解：正因为 `repartition(n)` 是轮询打散、不保证同 key 同分区，所以 `repartition(200).groupBy('city')` 里的 groupBy 往往还得再 Shuffle 一次（呼应 L4 那个「3 个 Stage」的例子）。",
        ),
        (
            "coalesce 不能增分区，要增必须 repartition",
            "coalesce 不能增分区，要增必须 repartition；repartition(n) 是轮询打散（同 key 未必同分区），repartition(n, col) 才按列哈希",
        ),
    ],
    # ---------------- L5-9 综合练习 ----------------
    48: [
        (
            "识别触发 Shuffle 的算子（groupBy / orderBy / join / distinct / repartition）；据 Shuffle 数判定 Stage 数（Shuffle 数 + 1）；",
            "识别触发 Shuffle 的算子（groupBy / orderBy / shuffle-based join / distinct / repartition）；对**单条线性依赖链**用「Shuffle 边界数 + 1」估算 Stage 数（多分支 / 多数据源的 DAG 要按实际依赖关系数，不能套公式）；",
        ),
        (
            "你写 `logs.groupBy('city').count().orderBy(F.desc('count')).limit(10).explain(True)`：Spark 先生成计划；你读出 groupBy 处一处 Exchange（Shuffle，切出 Stage）、orderBy 处又一处 Exchange（再切 Stage），共 2 次 Shuffle → 3 个 Stage；并发现 groupBy 用 reduceByKey 式本地预聚合（combine）已省传输；limit 不 Shuffle。整段分析零执行，纯粹「读图」。",
            "你写 `logs.groupBy('city').count().orderBy(F.desc('count')).limit(10).explain(True)`：Spark 先生成计划；你读出 groupBy 处一处 Exchange（Shuffle，切出 Stage）。后半段有个细节值得知道：`orderBy(...).limit(10)` 会被优化成 `TakeOrderedAndProject`，它内部是一次**单分区** Shuffle，而不是「先按 range 重排、再排序」两次动作。所以总计仍是 2 次 Shuffle → 3 个 Stage，且最后一个 Stage 只有 1 个 Task。整段分析零执行，纯粹「读图」。⚠️ Spark 3.2+ 开启 AQE 时，`explain()` 看到的是**初始**计划（`AdaptiveSparkPlan isFinalPlan=false`），分区数与最终执行计划可能不同。",
        ),
        (
            "读图三步：找 Shuffle（空中飞货）→ 数 Stage（Shuffle+1）→ 估计并行度（分区数）",
            "读图三步：找 Shuffle（空中飞货）→ 数 Stage（单条线性链：Shuffle 边界数 + 1）→ 估计并行度（分区数）",
        ),
        (
            "③ explain() 不触发执行，所以这套「读图」练习随时可做、零成本。",
            "③ explain() 不触发执行，所以这套「读图」练习随时可做、零成本。\n④ ⚠️ **版本提示**：Spark 3.2+ 默认开启 AQE，`explain()` 给出的是**初始**计划（可能出现 `AdaptiveSparkPlan isFinalPlan=false`），AQE 会在运行时按真实统计合并分区、甚至改 Join 策略。要确认最终执行计划，看 Spark UI 的 SQL 详情页。",
        ),
    ],
    # ---------------- L6-1 JOIN 是什么 ----------------
    49: [
        (
            "0 个 Exchange = 走了广播，大表免 Shuffle；2 个 Exchange = 两边都重排（SMJ）。这是判断 JOIN 代价的第一眼。",
            "只看到 **BroadcastExchange**、大表侧没有普通 Exchange = 走了广播，大表免 Shuffle；看到**两个普通 Exchange** = 两边都重排（SMJ）。注意 BroadcastExchange 名字里也带 Exchange，数的时候别把它漏掉或重复数。这是判断 JOIN 代价的第一眼。",
        ),
        (
            "因此 JOIN 是分布式计算中最昂贵的操作类别之一；唯一的常见例外是「一侧足够小、可以被广播」时，大数据那一侧可以完全免去 Shuffle。",
            "因此 JOIN 是分布式计算中最昂贵的操作类别之一。常见的免 Shuffle 路径有两条：「一侧足够小、可以被广播」（Broadcast Hash Join，第 3 课）；以及「两侧已经按同一个 join key 分好区」（如分桶表，或上游已经 `repartition(n, key)` 且分区数一致）——这时同 key 本来就在一起，无需再重排。",
        ),
        (
            "② 相比 groupBy 通常只把一边的货按 key 汇聚，JOIN 常常**两边**都要按 key 重排，所以一般更贵——但这是「通常」：当一侧足够小时，大表那次 Shuffle 是可以整个免掉的（第 3 课）。",
            "② 相比 groupBy 通常只把一边的货按 key 汇聚，JOIN 常常**两边**都要按 key 重排，所以一般更贵——但这是「通常」：当一侧足够小时，大表那次 Shuffle 可以整个免掉（Broadcast Join，第 3 课）；两侧已按同一 key 分好区时同样能免。",
        ),
        (
            "④ 别指望 explain 帮你跑一遍：explain 只是看计划、不执行（复用 L4）。",
            "④ 别指望 explain 帮你跑一遍：explain 只是看计划、不执行（复用 L4）。\n⑤ ⚠️ **版本提示**：（a）Spark 3.2+ 默认开启 AQE，它可能在**运行时**把计划里的 Sort-Merge Join 改成 Broadcast Hash Join（`spark.sql.adaptive.autoBroadcastJoinThreshold`），所以 `explain()` 的初始计划未必是最终执行路径，确认要看 Spark UI。（b）Spark 2.4 及更早，隐式笛卡尔积会直接抛 AnalysisException；Spark 3.0 起 `spark.sql.crossJoin.enabled` 默认 true，引擎不再替你拦这一枪——所以写完 join 更要自己 count() 验量级。",
        ),
        (
            "一侧足够小时可广播（BHJ），大表可免 Shuffle——唯一常见的免 Shuffle 路径",
            "一侧足够小时可广播（BHJ），或两侧已按同一 key 分好区 → 大表可免 Shuffle",
        ),
    ],
    # ---------------- L6-2 JOIN 策略全景 ----------------
    50: [
        (
            "① 三套预案**结果完全等价**，只是代价不同——策略选择是「等价改写」，不改变答案（这正是 Catalyst 能自由选的前提）。",
            "① 三套预案**结果完全等价**（在确定性求值的前提下），只是代价不同——策略选择是「等价改写」，不改变答案（这正是 Catalyst 能自由选的前提）。",
        ),
        (
            "③ 计划里的节点名是**物理计划**才有的（复用 L4 逻辑 vs 物理），看到的是 `BroadcastHashJoin` / `SortMergeJoin` / `ShuffledHashJoin`；具体哪个会出现跟 Spark 版本、表大小、配置都有关，别背死「某代码一定出某节点」。",
            "③ 计划里的节点名是**物理计划**才有的（复用 L4 逻辑 vs 物理），看到的是 `BroadcastHashJoin` / `SortMergeJoin` / `ShuffledHashJoin`；具体哪个会出现跟 Spark 版本、表大小、配置都有关，别背死「某代码一定出某节点」。⚠️ 补充两条版本事实：Spark 3.x 默认 `spark.sql.join.preferSortMergeJoin=true`，所以 SHJ 相对少见；Spark 3.2+ 的 AQE 又可能在运行时把 SMJ 改成 BHJ 或 SHJ——在 3.x 上，「物理计划」其实是一个会变的计划。",
        ),
    ],
    # ---------------- L6-3 Broadcast Hash Join ----------------
    51: [
        (
            "④ 「多大算小」由一个广播阈值控制，Spark 会拿小表的**统计大小估计**去和它比；具体阈值是多少、怎么调，是 Level 7 调优的内容，本课只讲「存在这个前提」。",
            "④ 「多大算小」由一个广播阈值控制，Spark 会拿小表的**统计大小估计**去和它比。⚠️ **版本事实**：这个阈值就是 `spark.sql.autoBroadcastJoinThreshold`，**默认 10MB**——记住它是「某个版本的行为」，不是 Spark 的概念定义；怎么调、调到多少是 Level 7 的事。另外广播还有 join 类型的限制（例如 FULL OUTER JOIN 无法走 BHJ），这也是 hint 会被忽略的常见原因之一。",
        ),
    ],
    # ---------------- L6-4 Sort-Merge Join ----------------
    52: [
        (
            "② 排序本身也要钱：全量排序，内存放不下时会 spill 到磁盘（复用 L5「spill 慢几个数量级」）；具体排序与溢出的调优留 L7。",
            "② 排序本身也要钱：全量排序，内存放不下时会 spill 到磁盘（复用 L5 的 spill 概念：磁盘通常比内存慢 1~2 个数量级）；具体排序与溢出的调优留 L7。",
        ),
        (
            "④ 归并扫描是线性的（排完序后两边各扫一遍），不是「每条去另一本里翻一遍」——否则就退化成嵌套循环了。",
            "④ 归并扫描是线性的（排完序后两边各扫一遍），不是「每条去另一本里翻一遍」——否则就退化成嵌套循环了。\n⑤ ⚠️ **版本提示**：Spark 3.2+ 的 AQE 在拿到运行时真实统计后，如果某一侧其实很小，会把 SMJ 改成 Broadcast Hash Join（`spark.sql.adaptive.autoBroadcastJoinThreshold`）。所以你在 `explain()` 里看到 SMJ，不代表执行时一定是 SMJ。",
        ),
    ],
    # ---------------- L6-5 Shuffle Hash Join 与兜底 ----------------
    53: [
        (
            "③ SHJ 具体在什么条件下被选中，跟 Spark 版本、配置、统计信息都有关系，**别背死条件**，看 explain 说话。",
            "③ SHJ 具体在什么条件下被选中，跟 Spark 版本、配置、统计信息都有关系，**别背死条件**，看 explain 说话。可参考的版本事实：Spark 3.x 默认 `spark.sql.join.preferSortMergeJoin=true`，所以 SHJ 比较少见；Spark 3.2+ 的 AQE 另有 `spark.sql.adaptive.maxShuffledHashJoinLocalMapThreshold`（默认 0，即关闭），调大后 AQE 会在运行时把小的 SMJ 改成 SHJ。",
        ),
        (
            "④ 兜底的两位都不是好消息：BroadcastNestedLoopJoin（一侧广播 + 嵌套循环，非等值条件时）、CartesianProduct（无 key，每条对每条）。看到它们意味着 O(n·m) 级别的风险。",
            "④ 兜底的两位都不是好消息：BroadcastNestedLoopJoin（一侧广播 + 嵌套循环，非等值条件时）、CartesianProduct（无 key，每条对每条）。看到它们意味着 O(n·m) 级别的风险。⚠️ **版本事实**：Spark 2.4 及更早会直接对隐式笛卡尔积抛 AnalysisException；Spark 3.0 起 `spark.sql.crossJoin.enabled` 默认为 true，不再报错——引擎不再替你兜底，只能自己 count() 验量级。",
        ),
    ],
    # ---------------- L6-6 Spark 怎么选 JOIN 策略 ----------------
    54: [
        (
            "④ 决策发生在**物理计划阶段**，所以只有 `explain()`（物理计划视角）才看得到结果，逻辑计划里没有策略之分。",
            "④ 决策发生在**物理计划阶段**，所以只有 `explain()`（物理计划视角）才看得到结果，逻辑计划里没有策略之分。\n⑤ ⚠️ **版本提示**：Spark 3.2+ 默认开启 AQE，Spark 会在**运行时**拿到真实的 shuffle 统计后再优化一次：把 SMJ 改成 BHJ（`spark.sql.adaptive.autoBroadcastJoinThreshold`），或改成 SHJ（`spark.sql.adaptive.maxShuffledHashJoinLocalMapThreshold`）。所以「决策只在规划期做一次」是简化说法——在 3.x 上它是「规划期一次 + 运行期若干次」，而运行期那次用的是实测值，往往更准。",
        ),
        (
            "由于依据的是估计值而非真实运行数据，统计信息缺失或不准确会导致策略误判。",
            "由于依据的是估计值而非真实运行数据，统计信息缺失或不准确会导致策略误判。（Spark 3.2+ 的 AQE 会在运行时用实测统计再优化一次，能纠正一部分规划期的误判。）",
        ),
    ],
    # ---------------- L6-8 JOIN 中的数据倾斜 ----------------
    56: [
        (
            "④ 具体的倾斜开关、自适应优化参数与深调优，**全部留给 Level 7**，本课只到「能认出来 + 懂原理」。",
            "④ 具体的倾斜开关、自适应优化参数与深调优，**全部留给 Level 7**，本课只到「能认出来 + 懂原理」。⚠️ **版本事实**：Spark 3.0+ 有 `spark.sql.adaptive.skewJoin.enabled`（默认 **true**，需配合 `spark.sql.adaptive.enabled`）——AQE 会自动把倾斜分区拆分（必要时复制）成大小相近的任务。也就是说在 Spark 3.x 上，「手工加盐」往往不是第一步：先看 AQE 的倾斜处理有没有生效（Spark UI），它没兜住再考虑 salting / 隔离大 key / 广播。",
        ),
        (
            "- **绕开 Shuffle**：若一侧足够小，改用 Broadcast Hash Join，让大表根本不按 key 重排，倾斜自然失效。",
            "- **绕开 Shuffle**：若一侧足够小，改用 Broadcast Hash Join，让大表根本不按 key 重排，倾斜自然失效；\n- **交给 AQE（Spark 3.0+）**：`spark.sql.adaptive.skewJoin.enabled` 默认开启，AQE 会在运行时把倾斜分区拆开并重算，多数情况下不需要你手写加盐。",
        ),
    ],
    # ---------------- L6-9 综合练习 ----------------
    57: [
        (
            "3. **数 Exchange**：0~1 个 = 走了广播（大表免飞）；2 个 = 两边都飞（SMJ/SHJ）；",
            "3. **数 Exchange**：只有 `BroadcastExchange`、大表侧没有普通 Exchange = 走了广播（大表免飞）；两个普通 Exchange = 两边都飞（SMJ/SHJ）。注意 BroadcastExchange 也是 Exchange，别数漏；",
        ),
        (
            "④ 策略是等价改写，选错不会算错结果，只会让你多付钱（时间/资源）。",
            "④ 策略是等价改写，选错不会算错结果，只会让你多付钱（时间/资源）。\n⑤ ⚠️ **版本提示**：Spark 3.2+ 默认开启 AQE，`explain()` 看到的是**初始**计划，运行时可能把 SMJ 改成 BHJ、合并 shuffle 分区、自动处理倾斜。诊断流程因此要加一步：「先看 Spark UI 的最终计划，再对照 explain() 的初始计划」。",
        ),
    ],
}

# ---------------------------------------------------------------- objective / description
OBJ_DESC_PATCHES = [
    (42, "objective", [
        ("知道 Shuffle 不是「错误」而是宽依赖的必然代价",
         "知道 Shuffle 不是「错误」而是宽依赖的通常代价（上游已按该 key 分区、或走 Broadcast Join 时可省）"),
    ]),
    (44, "objective", [
        ("宽依赖父分区数据发往多个子分区（必 Shuffle）",
         "宽依赖父分区数据发往多个子分区（通常需 Shuffle；上游已按该 key 分区时可省，Broadcast Join 不属于宽依赖）"),
        ("为什么宽依赖处必切 Stage",
         "为什么宽依赖处通常就切 Stage（上游已分区时例外）"),
    ]),
    (44, "description", [
        ("宽依赖父分区数据发往多个子分区（必 Shuffle）",
         "宽依赖父分区数据发往多个子分区（通常需 Shuffle；上游已按该 key 分区时可省，Broadcast Join 不属于宽依赖）"),
    ]),
    (45, "objective", [
        ("知道 join 只点出「是宽依赖、会 Shuffle」，深类型（broadcast/sort-merge 怎么选）留 Level 6",
         "知道 join 通常要按 key 重分布、但 Broadcast Join 可免，深类型（broadcast / sort-merge 怎么选）留 Level 6"),
    ]),
]

# ---------------------------------------------------------------- 题库替换
# {quiz_id: {"prompt": (old, new), "options": [(old, new), ...], "explanation": (old, new)}}
import json as _json

QUIZ_PATCHES = {
    # ---- L5 ----
    436: {"explanation": (
        "每个分区对应一个 Task，所以分区数直接决定同时执行的 Task 数（并行度）。",
        "每个分区对应一个 Task，所以分区数决定 Task 数（理论并行度）；实际能同时跑多少还受集群可用 core 数限制。",
    )},
    439: {"explanation": (
        "默认分区可能按 block 数给，但 repartition / 不同输入格式会改变它，二者非 1:1。",
        "读文件时 DataFrame 按 `spark.sql.files.maxPartitionBytes`（默认 128MB）切分，恰好常与 block 数接近；但 repartition / 不同输入格式会改变它，二者非 1:1。",
    )},
    445: {"explanation": (
        "并行度 = 同时执行的 Task 数 = 该 Stage 的分区数。",
        "并行度理论上 = 该 Stage 的分区数（Task 数）；实际上限还受集群可用 core 数限制。",
    )},
    450: {"explanation": (
        "默认 200，只是默认值，是否适合你的数据需结合规模判断（调优留 L7）。",
        "默认 200，只是**初始**值：Spark 3.2+ 默认开启 AQE，运行时会按真实数据量合并 shuffle 分区，最终分区数通常小于 200（定量调优留 L7）。",
    )},
    456: {
        "prompt": ("为什么 groupBy / join / orderBy 会触发 Shuffle？",
                   "为什么 groupBy / orderBy 通常会触发 Shuffle？（join 要分策略）"),
        "options": [("需要全局按 key 汇聚 / 全局有序，必须跨节点重排",
                     "需要全局按 key 汇聚 / 全局有序，通常要跨节点重排（上游已按该 key 分区时可省）")],
        "explanation": (
            "这些操作需要「全局按 key 汇聚或全局有序」，无法在本地完成，必须跨节点重排。",
            "这些操作需要「全局按 key 汇聚或全局有序」，通常要跨节点重排。例外：上游已按该 key 分区时不插 Exchange；join 走 Broadcast Join 时小表侧也不产生 ShuffleExchange。",
        ),
    },
    459: {"explanation": (
        "只要计算需全局按 key 汇聚，Shuffle 必然发生，它是代价不是错误。",
        "需要全局按 key 汇聚时通常发生 Shuffle（上游已按该 key 分区、或走 Broadcast Join 时可省）；它是代价不是错误。",
    )},
    464: {
        "options": [("需要全局汇聚时必然发生，躲不掉（除非无需汇聚）",
                     "通常需要；上游已按该 key 分区或走 Broadcast Join 时可省")],
        "explanation": (
            "宽依赖的必然代价，需要全局按 key 汇聚时无法避免。",
            "宽依赖的通常代价：需要全局按 key 汇聚时才发生；上游已按该 key 分区、或 join 走 Broadcast Join，都可以省掉。",
        ),
    },
    469: {
        "options": [("内存不足时 spill，磁盘 I/O 慢几个数量级，放大代价",
                     "内存不足时 spill，磁盘 I/O 通常比内存慢 1~2 个数量级，放大代价")],
        "explanation": (
            "spill 把中间结果写磁盘，I/O 远慢于内存，是 Shuffle 贵的重要放大器。",
            "spill 把中间结果写磁盘，磁盘（尤其随机 I/O）通常比内存慢 1~2 个数量级，是 Shuffle 贵的重要放大器。",
        ),
    },
    481: {
        "options": [("下游依赖全局重排，上游任何分区丢都要整体重算",
                     "Shuffle 输出丢失时可能要重跑相关上游 map task，恢复成本远高于本地重算一个分区")],
        "explanation": (
            "宽依赖下游依赖全局按 key 汇聚，上游丢失需整体重算，代价大（呼应 L4）。",
            "宽依赖的 Shuffle 输出落在 map 端，一旦丢失通常要重新执行相关的上游 map task 再重排；窄依赖只需沿本地依赖链重算受影响的分区。所以宽依赖恢复更贵——但「上游任何分区丢都整体重算」是 RDD 论文时代的简化说法（呼应 L4 已更正的口径）。",
        ),
    },
    482: {
        "options": [("宽依赖，父分区数据发往多个子分区（必 Shuffle）",
                     "宽依赖，父分区数据发往多个子分区（通常需 Shuffle；上游已按该 key 分区时可省）")],
        "explanation": (
            "groupBy 需跨节点按 key 重分布，父分区数据发往多个子分区。",
            "groupBy 通常需跨节点按 key 重分布；若上游已按 city 分好区，则不插 Exchange。",
        ),
    },
    485: {
        "options": [("groupBy / orderBy / distinct / join",
                     "groupBy / orderBy / distinct / repartition")],
        "explanation": (
            "这些操作需全局按 key 汇聚或全局有序，必然或通常触发 Shuffle。",
            "这些操作需全局按 key 汇聚、全局有序或强制重分布，通常触发 Shuffle；join 要分策略（Broadcast Join 不 Shuffle），所以没列进来。",
        ),
    },
    487: {
        "options": [("Exchange（两表按 id 重分布，Shuffle）",
                     "若走 Sort Merge Join 则两侧各一个 Exchange；若小表走 Broadcast Join 则只有 BroadcastExchange，大表不 Shuffle")],
        "explanation": (
            "join 按 key 重分布两表，产生 Exchange（Shuffle）。",
            "要看策略：sort-merge / shuffle-hash 会两侧各一个 Exchange；Broadcast Join 只广播小表，大表侧不产生 ShuffleExchange。策略细节留 Level 6。",
        ),
    },
    490: {
        "options": [("只点 join 是宽依赖会 Shuffle，深类型留 Level 6",
                     "只点 join 通常要按 key 重分布（Broadcast Join 可免），深类型留 Level 6")],
        "explanation": (
            "join 深类型（broadcast 等怎么选）是 Level 6 内容，本课只点「会 Shuffle」。",
            "join 深类型（broadcast / sort-merge 怎么选）是 Level 6 内容；本课只点「shuffle-based join 需要按 key 重分布，Broadcast Join 例外」。",
        ),
    },
    491: {"explanation": (
        "repartition 通过对数据 hash 重分布改分区数，必然触发 Shuffle。",
        "repartition(n) 用 round-robin（轮询）把数据均匀打散到 n 个分区，必然触发 Shuffle；它不保证同 key 同分区（要按列哈希得写 repartition(n, col)）。",
    )},
    492: {
        "options": [("按 key，通常需跨节点合并（Shuffle）",
                     "按 key，通常需跨节点合并；上游已按相同 key 分区时可省")],
        "explanation": (
            "按 key 的聚合通常需在 reduce 端跨节点合并，属 Shuffle 算子。",
            "按 key 的聚合通常需在 reduce 端跨节点合并；若上游已按相同 key 且相同分区数分区，则只做本地聚合、不 Shuffle。",
        ),
    },
    499: {
        "options": [("聚合函数须可交换、可结合（如 sum/min/max）",
                     "聚合函数须可结合（sum/min/max 等，通常同时可交换）")],
        "explanation": (
            "只有可交换可结合的聚合才能安全地在 map 端预聚合，否则会算错。",
            "严格说是「可结合」（associative）才能安全地在 map 端预聚合；sum/min/max 等同时也满足可交换。不可结合的聚合（如中位数）本地先聚合会算错。",
        ),
    },
    503: {
        "options": [("聚合是否可交换可结合",
                     "聚合是否可结合（能否安全本地预聚合）")],
        "explanation": (
            "可换的聚合（sum/min/max 等）可改 reduceByKey 省飞货；不可结合的不能。",
            "可结合的聚合（sum/min/max 等）可改 reduceByKey 省飞货；不可结合的（如中位数）不能。",
        ),
    },
    516: {
        "prompt": ("数 Stage 的公式是？", "对单条线性依赖链，估算 Stage 数的公式是？"),
        "options": [("Shuffle 数 + 1", "Shuffle（Exchange）边界数 + 1")],
        "explanation": (
            "Stage 数 = Shuffle（Exchange）数 + 1。",
            "对单条线性依赖链，Stage 数 ≈ Shuffle 边界数 + 1；多分支 / 多数据源的 DAG 要按实际依赖关系数，不能套公式。",
        ),
    },
    517: {"explanation": (
        "groupBy 与 orderBy 各一处 Exchange，limit 不 Shuffle，共 2 处。",
        "groupBy 一处 Exchange；`orderBy(...).limit(10)` 会被优化成 TakeOrderedAndProject（内部一次单分区 Shuffle），所以仍是 2 次 Shuffle → 3 个 Stage，且最后一个 Stage 只有 1 个 Task。注意 Spark 3.2+ AQE 会按运行时统计再调整。",
    )},
    524: {
        "options": [("初始 Stage（Stage 数 = Shuffle 数 + 1，从 1 起算）",
                     "初始 Stage（单条线性链：Stage 数 = Shuffle 数 + 1，从 1 起算）")],
        "explanation": (
            "易漏「初始 Stage」，记住从 1 开始加，Shuffle 数 + 1。",
            "易漏「初始 Stage」：单条线性链下从 1 开始加，Shuffle 边界数 + 1；多分支 DAG 不适用。",
        ),
    },
    # ---- L6 ----
    529: {"explanation": (
        "Broadcast Hash Join 会把小表广播出去，让大表侧完全不按 key 重排——这是唯一常见的免 Shuffle 路径。",
        "Broadcast Hash Join 会把小表广播出去，让大表侧完全不按 key 重排；另外两侧若已按同一 key 分好区（如分桶表），同样能免掉重排。",
    )},
    531: {"explanation": (
        "无等值 key 时 Spark 只能两两配对，1 亿 × 1 亿的结果量级足以压垮任何集群，且往往要跑很久才暴露。",
        "无等值 key 时 Spark 只能两两配对，1 亿 × 1 亿的结果量级足以压垮任何集群。⚠️ 版本差异：Spark 2.4 及更早会直接抛 AnalysisException 拦住隐式笛卡尔积；Spark 3.0 起 `spark.sql.crossJoin.enabled` 默认 true，不再报错，只能靠自己 count() 验量级。",
    )},
    551: {"explanation": (
        "BHJ 省的是大表那次重排；小表的分发依然存在，只是数据量小好几个数量级。",
        "BHJ 省的是大表那次重排；小表的分发依然存在，只是数据量小得多。",
    )},
    560: {"explanation": (
        "排序结果可溢写磁盘（复用 L5 的 spill 概念），代价是 I/O 慢几个数量级，但保证了「能跑完」。",
        "排序结果可溢写磁盘（复用 L5 的 spill 概念），代价是磁盘 I/O 通常比内存慢 1~2 个数量级，但保证了「能跑完」。",
    )},
    575: {"explanation": (
        "复用 L3/L4 的「Catalyst = 优化大脑」：策略决策发生在物理计划阶段，属于规划期行为。",
        "复用 L3/L4 的「Catalyst = 优化大脑」：策略决策发生在物理计划阶段，属于规划期行为。⚠️ Spark 3.2+ 默认开启 AQE，运行时还会按真实统计再优化一次（如把 SMJ 改成 BHJ），所以最终执行路径可能与 explain() 的初始计划不同。",
    )},
    603: {"explanation": (
        "倾斜时加机器只是让其他 Task 更快空转；只有改 key 分布或绕开 Shuffle 才真正有效。",
        "倾斜时加机器只是让其他 Task 更快空转；改 key 分布或绕开 Shuffle 才真正有效。⚠️ Spark 3.0+ 的 `spark.sql.adaptive.skewJoin.enabled` 默认 true，AQE 会自动拆分倾斜分区——先看它有没有生效（Spark UI），没兜住再考虑手工加盐（深调优 L7）。",
    )},
}


# ---------------------------------------------------------------- 工具
def walk_apply(node, pairs, stat):
    """递归对 JSON 结构里每个字符串叶子做替换，统计命中数。"""
    if isinstance(node, str):
        out = node
        for i, (old, new) in enumerate(pairs):
            if old in out:
                stat[i] += out.count(old)
                out = out.replace(old, new)
        return out
    if isinstance(node, list):
        return [walk_apply(x, pairs, stat) for x in node]
    if isinstance(node, dict):
        return {k: walk_apply(v, pairs, stat) for k, v in node.items()}
    return node


def do_lessons(apply):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("select id, title, content from lessons where id in (%s)"
                % ",".join("?" * len(LESSON_PATCHES)), list(LESSON_PATCHES))
    rows = cur.fetchall()
    print(f"== 课文：待处理 {len(rows)} 课 ==")
    for lid, title, raw in rows:
        pairs = LESSON_PATCHES[lid]
        data = _json.loads(raw)
        stat = [0] * len(pairs)
        data = walk_apply(data, pairs, stat)
        miss = [(i, pairs[i][0][:40]) for i, c in enumerate(stat) if c == 0]
        if miss:
            print(f"  [!] lesson {lid} {title} —— {len(miss)} 处未命中:")
            for i, s in miss:
                print(f"       #{i}: {s}")
        if apply:
            cur.execute("update lessons set content=? where id=?",
                        (_json.dumps(data, ensure_ascii=False), lid))
        print(f"  lesson {lid} {title}: 命中 {sum(stat)} 处，未命中 {len(miss)} 处")
    if apply:
        conn.commit()
    conn.close()


def do_obj_desc(apply):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    print("\n== objective / description ==")
    for lid, field, pairs in OBJ_DESC_PATCHES:
        if not pairs:
            continue
        cur.execute(f"select {field} from lessons where id=?", (lid,))
        r = cur.fetchone()
        if not r:
            print(f"  [!] lesson {lid} 不存在")
            continue
        val = r[0] or ""
        hit = 0
        for old, new in pairs:
            if old in val:
                hit += 1
                val = val.replace(old, new)
            else:
                print(f"  [!] lesson {lid} {field} 未命中: {old[:40]}")
        if apply and hit:
            cur.execute(f"update lessons set {field}=? where id=?", (val, lid))
        print(f"  lesson {lid} {field}: 命中 {hit}/{len(pairs)}")
    if apply:
        conn.commit()
    conn.close()


def do_quizzes(apply):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    print(f"\n== 题库：待处理 {len(QUIZ_PATCHES)} 题 ==")
    bad = 0
    for qid, patch in QUIZ_PATCHES.items():
        cur.execute("select prompt, options, correct_index, explanation from quizzes where id=?", (qid,))
        r = cur.fetchone()
        if not r:
            print(f"  [!] q{qid} 不存在")
            bad += 1
            continue
        prompt, opts_raw, ci, exp = r
        opts = _json.loads(opts_raw)
        msgs = []

        if "prompt" in patch:
            old, new = patch["prompt"]
            if prompt == old or old in prompt:
                prompt = prompt.replace(old, new)
            else:
                msgs.append("prompt 未命中"); bad += 1

        for old, new in patch.get("options", []):
            if old in opts:
                opts[opts.index(old)] = new
            else:
                msgs.append(f"选项未命中: {old[:30]}"); bad += 1

        if "explanation" in patch:
            old, new = patch["explanation"]
            if exp and old in exp:
                exp = exp.replace(old, new)
            else:
                msgs.append("explanation 未命中"); bad += 1

        # 自检：选项不能重复，正确项位置不变
        if len(set(opts)) != len(opts):
            msgs.append("选项出现重复！"); bad += 1

        if apply and not msgs:
            cur.execute("update quizzes set prompt=?, options=?, explanation=? where id=?",
                        (prompt, _json.dumps(opts, ensure_ascii=False), exp, qid))
        flag = " ".join(msgs) if msgs else "OK"
        print(f"  q{qid}: {flag}")
    if apply:
        conn.commit()
    conn.close()
    print(f"\n异常项：{bad}")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "--dry"
    if mode == "--apply":
        do_lessons(True); do_obj_desc(True); do_quizzes(True)
        print("\n已写入真库。")
    else:
        do_lessons(False); do_obj_desc(False); do_quizzes(False)
        print("\n[dry-run] 未写库。加 --apply 执行。")
