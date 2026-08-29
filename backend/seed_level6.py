# -*- coding: utf-8 -*-
"""一次性脚本：把 Level 6（JOIN 深类型与 Broadcast，9 课）合并进 course_seed.json 与 quiz_seed.json，
并幂等地 upsert 进 spark_quest.db 的 course_levels / lessons / quizzes 表。
不修改 Level 0/1/2/3/4/5 与已有的 lesson_mastery 进度数据。

运行：cd backend && python seed_level6.py
"""
import sqlite3, json, os

BASE = os.path.dirname(os.path.abspath(__file__))
SEED = os.path.join(BASE, "app", "course_seed.json")
QUIZ = os.path.join(BASE, "app", "quiz_seed.json")
DB = os.path.join(BASE, "spark_quest.db")

LEVEL6 = {
    "title": "Level 6：JOIN 深类型与 Broadcast",
    "description": "教读者「两个数据集按 key 拼合（JOIN）时，Spark 内部有哪几种拼法、它凭什么自动选、以及什么时候能免去大表的 Shuffle（Broadcast）」——把 Level 3 埋下的「JOIN 必 Shuffle、深类型留 L6」伏笔、Level 4 埋下的 BroadcastHashJoin / SortMergeJoin 计划标记、Level 5 埋下的「Shuffle 代价 / 空中飞货」全部延展到 JOIN 策略层面。覆盖 JOIN 为什么比单表聚合更重、JOIN 策略全景、Broadcast Hash Join、Sort-Merge Join、Shuffle Hash Join 与兜底、Spark 怎么选策略、broadcast() 主动提示与避坑、JOIN 数据倾斜（skew）、综合。为 Level 7（性能调优：Tungsten 内存/堆外/编码字节级、shuffle 分区数最优值、skew 深调优）铺垫，本身不抢跑调优。",
    "order_index": 6,
    "lessons": [
        {
            "title": "JOIN 是什么（为什么比单表聚合更重）",
            "slug": "l6-what-is-join",
            "description": "理解 JOIN = 两数据集按 key 对齐拼合；相比单表 groupBy，JOIN 往往要「两边都按 key 重排」或「一方被广播」，所以通常更贵。",
            "objective": "学完本课，你应该能够：用自己的话解释 JOIN 是「先按 key 对齐、再拼合」而不是「查两张表」；说清为什么 JOIN 通常比单表 groupBy 更贵（两侧都要按 key 重分布）；知道无 join key / 条件写错会退化成笛卡尔积或空结果；理解「一侧足够小可广播」是唯一常见的免 Shuffle 路径（本课只埋伏笔，第 3 课展开）；并明确本课不重讲 Level 3 的 INNER JOIN 语法。",
            "estimated_minutes": 12,
            "order_index": 0,
            "prerequisites": "",
            "content": {
                "explanation": "【先用人话理解】\n\n单表聚合（groupBy）像「把一筐水果按种类分堆」——货只有一筐，按 key 归拢就完事。JOIN 不一样：它是「两筐货要按同一个编号对上号，再拼成一张表」。麻烦在于，编号相同的那两条记录，一开始很可能躺在不同工人（Executor）手里，你得先把它们弄到一块儿，才能拼得起来。\n\n【一个直观的心智模型】\n\n复用 Level 3 的「两拨货按 key 拼桌」：订单表和客户表要按 customer_id 拼成一张大桌。可拼桌前有个硬前提——同一个 customer_id 的两条记录必须坐到一起。怎么做到？只有两条路：\n- **两边都按座号（key）重排**：两拨货各飞一次「空中运输」（复用 L5 的 Shuffle 隐喻），落到按 key 分好的新托盘上，再逐 key 配对——这是 Sort-Merge Join / Shuffle Hash Join 的路子（第 4、5 课细讲）；\n- **把小桌名单复印 N 份发到每个工人手里**：大表那拨货原地不动，工人拿手里的名单直接对照——这是 Broadcast Hash Join（第 3 课的主角）。\n\n所以 JOIN 的「重」，就重在这个「先对齐、再拼合」的前置动作上。\n\n⚠️ 比喻的边界（很重要）：\n① JOIN 不是「查两表」——它是先按 key 对齐再拼合的二元算子。没给 join key（或条件非等值），就退化成笛卡尔积：每条对每条，O(n·m) 的灾难。\n② 相比 groupBy 通常只把一边的货按 key 汇聚，JOIN 常常**两边**都要按 key 重排，所以一般更贵——但这是「通常」：当一侧足够小时，大表那次 Shuffle 是可以整个免掉的（第 3 课）。\n③ 拼桌是比喻，真实代价是「序列化 → 跨网络 → 反序列化 → 排序」（复用 L5 空中飞货三环节），不是把纸挪过去那么轻。\n④ 别指望 explain 帮你跑一遍：explain 只是看计划、不执行（复用 L4）。\n\n【正式的技术定义】\n\nJOIN 是按 join key（通常是等值条件）把两个数据集的记录配对拼接的二元算子。由于相同 key 的记录在物理上必须落到同一位置才能配对，JOIN 通常需要按 key 重新分布数据，即触发 Shuffle（宽依赖，对应执行计划里的 Exchange 节点）。因此 JOIN 是分布式计算中最昂贵的操作类别之一；唯一的常见例外是「一侧足够小、可以被广播」时，大数据那一侧可以完全免去 Shuffle。\n\n【写下代码后，Spark 内部发生了什么】\n\n你写 `orders.join(customers, 'customer_id')`：\n1. Catalyst（优化大脑，复用 L3）生成逻辑计划：Scan orders → Scan customers → Join；\n2. 进入物理计划阶段，它必须决定「到底怎么拼」——这正是 Level 6 后面几课的主题（BHJ / SMJ / SHJ）；\n3. 若走 SMJ：orders 与 customers **各自**按 customer_id 哈希分区并排序（两个 Exchange），相同 key 落到同一分区，再逐 key 归并配对；\n4. 若 customers 足够小走 BHJ：customers 被整份广播到每个 Executor（BroadcastExchange），orders 原地流式探测，计划里只出现一个 Exchange。\n同样一句 join 代码，内部可能是两条完全不同的执行路径——这就是「读计划认策略」的价值。",
                "examples": [
                    {
                        "title": "最基础的等值 JOIN + 看计划",
                        "code": "orders = spark.read.parquet('orders')\ncustomers = spark.read.parquet('customers')\norders.join(customers, 'customer_id').explain()\n# 先看两个数：Exchange 有几个？Join 节点叫什么？",
                        "note": "0 个 Exchange = 走了广播，大表免 Shuffle；2 个 Exchange = 两边都重排（SMJ）。这是判断 JOIN 代价的第一眼。"
                    },
                    {
                        "title": "单表 groupBy（一次 Shuffle）对照 JOIN",
                        "code": "orders.groupBy('customer_id').count().explain()\n# 1 次 Exchange（只汇聚一侧）\n\norders.join(customers, 'customer_id').explain()\n# 常见 2 次 Exchange（两侧都按 key 重排）",
                        "note": "同样是「按 key 处理」，JOIN 的 Exchange 往往比单表聚合多，这就是「JOIN 通常更贵」的直观证据。"
                    },
                    {
                        "title": "不给 key：笛卡尔积灾难",
                        "code": "# 危险：无 join 条件 → 每条对每条\norders.crossJoin(customers).explain()\n# 计划里出现 CartesianProduct，结果行数是 n × m",
                        "note": "crossJoin 是显式写法；更常见的事故是 join 条件写成了恒真表达式，本意等值、实则退化成笛卡尔积。"
                    },
                    {
                        "title": "条件写错：key 对不上，结果空掉或爆炸",
                        "code": "# 本想按 customer_id 关联，却写成了城市\norders.join(customers, orders.city == customers.city).count()\n# 多对多 → 行数暴增；key 完全不匹配 → 0 行",
                        "note": "JOIN 结果行数不等于任何一侧的行数。写完 join 先 count() 对一下量级，再往下走。"
                    }
                ],
                "key_points": [
                    "JOIN = 先按 key 对齐、再拼合，不是简单地「查两张表」",
                    "相同 key 必须落到同一位置 → JOIN 通常触发 Shuffle（宽依赖 / Exchange）",
                    "相比单表 groupBy，JOIN 常常两边都要重排，所以通常更贵",
                    "一侧足够小时可广播（BHJ），大表可免 Shuffle——唯一常见的免 Shuffle 路径",
                    "无 join key / 条件写错 → 笛卡尔积 O(n·m) 或空结果，是最贵的事故"
                ],
                "common_mistakes": [
                    {
                        "mistake": "以为 JOIN 只是「把两张表查出来、拼一列上去」。",
                        "why": "JOIN 要先把同 key 的数据物理凑到一起，通常意味着跨节点重排（Shuffle），不是免费拼列。",
                        "fix": "下笔前先问：两边大小如何？同 key 现在在哪？能不能广播？"
                    },
                    {
                        "mistake": "join 时不写条件，或条件写成恒真表达式（如拿一列跟自己比）。",
                        "why": "恒真条件等价于无 key，退化成笛卡尔积，n × m 行直接把集群压死。",
                        "fix": "始终写明确的等值 key；写完先 count() 看行数是否符合预期。"
                    },
                    {
                        "mistake": "看到 JOIN 就认定「两边一定都 Shuffle」。",
                        "why": "当一侧足够小，Spark 可以广播它，让大表完全不 Shuffle（Broadcast Hash Join）。",
                        "fix": "用 explain 数 Exchange，别凭感觉下结论——这是 L6 后面几课的核心技能。"
                    }
                ],
                "review": "Level 3 你学会了 INNER JOIN 的写法——两拨货按 key 对齐拼桌，只留两边都有的 key，当时就埋下「深类型留 L6」；Level 5 你又知道 JOIN 是宽依赖、会触发空中飞货。",
                "problem": "可同样一句 join，凭什么有时飞一次货、有时飞两次？大表那次昂贵的空中运输，到底能不能免掉？",
                "preview": "先把全景摆上桌：Spark 拼一张桌子其实有三套预案（BHJ / SMJ / SHJ），外加一个谁都不想要的兜底。下集先给这三套预案的名字和长相对上号。"
            }
        },
        {
            "title": "JOIN 策略全景（Spark 怎么拼）",
            "slug": "l6-join-strategies-overview",
            "description": "建立「JOIN 有三种执行策略」的框架：Broadcast Hash Join（BHJ）/ Sort-Merge Join（SMJ，大表默认）/ Shuffle Hash Join（SHJ）＋ 兜底（Cartesian / BroadcastNestedLoop），并理解 Spark 会按表大小自动选。",
            "objective": "学完本课，你应该能够：说出 Spark 三种主要 JOIN 执行策略的名字与各自一句话原理（BHJ / SMJ / SHJ）；知道还有两个兜底策略（BroadcastNestedLoopJoin / CartesianProduct）及其触发场景；能在 explain 输出里认出 BroadcastHashJoin / SortMergeJoin / ShuffledHashJoin 节点；理解三者结果等价、代价不同，且由 Spark 自动选择（具体怎么选是第 6 课）；并知道本课只建框架，不展开各策略细节、不给选择阈值。",
            "estimated_minutes": 13,
            "order_index": 1,
            "prerequisites": "",
            "content": {
                "explanation": "【先用人话理解】\n\n同一句 `df1.join(df2, 'id')`，Spark 内部其实有好几种「拼法」。就像拼桌这件小事，你可以把小名单复印给所有人对照，也可以两本名册先排序再逐页比对，还可以先把一方做成索引再让另一方来查。选哪种，取决于两拨货有多大。\n\n【一个直观的心智模型】\n\n同一场「两拨货按 key 拼桌」，Spark 备着三套预案：\n- **复印小册子对照（Broadcast Hash Join，BHJ）**：把小的那份名单复印 N 份发到每个工人手里，大表那拨货原地不动，工人拿手里的册子直接对照。→ 大表**不 Shuffle**。\n- **两本按 key 排序的电话簿逐页对照（Sort-Merge Join，SMJ）**：两拨货都按 key 排好序、飞到归并台上，两个人各翻各的，指针一路往下走，相同 key 就配对。→ **两边都 Shuffle**。\n- **一方按 key 重排做抽屉柜、另一方流式来查（Shuffle Hash Join，SHJ）**：把一拨货按 key 重排成一只抽屉柜（哈希表），另一拨货流式过来，每条直接拉开对应抽屉查。→ **至少一方 Shuffle**，且抽屉柜要塞得进内存。\n\n外加两个谁都不想要的**兜底**：小表广播 + 嵌套循环（BroadcastNestedLoopJoin，非等值条件时）、以及无 key 时的笛卡尔积（CartesianProduct）。\n\n⚠️ 比喻的边界（很重要）：\n① 三套预案**结果完全等价**，只是代价不同——策略选择是「等价改写」，不改变答案（这正是 Catalyst 能自由选的前提）。\n② 本课只给框架和名字，各策略的原理细节在第 3/4/5 课，Spark 到底凭什么选是第 6 课；本课不给任何阈值或参数。\n③ 计划里的节点名是**物理计划**才有的（复用 L4 逻辑 vs 物理），看到的是 `BroadcastHashJoin` / `SortMergeJoin` / `ShuffledHashJoin`；具体哪个会出现跟 Spark 版本、表大小、配置都有关，别背死「某代码一定出某节点」。\n④ 「抽屉柜」要占内存，「电话簿排序」要占磁盘与时间——没有免费的策略，只有合适的策略。\n\n【正式的技术定义】\n\n物理 JOIN 策略（Join Strategy）指 Spark 在物理计划阶段为逻辑 Join 选定的具体实现方式，主要有三种：\n- **Broadcast Hash Join（BHJ）**：小表广播到每个 Executor，内存构建哈希表，大表流式探测，大表不 Shuffle；\n- **Sort-Merge Join（SMJ）**：两侧按 join key 分区并排序（Shuffle），再归并配对，是大表 × 大表的通用默认策略；\n- **Shuffle Hash Join（SHJ）**：两侧按 key Shuffle 分区，较小一侧在内存建哈希表，较大一侧流式探测。\n兜底策略为 BroadcastNestedLoopJoin（一侧广播 + 嵌套循环，用于非等值条件）与 CartesianProduct（无等值条件时的笛卡尔积）。选择发生在物理计划阶段，由 Spark 依据统计信息与配置自动完成。\n\n【写下代码后，Spark 内部发生了什么】\n\n你写 `big.join(small, 'id').explain()`：Catalyst 先生成逻辑计划（只有一个 Join 节点，还没决定怎么拼），进入物理计划阶段后，由 join strategy 相关规则把它替换成某一种具体实现。所以你在 explain 里看到的 `BroadcastHashJoin(...)` / `SortMergeJoin(...)`，是**决策的结果**而不是你写出来的东西——决策依据（表大小估计、hint、配置）第 6 课拆。",
                "examples": [
                    {
                        "title": "BHJ 的计划长相（小表被广播）",
                        "code": "small = spark.read.parquet('dim_city')     # 很小\nbig   = spark.read.parquet('fact_order')   # 很大\nbig.join(small, 'city_id').explain()\n# 期望看到：BroadcastExchange + BroadcastHashJoin\n# 大表侧没有 Exchange → 大表不 Shuffle",
                        "note": "第一眼看 BroadcastExchange：它是「小表被复印发货」的信号，也是大表免 Shuffle 的证据。"
                    },
                    {
                        "title": "SMJ 的计划长相（两边都飞货）",
                        "code": "a = spark.read.parquet('big_a')\nb = spark.read.parquet('big_b')\na.join(b, 'id').explain()\n# 期望看到：两个 Exchange + SortMergeJoin",
                        "note": "两个 Exchange = 两边都按 key 重排。这是大表 × 大表最常见也最贵的形态。"
                    },
                    {
                        "title": "SHJ 的节点名（认得出就行）",
                        "code": "# 计划中出现 ShuffledHashJoin 时，说明走的是「建哈希抽屉柜 + 流式查」\na.join(b, 'id').explain()\n# ShuffledHashJoin(...) —— 与 SortMergeJoin 一样有 Exchange，但建的是哈希表不是排序",
                        "note": "SHJ 在默认配置的大表场景里不如 SMJ 常见，先记住名字与原理，条件在第 5 课讲。"
                    },
                    {
                        "title": "兜底：非等值条件 → 嵌套循环",
                        "code": "# 非等值 join：没法用哈希/归并，只能一条条比\na.join(b, a.amount > b.threshold).explain()\n# 常见：BroadcastNestedLoopJoin 或 CartesianProduct",
                        "note": "看到 NestedLoop / Cartesian 就是红灯——要么改写条件，要么先确认数据量是否小到能接受。"
                    }
                ],
                "key_points": [
                    "三种主要策略：BHJ（广播小表，大表免 Shuffle）/ SMJ（两边排序后归并）/ SHJ（一侧建哈希表、另一侧流式探测）",
                    "兜底：BroadcastNestedLoopJoin（非等值条件）/ CartesianProduct（无 key，O(n·m) 灾难）",
                    "三者结果等价、代价不同，选择发生在物理计划阶段",
                    "计划里认节点：BroadcastHashJoin / SortMergeJoin / ShuffledHashJoin",
                    "看 BroadcastExchange = 有小表被广播；数 Exchange 个数 = 判断重排了几次"
                ],
                "common_mistakes": [
                    {
                        "mistake": "以为三种策略会算出不同结果，于是纠结「哪个更准」。",
                        "why": "策略选择是等价改写（复用 L4 Catalyst 优化规则），结果一致，只影响快慢与资源占用。",
                        "fix": "关注代价（几次 Shuffle、占多少内存），别关注「正确性」。"
                    },
                    {
                        "mistake": "背「某段代码一定出 SortMergeJoin」。",
                        "why": "策略取决于两侧大小估计、hint、配置与 Spark 版本，不是代码文本决定的。",
                        "fix": "每次都实际 explain 看一眼，用计划说话。"
                    },
                    {
                        "mistake": "看到计划里没有 SortMergeJoin 就以为「没走 JOIN」。",
                        "why": "还可以是 BroadcastHashJoin 或 ShuffledHashJoin，节点名不同但都是 JOIN。",
                        "fix": "认全三个节点名，别只认一个。"
                    }
                ],
                "review": "上一课我们确认了 JOIN 的本质：先按 key 对齐、再拼合，所以通常比单表聚合更贵——而「对齐」这件事，Spark 内部其实有好几种做法。",
                "problem": "同一句 join，Spark 到底有哪几套拼法？它们的名字、长相和代价分别是什么？",
                "preview": "框架有了，接下来逐个拆。下集先讲最香的那套——把小表复印 N 份、「大表一次货都不用飞」的 Broadcast Hash Join。"
            }
        },
        {
            "title": "Broadcast Hash Join（小表广播）",
            "slug": "l6-broadcast-hash-join",
            "description": "掌握 BHJ 原理：把小表完整拷贝进每个 Executor 内存建哈希表，大表不 Shuffle 只流式探测；理解它为何能免去大表 Shuffle、以及「小表必须塞得进内存」这个硬前提。",
            "objective": "学完本课，你应该能够：说清 Broadcast Hash Join 的两步（广播小表 build / 大表流式 probe）；解释为什么它能免去大表那次 Shuffle，以及省下的正是 L5 讲的「序列化+网络+排序」那一串开销；知道硬前提是「小表必须能塞进 Executor 内存」，否则会 OOM 或退化；能在计划里认出 BroadcastExchange + BroadcastHashJoin；并明确具体广播阈值与调优留 Level 7，本课只讲前提与概念。",
            "estimated_minutes": 14,
            "order_index": 2,
            "prerequisites": "",
            "content": {
                "explanation": "【先用人话理解】\n\nL5 说过，Shuffle 贵就贵在「装箱 → 装车 → 卸货分拣」。那么最直接的省钱办法就是：**别让大表那批货飞**。如果你的维表只有几百几千行（城市字典、商品类目），而事实表有几十亿行，那根本没必要把几十亿行搬来搬去——把那本小字典复印 N 份发给每个工人就行了。\n\n【一个直观的心智模型】\n\n复用并正式命名 L5「空中飞货」的反面：**小册子复印 N 份**。\n- 小表 = 一本薄薄的小册子（城市字典）；\n- 大表 = 一仓库待处理的货；\n- 广播 = 把小册子复印 N 份，一个工人（Executor）手里塞一本；\n- 拼合 = 工人拿着手里的册子，对眼前的货逐条对照，当场就能拼好，**这批货一步都不用离开自己的托盘**。\n\n复用 L5 的「托盘 = 分区」：每个分区的货都在本地被处理，没有跨节点重排——这就是「大表不 Shuffle」。\n\n⚠️ 比喻的边界（很重要）：\n① **小表必须能塞进 Executor 内存**：工人手里的册子是占地方的真实内存，不是魔法投影。小表稍大一点，所有 Executor 同时撑着它，可能直接 OOM 或让 Spark 放弃广播、改走别的策略。\n② 广播**不是零成本**：小册子也要复印、也要运到每个工人手上（BroadcastExchange 本身就是一次网络传输），只是它搬的是小表，比搬大表便宜好几个数量级。\n③ 广播的是**整张小表**，不是「按需取用的索引」——即使大表里只用到其中 3 个 key，那一整本册子照样整份发过去。\n④ 「多大算小」由一个广播阈值控制，Spark 会拿小表的**统计大小估计**去和它比；具体阈值是多少、怎么调，是 Level 7 调优的内容，本课只讲「存在这个前提」。\n\n【正式的技术定义】\n\nBroadcast Hash Join（广播哈希连接）是 Spark 的一种物理 JOIN 策略：将较小一侧（build side）的完整数据通过 BroadcastExchange 发送到每个 Executor，在各 Executor 内存中构建哈希表；较大一侧（probe/stream side）的各分区数据在本地流式读取，逐条到哈希表中探测匹配。由于大表侧无需按 key 重分布，**大表不发生 Shuffle**，计划中只出现广播侧的 BroadcastExchange。适用前提是小表的统计大小低于广播阈值且能放入 Executor 内存。\n\n【写下代码后，Spark 内部发生了什么】\n\n你写 `big.join(small, 'city_id')`（small 很小）：\n1. 物理计划阶段，Catalyst 判断 small 的大小估计低于广播阈值 → 选定 BHJ；\n2. 计划中插入 `BroadcastExchange`，把 small 的完整数据收集后分发到每个 Executor；\n3. 每个 Executor 把收到的 small 在内存里建成哈希表（build）；\n4. big 的各个分区**在原 Executor 上**被逐条读取，拿 join key 去哈希表里探测（probe），命中就输出拼好的行；\n5. 全程 big 没有跨节点移动——省下的正是 L5 拆过的那串「装箱→装车→卸货分拣」。",
                "examples": [
                    {
                        "title": "典型的维表 JOIN：自动广播",
                        "code": "dim   = spark.read.parquet('dim_city')      # 几千行，很小\nfact  = spark.read.parquet('fact_order')    # 几十亿行\nfact.join(dim, 'city_id').explain()\n# BroadcastExchange + BroadcastHashJoin\n# 注意：fact 一侧没有 Exchange → 大表免 Shuffle",
                        "note": "这是数仓里最经典的「大事实表 × 小维表」，也是 BHJ 最该发挥的场景。"
                    },
                    {
                        "title": "手动加 broadcast 提示（写法预览，第 7 课细讲）",
                        "code": "from pyspark.sql import functions as F\nresult = fact.join(F.broadcast(dim), 'city_id')\nresult.explain()\n# 明确要求广播 dim，计划里同样出现 BroadcastExchange",
                        "note": "统计信息不准时 Spark 可能没自动广播，这时人可以主动提示——第 7 课展开。"
                    },
                    {
                        "title": "反例：把大表强行广播",
                        "code": "# 危险示范：dim 其实有上亿行，却强行要求广播\nfact.join(F.broadcast(huge_dim), 'city_id').explain()\n# 每个 Executor 都要在内存里撑一整份 huge_dim → 内存压力 / OOM",
                        "note": "广播的硬前提是小表真的小。别把「我以为它小」当成事实——先确认大小再广播。"
                    },
                    {
                        "title": "广播不是零成本：册子也要运",
                        "code": "# BroadcastExchange 本身就是一次网络传输\n# 只是传的是小表，而非大表\nfact.join(F.broadcast(dim), 'city_id').explain()\n# 计划里 BroadcastExchange 依然存在，只是数据量小得多",
                        "note": "BHJ 省的是「大表那次重排」，不是把所有传输都消灭了。"
                    }
                ],
                "key_points": [
                    "BHJ = 广播小表（build，内存建哈希表）+ 大表流式探测（probe）",
                    "最大收益：大表完全不 Shuffle，省掉 L5 那串「序列化+网络+排序」开销",
                    "硬前提：小表必须能塞进 Executor 内存，否则 OOM 或被 Spark 放弃",
                    "广播按整张小表发送，不是按需取用；广播本身仍有网络传输（BroadcastExchange）",
                    "计划认节点：BroadcastExchange + BroadcastHashJoin；大表侧无 Exchange"
                ],
                "common_mistakes": [
                    {
                        "mistake": "以为用了 BHJ 就「完全没有网络传输」。",
                        "why": "小表要被复制到每个 Executor，BroadcastExchange 本身就是一次传输，只是量小得多。",
                        "fix": "记住 BHJ 省的是大表那次 Shuffle，不是消灭所有传输。"
                    },
                    {
                        "mistake": "不管大小，给所有维表都加 broadcast。",
                        "why": "每个 Executor 都要在内存里撑一整份被广播的表，表一大就 OOM，还会挤占其他算子内存。",
                        "fix": "只在确认表「真的小」时广播；不确定就先 explain 看 Spark 自己的判断。"
                    },
                    {
                        "mistake": "以为「小表」是按行数判断的。",
                        "why": "Spark 判断的是数据的统计大小（字节级估计），宽表、长字符串字段会让它远比行数看起来大。",
                        "fix": "用「数据体积」而非「行数」判断能不能广播。"
                    }
                ],
                "review": "上一课我们把三套拼桌预案摆上了桌：复印小册子（BHJ）、电话簿逐页对照（SMJ）、抽屉柜流式查（SHJ）。",
                "problem": "最香的那套到底是怎么运作的？为什么小表一广播，大表就能一次货都不飞？代价和前提又是什么？",
                "preview": "可如果两边都是大表，谁都塞不进内存，小册子这招就废了。下集讲大表 × 大表的默认解法——两本电话簿排序后归并的 Sort-Merge Join。"
            }
        },
        {
            "title": "Sort-Merge Join（大表×大表默认）",
            "slug": "l6-sort-merge-join",
            "description": "掌握 SMJ 原理：两表各自按 join key 排序（两边都 Shuffle）后在归并台逐 key 扫描拼接；理解大表为何不能广播、以及为什么 SMJ 是大表场景的默认策略。",
            "objective": "学完本课，你应该能够：说清 Sort-Merge Join 的两步（两侧按 key 分区排序 → 归并配对）；解释为什么它必须两边都 Shuffle（同 key 必须到同一分区）、以及为什么大表不能走广播；理解「排序有代价，但不要求一侧塞进内存」使它成为大表 × 大表的通用默认；能在计划里认出两个 Exchange + SortMergeJoin；并知道具体调优（如排序溢出、分区数）留 Level 7。",
            "estimated_minutes": 14,
            "order_index": 3,
            "prerequisites": "",
            "content": {
                "explanation": "【先用人话理解】\n\n小册子那招有个硬前提：小表得真的小。可如果两边都是几十亿行呢？复印谁的都不合适——那就只能换思路：既然同 key 的记录必须凑到一起，那就**两边都按 key 重新排一遍**，让相同 key 落到同一个分区，然后两个指针顺着往下走，边走边配对。\n\n【一个直观的心智模型】\n\n想象两本**按字母排序的电话簿**（复用 L5 的空中飞货：这两本簿子是先各自排好序、再飞到归并台上的）：\n- 归并台两侧各放一本排好序的簿子；\n- 你左手翻 A 册、右手翻 B 册，比较当前页的姓氏；\n- 姓氏相同 → 配对输出，两边同时往下翻；\n- 不相同 → 把「字母更小」的那一侧往下翻一页，追上另一侧；\n- 一路扫到底，整张表就拼完了。\n\n复用「托盘 = 分区」「Executor = 工人」：排序后的簿子被切成 N 段（分区），每个工人领一段，各拼各的，互不干扰。\n\n⚠️ 比喻的边界（很重要）：\n① **两边都 Shuffle**：两本簿子都得重排一遍再飞过去，代价是双份的——这是 SMJ 最贵的地方。\n② 排序本身也要钱：全量排序，内存放不下时会 spill 到磁盘（复用 L5「spill 慢几个数量级」）；具体排序与溢出的调优留 L7。\n③ 但它**不要求任何一侧塞进内存**——这是它能扛住「大表 × 大表」的根本原因，也正是 BHJ 做不到的地方。\n④ 归并扫描是线性的（排完序后两边各扫一遍），不是「每条去另一本里翻一遍」——否则就退化成嵌套循环了。\n\n【正式的技术定义】\n\nSort-Merge Join（排序归并连接）是 Spark 处理等值 JOIN 的通用物理策略：两侧数据先按 join key 进行分区（Shuffle，各自一个 Exchange），并在分区内按 key 排序；随后在 reduce 端用两个游标对两侧有序数据进行归并扫描，key 相等即配对输出。由于它不要求任一侧完整驻留内存（可溢写磁盘），适用于大表 × 大表，是 Spark 在无法广播时的默认 JOIN 策略。\n\n【写下代码后，Spark 内部发生了什么】\n\n你写 `a.join(b, 'id')`（两边都很大）：\n1. 物理计划阶段：a 与 b 的大小估计都超过广播阈值 → 无法 BHJ，选定 SMJ；\n2. 计划中 a 侧插入一个 Exchange（按 id 哈希分区 + 分区内排序），b 侧同样插入一个 Exchange；\n3. Shuffle 完成后，同一个 id 的所有记录在两侧都落到了**同一个分区**；\n4. 每个分区内，两个有序游标归并扫描，key 相等就输出配对行；\n5. 整个计划里你会看到：`Exchange → Sort → SortMergeJoin`，两次 Exchange 就是它贵的证据。",
                "examples": [
                    {
                        "title": "大表 × 大表：默认走 SMJ",
                        "code": "a = spark.read.parquet('big_fact_a')   # 数十亿行\nb = spark.read.parquet('big_fact_b')   # 数十亿行\na.join(b, 'id').explain()\n# 期望看到：两个 Exchange + Sort + SortMergeJoin",
                        "note": "两个 Exchange 是 SMJ 的身份证：两侧都按 key 重排并排序，代价双份。"
                    },
                    {
                        "title": "为什么大表不能广播",
                        "code": "# 假想（危险）：把几十亿行的表广播出去\n# a.join(F.broadcast(b), 'id')\n# 每个 Executor 都要在内存里撑一整份 b → 必然 OOM",
                        "note": "广播要求「整份塞进内存」，几十亿行做不到——这就是 SMJ 存在的理由。"
                    },
                    {
                        "title": "SMJ 不要求一侧进内存",
                        "code": "# SMJ 的排序结果放不下时可溢写磁盘，虽慢但能跑完\na.join(b, 'id').explain()   # SortMergeJoin 节点本身不要求内存常驻整表",
                        "note": "能跑完比跑得快更重要——面对超大表，「能不 OOM」往往就是首要目标。"
                    },
                    {
                        "title": "归并是线性扫描，不是嵌套循环",
                        "code": "# 两侧已按 id 有序后，游标只需各扫一遍\na.join(b, 'id').explain()\n# SortMergeJoin ≠ NestedLoopJoin：复杂度天差地别",
                        "note": "看到 NestedLoop / Cartesian 才是红灯；SortMergeJoin 虽然贵，但它是「贵得有道理」。"
                    }
                ],
                "key_points": [
                    "SMJ = 两侧各自按 key 分区排序（两个 Exchange）+ 归并扫描配对",
                    "它是大表 × 大表的默认策略：不要求任一侧塞进内存",
                    "代价：两侧都 Shuffle + 全量排序，必要时 spill 磁盘（调优留 L7）",
                    "归并阶段是线性扫描（排序后各扫一遍），不是嵌套循环",
                    "计划认节点：两个 Exchange + Sort + SortMergeJoin"
                ],
                "common_mistakes": [
                    {
                        "mistake": "看到两个 Exchange 就以为「代码写错了，得消掉一个」。",
                        "why": "大表 × 大表必须两侧同 key 到同一分区，两个 Exchange 是物理必然，不是错误。",
                        "fix": "先判断能不能广播掉一侧；不能，就接受 SMJ 的代价。"
                    },
                    {
                        "mistake": "以为 SMJ 是把两边各读一遍、两两比对。",
                        "why": "归并建立在「两侧已按 key 有序」之上，是线性扫描，不是嵌套循环。",
                        "fix": "记住顺序：先排序（贵），后归并（便宜）。"
                    },
                    {
                        "mistake": "宁愿反复 OOM 也不肯放弃广播大表。",
                        "why": "广播要求整表进内存，几十亿行没有可行性。",
                        "fix": "大表对大表就用 SMJ：慢但能跑；要提速靠的是过滤/裁剪数据，不是硬广播。"
                    }
                ],
                "review": "上一课我们讲了最香的 BHJ：小册子复印 N 份，大表一次货都不用飞——前提是那本册子得真的小。",
                "problem": "可如果两边都是几十亿行的大表，谁都塞不进内存，小册子这招就彻底废了。那 Spark 怎么拼？",
                "preview": "除了「复印小册子」和「电话簿归并」，还有第三套预案：把一方做成抽屉柜（哈希表）、另一方流式来查的 Shuffle Hash Join——外加两个谁都不想要的兜底。"
            }
        },
        {
            "title": "Shuffle Hash Join 与兜底策略",
            "slug": "l6-shuffle-hash-join",
            "description": "掌握 Shuffle Hash Join（一侧按 key 重排建哈希表、另一侧流式探测）的原理与适用条件；以及两个兜底策略 BroadcastNestedLoopJoin / CartesianProduct 的触发场景与「千万别无 key 乱 join」的红线。",
            "objective": "学完本课，你应该能够：说清 Shuffle Hash Join 的原理（两侧按 key Shuffle 分区，较小一侧在内存建哈希表，较大一侧流式探测）；知道它与 BHJ/SMJ 的关键差异（仍需 Shuffle、且要求 build 侧能进内存）；认识两个兜底策略 BroadcastNestedLoopJoin（非等值条件）与 CartesianProduct（无 key，O(n·m)）；理解「无 key 乱 join 是灾难」这条红线；并明确 SHJ 的触发条件随版本变化，本课只讲原理不背条件。",
            "estimated_minutes": 13,
            "order_index": 4,
            "prerequisites": "",
            "content": {
                "explanation": "【先用人话理解】\n\nBHJ 是「小表不飞、大表不飞，只飞小册子」，SMJ 是「两边都飞、都排序再归并」。第三条路介于两者之间：**两边都按 key 重排（还是要飞），但其中一侧在内存里做成抽屉柜（哈希表），另一侧流式过来直接拉开抽屉查**——省掉排序这一步。\n\n【一个直观的心智模型】\n\n复用「拼桌」与 L5 的「空中飞货」：\n- 两拨货都按 key 飞到各自的托盘上（这一步和 SMJ 一样，仍是 Shuffle）；\n- 到位后，把**较小那一侧**做成一只抽屉柜：每个 key 一个抽屉，同 key 的记录全塞进对应抽屉；\n- 然后**较大那一侧**的货流式走过来，每条看一眼自己的 key，直接拉开那个抽屉，把里面的记录全配一遍。\n\n抽屉柜不用排序，但它得**做得进屋里**（内存）——这就是 SHJ 的命门。\n\n⚠️ 比喻的边界（很重要）：\n① SHJ **仍然要 Shuffle**（至少两侧按 key 重排），别把它和「免 Shuffle 的 BHJ」混为一谈；它省的是排序，不是传输。\n② 抽屉柜要占内存：build 侧一旦数据量偏大，就会撑爆内存或被迫放弃——所以大表场景 Spark 更偏爱 SMJ（可溢写磁盘）。\n③ SHJ 具体在什么条件下被选中，跟 Spark 版本、配置、统计信息都有关系，**别背死条件**，看 explain 说话。\n④ 兜底的两位都不是好消息：BroadcastNestedLoopJoin（一侧广播 + 嵌套循环，非等值条件时）、CartesianProduct（无 key，每条对每条）。看到它们意味着 O(n·m) 级别的风险。\n\n【正式的技术定义】\n\nShuffle Hash Join（SHJ）：两侧数据按 join key 进行 Shuffle 分区，使相同 key 落到同一分区；随后较小一侧（build side）在内存中构建哈希表，较大一侧（stream/probe side）以流式方式逐条探测匹配。它不要求排序，但要求 build 侧能放入内存。\n兜底策略：\n- **BroadcastNestedLoopJoin（BNLJ）**：将一侧广播后，用嵌套循环逐条比对，用于非等值连接条件；\n- **CartesianProduct**：无等值条件（或条件恒真）时的笛卡尔积，结果行数为两侧行数之积。\n二者在数据量大时都极其昂贵，属于应避免出现在生产计划里的节点。\n\n【写下代码后，Spark 内部发生了什么】\n\n你写 `a.join(b, 'id')` 且 Spark 选了 SHJ：两侧各一次 Exchange 按 id 分区（Shuffle），同一分区内 b（较小侧）被读进内存建哈希表，a 的记录流式过来逐条探测、命中即输出——全程没有排序，但有传输、有内存占用。\n你写 `a.crossJoin(b)` 或 join 条件恒真：Spark 找不到可用等值 key，退化成 CartesianProduct，结果行数 = count(a) × count(b)，集群会在瞬间被压垮。",
                "examples": [
                    {
                        "title": "SHJ 的计划长相",
                        "code": "a.join(b, 'id').explain()\n# 出现 ShuffledHashJoin：有 Exchange（按 key 重排），但无 Sort\n# build 侧在内存建哈希表，stream 侧流式探测",
                        "note": "和 SMJ 的区别一眼可见：有没有 Sort。SHJ 省排序、费内存。"
                    },
                    {
                        "title": "SHJ 与 BHJ 的本质差别",
                        "code": "# BHJ：小表广播，大表不 Shuffle\nbig.join(F.broadcast(small), 'id').explain()\n#   大表侧无 Exchange\n\n# SHJ：两侧都要按 key 重排\na.join(b, 'id').explain()\n#   两侧都有 Exchange",
                        "note": "只有 BHJ 能免掉大表那次 Shuffle；SHJ 免的是排序，不是传输。"
                    },
                    {
                        "title": "兜底：非等值条件 → 嵌套循环",
                        "code": "# 非等值条件：哈希与归并都使不上\na.join(b, a.amount > b.threshold).explain()\n# 常见 BroadcastNestedLoopJoin（一侧广播后逐条比对）",
                        "note": "看到 NestedLoop 先确认数据量：小表尚可，大表就是灾难。"
                    },
                    {
                        "title": "红线：无 key 的笛卡尔积",
                        "code": "a.crossJoin(b).explain()\n# CartesianProduct：结果行数 = count(a) × count(b)\n# 1 亿 × 1 亿 = 1 亿亿行，神仙难救",
                        "note": "生产里最常见的事故是 join 条件写错（恒真/列选错）悄悄退化成笛卡尔积——写完先 count() 验量级。"
                    }
                ],
                "key_points": [
                    "SHJ = 两侧按 key Shuffle 分区 + build 侧内存建哈希表 + stream 侧流式探测",
                    "SHJ 免的是排序，不是 Shuffle；它仍需两侧按 key 重排",
                    "SHJ 要求 build 侧能进内存，数据量大时 Spark 更倾向可溢写的 SMJ",
                    "兜底策略：BroadcastNestedLoopJoin（非等值条件）/ CartesianProduct（无 key）",
                    "看到 NestedLoop / Cartesian = 红灯，先确认数据量或改写条件"
                ],
                "common_mistakes": [
                    {
                        "mistake": "以为 SHJ 和 BHJ 一样「不用 Shuffle」。",
                        "why": "SHJ 仍需两侧按 key 分区重排，只是把排序换成了建哈希表。",
                        "fix": "只有 BHJ 能让大表免 Shuffle；SHJ 只是省了排序。"
                    },
                    {
                        "mistake": "死记「什么情况下一定走 SHJ」。",
                        "why": "触发条件与 Spark 版本、配置、统计信息估计都有关，会变。",
                        "fix": "认原理 + 看 explain，别背条件表。"
                    },
                    {
                        "mistake": "join 条件写错，悄悄退化成笛卡尔积还浑然不觉。",
                        "why": "恒真条件或选错列等价于无 key，结果行数爆炸，作业会「跑很久后才挂」。",
                        "fix": "join 完先 count() 看量级；explain 里看到 CartesianProduct 立刻停手检查条件。"
                    }
                ],
                "review": "上一课我们讲了大表 × 大表的默认解法 SMJ：两边都飞、都排序，然后像两本排序电话簿一样归并配对。",
                "problem": "可排序本身也很贵。有没有一种办法：保留「按 key 重排」，但省掉排序，改成建一张查询飞快的抽屉柜？",
                "preview": "三套预案都见过了，可 Spark 到底凭什么在这三套之间做选择？下集拆开它的决策依据——表大小统计、阈值概念、hint 与配置开关，以及统计不准时会发生什么。"
            }
        },
        {
            "title": "Spark 怎么选 JOIN 策略（基于代价）",
            "slug": "l6-how-spark-chooses",
            "description": "拆解 Spark 在物理计划阶段选择 JOIN 策略的决策依据：两侧大小统计、广播阈值概念、hint 提示、配置开关；并教读者用 explain 识别实际走了哪种策略。",
            "objective": "学完本课，你应该能够：说清 JOIN 策略是在物理计划阶段由 Spark 自动选定的；列举决策依据（两侧大小的统计估计、广播阈值概念、是否等值连接、hint、相关配置开关）；理解统计信息缺失/不准会导致误判（该广播没广播、不该广播却广播）；知道用 explain 验证实际策略、必要时用 Spark UI 佐证；并明确具体阈值数值、参数改写与调优留 Level 7。",
            "estimated_minutes": 14,
            "order_index": 5,
            "prerequisites": "",
            "content": {
                "explanation": "【先用人话理解】\n\n三套预案摆在面前，谁来做选择？还是那位老熟人——Catalyst 优化大脑（复用 L3/L4）。它不看你写了什么花哨的 API，只看一件事：**这两拨货各有多大，按哪种拼法最划算**。\n\n【一个直观的心智模型】\n\n复用 L3 的「Catalyst = 优化大脑 / 总工程师」：总工站在两堆货前，先看一眼两堆的**尺码单**（统计信息），再决定：\n- 小得能塞进工人手里的（大小估计低于广播阈值）→ 复印小册子（BHJ）；\n- 小不了但某一侧还算苗条、能做成抽屉柜 → 建哈希抽屉柜（SHJ）；\n- 两边都巨大 → 两本电话簿排序归并（SMJ）。\n\n它的判断完全基于**尺码单**，而不是基于真实的称重结果——这点非常关键。\n\n⚠️ 比喻的边界（很重要）：\n① 尺码单是**估计值**，不是实测。数据源没统计信息（如未做过 analyze、或中间经过 UDF/复杂变换无法估计）时，Spark 只能猜，猜错就会误判：该广播的没广播、不该广播的硬广播。\n② 「大小」的判断由**广播阈值**这把尺子决定（概念上就是「多大算小」）；尺子的具体刻度和怎么调，是 Level 7 调优的事，本课只讲「存在这把尺子、它是决策依据之一」。\n③ hint 是**建议不是命令**：你可以用 `F.broadcast()` 表达倾向，但 Spark 仍可能基于自身判断不采纳（下一课细讲）。\n④ 决策发生在**物理计划阶段**，所以只有 `explain()`（物理计划视角）才看得到结果，逻辑计划里没有策略之分。\n\n【正式的技术定义】\n\nJOIN 策略选择（Join Selection）发生在 Spark 物理计划阶段：优化器依据两侧数据的**统计大小估计**、join 类型（是否等值连接、是否外连接等）、用户 hint、以及相关配置开关（如广播阈值的启用与否），在候选策略中择优。一般优先级是：可广播则优先 Broadcast Hash Join；否则在 Shuffle Hash Join 与 Sort-Merge Join 间依「build 侧能否进内存 / 是否可排序溢写」等条件取舍，Sort-Merge Join 是最通用的兜底。由于依据的是估计值而非真实运行数据，统计信息缺失或不准确会导致策略误判。\n\n【写下代码后，Spark 内部发生了什么】\n\n你写 `a.join(b, 'id')` 并 explain：\n1. Catalyst 先生成并优化逻辑计划（此时还没有「怎么拼」的概念）；\n2. 物理计划阶段，join 选择规则读取两侧的大小估计；\n3. 若 b 的估计大小低于广播阈值且连接类型支持 → 选 BHJ，计划中出现 BroadcastExchange；\n4. 否则按条件在 SHJ / SMJ 之间取舍，通常落到 SMJ（两 Exchange + Sort）；\n5. 你看到的节点名就是这次决策的**结果**。若发现「明明是小表却没广播」，八成是统计信息缺失导致估计偏大——这就是下一课要动手解决的场景。",
                "examples": [
                    {
                        "title": "用 explain 验证实际策略",
                        "code": "a.join(b, 'id').explain()\n# 看节点名：BroadcastHashJoin / ShuffledHashJoin / SortMergeJoin\n# 看 Exchange 个数：0~1 = 广播路径；2 = 两侧重排",
                        "note": "explain 是验证决策的唯一低成本手段（它不执行，复用 L4）。"
                    },
                    {
                        "title": "小表却没广播？多半是估计不准",
                        "code": "# dim 明显很小，explain 却显示 SortMergeJoin\na.join(dim, 'id').explain()\n# 常见原因：dim 经过了复杂变换，Spark 估不出它的真实大小，只能保守按大表处理",
                        "note": "优化器是「按尺码单发货」——尺码单缺失，它就按最坏情况处理。"
                    },
                    {
                        "title": "先过滤再 join，改变大小估计",
                        "code": "dim_small = spark.read.parquet('dim').filter('region = 86')\na.join(dim_small, 'id').explain()\n# 过滤后数据量骤减，更可能落在广播阈值内",
                        "note": "过滤是改变「尺码单」最直接的手段；谓词下推（L4）会让这一步更省。"
                    },
                    {
                        "title": "hint 只是建议，仍需 explain 验证",
                        "code": "from pyspark.sql import functions as F\na.join(F.broadcast(dim), 'id').explain()\n# 即便给了 hint，也要看计划里是否真的出现 BroadcastExchange",
                        "note": "给了 hint 不等于一定采纳——第 7 课讲清什么时候它会失效。"
                    }
                ],
                "key_points": [
                    "策略在物理计划阶段由 Spark 自动选定，依据的是估计值而非实测",
                    "决策依据：两侧大小统计、广播阈值（概念）、是否等值连接、hint、配置开关",
                    "一般优先级：能广播优先 BHJ；否则在 SHJ / SMJ 间取舍，SMJ 是通用兜底",
                    "统计信息缺失/不准 → 误判：该广播没广播、或硬广播大表",
                    "具体阈值数值、参数改写与调优留 Level 7；本课只讲决策框架"
                ],
                "common_mistakes": [
                    {
                        "mistake": "以为 Spark 会先跑一遍看看真实大小再决定策略。",
                        "why": "它用的是统计估计（规划期），不是实测（运行期），所以会误判。",
                        "fix": "对关键 JOIN 自己 explain 一眼；估计不准时用 hint 或先过滤。"
                    },
                    {
                        "mistake": "以为「小表」是按行数肉眼判断，Spark 也这么想。",
                        "why": "Spark 看的是字节级大小估计，宽表/长字符串会让它远比行数看起来大。",
                        "fix": "把「体积」而不是「行数」作为判断口径。"
                    },
                    {
                        "mistake": "现在就去死磕广播阈值的最佳数值。",
                        "why": "具体阈值与调优参数是 Level 7 的主题，本课只讲它是决策依据之一。",
                        "fix": "先掌握「怎么看出走了哪条路」，调优留 L7。"
                    }
                ],
                "review": "上一课我们见过了第三套预案 SHJ（抽屉柜、免排序但仍要 Shuffle）以及两个谁都不想要的兜底策略。三套预案齐了。",
                "problem": "可 Spark 到底凭什么在这三套之间做选择？它看的是什么——真实大小，还是别的东西？",
                "preview": "既然决策靠的是「尺码单」，那尺码单不灵的时候怎么办？下集讲人怎么主动出手：broadcast() 提示怎么写、什么时候会失效、以及广播反噬的坑。"
            }
        },
        {
            "title": "主动控制：broadcast() 提示与避坑",
            "slug": "l6-broadcast-hint-and-control",
            "description": "掌握主动干预手段：F.broadcast() / hint('broadcast') 强制广播；当统计信息缺失导致没广播时手动补救；以及广播反噬（小表不小、内存压力）的避坑。",
            "objective": "学完本课，你应该能够：会用 `F.broadcast(df)` 、`df.hint('broadcast')` 与 SQL 的 broadcast hint 主动要求广播；说清什么场景需要人工提示（统计信息缺失/不准导致该广播没广播）；知道 hint 是「建议不是命令」及常见失效情况；识别广播反噬（小表其实不小、同时广播多张表占满 Executor 内存）；并明确具体调优参数与阈值改写留 Level 7。",
            "estimated_minutes": 13,
            "order_index": 6,
            "prerequisites": "",
            "content": {
                "explanation": "【先用人话理解】\n\n上一课说了，Spark 决策靠的是「尺码单」（统计估计）。尺码单一缺失，它就保守处理——明明是本小册子，它偏当大部头，于是老老实实走 SMJ，白花两次 Shuffle 的钱。这时候你得自己出手：把册子塞到总工手里说「就这本，广播它」。\n\n【一个直观的心智模型】\n\n复用「小册子复印 N 份」：正常情况下，总工（Catalyst）自己会看哪本薄、主动复印；可当他看不清厚度时（统计缺失），你就**主动把那本册子递过去**，明确说「别空运大表了，用它对照」。\n\n注意你的措辞是**建议**：「我建议你复印这本」——总工仍可能基于自己的判断（比如他发现这册子其实有八百页）拒绝执行。\n\n⚠️ 比喻的边界（很重要）：\n① hint 是**建议不是命令**：当被广播侧本身太大、或连接类型不支持广播时，Spark 可以不采纳你的 hint，悄悄走回 SMJ——所以给了 hint 之后**必须 explain 验证**，不能「写了就当生效了」。\n② 广播**反噬**：被广播的表会完整驻留在每个 Executor 的内存里。同时 join 多张维表、或广播的表其实没你想的那么小，Executor 内存会被挤爆，反而拖垮整个作业（甚至 OOM）。\n③ 「它看起来小」≠「它真的不小」：读进来的原始表可能很大，你以为 `filter` 之后就小了，但**估计值未必更新**——广播的是过滤后的结果，判断却可能基于过滤前的估计。\n④ 广播表被整份发送：即使大表只用到其中几个 key，整张表照样全发一遍。\n⑤ 具体的阈值参数与改写技巧留 Level 7，本课只讲「怎么用 hint、什么时候会翻车」。\n\n【正式的技术定义】\n\nbroadcast hint 是用户向优化器表达的**策略倾向**：通过 `F.broadcast(df)`（DataFrame API）、`df.hint('broadcast')` 或 SQL 中的 broadcast 提示，建议 Spark 将指定一侧作为 build side 进行广播，从而走 Broadcast Hash Join。它在计划中表现为 ResolvedHint / BroadcastExchange 节点。hint 不保证生效——优化器仍可能因大小估计、连接类型或配置原因选择其他策略。广播的代价是被广播表将在每个 Executor 内存中保留一份完整副本。\n\n【写下代码后，Spark 内部发生了什么】\n\n你写 `fact.join(F.broadcast(dim), 'city_id')`：\n1. 逻辑计划里先出现一个 ResolvedHint（记住了你的倾向）；\n2. 物理计划阶段，若优化器采纳 → 插入 BroadcastExchange，把 dim 的完整数据分发到每个 Executor，走 BHJ；\n3. 若不采纳（例如 dim 的大小估计远超广播阈值、或连接类型不支持）→ 计划里回到 SortMergeJoin，hint 被静默忽略；\n4. 生效后，每个 Executor 内存中都常驻一份 dim 的哈希表——这就是它的内存账单。",
                "examples": [
                    {
                        "title": "DataFrame API：F.broadcast()",
                        "code": "from pyspark.sql import functions as F\nresult = fact.join(F.broadcast(dim), 'city_id')\nresult.explain()\n# 生效时可见 BroadcastExchange + BroadcastHashJoin",
                        "note": "最常用的写法。给了 hint 一定要回看 explain——生效与否看计划，不看你的心意。"
                    },
                    {
                        "title": "等价写法：hint('broadcast')",
                        "code": "result = fact.join(dim.hint('broadcast'), 'city_id')\nresult.explain()\n# 与 F.broadcast(dim) 目的一致：指定广播左侧/该侧",
                        "note": "两种写法等价，选一个团队统一即可。"
                    },
                    {
                        "title": "SQL 里的 broadcast 提示",
                        "code": "spark.sql('SELECT /*+ BROADCAST(d) */ f.*, d.city_name '\n          'FROM fact f JOIN dim d ON f.city_id = d.city_id').explain()\n# 提示写在 SELECT 后的注释语法里，效果与 API 一致",
                        "note": "SQL 与 API 共用同一个 Catalyst（L3），所以 hint 效果一样。"
                    },
                    {
                        "title": "反例：一次广播太多张表",
                        "code": "# 每张维表都要在每个 Executor 内存里各占一份\nr = (fact\n     .join(F.broadcast(dim_city), 'city_id')\n     .join(F.broadcast(dim_prod), 'prod_id')\n     .join(F.broadcast(dim_user), 'user_id'))\nr.explain()\n# 三份常驻内存 + fact 自身计算内存 → Executor 压力陡增",
                        "note": "广播不是免费的午餐：每多广播一张，就多一份常驻内存。宁可只广播最有价值的那张。"
                    }
                ],
                "key_points": [
                    "主动提示三种写法：F.broadcast(df) / df.hint('broadcast') / SQL /*+ BROADCAST(别名) */",
                    "典型用途：统计信息缺失导致「小表没被自动广播」时人工补救",
                    "hint 是建议不是命令，可能被静默忽略 → 必须 explain 验证",
                    "广播反噬：被广播表在每个 Executor 内存各留一份完整副本，多了会 OOM",
                    "具体阈值参数与改写技巧留 Level 7，本课只讲用法与避坑"
                ],
                "common_mistakes": [
                    {
                        "mistake": "写了 F.broadcast() 就默认它一定生效。",
                        "why": "hint 只是建议；当被广播侧过大或连接类型不支持时，优化器会忽略它。",
                        "fix": "每次写完都用 explain 确认计划里真的出现了 BroadcastExchange。"
                    },
                    {
                        "mistake": "给所有 join 都无脑加 broadcast，以为能普遍提速。",
                        "why": "每张被广播的表都会在每个 Executor 内存里常驻一份，多了直接挤爆内存。",
                        "fix": "只广播确认很小、且能省掉最大那次 Shuffle 的表。"
                    },
                    {
                        "mistake": "以为 filter 之后的小表「一定」被准确估计为小表。",
                        "why": "统计估计可能基于过滤前的体积，优化器仍按大表处理。",
                        "fix": "这种场景正是 broadcast hint 的价值所在——先 explain 看，没广播就手动提示。"
                    }
                ],
                "review": "上一课我们拆了 Spark 的决策依据：它靠「尺码单」（统计估计）选策略，尺码单不灵就会误判——明明的小册子被当成大部头，白花两次 Shuffle。",
                "problem": "那尺码单不灵的时候，人能不能自己出手？怎么写这个提示、它什么时候会失效、又会在什么时候反噬？",
                "preview": "策略选对了、广播也给了，作业却还是卡在最后 1% 上不动——下集讲 JOIN 里最阴险的那个问题：数据倾斜。"
            }
        },
        {
            "title": "JOIN 中的数据倾斜（Skew）",
            "slug": "l6-join-data-skew",
            "description": "识别 JOIN 数据倾斜：某 key 数据爆炸导致对应 Task 扛绝大多数数据、长尾巨慢；理解它的运行时现象（计划里看不出）与原理级应对思路（salting 加盐打散、隔离大 key、用 BHJ 绕过）。",
            "objective": "学完本课，你应该能够：说清 JOIN 数据倾斜是什么（某 key 记录数远超其他 → 该分区 Task 数据量巨大 → 成为长尾任务拖慢整体）；知道它在执行计划里看不出来、要在运行时指标（Task 耗时/数据量分布）里发现；理解三条原理级应对思路（salting 加盐把大 key 拆成 N 个子 key、把大 key 单独拆出来分别处理、用广播绕过 Shuffle）；并明确 skew 的具体开关与深调优留 Level 7。",
            "estimated_minutes": 14,
            "order_index": 7,
            "prerequisites": "",
            "content": {
                "explanation": "【先用人话理解】\n\n前面所有策略都在解决「怎么拼更省」。可有一种慢，跟策略无关：99 个 Task 早就干完下班了，剩下 1 个还在苦哈哈地搬——因为它手里那个 key 的数据量，比别人多几百倍。整体作业只能等它。这就是数据倾斜（Data Skew）。\n\n【一个直观的心智模型】\n\n复用「两拨货按 key 拼桌」：拼桌时按 key 分座位。正常情况下每个座位坐几个人；可偏偏有个座位（比如 key = 未知城市 / 空值 / 热门商品）挤了 **90% 的人**。\n\n结果就是：那一桌的工人累死，其他桌的工人早就收工在旁边喝茶——**整体完工时间 = 最慢那一桌的时间**。\n\n⚠️ 比喻的边界（很重要）：\n① **计划里看不出倾斜**：执行计划只告诉你「按 key 重排」，不告诉你每个 key 有多少条。这是 L4 就埋下的伏笔——「计划相同 ≠ 运行时性能相同」。要发现它，得看运行时（Spark UI 的 Task 耗时/数据量分布）。\n② **加分区数救不了单个 key**：同 key 的记录按哈希必须落到同一个分区，你把托盘数从 200 加到 2000，那个巨大的 key 依然完整地待在同一个分区里——它只会被换到另一个托盘，不会被拆开。这正是「加盐」必须存在的原因。\n③ 应对的**原理**是打散：把大 key 拆成 N 个子 key 让它在多个分区间摊开（salting），或把大 key 单独拎出来单独处理，或用广播直接绕开 Shuffle。\n④ 具体的倾斜开关、自适应优化参数与深调优，**全部留给 Level 7**，本课只到「能认出来 + 懂原理」。\n\n【正式的技术定义】\n\n数据倾斜（Data Skew）指数据按 key 分布严重不均：少数 key 拥有的记录数远超平均值。在 JOIN（以及 groupBy 等按 key 重分布的操作）中，相同 key 必须落到同一分区，因此这些「巨型 key」会让个别 Task 处理的数据量远超其他，成为长尾任务（straggler），作业的最终完成时间被最慢的 Task 决定。\n原理级应对思路：\n- **Salting（加盐）**：给大 key 的记录加上随机前缀（如 key_0 ~ key_N），把它拆成 N 个子 key 分散到不同分区，另一侧对应地「复制膨胀」后再 join；\n- **隔离大 key**：把少数巨型 key 单独过滤出来单独处理，其余走常规路径；\n- **绕开 Shuffle**：若一侧足够小，改用 Broadcast Hash Join，让大表根本不按 key 重排，倾斜自然失效。\n\n【写下代码后，Spark 内部发生了什么】\n\n你写 `a.join(b, 'id')` 且 id = 0 占了 80% 的记录：Shuffle 时所有 id=0 的记录被哈希到同一分区，那个 Task 要处理 80% 的数据，其余 199 个 Task 分剩下 20%。explain 输出一切如常（两个 Exchange + SortMergeJoin），只有运行时才发现「1 个 Task 跑了 40 分钟，其他 199 个 20 秒」。\n加盐之后：a 侧的 id=0 被改写成 `0_0` ~ `0_7` 共 8 个子 key，b 侧的 id=0 记录复制 8 份分别对应这 8 个子 key，Shuffle 时它们被哈希到 8 个不同分区，压力被摊开——代价是 b 侧数据被放大了 N 倍，所以它只适合「少数大 key」的场景。",
                "examples": [
                    {
                        "title": "倾斜的典型症状（运行时才看得见）",
                        "code": "a.join(b, 'id').count()\n# explain 一切正常：两个 Exchange + SortMergeJoin\n# 但运行时：199 个 Task 20 秒完成，1 个 Task 跑了 40 分钟",
                        "note": "计划相同 ≠ 运行时相同（复用 L4 边界）。看到「进度条卡在 99%」就该怀疑倾斜。"
                    },
                    {
                        "title": "为什么加分区数救不了倾斜",
                        "code": "# 增加分区数不会把同一个 key 拆开：\na.repartition(2000).join(b.repartition(2000), 'id')\n# id=0 的所有记录仍哈希到同一个分区，只是换了个托盘",
                        "note": "同 key 必须同分区——这是哈希分区的铁律，也是倾斜无法靠加分区解决的原因。"
                    },
                    {
                        "title": "Salting 加盐：把大 key 拆成 N 个子 key",
                        "code": "from pyspark.sql import functions as F\nN = 8\n# a 侧：给 id 加随机后缀，把大 key 打散成 N 份\na_salt = a.withColumn('salt', F.floor(F.rand() * N)) \\\n          .withColumn('id_salt', F.concat(F.col('id'), F.lit('_'), F.col('salt')))\n# b 侧：把每条记录膨胀成 N 份，分别对应 0~N-1 号后缀\nb_salt = b.withColumn('salt', F.explode(F.array([F.lit(i) for i in range(N)]))) \\\n          .withColumn('id_salt', F.concat(F.col('id'), F.lit('_'), F.col('salt')))\na_salt.join(b_salt, 'id_salt').count()\n# 原理：大 key 被拆到 N 个分区平摊压力（代价是 b 侧数据膨胀 N 倍）",
                        "note": "这是原理示意：加盐只适合「少数大 key」——否则膨胀的代价会超过收益。深调优留 L7。"
                    },
                    {
                        "title": "另一条路：用广播绕开 Shuffle",
                        "code": "# 若 b 其实足够小，广播后大表不按 key 重排，倾斜无从谈起\na.join(F.broadcast(b), 'id').count()",
                        "note": "BHJ 顺带解决倾斜：没有按 key 的 Shuffle，就没有「某 key 撑爆某分区」。"
                    }
                ],
                "key_points": [
                    "倾斜 = 少数 key 数据爆炸 → 该分区 Task 成为长尾，整体被最慢 Task 拖住",
                    "执行计划里看不出倾斜，必须看运行时（Task 耗时/数据量分布）",
                    "加分区数救不了：同 key 必须同分区，巨大 key 不会被拆开",
                    "原理级应对：salting 加盐打散 / 隔离大 key 单独处理 / 用 BHJ 绕开 Shuffle",
                    "具体倾斜开关与深调优留 Level 7，本课只到「能识别 + 懂原理」"
                ],
                "common_mistakes": [
                    {
                        "mistake": "作业卡在 99% 时，第一反应是加资源或加分区数。",
                        "why": "倾斜时单个 key 无法被分区拆开，加机器只是让 199 个 Task 更快空转。",
                        "fix": "先确认是不是倾斜（看 Task 耗时分布），再按打散/隔离/广播的思路处理。"
                    },
                    {
                        "mistake": "以为 explain 能看出倾斜。",
                        "why": "计划只有算子和估算行数，没有「每个 key 多少条」的真实分布。",
                        "fix": "用运行时指标识别（Spark UI）；计划只负责「怎么看拼」，不管「数据均不均」。"
                    },
                    {
                        "mistake": "对所有 key 无脑加盐。",
                        "why": "加盐要把另一侧膨胀 N 倍，key 一多，膨胀的数据量比省下的还多。",
                        "fix": "加盐只针对少数巨型 key，或用于隔离出来的那一小撮数据。"
                    }
                ],
                "review": "上一课我们学会了主动出手：用 broadcast() 提示弥补统计信息的失灵，也知道 hint 可能被忽略、广播太多会反噬。",
                "problem": "可策略选对了、广播也给了，作业还是卡在最后 1% 一动不动——199 个 Task 早下班了，剩下 1 个还在死扛。这是怎么回事？",
                "preview": "最后把所有道具串成一张「拼桌预案单」：判大小 → 选策略 → 找倾斜 → 决定要不要广播。下集综合实战。"
            }
        },
        {
            "title": "综合练习",
            "slug": "l6-comprehensive",
            "description": "给真实 JOIN 代码，用 explain 判断实际策略、是否触发大表 Shuffle、识别可广播的小表、指出倾斜风险；能选策略、能给 hint。",
            "objective": "学完本课，你应该能够：拿到一段真实 JOIN 代码，按「判两侧大小 → 看计划认策略 → 数 Exchange 判断是否免 Shuffle → 找可广播的小表并给 hint → 指出潜在倾斜风险」的完整流程做诊断；说清 BHJ / SMJ / SHJ / 兜底四者的触发场景与代价差异；并明确本课只验证「看得懂、能选、能给 hint」，不要求手调参数（深调优留 Level 7）。",
            "estimated_minutes": 15,
            "order_index": 8,
            "prerequisites": "",
            "content": {
                "explanation": "【先用人话理解】\n\nLevel 6 到这儿就齐了。回头看，我们其实只教你一套**固定动作**：拿到一句 join，先问多大、再看计划、数 Exchange、找小册子、最后想想有没有哪个 key 会撑爆一个工位。走完这五步，你就能对任意一句 JOIN 说出「它现在是怎么跑的、能不能更省、风险在哪」。\n\n【一个直观的心智模型】\n\n把前面所有道具串成一张**拼桌预案单**（检查清单）：\n1. **判大小**：两拨货各多大？有没有明显的小表？（小册子候选）\n2. **看计划**：explain 一眼，节点名是 BroadcastHashJoin / SortMergeJoin / ShuffledHashJoin / NestedLoop / Cartesian？\n3. **数 Exchange**：0~1 个 = 走了广播（大表免飞）；2 个 = 两边都飞（SMJ/SHJ）；\n4. **给不给 hint**：该广播没广播（统计失灵）→ `F.broadcast()`；不该广播别乱给（内存反噬）；\n5. **找倾斜**：有没有 key 会一桌挤满人？有 → 打散 / 隔离 / 广播绕过。\n\n⚠️ 比喻的边界（很重要）：\n① 这张清单只是**读得懂**的清单，不是调优清单：具体阈值、分区数最优值、倾斜开关等都是 Level 7 的地盘，本课不要求你会调参数。\n② **计划相同 ≠ 运行时性能相同**：同样的 SortMergeJoin，一次 30 秒、一次 40 分钟，差别可能在倾斜、在数据分布、在 spill——清单第 5 步正是为此存在。\n③ explain 不执行、零成本（复用 L4）：诊断阶段随便看，但别把「看起来省」当成「真的快」，最终仍要以运行时为准。\n④ 策略是等价改写，选错不会算错结果，只会让你多付钱（时间/资源）。\n\n【正式的技术定义】\n\nJOIN 诊断的标准化流程：\n（1）估算两侧数据规模，识别广播候选；\n（2）用 `explain()` 读取物理计划，依据节点名识别实际策略（BroadcastHashJoin / ShuffledHashJoin / SortMergeJoin / BroadcastNestedLoopJoin / CartesianProduct）；\n（3）通过 Exchange 的数量判断重排次数，BroadcastExchange 表示存在广播、大表侧无 Exchange 即免 Shuffle；\n（4）对「应广播而未广播」的场景施加 broadcast hint，并复核其是否生效；\n（5）评估 key 分布，识别数据倾斜风险，按 salting / 隔离大 key / 广播绕过等原理级思路应对。\n该流程只覆盖「识别与选择」，不涉及定量调优（Level 7）。\n\n【写下代码后，Spark 内部发生了什么】\n\n你拿到 `fact.join(dim_city, 'city_id').join(dim_prod, 'prod_id')` 这样的真实代码：\n1. Catalyst 为每个 Join 分别做策略选择（不是整条链统一选一种）；\n2. 第一个 join 若 dim_city 够小 → BHJ（BroadcastExchange + 大表不飞）；\n3. 第二个 join 若 dim_prod 估不出大小 → 可能落到 SMJ（两个 Exchange + Sort）；\n4. 你 explain 后决定给 dim_prod 加 `F.broadcast()`，再 explain 确认 BroadcastExchange 真的出现；\n5. 最后想一想：city_id 里有没有「未知城市」这种巨型 key？有 → 隔离或打散。\n走完这五步，一句 JOIN 的账你就算清楚了。",
                "examples": [
                    {
                        "title": "完整诊断：先看计划再动手",
                        "code": "q = (fact.join(dim_city, 'city_id')\n         .join(dim_prod, 'prod_id'))\nq.explain()\n# 逐个 Join 看：\n#   BroadcastHashJoin → 已广播，大表免 Shuffle\n#   SortMergeJoin     → 两边都 Exchange，考虑能不能广播掉一侧",
                        "note": "一条链上的每个 join 是独立选策略的——别只看第一个就下结论。"
                    },
                    {
                        "title": "数 Exchange：判断钱花在哪",
                        "code": "fact.join(dim_city, 'city_id').explain()\n# 只有 BroadcastExchange（小表飞一次）→ 好\n\nbig_a.join(big_b, 'id').explain()\n# 两个 Exchange（两边都飞）→ 贵，但大表对大表只能如此",
                        "note": "Exchange 的个数就是你的账单行数：每次重排都要付「装箱+装车+卸货分拣」。"
                    },
                    {
                        "title": "该广播没广播：给 hint 并复核",
                        "code": "from pyspark.sql import functions as F\nq2 = fact.join(F.broadcast(dim_prod), 'prod_id')\nq2.explain()   # 复核：BroadcastExchange 出现了吗？",
                        "note": "hint 是建议不是命令——不复核等于没做。出现 BroadcastHashJoin 才算生效。"
                    },
                    {
                        "title": "倾斜风险检查：找「一桌挤满人」的 key",
                        "code": "# 先看 key 分布，找有没有一个 key 占绝对多数\nfact.groupBy('city_id').count().orderBy(F.desc('count')).show(10)\n# 若某个 city_id（如未知/空值）占 80%，join 时它必然撑爆一个分区",
                        "note": "这一步 explain 帮不了你：计划里没有 key 分布。识别靠 groupBy 抽样 + 运行时观察。"
                    }
                ],
                "key_points": [
                    "诊断五步：判大小 → 看计划认策略 → 数 Exchange → 给/不给 hint → 查倾斜",
                    "一条链上的每个 join 独立选策略，逐个看",
                    "BHJ（大表免 Shuffle）是首选目标，但前提是小表真的小",
                    "hint 必须 explain 复核才能算生效；广播过多会内存反噬",
                    "计划相同 ≠ 运行时相同：倾斜要让位给运行时观察（深调优留 L7）"
                ],
                "common_mistakes": [
                    {
                        "mistake": "只看第一个 join 的计划就对整个查询下结论。",
                        "why": "每个 join 独立选择策略，后面的 join 可能完全是另一条路径。",
                        "fix": "逐个 join 看节点名与 Exchange，别以偏概全。"
                    },
                    {
                        "mistake": "把「综合练习」当调优考试，纠结参数该设多少。",
                        "why": "本课只验证「看得懂、能选策略、能给 hint」，定量调优是 L7 的内容。",
                        "fix": "把力气花在「判大小、认节点、数 Exchange、查倾斜」这四件基本功上。"
                    },
                    {
                        "mistake": "诊断完就认为性能一定变好。",
                        "why": "策略只是影响因素之一；数据分布、倾斜、spill 都会让「看起来省」落空。",
                        "fix": "改完仍要以运行时表现为准，别只看计划变漂亮了。"
                    }
                ],
                "review": "九课走完，你已经认全了 Spark 拼一张桌子的全部套路：复印小册子（BHJ，大表免飞）、电话簿排序归并（SMJ，两边都飞）、抽屉柜流式查（SHJ，免排序仍要飞）、以及两个谁都不想要的兜底（NestedLoop / Cartesian）；还知道策略是谁选的、人怎么插手、以及最阴险的倾斜长尾。",
                "problem": "把这套本事落到一段真实代码上：它现在走的是哪条路、钱花在哪、能不能更省、风险在哪？",
                "preview": "恭喜走完 Level 6——你现在能在计划里一眼认出 JOIN 策略，懂得用小册子省下大表那次昂贵的空中飞货，也认得出数据倾斜的阴招。至于「内存里到底怎么存、分区数到底设多少、倾斜怎么系统调优」，那是 Level 7 性能调优的主场。去测验检验自己吧。🏁"
            }
        }
    ]
}

LEVEL6_QUIZZES = [
    {"lesson_slug": "l6-what-is-join", "questions": [
        {"type": "single_choice", "prompt": "JOIN 最准确的本质是？", "options": ["把两张表查出来、拼上一列", "一种特殊的 groupBy", "先按 key 对齐、再拼合的二元算子", "只在 Driver 端完成的合并操作"], "correct_index": 2, "explanation": "JOIN 要先把相同 key 的记录凑到一起再拼合——它的「重」就重在这个前置的对齐动作上，不是简单地拼列。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "为什么 JOIN 通常比单表 groupBy 更贵？", "options": ["groupBy 通常只汇聚一侧，JOIN 往往两侧都要按 key 重分布", "JOIN 涉及的列更多", "JOIN 一定在 Driver 端执行", "JOIN 的结果行数一定更多"], "correct_index": 0, "explanation": "单表 groupBy 只对一侧按 key 汇聚（通常 1 次 Exchange）；JOIN 常要两侧都按 key 重排（2 次 Exchange），代价自然更高。", "dimension": "why"},
        {"type": "single_choice", "prompt": "写下 orders.join(customers, 'customer_id') 后，Spark 内部的关键约束是？", "options": ["必须把两张表都读进 Driver 内存", "必须先对两表全量排序才能 join", "两表分区数必须完全相同才能 join", "相同 key 的记录必须落到同一位置才能配对"], "correct_index": 3, "explanation": "同 key 必须同位置才能配对，这就是 JOIN 通常触发 Shuffle（Exchange）的物理根源。", "dimension": "mechanism"},
        {"type": "single_choice", "prompt": "写完一句 join 之后，第一步最该做的是？", "options": ["直接 write 落盘", "先 count() 核对行数量级，再用 explain 看走了什么策略", "立刻给两侧都加 F.broadcast()", "把分区数调到 2000"], "correct_index": 1, "explanation": "JOIN 结果行数不等于任一侧行数：条件写错会导致空结果或行数爆炸。先 count() 验量级、explain 看计划，是最便宜的自检。", "dimension": "apply"},
        {"type": "single_choice", "prompt": "关于「JOIN 一定两边都 Shuffle」，正确的是？", "options": ["不一定：一侧足够小时可广播，大表完全不 Shuffle", "永远成立", "只有 SQL 写法会这样", "分区数足够大就能免 Shuffle"], "correct_index": 0, "explanation": "Broadcast Hash Join 会把小表广播出去，让大表侧完全不按 key 重排——这是唯一常见的免 Shuffle 路径。", "dimension": "comparison"},
        {"type": "single_choice", "prompt": "关于 JOIN 的结果行数，正确的是？", "options": ["等于左表行数", "等于右表行数", "恒等于两表行数之和", "取决于 key 的匹配关系，可能变多、变少甚至为 0"], "correct_index": 3, "explanation": "多对多会放大行数，key 完全不匹配会得到 0 行——所以写完 join 先 count() 对量级。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "为什么「无 join key」或条件恒真是严重事故？", "options": ["会让 Spark 直接报错退出", "会退化成笛卡尔积，结果行数是 n × m", "只是结果不准，代价不大", "会强制走广播"], "correct_index": 1, "explanation": "无等值 key 时 Spark 只能两两配对，1 亿 × 1 亿的结果量级足以压垮任何集群，且往往要跑很久才暴露。", "dimension": "why"},
        {"type": "single_choice", "prompt": "用 explain() 诊断 JOIN 时，它实际做了什么？", "options": ["先跑一遍再给计划", "把结果拉回 Driver 统计", "只打印计划，不触发执行", "自动帮你改写并优化代码"], "correct_index": 2, "explanation": "explain 是零成本的静态窥视（复用 L4），不会执行任何计算，所以可以放心反复看。", "dimension": "mechanism"},
        {"type": "single_choice", "prompt": "想知道大表有没有被免掉 Shuffle，最直接的看点是？", "options": ["看结果行数", "看代码里有没有 filter", "看 Executor 数量和核心数", "数 Exchange：大表侧没有 Exchange 就说明没重排"], "correct_index": 3, "explanation": "Exchange 就是 Shuffle 信号。大表侧没有 Exchange（只出现 BroadcastExchange）＝ 大表一次货都没飞。", "dimension": "apply"},
        {"type": "single_choice", "prompt": "同样是「按 key 处理」，单表 groupBy 与 JOIN 在计划上最典型的区别是？", "options": ["两者 Exchange 数一定相同", "groupBy 常见 1 次 Exchange，JOIN 常见 2 次", "groupBy 从不产生 Exchange", "JOIN 一定不会产生 Exchange"], "correct_index": 1, "explanation": "groupBy 只汇聚一侧（1 次），JOIN 常要两侧都重排（2 次）——这是「JOIN 通常更贵」最直观的证据。", "dimension": "comparison"}
    ]},
    {"lesson_slug": "l6-join-strategies-overview", "questions": [
        {"type": "single_choice", "prompt": "Spark 三种主要的 JOIN 执行策略是？", "options": ["Inner / Left / Full Join", "Nested Loop / Index Scan / Hash Scan", "Map Join / Reduce Join / Combine Join", "Broadcast Hash Join / Sort-Merge Join / Shuffle Hash Join"], "correct_index": 3, "explanation": "BHJ（广播小表）/ SMJ（排序归并）/ SHJ（建哈希表）是 Spark 物理计划的三种主要 JOIN 实现；Inner/Left 那是 join 类型，不是执行策略。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "为什么同一句 join 要有好几种执行策略？", "options": ["为了让计划看起来更丰富", "不同数据规模下最省的拼法不同；策略结果等价、代价不同", "Spark 会随机挑一种", "因为 SQL 和 API 需要不同的策略"], "correct_index": 1, "explanation": "策略选择是等价改写——结果一致，只影响快慢与资源占用，所以优化器才能自由地在其中择优。", "dimension": "why"},
        {"type": "single_choice", "prompt": "JOIN 策略是在哪个阶段被确定的？", "options": ["物理计划阶段（所以只有 explain 才看得到）", "读数据时", "Action 触发执行之后", "由 Driver 在运行时动态切换"], "correct_index": 0, "explanation": "逻辑计划里只有一个 Join 节点，进入物理计划阶段才被替换成具体策略实现。", "dimension": "mechanism"},
        {"type": "single_choice", "prompt": "在计划里认出 Broadcast Hash Join，应找哪组节点？", "options": ["两个 Exchange + Sort", "FileScan + Filter", "BroadcastExchange + BroadcastHashJoin", "CartesianProduct"], "correct_index": 2, "explanation": "BroadcastExchange 表示有小表被广播分发，紧随其后的 BroadcastHashJoin 就是它的连接节点。", "dimension": "apply"},
        {"type": "single_choice", "prompt": "Sort-Merge Join 与 Shuffle Hash Join 的关键差异是？", "options": ["SMJ 不需要 Shuffle，SHJ 需要", "SMJ 两侧排序后归并（有 Sort），SHJ 一侧在内存建哈希表（无 Sort 但要进内存）", "两者完全一样，只是名字不同", "SHJ 只用于非等值条件"], "correct_index": 1, "explanation": "两者都要按 key Shuffle 分区；差别在分区内是排序归并还是建哈希表——前者可溢写磁盘，后者要占内存。", "dimension": "comparison"},
        {"type": "single_choice", "prompt": "下列属于「兜底策略」的是？", "options": ["BroadcastNestedLoopJoin 与 CartesianProduct", "Broadcast Hash Join 与 Sort-Merge Join", "谓词下推与列裁剪", "WholeStageCodegen"], "correct_index": 0, "explanation": "非等值条件会退化为 BroadcastNestedLoopJoin，无 key 时直接是 CartesianProduct——两个都是红灯。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "三种策略算出来的结果会不一样吗？", "options": ["会，BHJ 结果最少", "会，SMJ 结果最全", "不会：策略是等价改写，结果一致，只影响代价", "取决于 Spark 版本"], "correct_index": 2, "explanation": "策略选择属于 Catalyst 的等价改写（复用 L4），结果不变，只改变执行成本。", "dimension": "why"},
        {"type": "single_choice", "prompt": "关于逻辑计划与 JOIN 策略，正确的是？", "options": ["逻辑计划里已经写明了用哪种策略", "两者同时确定", "逻辑计划里写的是 Sort-Merge，物理计划才改写", "逻辑计划里只有一个 Join 节点，策略到物理计划阶段才确定"], "correct_index": 3, "explanation": "复用 L4 的「概念图 vs 施工图」：概念图只说「要拼」，施工图才说「怎么拼」。", "dimension": "mechanism"},
        {"type": "single_choice", "prompt": "explain 里看到 CartesianProduct，你应该？", "options": ["立刻停下检查 join 条件是否缺失或写错", "放心跑，Cartesian 是最快的策略", "把分区数调大", "给两侧都加 broadcast hint"], "correct_index": 0, "explanation": "CartesianProduct 意味着两两配对、n × m 的结果量级，几乎一定是条件写错的信号。", "dimension": "apply"},
        {"type": "single_choice", "prompt": "非等值 join 条件（如 a.amount > b.threshold）通常会怎样？", "options": ["照常走 Sort-Merge Join", "照常走 Broadcast Hash Join", "哈希与归并用不上，常退化为嵌套循环（NestedLoop）", "Spark 直接报错不支持"], "correct_index": 2, "explanation": "哈希表和排序归并都依赖等值 key；非等值条件只能一条条比，代价随数据量平方级上升。", "dimension": "comparison"}
    ]},
    {"lesson_slug": "l6-broadcast-hash-join", "questions": [
        {"type": "single_choice", "prompt": "Broadcast Hash Join 的两步是？", "options": ["广播小表建哈希表（build）+ 大表流式探测（probe）", "两侧都排序后归并", "把大表复制到每个 Executor", "把两表都读进 Driver 后拼接"], "correct_index": 0, "explanation": "小表被广播到每个 Executor 并建成哈希表，大表各分区在本地逐条探测匹配——大表始终不移动。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "BHJ 为什么能省下大量开销？", "options": ["它把 join 变成了 filter", "它把结果写进了缓存", "它免掉了大表那次 Shuffle，即 L5 讲的序列化+网络+排序那一串", "它减少了读取的列数"], "correct_index": 2, "explanation": "大表不按 key 重排，就省掉了整条「装箱→装车→卸货分拣」链路，这是 BHJ 最大的价值。", "dimension": "why"},
        {"type": "single_choice", "prompt": "BHJ 执行时，数据在 Executor 上的流向是？", "options": ["大表复制到每个 Executor", "小表整份复制到每个 Executor，大表分区留在本地被逐条探测", "两表都先回 Driver 合并再分发", "两表都按 key 重排到同一分区"], "correct_index": 1, "explanation": "BroadcastExchange 把小表发到所有 Executor，大表各分区原地不动、流式探测——所以大表侧没有 Exchange。", "dimension": "mechanism"},
        {"type": "single_choice", "prompt": "想让小维表走广播，正确的写法是？", "options": ["fact.join(dim, 'city_id').repartition(200)", "fact.join(dim, 'city_id').cache()", "dim.join(fact, 'city_id')", "fact.join(F.broadcast(dim), 'city_id')"], "correct_index": 3, "explanation": "F.broadcast() 明确要求广播该侧；注意给完 hint 还要 explain 复核是否真的生效。", "dimension": "apply"},
        {"type": "single_choice", "prompt": "关于 BHJ 与 SMJ 的代价，正确的是？", "options": ["两者 Shuffle 次数相同", "SMJ 一定更快", "BHJ 大表不 Shuffle，SMJ 两侧都 Shuffle", "BHJ 连小表都不用传输"], "correct_index": 2, "explanation": "BHJ 只飞小表（BroadcastExchange），SMJ 两侧各飞一次——这是两者最本质的代价差异。", "dimension": "comparison"},
        {"type": "single_choice", "prompt": "BHJ 成立的硬前提是？", "options": ["小表行数少于 1000 行", "小表必须能塞进 Executor 内存", "任意一侧都可以，只要加了 hint", "两表分区数相同"], "correct_index": 1, "explanation": "被广播的表要在每个 Executor 内存里完整建哈希表，塞不进去就会 OOM 或被优化器放弃广播。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "为什么说广播不是零成本？", "options": ["广播会触发全表排序", "广播会把数据写回磁盘", "广播要占用 Driver 的内存", "小册子也要复印并运到每个工人手上，BroadcastExchange 本身也是一次网络传输"], "correct_index": 3, "explanation": "BHJ 省的是大表那次重排；小表的分发依然存在，只是数据量小好几个数量级。", "dimension": "why"},
        {"type": "single_choice", "prompt": "计划中出现 BroadcastExchange 说明什么？", "options": ["有数据被广播分发到各 Executor（通常是小表）", "发生了大表 Shuffle", "发生了数据倾斜", "作业失败了"], "correct_index": 0, "explanation": "BroadcastExchange 就是「复印小册子并发货」的信号，配合 BroadcastHashJoin 一起出现。", "dimension": "mechanism"},
        {"type": "single_choice", "prompt": "判断一张表「能不能广播」，更靠谱的口径是？", "options": ["看行数是否少于 1 万", "看它的数据体积（字节级大小）能否塞进 Executor 内存", "看它的分区数", "看它有没有索引"], "correct_index": 1, "explanation": "宽表、长字符串字段会让「行数很少」的表实际体积很大；Spark 判断的也是统计大小（体积），不是行数。", "dimension": "apply"},
        {"type": "single_choice", "prompt": "关于「给所有维表都加 broadcast」，正确的是？", "options": ["推荐，能普遍提速", "无所谓，广播不占资源", "只要表小就没问题，跟数量无关", "危险：每张被广播的表都会在每个 Executor 内存里常驻一份，多了会 OOM"], "correct_index": 3, "explanation": "广播是「每个 Executor 各存一份」的内存账，同时广播多张表会迅速挤爆 Executor 内存。", "dimension": "comparison"}
    ]},
    {"lesson_slug": "l6-sort-merge-join", "questions": [
        {"type": "single_choice", "prompt": "Sort-Merge Join 的两步是？", "options": ["广播小表 + 大表流式探测", "两侧按 key 分区并排序（两个 Exchange）+ 归并扫描配对", "一侧建哈希表 + 另一侧流式探测", "把两表都读进 Driver 排序"], "correct_index": 1, "explanation": "SMJ 先让两侧同 key 落到同一分区并有序，再用两个游标归并配对——两次 Exchange 就是它的身份证。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "为什么大表 × 大表不能走广播？", "options": ["大表没有 join key", "Spark 禁止对大表使用 join", "广播只能用于左表", "广播要求整表塞进 Executor 内存，几十亿行做不到"], "correct_index": 3, "explanation": "广播要在每个 Executor 内存里完整建哈希表；表一大就只能改走可溢写磁盘的 SMJ。", "dimension": "why"},
        {"type": "single_choice", "prompt": "SMJ 的归并阶段实际在做什么？", "options": ["每条记录去另一侧全表扫一遍", "把两表都拉回 Driver 逐条比对", "两侧已按 key 有序，两个游标各扫一遍，key 相等就配对输出", "随机抽样后估算结果"], "correct_index": 2, "explanation": "归并是线性扫描（排序后各扫一遍），不是嵌套循环——贵的是排序，不是归并本身。", "dimension": "mechanism"},
        {"type": "single_choice", "prompt": "explain 里怎么一眼认出 SMJ？", "options": ["两侧各一个 Exchange + Sort + SortMergeJoin", "出现 BroadcastExchange", "出现 CartesianProduct", "只有一个 FileScan"], "correct_index": 0, "explanation": "两个 Exchange 表示两侧都按 key 重排，Sort + SortMergeJoin 表示排序归并——三者一起出现基本就是 SMJ。", "dimension": "apply"},
        {"type": "single_choice", "prompt": "SMJ 相比 BHJ 的优势与劣势分别是？", "options": ["更快且更省内存", "完全不需要 Shuffle", "只支持非等值条件", "不要求任一侧进内存（能扛超大表），但两侧都要 Shuffle + 排序"], "correct_index": 3, "explanation": "SMJ 的代价是双份 Shuffle + 全量排序，但它能溢写磁盘，是唯一扛得住大表 × 大表的常规策略。", "dimension": "comparison"},
        {"type": "single_choice", "prompt": "SMJ 里的「排序」在内存不足时会怎样？", "options": ["直接报错退出", "自动切换成广播", "spill 到磁盘继续排，慢但能跑完", "丢弃部分数据"], "correct_index": 2, "explanation": "排序结果可溢写磁盘（复用 L5 的 spill 概念），代价是 I/O 慢几个数量级，但保证了「能跑完」。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "为什么 SMJ 是 Spark 无法广播时的默认选择？", "options": ["因为它是唯一通用：不依赖内存常驻、支持超大表", "因为它结果最准确", "因为它代码最短", "因为 Spark 只实现了这一种"], "correct_index": 0, "explanation": "不要求任一侧重排进内存、可溢写磁盘，使 SMJ 成为最通用也最稳妥的大表 JOIN 策略。", "dimension": "why"},
        {"type": "single_choice", "prompt": "大表 × 大表 join 时，计划里通常会出现几次 Exchange？", "options": ["0 次", "2 次（两侧各一次）", "1 次", "取决于结果行数"], "correct_index": 1, "explanation": "两侧同 key 必须到同一分区，因此各重排一次——两个 Exchange 就是这类 JOIN 的常规账单。", "dimension": "mechanism"},
        {"type": "single_choice", "prompt": "看到计划里有两个 Exchange，正确的反应是？", "options": ["代码写错了，必须消掉一个", "立刻把分区数调到最大", "先判断能不能广播掉一侧；不能，就接受这是大表 JOIN 的必然代价", "改用 crossJoin 简化计划"], "correct_index": 2, "explanation": "两个 Exchange 未必是错误：大表对大表本身就是双份重排。优化方向是「能不能广播一侧」或「先裁剪数据」。", "dimension": "apply"},
        {"type": "single_choice", "prompt": "关于 SMJ 与 NestedLoopJoin，正确的是？", "options": ["SMJ 排序后线性归并，NestedLoop 是两两比对，复杂度天差地别", "两者复杂度差不多", "NestedLoop 更快因为不用排序", "SMJ 只用于非等值条件"], "correct_index": 0, "explanation": "SMJ 是「排序 O(n log n) + 线性归并」，NestedLoop 是 O(n·m)——看到 NestedLoop/Cartesian 才是真正该警惕的红灯。", "dimension": "comparison"}
    ]},
    {"lesson_slug": "l6-shuffle-hash-join", "questions": [
        {"type": "single_choice", "prompt": "Shuffle Hash Join 的原理是？", "options": ["广播小表，大表不 Shuffle", "两侧排序后归并", "两侧按 key Shuffle 分区后，较小一侧在内存建哈希表，较大一侧流式探测", "把两表都广播出去"], "correct_index": 2, "explanation": "SHJ 仍然两侧重排（按 key 分区），只是把「排序归并」换成了「建哈希表 + 流式查」。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "SHJ 存在的意义是？", "options": ["省掉排序这一步（代价是 build 侧必须进内存）", "彻底免掉 Shuffle", "让结果更准确", "专门用于非等值条件"], "correct_index": 0, "explanation": "SHJ 与 SMJ 都要 Shuffle，差别在于分区内是建哈希抽屉柜还是排序——前者省排序、费内存。", "dimension": "why"},
        {"type": "single_choice", "prompt": "SHJ 执行时，内存里放的是什么？", "options": ["两表的全部数据", "Driver 端的执行计划", "排序后的临时文件", "较小一侧（build side）按 key 建成的哈希表"], "correct_index": 3, "explanation": "build 侧要完整驻留内存才能被随机查找；stream 侧则是流式逐条过来探测。", "dimension": "mechanism"},
        {"type": "single_choice", "prompt": "想在计划里认出 SHJ，应找？", "options": ["BroadcastExchange", "ShuffledHashJoin 节点（有 Exchange 但通常无 Sort）", "CartesianProduct", "FileScan 节点"], "correct_index": 1, "explanation": "和 SMJ 的关键区别就是有没有 Sort：ShuffledHashJoin 建哈希表，SortMergeJoin 先排序再归并。", "dimension": "apply"},
        {"type": "single_choice", "prompt": "BHJ 与 SHJ 的本质差别是？", "options": ["BHJ 免掉大表的 Shuffle，SHJ 仍需两侧按 key 重排", "两者都不需要 Shuffle", "SHJ 更快且从不占内存", "BHJ 只用于非等值条件"], "correct_index": 0, "explanation": "只有 BHJ 能让大表完全不 Shuffle；SHJ 免的是排序，不是传输——别把两者混为一谈。", "dimension": "comparison"},
        {"type": "single_choice", "prompt": "数据量大时，Spark 为什么更偏爱 SMJ 而不是 SHJ？", "options": ["SMJ 结果更准", "SHJ 语法不支持", "SMJ 不需要 Shuffle", "SHJ 要求 build 侧进内存，数据一大就撑不住；SMJ 可溢写磁盘"], "correct_index": 3, "explanation": "能否溢写磁盘是分水岭：SHJ 的哈希表必须常驻内存，SMJ 的排序可以落盘。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "为什么不建议死记「什么条件下一定走 SHJ」？", "options": ["因为 SHJ 已被废弃", "触发条件与 Spark 版本、配置、统计估计都有关，会变", "因为 SHJ 从不出现", "因为书上没写"], "correct_index": 1, "explanation": "记原理（免排序、占内存、仍 Shuffle）+ 看 explain，比背一张会过期的条件表可靠得多。", "dimension": "why"},
        {"type": "single_choice", "prompt": "join 条件写成恒真表达式（如两列恒等）会发生什么？", "options": ["正常走 Sort-Merge Join", "自动切换成广播", "等价于无 key，退化为笛卡尔积，结果行数 n × m", "Spark 报错拒绝执行"], "correct_index": 2, "explanation": "恒真条件让 Spark 找不到有效的等值 key，只能两两配对——这是生产中最隐蔽的性能事故之一。", "dimension": "mechanism"},
        {"type": "single_choice", "prompt": "发现计划里出现 CartesianProduct，第一步该做？", "options": ["加大分区数", "给两侧加 broadcast", "直接重跑一次看看", "检查 join 条件是否缺失或写错，并先 count() 验量级"], "correct_index": 3, "explanation": "先停下来核条件：笛卡尔积的代价是平方级的，跑下去只会浪费整个集群的时间。", "dimension": "apply"},
        {"type": "single_choice", "prompt": "关于两个兜底策略，正确的是？", "options": ["它们是最快的策略，应优先使用", "BroadcastNestedLoopJoin 用于非等值条件、CartesianProduct 用于无 key，二者在大表上都是灾难", "它们都能免 Shuffle", "它们只在广播时才会出现"], "correct_index": 1, "explanation": "两个兜底都是两两比对的量级，只适合极小数据；在大表上出现就要重新设计 join 条件。", "dimension": "comparison"}
    ]},
    {"lesson_slug": "l6-how-spark-chooses", "questions": [
        {"type": "single_choice", "prompt": "JOIN 策略是由谁、在什么时候决定的？", "options": ["用户写代码时指定", "Executor 在运行时动态切换", "Driver 在收集结果后回选", "Catalyst 在物理计划阶段依据估计信息自动选定"], "correct_index": 3, "explanation": "复用 L3/L4 的「Catalyst = 优化大脑」：策略决策发生在物理计划阶段，属于规划期行为。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "Spark 决定能不能广播，主要看什么？", "options": ["表的行数", "两侧数据的统计大小估计与广播阈值（概念上的尺子）", "SQL 里有没有写 hint", "集群的磁盘容量"], "correct_index": 1, "explanation": "优化器拿「大小估计」去和广播阈值比；具体阈值数值与调优是 L7 的内容，本课只讲它是决策依据。", "dimension": "why"},
        {"type": "single_choice", "prompt": "关于策略选择的一般优先级，正确的是？", "options": ["能广播则优先 BHJ；否则在 SHJ / SMJ 间取舍，SMJ 是最通用的兜底", "永远优先 CartesianProduct", "永远优先 SMJ", "随机选择"], "correct_index": 0, "explanation": "BHJ 最省（大表免 Shuffle）所以优先；不能广播时才在 SHJ/SMJ 之间按内存与排序条件取舍。", "dimension": "mechanism"},
        {"type": "single_choice", "prompt": "验证「实际走了哪种策略」最便宜的手段是？", "options": ["把作业跑完看耗时", "直接查看 Spark 源码", "用 explain() 看物理计划里的 Join 节点名与 Exchange 个数", "把数据 collect 回来看"], "correct_index": 2, "explanation": "explain 不执行、零成本，还能直接看到 BroadcastHashJoin / SortMergeJoin / ShuffledHashJoin 节点。", "dimension": "apply"},
        {"type": "single_choice", "prompt": "「统计估计」与「实际运行」的关系，正确的是？", "options": ["两者永远一致", "Spark 决策用的是规划期的估计值，不是实测，所以会误判", "Spark 会先跑一遍再决定", "估计值只在 SQL 里使用"], "correct_index": 1, "explanation": "估计来自统计信息，缺失或不准就会误判——这也是「该广播没广播」最常见的原因。", "dimension": "comparison"},
        {"type": "single_choice", "prompt": "本课提到的「广播阈值」指的是？", "options": ["一个决定「多大算小、能不能广播」的尺子（概念），具体值与调优留 L7", "磁盘容量上限", "Executor 个数", "结果行数的上限"], "correct_index": 0, "explanation": "它是 Spark 判断「这表小不小」的判据；本课只讲它在决策中的作用，不展开数值与调优。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "为什么「明明是小表，Spark 却没广播」？", "options": ["Spark 有 bug", "因为没写 SQL", "小表经过复杂变换后统计信息缺失，优化器估不出真实大小，只能保守按大表处理", "因为列名不同"], "correct_index": 2, "explanation": "尺码单缺失时优化器按最坏情况处理，于是走保守的 SMJ——这正是需要人工 hint 的典型场景。", "dimension": "why"},
        {"type": "single_choice", "prompt": "先 filter 再 join，对策略选择有什么影响？", "options": ["没有影响", "会强制走笛卡尔积", "会禁用广播", "过滤后数据量骤减，大小估计变小，更可能落在广播阈值内"], "correct_index": 3, "explanation": "缩小参与 join 的数据体积，是让 Spark 更愿意广播的最直接手段（配合谓词下推更省）。", "dimension": "mechanism"},
        {"type": "single_choice", "prompt": "怀疑优化器误判时，合理的做法是？", "options": ["先用 explain 确认实际策略，必要时加 broadcast hint 再复核；定量调优留 L7", "直接改源码", "把所有表都缓存一遍", "放弃优化，按原样跑"], "correct_index": 0, "explanation": "先诊断（explain）→ 再干预（hint）→ 再复核（explain），这是 L6 要求的完整动作。", "dimension": "apply"},
        {"type": "single_choice", "prompt": "关于 hint 与自动选择的关系，正确的是？", "options": ["hint 是命令，Spark 必须执行", "hint 会禁用 Catalyst", "hint 是建议，可能被忽略，所以必须 explain 复核", "hint 只影响逻辑计划"], "correct_index": 2, "explanation": "优化器可以基于自身判断不采纳 hint——所以「写了」不等于「生效了」。", "dimension": "comparison"}
    ]},
    {"lesson_slug": "l6-broadcast-hint-and-control", "questions": [
        {"type": "single_choice", "prompt": "主动要求广播的三种写法是？", "options": ["F.broadcast(df) / df.hint('broadcast') / SQL 里的 broadcast 提示", "repartition / coalesce / cache", "join / union / crossJoin", "explain / show / count"], "correct_index": 0, "explanation": "三种写法殊途同归，都是向优化器表达「建议广播这一侧」；团队内统一用一种即可。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "什么时候最需要人工给 broadcast hint？", "options": ["两表都很大时", "结果行数不确定时", "统计信息缺失/不准，导致小表没被自动广播时", "使用 SQL 的时候必须给"], "correct_index": 2, "explanation": "优化器靠估计值决策，估计失灵就需要人递上那本「小册子」——这是 hint 最典型的使用场景。", "dimension": "why"},
        {"type": "single_choice", "prompt": "给 hint 之后，计划里会先出现什么、再变成什么？", "options": ["先 Sort 再 Exchange", "先 ResolvedHint（记住倾向），生效后插入 BroadcastExchange 走 BHJ", "直接跳到 CartesianProduct", "计划不会有任何变化"], "correct_index": 1, "explanation": "hint 先在逻辑层留下 ResolvedHint 标记；被采纳后物理计划插入 BroadcastExchange，节点变成 BroadcastHashJoin。", "dimension": "mechanism"},
        {"type": "single_choice", "prompt": "给了 F.broadcast() 之后，正确的收尾动作是？", "options": ["直接 write 落盘", "立刻把分区数翻倍", "把结果 collect 回来", "再 explain 一次，确认计划里真的出现了 BroadcastExchange"], "correct_index": 3, "explanation": "hint 是建议不是命令，可能被静默忽略——不复核就等于没做。", "dimension": "apply"},
        {"type": "single_choice", "prompt": "关于 hint 与调优参数的关系，正确的是？", "options": ["hint 就是调优参数，二者等价", "调优参数能替代 hint", "hint 是策略倾向的表达；具体阈值与调优参数是 L7 的内容", "hint 会覆盖所有调优参数"], "correct_index": 2, "explanation": "L6 只教「怎么表达倾向、会不会翻车」；定量调优（阈值、分区数）留给 L7。", "dimension": "comparison"},
        {"type": "single_choice", "prompt": "「广播反噬」指的是？", "options": ["广播让结果行数变多", "被广播的表在每个 Executor 内存各留一份完整副本，多了会挤爆内存甚至 OOM", "广播会让计划变复杂", "广播会禁用 Catalyst"], "correct_index": 1, "explanation": "广播不是免费的：每多广播一张表，每个 Executor 就多一份常驻内存账。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "为什么「看起来小」的表广播后仍可能出问题？", "options": ["因为广播会触发全表排序", "因为 Executor 数量太多", "因为 Spark 会重复广播三次", "大小判断基于统计估计（体积），宽表/长字符串会让它远比行数看起来大"], "correct_index": 3, "explanation": "判断口径是数据体积而非行数；估计还可能停留在 filter 之前的体积上。", "dimension": "why"},
        {"type": "single_choice", "prompt": "同时 join 三张维表并都加 broadcast，会发生什么？", "options": ["三份表各自在每个 Executor 内存常驻，内存压力陡增，可能 OOM", "一定最快", "只有第一个 hint 生效", "Spark 会自动合并成一次广播"], "correct_index": 0, "explanation": "广播代价随表数量线性叠加——宁可只广播能省掉最大那次 Shuffle 的那张。", "dimension": "mechanism"},
        {"type": "single_choice", "prompt": "发现 hint 没有生效（计划仍是 SortMergeJoin），下一步是？", "options": ["再多加几个 hint 强制", "接受结果：检查被广播侧是否其实过大或连接类型不支持，必要时先过滤缩小数据", "改用 crossJoin", "重启 SparkSession"], "correct_index": 1, "explanation": "hint 被忽略通常有理由（太大/不支持）；硬加 hint 无效，应从缩小数据体积入手。", "dimension": "apply"},
        {"type": "single_choice", "prompt": "关于「无脑给所有 join 加 broadcast」，正确的是？", "options": ["推荐做法，能普遍提速", "无所谓，hint 不会有任何副作用", "只在 SQL 里才危险", "危险：会显著抬高 Executor 内存占用，甚至拖垮作业"], "correct_index": 3, "explanation": "广播的价值在于「能省掉最大那次 Shuffle」；不加区分地广播只是把账单从网络转到了内存。", "dimension": "comparison"}
    ]},
    {"lesson_slug": "l6-join-data-skew", "questions": [
        {"type": "single_choice", "prompt": "JOIN 中的数据倾斜指的是？", "options": ["某个 Executor 宕机", "少数 key 的记录数远超其他，导致对应 Task 数据量巨大、成为长尾任务", "join 条件写错", "结果行数比预期多"], "correct_index": 1, "explanation": "同 key 必须同分区，巨型 key 就会撑爆一个 Task，而整体完工时间由最慢的 Task 决定。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "为什么增加分区数救不了倾斜？", "options": ["分区数有上限", "加分区会触发更多 Shuffle", "加分区会让结果变错", "同 key 必须哈希到同一分区，巨大的 key 只会被换个托盘，不会被拆开"], "correct_index": 3, "explanation": "这是哈希分区的铁律：只要 key 相同，它就一定整块落在同一个分区里——所以必须靠「加盐」改 key 才能打散。", "dimension": "why"},
        {"type": "single_choice", "prompt": "倾斜为什么在执行计划里看不出来？", "options": ["计划被优化器隐藏了", "因为 explain 有 bug", "计划只有算子与估算行数，不含「每个 key 多少条」的真实分布", "只有 SQL 才看得出"], "correct_index": 2, "explanation": "这正是 L4 埋下的伏笔——「计划相同 ≠ 运行时性能相同」，倾斜属于运行时现象，要看 Task 耗时/数据量分布。", "dimension": "mechanism"},
        {"type": "single_choice", "prompt": "怀疑倾斜时，最该去看的是？", "options": ["运行时各 Task 的耗时与处理数据量分布（如 Spark UI）", "explain 的节点名", "代码的缩进", "表的 Schema"], "correct_index": 0, "explanation": "典型信号是「进度条卡在 99%、少数 Task 耗时是其他的几十倍」——只有运行时指标能暴露它。", "dimension": "apply"},
        {"type": "single_choice", "prompt": "关于 salting（加盐）的正确理解是？", "options": ["把所有 key 都加上随机数，永远安全", "一种压缩算法", "让结果去重的方法", "给大 key 加随机前缀拆成 N 个子 key 分散到不同分区，另一侧需对应膨胀；适合少数大 key"], "correct_index": 3, "explanation": "加盐的代价是另一侧数据膨胀 N 倍，只适合少数巨型 key；对所有 key 加盐会得不偿失。", "dimension": "comparison"},
        {"type": "single_choice", "prompt": "本课讲的倾斜应对思路不包括哪一项？", "options": ["salting 加盐打散", "把大 key 隔离出来单独处理", "调整 skew 相关开关的具体参数值", "用广播（BHJ）绕开按 key 的 Shuffle"], "correct_index": 2, "explanation": "具体倾斜开关与深调优是 Level 7 的内容，本课只到「能识别 + 懂原理」。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "为什么广播（BHJ）能顺带解决倾斜？", "options": ["大表不再按 key 重排，自然就不存在「某 key 撑爆某分区」", "广播会重排 key 使其均匀", "广播会过滤掉大 key", "广播只保留出现次数多的 key"], "correct_index": 0, "explanation": "倾斜是「按 key 重分布」的副产品；取消大表那次重排，倾斜就无从谈起。", "dimension": "why"},
        {"type": "single_choice", "prompt": "加盐之后，Shuffle 时数据如何分布？", "options": ["仍全部落在一个分区", "大 key 被拆成 N 个子 key，哈希到不同分区，压力被摊开", "被丢弃一部分", "被复制到每个 Executor"], "correct_index": 1, "explanation": "改了 key 就改了哈希结果——这是唯一能绕开「同 key 同分区」铁律的办法。", "dimension": "mechanism"},
        {"type": "single_choice", "prompt": "作业卡在 99%，199 个 Task 早完成、1 个还在跑，正确处置是？", "options": ["加机器、加分区数继续等", "把 join 改成 crossJoin", "先确认是否倾斜，再从打散/隔离/广播三条思路里选应对", "直接重跑，可能是偶发"], "correct_index": 2, "explanation": "倾斜时加机器只是让其他 Task 更快空转；只有改 key 分布或绕开 Shuffle 才真正有效。", "dimension": "apply"},
        {"type": "single_choice", "prompt": "关于「对所有 key 加盐」，正确的是？", "options": ["代价是另一侧膨胀 N 倍，key 一多反而更慢，只适合少数大 key", "是标准做法，应优先采用", "加盐不需要改另一侧", "加盐会改变 join 结果"], "correct_index": 0, "explanation": "加盐是把压力换成数据量，只在「少数大 key」时划算；滥用会让膨胀代价超过收益。", "dimension": "comparison"}
    ]},
    {"lesson_slug": "l6-comprehensive", "questions": [
        {"type": "single_choice", "prompt": "拿到一句 join 做诊断，第一步是？", "options": ["直接加 broadcast hint", "把分区数调到 2000", "判断两侧数据规模，识别有没有可广播的小表", "改成 SQL 写法"], "correct_index": 2, "explanation": "诊断五步从「判大小」开始：能不能广播，决定了后面所有选择的走向。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "为什么一条查询里的每个 join 都要单独看？", "options": ["每个 join 独立进行策略选择，可能走完全不同的路径", "因为计划太长看不完", "因为 Spark 对每个 join 单独收费", "因为后面的 join 一定更慢"], "correct_index": 0, "explanation": "Catalyst 对每个 Join 节点分别决策：第一个可能 BHJ，第二个可能仍是 SMJ。", "dimension": "why"},
        {"type": "single_choice", "prompt": "数 Exchange 的意义是什么？", "options": ["数出一共有多少个 join", "判断结果行数", "判断倾斜程度", "判断重排了几次：大表侧无 Exchange = 广播免 Shuffle；两侧各一个 = 都重排"], "correct_index": 3, "explanation": "Exchange 就是账单行：每一次按 key 重排都要付「装箱+装车+卸货分拣」的钱。", "dimension": "mechanism"},
        {"type": "single_choice", "prompt": "检查倾斜风险，最实用的手段是？", "options": ["看 explain 的节点名", "先 groupBy key 看分布（找出占比过高的 key），再结合运行时 Task 耗时观察", "只看代码", "看表有多少列"], "correct_index": 1, "explanation": "计划里没有 key 分布，只能自己查分布 + 观察运行时——这是清单里唯一「计划帮不上忙」的一步。", "dimension": "apply"},
        {"type": "single_choice", "prompt": "关于「改完计划就一定更快」，正确的是？", "options": ["不成立：数据分布、倾斜、spill 都会让「看起来省」落空，最终以运行时为准", "一定成立，计划更省就是更快", "只在小数据量下成立", "只有 SQL 才成立"], "correct_index": 0, "explanation": "复用 L4/L5 的核心边界：计划相同 ≠ 运行时相同；反过来，计划变省也不等于一定更快。", "dimension": "comparison"},
        {"type": "single_choice", "prompt": "本课的综合练习要求达到什么水平？", "options": ["能手调所有 Spark 性能参数", "能写出 Spark 源码级优化", "能消除所有 Shuffle", "看得懂计划、能认策略、能判断要不要广播、能指出倾斜风险，不要求调优"], "correct_index": 3, "explanation": "L6 只验证「看得懂 + 能选 + 能给 hint」；定量调优是 Level 7 的主场。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "为什么综合练习不要求你调参数？", "options": ["参数没用", "定量调优（阈值、分区数最优值、倾斜开关）属于 Level 7，L6 只打基本功", "参数会导致结果错误", "Spark 不允许改参数"], "correct_index": 1, "explanation": "分阶段学习是有意为之：先能诊断，再学治疗——L6 负责前者，L7 负责后者。", "dimension": "why"},
        {"type": "single_choice", "prompt": "给某个维表加了 broadcast 后，计划的正常变化是？", "options": ["出现 CartesianProduct", "Exchange 数量翻倍", "出现 BroadcastExchange + BroadcastHashJoin，大表侧不再有 Exchange", "计划完全不变"], "correct_index": 2, "explanation": "这就是「生效」的标志：小表多了一次广播分发，大表省掉了一次重排。", "dimension": "mechanism"},
        {"type": "single_choice", "prompt": "大事实表 join 小维表，最理想的策略与理由是？", "options": ["SMJ，因为它最通用", "SHJ，因为它免排序", "Cartesian，因为维表小", "BHJ：广播小表，让大表完全不 Shuffle，省下最贵的那次空中飞货"], "correct_index": 3, "explanation": "这是数仓里最经典的形态，也是 BHJ 价值最大化的场景——大表一次货都不用飞。", "dimension": "apply"},
        {"type": "single_choice", "prompt": "走完 L6 的诊断清单，你的输出应该是？", "options": ["一份完整的参数调优方案", "「它现在走哪条路、钱花在哪、能不能更省、风险在哪」的判断", "一个全新的 Spark 引擎", "所有 Shuffle 的消除方案"], "correct_index": 1, "explanation": "L6 的产出是「判断力」：认策略、数 Exchange、给 hint、查倾斜——把调优留给 L7。", "dimension": "comparison"}
    ]}
]


def upsert():
    # 1) 合并进 course_seed.json
    with open(SEED, encoding="utf-8") as f:
        data = json.load(f)
    exists = any(lv.get("order_index") == 6 for lv in data["levels"])
    if not exists:
        data["levels"].append(LEVEL6)
        with open(SEED, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print("已写入 course_seed.json（Level 6）")
    else:
        print("course_seed.json 已存在 Level 6，跳过 JSON 写入")

    # 2) 合并进 quiz_seed.json
    with open(QUIZ, encoding="utf-8") as f:
        qdata = json.load(f)
    qentries = qdata.setdefault("quizzes", [])
    existing = {e["lesson_slug"] for e in qentries}
    added_q = 0
    for entry in LEVEL6_QUIZZES:
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
        print("quiz_seed.json 已包含 Level 6 题库，跳过")

    # 3) upsert 进数据库
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT id,title FROM course_levels WHERE order_index=6")
    row = cur.fetchone()
    if row:
        level_id = row[0]
        print(f"Level 6 已存在于 DB (id={level_id})，仅补充缺失 lesson")
    else:
        cur.execute(
            "INSERT INTO course_levels (title, description, order_index, status) VALUES (?,?,?,?)",
            (LEVEL6["title"], LEVEL6["description"], LEVEL6["order_index"], "active"))
        level_id = cur.lastrowid
        print(f"已插入 Level 6 (id={level_id})")

    inserted_lessons = 0
    for ls in LEVEL6["lessons"]:
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
    for entry in LEVEL6_QUIZZES:
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
