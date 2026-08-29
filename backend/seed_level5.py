# -*- coding: utf-8 -*-
"""一次性脚本：把 Level 5（分区与 Shuffle，9 课）合并进 course_seed.json 与 quiz_seed.json，
并幂等地 upsert 进 spark_quest.db 的 course_levels / lessons / quizzes 表。
不修改 Level 0/1/2/3/4 与已有的 lesson_mastery 进度数据。

运行：cd backend && python seed_level5.py
"""
import sqlite3, json, os

BASE = os.path.dirname(os.path.abspath(__file__))
SEED = os.path.join(BASE, "app", "course_seed.json")
QUIZ = os.path.join(BASE, "app", "quiz_seed.json")
DB = os.path.join(BASE, "spark_quest.db")

LEVEL5 = {
    "title": "Level 5：分区与 Shuffle",
    "description": "教读者「数据在 Spark 里是怎么被切分、又在什么情况下被搬来搬去（Shuffle）的」——把 Level 4 埋下的 Exchange 节点 / 宽依赖伏笔，落到分区（Partition）与 Shuffle 代价的物理层面。覆盖分区是什么、分区数即并行度、Shuffle 定义、Shuffle 为什么贵、窄宽依赖在分区层面的含义、触发 Shuffle 的操作、reduceByKey 为何比 groupByKey 省、repartition 与 coalesce 区别、综合。为 Level 6（Join 深类型/broadcast/调优）→ Level 7（性能调优：Tungsten 内存/堆外/调优参数）铺垫，本身不抢跑调优。",
    "order_index": 5,
    "lessons": [
        {
            "title": "分区是什么",
            "slug": "l5-what-is-partition",
            "description": "理解「数据按分区（partition）切分并分布到 Executor」；分区是 Spark 并行计算的最小数据单元，一个分区由一个 Task 处理。",
            "objective": "学完本课，你应该能够：用自己的话解释分区（Partition）是什么；说清「分区是 Spark 并行计算的最小数据单元，一个分区由一个 Task 处理」；理解分区是逻辑切分（由 partitioner/输入切片决定）而非把文件物理劈开；知道分区数影响并行度但不影响结果正确性；并厘清 HDFS block 与分区不是 1:1。",
            "estimated_minutes": 12,
            "order_index": 0,
            "prerequisites": "",
            "content": {
                "explanation": "【先用人话理解】\n\n你已经知道 Spark 把活分给很多工人（Executor）并行干。可「分给工人」是按什么切的？答案是分区（Partition）。就像仓库里那一大堆货被分成 N 个托盘，每个托盘交给一个工人搬。分区就是 Spark 并行计算的最小数据单元——一个分区，由一个 Task 处理。\n\n【一个直观的心智模型】\n\n把分区想成「大仓库里的货被分成的 N 个托盘」。每个托盘（分区）是一份独立的数据切片，交给一个工人（Executor）去搬、去算。Task 数 = 托盘数，托盘越多能同时开工的工人越多。复用 L4 的「Task = 每分区一份活」和 L0 的「Executor = 工人」：托盘就是分给工人的那摞活。\n\n⚠️ 比喻的边界（很重要）：\n① 分区是逻辑切分，由 partitioner（如 HashPartitioner）或输入切片决定，并不是把文件在磁盘上物理劈成几块；同一文件的不同分区可能仍属同一文件的不同字节区间。\n② 分区数影响并行度，不影响结果正确性——切 2 份还是 200 份，算出来的答案一样，只是快慢不同。\n③ HDFS block 与分区不是 1:1：Spark 默认按 block 数给初始分区，但 repartition / 不同输入格式会改变它，别把「block 数」当成「分区数」。\n\n【正式的技术定义】\n\nPartition（分区）是 RDD / DataFrame 底层数据的逻辑切片，是 Spark 并行计算的最小数据单元。一个分区由一个 Task 在一个 Executor 上处理。分区数决定并行 Task 数（理论并行度）。分区方案由 partitioner（如 HashPartitioner）或输入格式（如 HDFS 切片）决定。\n\n【写下代码后，Spark 内部发生了什么】\n\n你写 `df = spark.read.parquet('sales')`，Spark 先按文件物理布局（block / 文件数）算出初始分区数——假设 128 个。当你调用 `df.count()`（Action），Spark 为这 128 个分区各起一个 Task，分派给集群 Executor 并行处理。每个 Task 只搬自己那份分区数据去算，互不重叠。你看到的并行度，本质就是分区数。",
                "examples": [
                    {
                        "title": "查看当前分区数",
                        "code": "df = spark.read.parquet('sales')\nprint(df.rdd.getNumPartitions())\n# 输出初始分区数（如 128）",
                        "note": "getNumPartitions 直接看真实分区数；初始值通常来自输入文件的 block 数。"
                    },
                    {
                        "title": "分区是逻辑切分，不是物理劈文件",
                        "code": "# 同一份数据，不同读取方式分区数可能不同\ndf1 = spark.read.parquet('sales')\ndf2 = spark.read.csv('sales.csv')\nprint(df1.rdd.getNumPartitions(), df2.rdd.getNumPartitions())",
                        "note": "分区来自「怎么读」，不是「文件被切成几块」；别和 HDFS block 混为一谈。"
                    },
                    {
                        "title": "分区数决定 Task 数",
                        "code": "df = spark.read.parquet('sales').repartition(200)\ndf.count()   # 200 个分区 → 约 200 个 Task 并行",
                        "note": "repartition(200) 显式把分区数改成 200，Action 时就有约 200 个 Task 并行。"
                    }
                ],
                "key_points": [
                    "分区是 Spark 并行计算的最小数据单元，一个分区由一个 Task 处理",
                    "分区数 = 并行 Task 数 = 理论并行度（复用 L4 Job/Stage/Task）",
                    "分区是逻辑切分（由 partitioner/输入切片决定），不是把文件物理劈开",
                    "分区数影响性能，不影响结果正确性",
                    "HDFS block 与分区非 1:1，别混为一谈"
                ],
                "common_mistakes": [
                    {
                        "mistake": "以为分区是把文件在磁盘上物理劈成几块。",
                        "why": "分区是逻辑切片，由 partitioner/输入格式决定，文件在磁盘上没被切。",
                        "fix": "记住分区是「怎么读/怎么分配」的视图，不是磁盘切割。"
                    },
                    {
                        "mistake": "以为「分区越多越快」。",
                        "why": "太多分区带来调度与小块开销，反而慢。",
                        "fix": "并行度调优是 Level 7 的内容，本课先建立「分区 = 并行度」的概念。"
                    },
                    {
                        "mistake": "把 HDFS block 数直接当成分区数。",
                        "why": "不同输入格式/算子会改变分区数。",
                        "fix": "用 getNumPartitions() 看真实分区数，别拍脑袋。"
                    }
                ],
                "review": "从 Level 0 你就知道 Spark 把活分给很多工人（Executor）并行干；Level 4 你还学到「Task 数 = 该 Stage 的分区数」。可「分区」到底是什么，我们一直没正面讲。",
                "problem": "数据在 Spark 里到底按什么切分、分给工人？为什么「一个分区一个 Task」？分区数和结果正确性有关系吗？",
                "preview": "下集我们建立「分区数 = 并行度」的量化直觉，看分区太少或太多分别会怎样。"
            }
        },
        {
            "title": "分区数与并行度",
            "slug": "l5-partition-count-parallelism",
            "description": "建立「分区数 = 并行 Task 数 = 理论并行度」；分区太少→Executor 闲置/长任务，太多→调度与小块开销。",
            "objective": "学完本课，你应该能够：建立「分区数 = 并行 Task 数 = 理论并行度」的等式；说清分区太少会让 Executor 闲置或单任务过长、分区太多会带来调度与小文件开销；理解本课只讲「多少都影响性能」的原理级内容，不给出最优分区数经验公式或 spark.sql.shuffle.partitions 调优值（留 Level 7）。",
            "estimated_minutes": 12,
            "order_index": 1,
            "prerequisites": "",
            "content": {
                "explanation": "【先用人话理解】\n\n分区数不是随便定的数字，它直接决定了「能有几个人同时干活」。分区太少，工人（Executor）闲着没事做、或者一个人扛巨量数据干到天黑；分区太多，光是派活、收活的管理开销就把时间吃掉，还可能产生海量小文件。所以「多少都影响性能」——关键在平衡。\n\n【一个直观的心智模型】\n\n把分区数想成「派工单上写的 N 个托盘」——它等于同时能开工的工人上限。托盘太少：有的工人闲着、有的托盘巨大干到崩溃；托盘太多：光是「点名、发单、收工」的管理动作就比正活还多。复用 Executor=工人、托盘=分区的口径。\n\n⚠️ 比喻的边界（很重要）：\n① 本课只讲「分区数影响性能」的原理，不给你一个万能最优值——最优分区数取决于数据量、集群核数、单条记录大小，是 Level 7 调优的主题。\n② 默认分区数有来源（如读文件按 block、shuffle 按 spark.sql.shuffle.partitions 默认 200），但这些默认值未必适合你的数据，本课点到为止。\n③ 分区数与「结果正确性」无关，只与「快慢」有关；别为了「算对」去纠结分区数。\n\n【正式的技术定义】\n\n并行度（Parallelism）指同时执行的 Task 数量，在 Spark 中等于该 Stage 的分区数。分区过少 → 集群算力未被充分利用（Executor 闲置）或单个 Task 处理数据过大（长尾任务、易 OOM）；分区过多 → 任务调度、任务启动、小文件（每个 Task 一个输出文件）等固定开销累积。合理的分区数是性能调优的核心杠杆之一。\n\n【写下代码后，Spark 内部发生了什么】\n\n你写 `df.repartition(2).count()`：Spark 把数据重排成 2 个分区，Action 时只起 2 个 Task——若集群有 100 个核，98 个核全程闲着。反过来 `df.repartition(10000).count()`：起 10000 个 Task，绝大多数 Task 只处理几 KB 数据，但调度 10000 次任务的开销可能超过计算本身。两种极端都慢。",
                "examples": [
                    {
                        "title": "分区太少，资源闲置",
                        "code": "df = spark.read.parquet('sales').repartition(2)\ndf.count()   # 仅 2 个 Task，百核集群 98 核闲置",
                        "note": "分区数远低于核数时，并行度上不去，算力浪费。"
                    },
                    {
                        "title": "分区太多，调度开销爆炸",
                        "code": "df = spark.read.parquet('sales').repartition(10000)\ndf.count()   # 1 万个 Task，多数只处理几 KB",
                        "note": "海量小 Task 的调度/启动开销可能超过计算本身，且易产生小文件。"
                    },
                    {
                        "title": "看 shuffle 默认分区数来源",
                        "code": "print(spark.conf.get('spark.sql.shuffle.partitions'))\n# 默认 200，是 shuffle 后分区的默认值（非最优保证）",
                        "note": "shuffle 类操作默认按这个值定分区数；它只是默认值，调优留 Level 7。"
                    }
                ],
                "key_points": [
                    "分区数 = 并行 Task 数 = 理论并行度",
                    "分区太少 → Executor 闲置 / 单 Task 过大（长尾、OOM 风险）",
                    "分区太多 → 调度与小文件开销累积",
                    "最优分区数取决于数据量/核数/记录大小，本课不给药（留 L7）",
                    "分区数只影响性能，不影响结果正确性"
                ],
                "common_mistakes": [
                    {
                        "mistake": "以为「分区越多越并行、越快」。",
                        "why": "海量小 Task 的调度开销会反噬。",
                        "fix": "理解分区数是平衡杠杆，不是越大越好（L7 才定量）。"
                    },
                    {
                        "mistake": "现在就去调 spark.sql.shuffle.partitions 到「最优」。",
                        "why": "没有放之四海皆准的最优值，需结合数据。",
                        "fix": "本课只建原理直觉，具体调优参数留 Level 7。"
                    },
                    {
                        "mistake": "以为分区数影响答案对错。",
                        "why": "分区只切数据分布，不改变计算结果。",
                        "fix": "分区数 = 性能旋钮，不是正确性旋钮。"
                    }
                ],
                "review": "上一课我们说「一个分区一个 Task」，分区数 = 并行度。可这个数字定多少才对？随便定会不会有事？",
                "problem": "为什么「分区数 = 并行度」？分区太少或太多分别会带来什么性能问题？有没有一个万能最优值？",
                "preview": "知道了「切几份」影响快慢，下集就讲 Spark 里最贵的那件事——Shuffle：数据是怎么被「搬来搬去」的。"
            }
        },
        {
            "title": "Shuffle 是什么",
            "slug": "l5-what-is-shuffle",
            "description": "理解 Shuffle = 跨节点按 key 重新分布数据；是宽依赖的物化，也是「为什么某些操作特别慢」的根源。",
            "objective": "学完本课，你应该能够：用自己的话解释 Shuffle 是什么——跨节点按 key 重新分布数据；理解 Shuffle 是宽依赖的物化，也是「为什么某些操作特别慢」的根源；知道 Shuffle 不是「错误」而是宽依赖的必然代价；并复用 Level 2/3/4 的「货在空中飞」隐喻正式命名它。",
            "estimated_minutes": 12,
            "order_index": 2,
            "prerequisites": "",
            "content": {
                "explanation": "【先用人话理解】\n\n前面讲的分区，数据都在各自工人手里就地算。可一旦某个操作需要「把所有工人手里『同 key』的数据凑到一起」，事情就麻烦了——每个人手里的货得跨节点飞到别人工位上重新归拢。这个「跨节点、按 key 重排数据」的过程，就叫 Shuffle。\n\n【一个直观的心智模型】\n\n复用 Level 2/3/4 的「货在空中飞」：平常数据安静躺在各工人（Executor）手里；一旦遇到 groupBy / join / orderBy，就像吹了声哨，所有工人把「同 key 的货」抛到空中，按 key 重新落到对应工人的新托盘上。空中飞货 = Shuffle = 数据离开原车间、按 key 重排。复用 Stage=不跨车间的连续工序段：Shuffle 就是把货搬出车间这道动作。\n\n⚠️ 比喻的边界（很重要）：\n① Shuffle 不是「错误」，而是宽依赖（Wide Dependency）的必然代价——只要计算需要「全局按 key 汇聚」，它就必须发生，躲不掉（除非本就无需汇聚）。\n② 本课只正式定义它；它「贵在哪」下节课拆，具体调优（buffer/压缩/分区数）留 Level 7。\n③ Shuffle 发生时数据跨网络，意味着 Driver 端依然不抱数据——是 Executor 之间互传，不是回 Driver 中转。\n\n【正式的技术定义】\n\nShuffle 是 Spark 在执行宽依赖算子时，将各分区数据按 key 重新哈希/排序并跨节点传输、再在目标节点重新分区的物理过程。它是宽依赖（如 groupBy / join / orderBy / distinct）的物化，对应执行计划里的 Exchange 节点。Shuffle 是 Spark 作业中最昂贵的操作之一。\n\n【写下代码后，Spark 内部发生了什么】\n\n你写 `df.groupBy('city').count()` 触发 Action：Stage 0 在本地读数据并做预聚合（窄），到 Shuffle 边界，Spark 把每个分区的记录按 `city` 哈希，序列化后经网络发到持有目标分区的 Executor，目标端反序列化、归并、再进入 Stage 1 做最终聚合。这一「序列化→网络→反序列化→重排」就是 Shuffle 的全貌。",
                "examples": [
                    {
                        "title": "Shuffle 在计划里叫 Exchange",
                        "code": "df.groupBy('city').count().explain()\n# 计划中出现 Exchange 节点 = Shuffle 信号",
                        "note": "Exchange 就是 Shuffle 的物理信号，复用 L4 的读法。"
                    },
                    {
                        "title": "为什么需要 Shuffle",
                        "code": "# 要按 city 聚合，必须先让『同 city』的记录到同一个工人手里\ndf.groupBy('city').sum('amount')",
                        "note": "全局按 key 汇聚无法在本地完成，必须跨节点重排。"
                    },
                    {
                        "title": "Shuffle 切出 Stage",
                        "code": "df.groupBy('city').count().explain()\n# 一个 Exchange → 两个 Stage（本地预聚合 / 跨节点合并）",
                        "note": "Shuffle 处切开 Stage，呼应 L4 的宽依赖=Stage 断点。"
                    }
                ],
                "key_points": [
                    "Shuffle = 跨节点按 key 重新分布数据",
                    "Shuffle 是宽依赖的物化，对应执行计划里的 Exchange 节点",
                    "Shuffle 是「某些操作特别慢」的根源之一",
                    "Shuffle 不是错误，是宽依赖的必然代价（躲不掉）",
                    "数据是 Executor 之间互传，不经 Driver 中转"
                ],
                "common_mistakes": [
                    {
                        "mistake": "看到 Exchange（Shuffle）就觉得「代码写错了」。",
                        "why": "很多聚合/排序/关联本就需要全局按 key 汇聚。",
                        "fix": "区分「必要 Shuffle」与「本可避免的冗余 Shuffle」，后者才是优化点（L7）。"
                    },
                    {
                        "mistake": "以为 Shuffle 数据会先回 Driver 再分发。",
                        "why": "是 Executor 之间直接互传。",
                        "fix": "Driver 不抱数据，Shuffle 在 Executor 间完成。"
                    },
                    {
                        "mistake": "以为本课就要学会「消除 Shuffle」。",
                        "why": "本课只定义 Shuffle，代价与调优在后续。",
                        "fix": "先认清它是什么，代价拆解留 L5 下节课、调优留 L7。"
                    }
                ],
                "review": "上一课我们讲了「分区」和「分区数 = 并行度」。可光把数据切好分下去，计算并不总是能就地完成——有些操作必须把货搬来搬去。",
                "problem": "Shuffle 到底是什么？为什么 groupBy / join / orderBy 会触发它？它是不是一种「错误」？",
                "preview": "知道了 Shuffle 是「空中飞货」，下集就拆开它到底贵在哪几个环节——为什么一次跨节点搬运能拖垮整段作业。"
            }
        },
        {
            "title": "Shuffle 为什么贵",
            "slug": "l5-shuffle-cost",
            "description": "拆解 Shuffle 代价环节：磁盘 spill、跨网络传输、序列化/反序列化、map 端排序、reduce 端拉取。",
            "objective": "学完本课，你应该能够：拆解 Shuffle 的代价环节——磁盘 spill、跨网络传输、序列化/反序列化、map 端排序、reduce 端拉取；理解每个环节都花钱；并知道本课只讲「贵在哪」的原理，不给出 spark.shuffle.file.buffer / compression 等具体参数（留 Level 7），也不要求你会调。",
            "estimated_minutes": 13,
            "order_index": 3,
            "prerequisites": "",
            "content": {
                "explanation": "【先用人话理解】\n\nShuffle 之所以是性能杀手，是因为它不是「把货从 A 桌挪到 B 桌」那么轻松——它要先装箱（序列化）、装车发运（走网络）、卸货分拣（排序/聚合）。每一道都是实打实的开销。理解这笔账，你就懂为什么能不 Shuffle 就不 Shuffle。\n\n【一个直观的心智模型】\n\n把一次 Shuffle 想成「一次空中运输」：\n- 装箱：把每件货打成标准包裹（序列化）；\n- 装车发运：包裹走网线飞到目标工人（跨网络传输）；\n- 卸货分拣：目标端拆包（反序列化）、按 key 排序、归并聚合。\n复用「空中飞货」隐喻：飞这一趟，光油费（网络）+ 打包人工（序列化）+ 卸货分拣（排序聚合）就不少。\n\n⚠️ 比喻的边界（很重要）：\n① 本课只讲「贵在哪几个环节」，不给你 spark.shuffle.file.buffer / compression 等具体调优参数——那是 Level 7 的事。\n② 当内存放不下中间结果，Spark 会把数据 spill 到磁盘，磁盘 I/O 比内存慢几个数量级，进一步放大代价。\n③ 网络传输受带宽与节点间距离限制；数据倾斜时某些 key 的货特别多，「空中运输」会严重不均衡（倾斜调优留 L7）。\n\n【正式的技术定义】\n\nShuffle 的代价来自多个环节：map 端按 key 分区并常做排序/combine、序列化后写磁盘/网络；数据跨节点传输；reduce 端通过网络拉取（fetch）自己负责的分区、反序列化、归并排序后交付后续算子。任一环节（磁盘 spill、网络、序列化、排序、拉取）在大数据量下都可能是瓶颈。\n\n【写下代码后，Spark 内部发生了什么】\n\n你写 `df.groupBy('city').count()`：map 端先把记录按 city 分区、本地排序/combine，序列化成块写入；reduce 端发起 fetch 拉取属于自己 key 的块，跨网络传输，反序列化后在本地归并排序，得到每 city 的计数。整条链路「排序+序列化+网络+反序列化+排序」一个不落，这就是 Shuffle 的贵。",
                "examples": [
                    {
                        "title": "序列化 + 网络 + 反序列化",
                        "code": "df.groupBy('city').sum('amount').explain()\n# Exchange 背后 = 序列化→网络→反序列化→重排",
                        "note": "看到 Exchange 就想到这一串跨节点开销。"
                    },
                    {
                        "title": "内存不够会 spill 到磁盘",
                        "code": "# 单分区数据过大时，map/reduce 端都会 spill 到磁盘\n# 磁盘 I/O 远慢于内存，代价进一步放大",
                        "note": "spill 是 Shuffle 贵的重要放大器（调优留 L7）。"
                    },
                    {
                        "title": "数据倾斜让运输不均",
                        "code": "# 某个 city 记录极多 → 该 key 的 Shuffle 块远超其他\n# 单节点被压垮，整体被拖慢（倾斜留 L7）",
                        "note": "倾斜时「空中运输」严重不均衡，是运行时典型瓶颈。"
                    }
                ],
                "key_points": [
                    "Shuffle 代价环节：序列化 → 网络传输 → 反序列化 → 排序/聚合",
                    "map 端常做分区+排序+combine，reduce 端 fetch+归并",
                    "内存不足会 spill 到磁盘，I/O 慢几个数量级",
                    "网络传输受带宽/距离限制，是分布式固有成本",
                    "数据倾斜会放大 Shuffle 代价（调优留 L7）"
                ],
                "common_mistakes": [
                    {
                        "mistake": "以为 Shuffle 只是「内存里挪一下数据」。",
                        "why": "它涉及序列化、跨网络、排序、可能 spill 磁盘。",
                        "fix": "记住 Shuffle 是多环节重活，不是零成本内存操作。"
                    },
                    {
                        "mistake": "本课就去调 spark.shuffle.file.buffer 等参数。",
                        "why": "具体调优参数留 Level 7。",
                        "fix": "本课只建立「贵在哪」的原理直觉。"
                    },
                    {
                        "mistake": "以为所有 key 的 Shuffle 一样快。",
                        "why": "倾斜时少数 key 极慢，拖垮整体。",
                        "fix": "理解倾斜是运行时问题，识别与调优留 L7。"
                    }
                ],
                "review": "上一课我们正式命名了 Shuffle——宽依赖的物化、空中飞货。可为什么大家都说它「贵」？贵在哪？",
                "problem": "Shuffle 到底贵在哪几个环节？为什么「序列化+网络+排序」这一串这么花钱？spill 和倾斜又怎么放大代价？",
                "preview": "拆完代价，下集把 Level 4 的窄/宽依赖落回到分区层面——为什么有些算子能就地算、有些必须空中飞货。"
            }
        },
        {
            "title": "窄/宽依赖在分区层面的含义",
            "slug": "l5-narrow-wide-partition",
            "description": "把 L4 的窄/宽依赖定义落到分区：窄依赖父分区只映射一个子分区（无需重排），宽依赖父分区数据发往多个子分区（必 Shuffle）；理解「Stage 边界 = Shuffle 发生的切口」。",
            "objective": "学完本课，你应该能够：把 Level 4 的窄/宽依赖定义落到分区层面——窄依赖父分区只映射一个子分区（无需重排），宽依赖父分区数据发往多个子分区（必 Shuffle）；理解「Stage 边界 = Shuffle 发生的切口」；知道 L5 不重讲窄宽定义（L4 已讲），重点在「分区如何被重新分配」+「为什么宽依赖处必切 Stage」。",
            "estimated_minutes": 13,
            "order_index": 4,
            "prerequisites": "",
            "content": {
                "explanation": "【先用人话理解】\n\n窄依赖和宽依赖，落到分区上就是一句话：子分区需要的货，是「老老实实待在原地、只从一个父分区来」，还是「必须从所有父分区按 key 空运到别处拼起来」。前者不动窝，后者必飞货。这就是同一件事的两个说法。\n\n【一个直观的心智模型】\n\n- 窄依赖 = 一个托盘（父分区）直接交给一个工人（子分区），不拆不飞（复用「车间内部传递」）。\n- 宽依赖 = 一个托盘的货按 key 拆开，分别空运到不同工人的新托盘（复用「空中飞货」+ Stage=连续不跨车间工序段）。\n所以宽依赖处就是 Stage 的切口：飞货一出车间，这道连续工序段就结束了。\n\n⚠️ 比喻的边界（很重要）：\n① L5 不重讲窄宽「定义」（L4 已讲），本课重点在「分区怎么被重新分配」——窄：子分区只依赖父的局部分区；宽：子分区依赖父全部分区中同 key 数据。\n② 宽依赖处必切 Stage，是因为子分区要等「所有上游同 key 货到齐」才能算，天然跨节点，无法留在同一段连续工序里。\n③ 并行度调优（怎么定分区数最优）留 Level 7，本课只讲依赖类型如何决定数据流向与 Stage 边界。\n\n【正式的技术定义】\n\n在分区层面：Narrow Dependency 中每个子分区只由有限个（通常 1 个或同节点）父分区计算得到，无需跨节点重排；Wide Dependency 中每个子分区依赖所有父分区中同 key 的数据，必须跨节点重分布（Shuffle）。宽依赖处即 Stage 边界，也是融合（WholeStageCodegen）的断点。\n\n【写下代码后，Spark 内部发生了什么】\n\n你写 `df.filter(...).select(...)`（窄）：Spark 在同一 Stage 内把这几个算子融合，各分区就地连续处理，无跨节点移动。你写 `df.groupBy('city').count()`（宽）：Stage 0 本地预聚合后，在 Shuffle 处把数据按 city 重分布到新分区，切出 Stage 1 做跨节点合并。分区层面的「重分配」就是 Stage 划分的物理依据。",
                "examples": [
                    {
                        "title": "窄依赖：分区就地处理",
                        "code": "df.filter(df.amount > 0).select('city').explain()\n# 无 Exchange，整段同一 Stage，分区不跨节点",
                        "note": "窄依赖中父→子分区是局部分配，无重排。"
                    },
                    {
                        "title": "宽依赖：分区被重分配",
                        "code": "df.groupBy('city').count().explain()\n# Exchange 处分区按 city 重分布到新分区，切 Stage",
                        "note": "宽依赖中父分区数据发往多个子分区，必 Shuffle。"
                    },
                    {
                        "title": "依赖类型决定 Stage 边界",
                        "code": "# 每多一次宽依赖（Exchange），多切一个 Stage\ndf.groupBy('city').count().explain()",
                        "note": "Stage 边界 = Shuffle 切口，根子在依赖类型。"
                    }
                ],
                "key_points": [
                    "窄依赖：子分区只依赖父局部分区，无需重排（车间内部）",
                    "宽依赖：子分区依赖父全部分区同 key 数据，必 Shuffle（空中飞货）",
                    "宽依赖处 = Stage 边界 = 融合断点",
                    "L5 重点在「分区如何被重分配」，窄宽定义 L4 已讲",
                    "并行度调优留 Level 7，本课只看依赖决定数据流向"
                ],
                "common_mistakes": [
                    {
                        "mistake": "以为「算子多就切 Stage」。",
                        "why": "只有宽依赖（Exchange）才切 Stage。",
                        "fix": "窄算子在同一 Stage 融合，看 Exchange 而非算子数。"
                    },
                    {
                        "mistake": "在 L5 重讲窄宽定义。",
                        "why": "L4 已讲定义，L5 只延展到分区物化。",
                        "fix": "聚焦「分区怎么被重新分配」与 Stage 切口。"
                    },
                    {
                        "mistake": "以为窄依赖也会跨节点。",
                        "why": "窄依赖父→子分区是局部分配。",
                        "fix": "只有宽依赖才触发跨节点重分布。"
                    }
                ],
                "review": "Level 4 我们讲了窄依赖/宽依赖的定义，以及「宽依赖是 Stage 断点」。可「断点」在分区层面到底长什么样？",
                "problem": "窄/宽依赖落到分区上分别意味着什么？为什么说「Stage 边界 = Shuffle 发生的切口」？分区是怎么被重新分配的？",
                "preview": "知道了依赖决定流向，下集就列一张清单——到底哪些操作会触发 Shuffle，哪些「可能」触发。"
            }
        },
        {
            "title": "哪些操作会触发 Shuffle",
            "slug": "l5-shuffle-trigger-operators",
            "description": "列举触发 Shuffle 的常见算子（groupBy / reduceByKey / aggregateByKey / join / distinct / repartition / orderBy / sort 等），区分「一定 Shuffle」与「可能 Shuffle」。",
            "objective": "学完本课，你应该能够：列举触发 Shuffle 的常见算子（groupBy / reduceByKey / aggregateByKey / join / distinct / repartition / orderBy / sort 等）；区分「一定 Shuffle」与「可能 Shuffle」；知道 join 只点出「是宽依赖、会 Shuffle」，深类型（broadcast/sort-merge 怎么选）留 Level 6；不展开各 join 策略优劣。",
            "estimated_minutes": 13,
            "order_index": 5,
            "prerequisites": "",
            "content": {
                "explanation": "【先用人话理解】\n\n既然 Shuffle 这么贵，你至少得认得出「哪些工序会叫空中货运」。就像仓库里有张清单，列着哪些动作必然要搬货、哪些动作可能要搬。认全这张清单，你写代码时才能下意识避开不必要的飞货。\n\n【一个直观的心智模型】\n\n把触发 Shuffle 的算子想成「会叫空中货运的那些工序清单」：groupBy 分拣、join 拼桌、distinct 去重、orderBy 重排、repartition 推倒重排——这些都是「需要全局按 key / 全局有序 / 全局重分布」的动作，必然或可能叫飞货。复用「空中飞货」与「水果分拣派对 = groupBy 聚合」。\n\n⚠️ 比喻的边界（很重要）：\n① 区分「一定 Shuffle」与「可能 Shuffle」：groupBy / distinct / orderBy / sort / join / repartition 通常一定 Shuffle；而像 `union`（同 schema 简单拼接）一般不 Shuffle；某些 `reduceByKey` 在已按相同 key 分区时仍可能仍需跨节点合并（取决于上游分区）。\n② join 只点出「是宽依赖、会 Shuffle」；broadcast / sort-merge / shuffle-hash 怎么选、什么时候 broadcast，是 Level 6 的深类型，本课不展开。\n③ 不要背死「某算子必 Shuffle」——要看它是否需要「全局按 key 汇聚 / 全局有序」，那是 Shuffle 的真正判据。\n\n【正式的技术定义】\n\n触发 Shuffle 的算子通常需要跨分区按 key 重分布或全局排序：groupBy / groupByKey / reduceByKey / aggregateByKey（按 key）、join / cogroup（按 key 对齐）、distinct / dropDuplicates（按整行或列去重需重排）、orderBy / sort / sortWithinPartitions（全局有序需重排）、repartition（强制重分布）。是否实际 Shuffle 取决于上游是否已是目标分区分布。\n\n【写下代码后，Spark 内部发生了什么】\n\n你写 `df.orderBy('city')`：因需要全局有序，Spark 在 Shuffle 处把数据按排序键重分布到新分区并排序，切出 Stage。你写 `dfA.join(dfB, 'id')`：两表按 id 重分布（Shuffle）后对齐拼桌。你写 `df.union(other)`（同 schema）：仅拼接分区、不重排，通常无 Shuffle——印证「是否需全局重分布」才是判据。",
                "examples": [
                    {
                        "title": "一定 Shuffle 的算子",
                        "code": "df.groupBy('city').count()\ndf.orderBy('city')\ndf.distinct()\n# 都需全局按 key/有序重分布 → 必 Shuffle",
                        "note": "groupBy / orderBy / distinct 是 Shuffle 常客。"
                    },
                    {
                        "title": "join 也 Shuffle",
                        "code": "dfA.join(dfB, 'id').explain()\n# 两表按 id 重分布 → Exchange（Shuffle）",
                        "note": "join 是宽依赖；策略深类型留 Level 6。"
                    },
                    {
                        "title": "可能不 Shuffle：union",
                        "code": "df.union(other).explain()\n# 同 schema 简单拼接分区，通常无 Exchange",
                        "note": "是否 Shuffle 看「是否需全局重分布」，不是看算子名。"
                    }
                ],
                "key_points": [
                    "一定/通常 Shuffle：groupBy / distinct / orderBy / sort / join / repartition",
                    "reduceByKey / aggregateByKey 按 key，通常需跨节点合并",
                    "union（同 schema 拼接）通常不 Shuffle",
                    "判据是「是否需全局按 key 汇聚/全局有序」，而非算子名",
                    "join 深类型（broadcast 等）留 Level 6，本课只点「会 Shuffle」"
                ],
                "common_mistakes": [
                    {
                        "mistake": "以为「记住某算子必 Shuffle」就够。",
                        "why": "是否真 Shuffle 取决于上游分区分布。",
                        "fix": "抓住判据：是否需要全局按 key 汇聚/有序。"
                    },
                    {
                        "mistake": "在 L5 展开 join 策略优劣。",
                        "why": "broadcast/sort-merge 选择是 Level 6。",
                        "fix": "本课只点 join 是宽依赖、会 Shuffle。"
                    },
                    {
                        "mistake": "以为 union 也 Shuffle。",
                        "why": "同 schema union 只是拼接分区。",
                        "fix": "union 通常无 Shuffle，别一刀切。"
                    }
                ],
                "review": "上一课我们把窄/宽依赖落到了分区层面，知道宽依赖必飞货。可落到具体算子上，到底哪些动作会触发飞货？",
                "problem": "哪些算子会触发 Shuffle？怎么区分「一定 Shuffle」和「可能 Shuffle」？判断 Shuffle 的真正判据是什么？",
                "preview": "列完触发清单，下集讲一个经典优化原理——为什么 reduceByKey 比 groupByKey 省那么多 Shuffle。"
            }
        },
        {
            "title": "reduceByKey vs groupByKey",
            "slug": "l5-reducebykey-vs-groupbykey",
            "description": "经典 Shuffle 优化原理：reduceByKey 在 map 端先做本地 combine（同 key 先聚合），大幅减少跨网络传输量；groupByKey 不做 combine，所有 value 原样 Shuffle。",
            "objective": "学完本课，你应该能够：说清 reduceByKey 与 groupByKey 的核心差异——reduceByKey 在 map 端先做本地 combine（同 key 先聚合），大幅减少跨网络传输量；groupByKey 不做 combine，所有 value 原样 Shuffle；理解 combine 要求聚合函数可交换可结合；并知道本课只讲原理级「为什么 reduceByKey 更省 Shuffle」，不写「设 partitioner / 调 shuffle.partitions 到最优」的 tuning 代码（留 Level 7）。",
            "estimated_minutes": 14,
            "order_index": 6,
            "prerequisites": "",
            "content": {
                "explanation": "【先用人话理解】\n\n同样是把同 key 的货凑一起，做法不同，空中运费天差地别。一种做法是：每个工人先把自家的同 key 货捆成小包（本地先聚合），再只把小包空运去中央汇总；另一种是：把每件散货原样空运，到中央再慢慢捆。前者飞货量小得多——这就是 reduceByKey 比 groupByKey 省的根本原因。\n\n【一个直观的心智模型】\n\n- reduceByKey = 先在各自车间把同类项捆成小包（map-side combine），再只空运小包到中央汇总（复用「空中飞货」+ 水果分拣派对：每个人扔之前先本地预聚合，只扔两个大袋）。\n- groupByKey = 把每件散货都原样空运（不捆），到中央再分组——空中飞的全是未聚合的原始 value，运力浪费。\n\n⚠️ 比喻的边界（很重要）：\n① combine 有前提：聚合函数必须是可交换、可结合的（如 sum/ min/ max），否则本地先聚合会算错；groupBy 的「分组后随便处理」没有这个限制。\n② 本课只讲「为什么 reduceByKey 更省 Shuffle」的原理，不写「设自定义 partitioner / 调 spark.sql.shuffle.partitions 到最优」的 tuning 代码——那是 Level 7。\n③ 即便省了 Shuffle 量，reduceByKey 仍有一次 Shuffle（只是传输量小）；它优化的是「传输体积」，不是「消除 Shuffle」。\n\n【正式的技术定义】\n\nreduceByKey 在 map 端对每个分区内的同 key 记录先做本地聚合（combine），再 Shuffle 传输已聚合的部分结果，reduce 端合并得到最终值，因此跨网络传输的数据量远小于原始记录数。groupByKey 不做 map 端 combine，直接将每个 key 的全部 value 原样 Shuffle 到 reduce 端再分组，传输量 = 原始 value 总数，网络代价高。\n\n【写下代码后，Spark 内部发生了什么】\n\n你写 `rdd.map(...).reduceByKey(_ + _)`：每个 Executor 先在本地把同 key 的 value 相加成部分和，Shuffle 时只传这些部分和（例如每分区每 key 一个和），reduce 端加总。你写 `rdd.map(...).groupByKey()`：每个 value 原样序列化飞到目标 Executor，目标端收齐所有 value 再处理——同样数据量，空中飞货量可能是前者的几十倍。",
                "examples": [
                    {
                        "title": "reduceByKey：先本地 combine",
                        "code": "words = rdd.map(lambda w: (w, 1))\nwords.reduceByKey(lambda a, b: a + b).collect()\n# 每分区先本地求和，再 Shuffle 部分和",
                        "note": "map 端 combine 大幅减少空中飞货量。"
                    },
                    {
                        "title": "groupByKey：原样 Shuffle",
                        "code": "words.groupByKey().mapValues(sum).collect()\n# 所有 value 原样飞到目标端再分组求和",
                        "note": "无 combine，传输量 = 原始 value 总数，贵。"
                    },
                    {
                        "title": "combine 的前提",
                        "code": "# sum/min/max 可交换可结合，能本地 combine\n# 若聚合依赖全局顺序（如求中位数），不能简单 combine",
                        "note": "只有可交换可结合的聚合才能 map 端预聚合。"
                    }
                ],
                "key_points": [
                    "reduceByKey：map 端先本地 combine，再 Shuffle 部分和（传输量小）",
                    "groupByKey：不 combine，所有 value 原样 Shuffle（传输量大）",
                    "combine 要求聚合函数可交换、可结合（sum/min/max）",
                    "reduceByKey 优化的是「Shuffle 传输体积」，不是消除 Shuffle",
                    "tuning 代码（partitioner/分区数）留 Level 7，本课只讲原理"
                ],
                "common_mistakes": [
                    {
                        "mistake": "以为 reduceByKey 不 Shuffle。",
                        "why": "它仍有一次 Shuffle，只是传输量小。",
                        "fix": "理解它优化体积，不消除 Shuffle。"
                    },
                    {
                        "mistake": "对任何聚合都用 groupByKey。",
                        "why": "原样 Shuffle 传输量最大。",
                        "fix": "可换的聚合优先 reduceByKey / aggregateByKey。"
                    },
                    {
                        "mistake": "以为所有聚合都能 map 端 combine。",
                        "why": "依赖全局顺序的聚合不可结合。",
                        "fix": "只有可交换可结合的聚合能本地预聚合。"
                    }
                ],
                "review": "上一课我们列了触发 Shuffle 的算子清单，groupBy / reduceByKey 都在列。可同样要按 key 聚合，写法不同，空中运费差很多。",
                "problem": "为什么 reduceByKey 比 groupByKey 省 Shuffle？map 端 combine 是什么？为什么不是所有聚合都能本地预聚合？",
                "preview": "懂了「怎么让飞货更省」，下集讲怎么主动控制分区数——repartition 与 coalesce 有什么区别。"
            }
        },
        {
            "title": "repartition vs coalesce",
            "slug": "l5-repartition-coalesce",
            "description": "掌握控制分区数的两个手段：repartition（一定触发 Shuffle，增减分区都可）vs coalesce（减少分区走窄依赖合并、不触发 Shuffle，但不能增分区）。",
            "objective": "学完本课，你应该能够：掌握控制分区数的两个手段——repartition（一定触发 Shuffle、增/减分区都行）与 coalesce（减少分区走窄依赖合并、不触发 Shuffle，但不能增分区）；理解「想减分区又不想白付 Shuffle 就选 coalesce」；知道 coalesce 增分区无效（需 repartition）、coalesce 跨节点合并仍可能移动数据（shuffle=False 仅合并同节点）；并行度/性能调优留 Level 7。",
            "estimated_minutes": 13,
            "order_index": 7,
            "prerequisites": "",
            "content": {
                "explanation": "【先用人话理解】\n\n想调整分区数（托盘数）有两个扳手：一个粗暴——把所有托盘推倒重排，必叫空中货运；一个温柔——把相邻的托盘就地并拢，不拆不飞。前者能增能减但必付 Shuffle；后者只能减、但免费。选哪个，看你是要「加托盘」还是「减托盘」。\n\n【一个直观的心智模型】\n\n- repartition = 把所有托盘推倒重排（必空中飞货）：能增能减，但每次都付一次 Shuffle。\n- coalesce = 把相邻托盘就地并拢（不拆不飞，窄合并）：只能减不能增，且不触发 Shuffle。\n复用「空中飞货」与「托盘 = 分区」：想减托盘又不想白付飞货，就选 coalesce。\n\n⚠️ 比喻的边界（很重要）：\n① coalesce 不能增分区——它只做「合并」，没有数据可凭空多出托盘；要增分区必须 repartition。\n② coalesce 默认 shuffle=False，只在同节点内合并相邻分区；若跨节点合并仍可能移动数据，想要强制不跨节点可传 shuffle=False 并依赖同节点布局（通常无需显式）。\n③ 并行度/性能调优（选多少分区最优）留 Level 7；本课只讲两个手段的「触发 Shuffle 与否」与「能否增减」。\n\n【正式的技术定义】\n\nrepartition(n) 通过对数据做 hash 重分布把分区数改为 n，**一定触发 Shuffle**，可增可减。coalesce(n) 通过合并现有分区减少分区数（n < 当前），默认走窄依赖合并、**不触发 Shuffle**，但只能减少不能增加；若想跨节点均匀合并可传 shuffle=True（那就变 Shuffle）。二者都返回新 DataFrame，原 DataFrame 不变（不可变语义）。\n\n【写下代码后，Spark 内部发生了什么】\n\n你写 `df.repartition(200)`：Spark 按 key 哈希把数据重分布到 200 个分区，一次 Shuffle，分区数变 200（增或减都行）。你写 `df.coalesce(2)`：Spark 把相邻分区合并成 2 个，不跨节点重排、无 Shuffle，分区数从多降到 2（只能减）。你写 `df.coalesce(500)`（当前只有 10 个分区）则无效——不能凭空增多。",
                "examples": [
                    {
                        "title": "repartition：必 Shuffle，能增能减",
                        "code": "df.repartition(200).explain()\n# 出现 Exchange，分区数改为 200（增或减都触发 Shuffle）",
                        "note": "repartition 任何方向都付一次 Shuffle。"
                    },
                    {
                        "title": "coalesce：不 Shuffle，只能减",
                        "code": "df.coalesce(2).explain()\n# 无 Exchange，相邻分区合并，分区数降到 2",
                        "note": "想减分区又不想白付 Shuffle，选 coalesce。"
                    },
                    {
                        "title": "coalesce 不能增分区",
                        "code": "df.coalesce(500)  # 当前仅 10 分区 → 无效，不会变多\n# 要增分区必须用 repartition(500)",
                        "note": "coalesce 只合并、不创造新分区。"
                    }
                ],
                "key_points": [
                    "repartition：一定触发 Shuffle，可增可减分区",
                    "coalesce：默认不 Shuffle（窄合并），只能减少分区",
                    "想减分区又不想白付 Shuffle → 选 coalesce",
                    "coalesce 不能增分区，要增必须 repartition",
                    "coalesce 跨节点合并仍可能移动数据；调优留 L7"
                ],
                "common_mistakes": [
                    {
                        "mistake": "用 coalesce 想增加分区数。",
                        "why": "coalesce 只合并，不能凭空增多。",
                        "fix": "增分区用 repartition。"
                    },
                    {
                        "mistake": "减分区也一律用 repartition。",
                        "why": "白付一次不必要的 Shuffle。",
                        "fix": "纯减分区优先 coalesce（免 Shuffle）。"
                    },
                    {
                        "mistake": "以为 coalesce 永远零移动。",
                        "why": "跨节点合并仍可能移动数据。",
                        "fix": "理解 shuffle=False 主要是同节点合并，并非绝对零移动。"
                    }
                ],
                "review": "前面几课我们建立了「分区数 = 并行度」「Shuffle 很贵」。那能不能主动控制分区数，又尽量少付 Shuffle？",
                "problem": "repartition 和 coalesce 有什么区别？为什么减分区优先用 coalesce？为什么说 coalesce 不能增分区？",
                "preview": "学完两个控制分区的扳手，下集做综合练习——给你一段真实代码，指出哪些操作触发 Shuffle、数出 Stage、估计并行度。"
            }
        },
        {
            "title": "综合练习",
            "slug": "l5-comprehensive",
            "description": "给一段真实代码，能指出哪些操作触发 Shuffle、数出 Stage、估计分区/并行度，并能用「reduceByKey 优于 groupByKey」原理指出可优化点（仅原理，不写 tuning）。",
            "objective": "学完本课，你应该能够：给一段真实代码，独立指出哪些操作触发 Shuffle、数出 Stage、估计分区/并行度，并能用「reduceByKey 优于 groupByKey」原理指出可优化点（仅原理，不写 tuning）；理解综合只验证「看得懂分区与 Shuffle、能识别触发点」，不要求给出调优参数或最优分区数（留 Level 7）；理解计划相同 ≠ 运行时性能相同（倾斜留 Level 7）。",
            "estimated_minutes": 18,
            "order_index": 8,
            "prerequisites": "",
            "content": {
                "explanation": "【先用人话理解】\n\n这是 Level 5 的收束：给你一段真实代码，让你像看「运输排程单」一样，把前面所有道具串成一张完整图——先找空中飞货（Shuffle），再数托盘（分区/并行度），最后找「能本地先捆包」的机会（combine）。它逼你把「看分区与 Shuffle」从「看得懂单个概念」升级到「看得懂整段作业」。\n\n示例任务：读一份日志，按城市分组统计错误数，按数量降序取前 10。\n目标：独立指出 ① 哪几步触发 Shuffle（groupBy / orderBy）；② 分成几个 Stage（Shuffle 数 + 1）；③ 并行度约等于多少（看分区数）；④ 能否用 reduceByKey 类思路减少飞货。\n\n【一个直观的心智模型】\n\n把这次练习想成「把前面道具串成一张运输排程单」：\n1. 先找 **空中飞货（Shuffle）**——groupBy / orderBy / join 等，它们是性能重点信号。\n2. 再数 **托盘（分区 / 并行度）**——分区数 = Task 数 = 理论并行度。\n3. 最后找 **可本地捆包的机会（combine）**——能用 reduceByKey 就不用 groupByKey。\n\n⚠️ 比喻的边界（很重要）：\n① 计划相同 ≠ 运行时性能相同：同样一份计划，数据倾斜、分区数不同，真实耗时天差地别（Level 7 才展开）。\n② 本课综合**只验证「看得懂」**——能指认 Shuffle、数出 Stage、估计并行度、指出 reduceByKey 优化点，就达标；不要求你写 tuning 代码或给最优分区数。\n③ explain() 不触发执行，所以这套「读图」练习随时可做、零成本。\n\n【正式的技术定义】\n\n综合练习 = 对一段真实 Spark 代码，完整应用 Level 5 所学：识别触发 Shuffle 的算子（groupBy / orderBy / join / distinct / repartition）；据 Shuffle 数判定 Stage 数（Shuffle 数 + 1）；据分区数估计并行度（Task 数）；并据「map 端 combine」原理判断能否用 reduceByKey 类算子替代 groupByKey 以减少传输。输出一份「分区与 Shuffle 读图报告」。\n\n【写下代码后，Spark 内部发生了什么】\n\n你写 `logs.groupBy('city').count().orderBy(F.desc('count')).limit(10).explain(True)`：Spark 先生成计划；你读出 groupBy 处一处 Exchange（Shuffle，切出 Stage）、orderBy 处又一处 Exchange（再切 Stage），共 2 次 Shuffle → 3 个 Stage；并发现 groupBy 用 reduceByKey 式本地预聚合（combine）已省传输；limit 不 Shuffle。整段分析零执行，纯粹「读图」。",
                "examples": [
                    {
                        "title": "完整读图练习",
                        "code": "logs.groupBy('city').count() \\\n     .orderBy(F.desc('count')).limit(10).explain(True)\n# 读图：groupBy + orderBy 两处 Exchange → 3 Stage；limit 不 Shuffle",
                        "note": "独立指认 Shuffle、Stage 数、并行度、combine 机会即达标。"
                    },
                    {
                        "title": "指出可优化点（原理）",
                        "code": "# 若看到 groupByKey 后 sum，可改为 reduceByKey 减少飞货\nrdd.map(lambda w: (w, 1)).reduceByKey(lambda a, b: a + b)",
                        "note": "只点原理：map 端 combine 更省 Shuffle；不写 tuning 代码。"
                    },
                    {
                        "title": "只验证读懂，不调优",
                        "code": "# 目标不是改快，而是说清「它怎么切、怎么飞、并行多少」\nlogs.groupBy('city').count().explain()",
                        "note": "综合练习只验收「看得懂分区与 Shuffle」，调优留 L7。"
                    }
                ],
                "key_points": [
                    "读图三步：找 Shuffle（空中飞货）→ 数 Stage（Shuffle+1）→ 估计并行度（分区数）",
                    "能指认 Shuffle、数出 Stage、估计并行度、指出 reduceByKey 优化点即达标",
                    "计划相同 ≠ 运行时性能相同（倾斜/分区数影响，L7）",
                    "综合只验证「看得懂」，不要求调优或给最优分区数",
                    "explain() 不触发执行，读图练习零成本"
                ],
                "common_mistakes": [
                    {
                        "mistake": "综合练习里急着「改代码调快」。",
                        "why": "本课只验收读得懂。",
                        "fix": "先把图读准，调优是 L7。"
                    },
                    {
                        "mistake": "数 Stage 时漏算「初始 Stage」。",
                        "why": "Stage 数 = Shuffle 数 + 1。",
                        "fix": "从 1 开始加。"
                    },
                    {
                        "mistake": "以为看 plan 就能定性能。",
                        "why": "计划是静态，倾斜/分区数是运行时因素。",
                        "fix": "真实性能看 Spark UI（L7）。"
                    }
                ],
                "review": "从「分区是什么」「分区数=并行度」「Shuffle 定义与代价」「窄宽在分区层面」「触发算子」「reduceByKey vs groupByKey」「repartition vs coalesce」，Level 5 的零件都齐了。",
                "problem": "能不能不靠提示，独立给一段真实代码读出它的 Shuffle、Stage、并行度，并指出 reduceByKey 比 groupByKey 省的优化点？这正是检验你是否真正串起 Level 5 的标准。",
                "preview": "恭喜走完 Level 5——你现在能「看见」数据怎么被切分、怎么被搬来搬去、哪里最贵。但「怎么让它真的算得更快」的定量调优，是 Level 6（Join 深类型/broadcast）→ Level 7（性能调优）的主场。去测验检验自己吧。🏁"
            }
        }
    ]
}

LEVEL5_QUIZZES = [
    {"lesson_slug": "l5-what-is-partition", "questions": [
        {"type": "single_choice", "prompt": "分区（Partition）最准确的定位是？", "options": ["结果正确性的保证", "Spark 并行计算的最小数据单元，一个分区由一个 Task 处理", "磁盘上被劈开的物理文件块", "Driver 端的内存容器"], "correct_index": 1, "explanation": "分区是并行计算的最小数据单元，一个分区由一个 Task 在一个 Executor 上处理；它是逻辑切片，不是磁盘物理切割。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "为什么分区数影响并行度？", "options": ["分区数 = 并行 Task 数 = 理论并行度", "分区数 = Executor 数", "分区越多结果越准", "分区数 = Stage 数"], "correct_index": 0, "explanation": "每个分区对应一个 Task，所以分区数直接决定同时执行的 Task 数（并行度）。", "dimension": "why"},
        {"type": "single_choice", "prompt": "写下 df = spark.read.parquet('sales') 后调用 df.count()，Spark 内部发生什么？", "options": ["为各分区各起一个 Task 并行处理", "先把全表读进 Driver 再算", "不切分区直接算", "只起一个 Task"], "correct_index": 0, "explanation": "Action 触发时，Spark 为当前每个分区起一个 Task，分派给 Executor 并行处理，Task 数 = 分区数。", "dimension": "mechanism"},
        {"type": "single_choice", "prompt": "想查看当前 DataFrame 的分区数，用？", "options": ["df.rdd.getNumPartitions()", "df.count()", "df.show()", "spark.conf.get('partitions')"], "correct_index": 0, "explanation": "getNumPartitions() 直接返回当前分区数，是看清并行度的入口。", "dimension": "apply"},
        {"type": "single_choice", "prompt": "关于分区与 HDFS block，正确的是？", "options": ["分区数一定等于 block 数", "分区与 block 不是 1:1，输入格式/算子会改变分区数", "block 就是分区", "分区由 Driver 决定与 block 无关"], "correct_index": 1, "explanation": "默认分区可能按 block 数给，但 repartition / 不同输入格式会改变它，二者非 1:1。", "dimension": "comparison"},
        {"type": "single_choice", "prompt": "分区是以下哪种？", "options": ["逻辑切分（由 partitioner/输入切片决定）", "把文件在磁盘上物理劈成几块", "Driver 内存中的对象", "网络带宽的单位"], "correct_index": 0, "explanation": "分区是逻辑切片，由 partitioner 或输入格式决定，文件在磁盘上并未被物理劈开。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "为什么「分区数不影响结果正确性」？", "options": ["切 2 份还是 200 份答案一样，只影响快慢", "分区数越多结果越准", "分区决定算法", "分区只影响显示"], "correct_index": 0, "explanation": "分区只决定数据怎么分布并行，不改变计算结果，只影响性能。", "dimension": "why"},
        {"type": "single_choice", "prompt": "repartition(200) 后 count()，大约产生几个 Task？", "options": ["约 200 个", "1 个", "2 个", "0 个"], "correct_index": 0, "explanation": "分区数改为 200，Action 时约 200 个 Task 并行，每个 Task 处理一个分区。", "dimension": "mechanism"},
        {"type": "single_choice", "prompt": "想减少「不必要的分区误解」，该怎么做？", "options": ["用 getNumPartitions() 看真实分区数", "直接默认 block 数就是分区数", "凭感觉设分区数", "认为分区越多越准"], "correct_index": 0, "explanation": "分区可能受算子/格式影响，应实际查看而非拍脑袋。", "dimension": "apply"},
        {"type": "single_choice", "prompt": "关于「分区 vs 文件物理块」，正确的是？", "options": ["分区是逻辑视图，文件未被物理劈开", "分区一定等于物理文件块", "分区在 Driver 内存", "分区是网络概念"], "correct_index": 0, "explanation": "分区是「怎么读/怎么分配」的逻辑视图，不是磁盘切割。", "dimension": "comparison"}
    ]},
    {"lesson_slug": "l5-partition-count-parallelism", "questions": [
        {"type": "single_choice", "prompt": "「并行度」在 Spark 中约等于？", "options": ["该 Stage 的分区数（Task 数）", "Executor 的硬盘大小", "SQL 行数", "网络带宽"], "correct_index": 0, "explanation": "并行度 = 同时执行的 Task 数 = 该 Stage 的分区数。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "为什么分区数太少会慢？", "options": ["Executor 闲置或单 Task 过大（长尾/OOM）", "分区少结果算错", "分区少必 Shuffle", "分区少网络更堵"], "correct_index": 0, "explanation": "分区远少于核数时算力闲置；单分区过大则长尾任务、易 OOM。", "dimension": "why"},
        {"type": "single_choice", "prompt": "写下 df.repartition(10000).count() 会发生什么？", "options": ["起 1 万个 Task，多数只处理几 KB，调度开销反噬", "只起 1 个 Task", "结果变准", "不切分区"], "correct_index": 0, "explanation": "海量小 Task 的调度/启动开销可能超过计算本身，且易产生小文件。", "dimension": "mechanism"},
        {"type": "single_choice", "prompt": "想避免「百核集群 98 核闲置」，应该？", "options": ["让分区数匹配集群并行能力（合理设置分区数）", "把分区降到 1", "增加 block 数硬凑", "无能为力"], "correct_index": 0, "explanation": "分区数应大致匹配可用并行度，否则资源浪费（具体最优值调优留 L7）。", "dimension": "apply"},
        {"type": "single_choice", "prompt": "关于「分区数 vs 结果正确性」，正确的是？", "options": ["只影响性能，不影响正确性", "分区数决定答案", "分区少答案错", "分区多答案才对"], "correct_index": 0, "explanation": "分区是性能旋钮，不是正确性旋钮。", "dimension": "comparison"},
        {"type": "single_choice", "prompt": "默认 shuffle 分区数（spark.sql.shuffle.partitions）通常是？", "options": ["200（默认值，非最优保证）", "1", "等于核数", "无限"], "correct_index": 0, "explanation": "默认 200，只是默认值，是否适合你的数据需结合规模判断（调优留 L7）。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "为什么本课不给「最优分区数经验公式」？", "options": ["最优值取决于数据量/核数/记录大小，是 L7 调优主题", "公式不存在", "作者忘了", "Spark 自动完美"], "correct_index": 0, "explanation": "最优分区数依数据和集群而定，本课只建原理直觉，定量调优留 L7。", "dimension": "why"},
        {"type": "single_choice", "prompt": "分区太多除了调度开销，还容易带来？", "options": ["海量小文件（每 Task 一个输出）", "结果错误", "必然 Shuffle", "内存溢出到 Driver"], "correct_index": 0, "explanation": "每个 Task 通常产生一个输出文件，分区过多易产生小文件问题。", "dimension": "mechanism"},
        {"type": "single_choice", "prompt": "评估一段作业是否「分区过少」应看？", "options": ["任务并行度是否远低于可用核数", "文件大小", "SQL 行数", "网络延迟"], "correct_index": 0, "explanation": "并行度（Task 数）远低于核数即资源浪费，是分区过少的信号。", "dimension": "apply"},
        {"type": "single_choice", "prompt": "关于「分区越多越并行越快」，正确的是？", "options": ["不一定，太多调度开销反噬", "永远成立", "分区与并行无关", "只影响正确性"], "correct_index": 0, "explanation": "分区数是平衡杠杆，不是越大越好。", "dimension": "comparison"}
    ]},
    {"lesson_slug": "l5-what-is-shuffle", "questions": [
        {"type": "single_choice", "prompt": "Shuffle 最准确的定位是？", "options": ["跨节点按 key 重新分布数据", "把文件物理劈开", "Driver 中转数据", "一种排序算法"], "correct_index": 0, "explanation": "Shuffle 是宽依赖时跨节点按 key 重分布数据的物理过程。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "为什么 groupBy / join / orderBy 会触发 Shuffle？", "options": ["需要全局按 key 汇聚 / 全局有序，必须跨节点重排", "它们写错了", "Driver 要求", "为了显示进度"], "correct_index": 0, "explanation": "这些操作需要「全局按 key 汇聚或全局有序」，无法在本地完成，必须跨节点重排。", "dimension": "why"},
        {"type": "single_choice", "prompt": "写下 df.groupBy('city').count() 触发 Action 后，Shuffle 阶段发生什么？", "options": ["按 city 哈希、序列化、跨网络发到目标 Executor、反序列化归并", "数据回 Driver 再分发", "不移动数据", "只排序不传输"], "correct_index": 0, "explanation": "map 端按 key 分区/combine、序列化、网络传输到目标端、反序列化归并，完成跨节点重排。", "dimension": "mechanism"},
        {"type": "single_choice", "prompt": "在计划里认出 Shuffle，应该看哪个节点？", "options": ["Exchange", "Scan", "Project", "Filter"], "correct_index": 0, "explanation": "Exchange 节点就是 Shuffle 的物理信号，复用 L4 的读法。", "dimension": "apply"},
        {"type": "single_choice", "prompt": "关于 Shuffle 与宽依赖，正确的是？", "options": ["Shuffle 是宽依赖的物化，不是错误", "Shuffle 是写错代码", "宽依赖不 Shuffle", "Shuffle 只发生在 Driver"], "correct_index": 0, "explanation": "只要计算需全局按 key 汇聚，Shuffle 必然发生，它是代价不是错误。", "dimension": "comparison"},
        {"type": "single_choice", "prompt": "Shuffle 发生时数据在谁之间传输？", "options": ["Executor 之间直接互传", "先回 Driver 再分发", "只在磁盘内", "经网络到客户端"], "correct_index": 0, "explanation": "Shuffle 是 Executor 之间跨节点互传，Driver 不抱数据。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "为什么 Shuffle 是「某些操作特别慢」的根源？", "options": ["它涉及跨节点重分布（序列化+网络+反序列化+排序）", "它不改代码", "它只排序", "它很快"], "correct_index": 0, "explanation": "跨节点重分布带来多环节开销，是作业中最昂贵的操作之一。", "dimension": "why"},
        {"type": "single_choice", "prompt": "df.groupBy('city').count().explain() 会显示几个 Stage？", "options": ["2 个（1 次 Shuffle 切出）", "1 个", "0 个", "10 个"], "correct_index": 0, "explanation": "1 次 Exchange（Shuffle）→ 2 个 Stage（本地预聚合 / 跨节点合并）。", "dimension": "mechanism"},
        {"type": "single_choice", "prompt": "看到代码里有 Exchange，第一反应应是？", "options": ["注意这是 Shuffle，是性能重点信号", "代码写错了", "结果会错", "无需关心"], "correct_index": 0, "explanation": "Exchange = Shuffle，是性能重点信号，但未必是错误。", "dimension": "apply"},
        {"type": "single_choice", "prompt": "关于「Shuffle 能否避免」，正确的是？", "options": ["需要全局汇聚时必然发生，躲不掉（除非无需汇聚）", "永远可避免", "永远无法发生", "只有 join 才 Shuffle"], "correct_index": 0, "explanation": "宽依赖的必然代价，需要全局按 key 汇聚时无法避免。", "dimension": "comparison"}
    ]},
    {"lesson_slug": "l5-shuffle-cost", "questions": [
        {"type": "single_choice", "prompt": "Shuffle 代价主要来自哪些环节？", "options": ["序列化 → 网络传输 → 反序列化 → 排序/聚合", "只排序", "只读取", "只写磁盘"], "correct_index": 0, "explanation": "Shuffle 跨节点重排涉及序列化、网络、反序列化、排序/聚合多环节开销。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "为什么 Shuffle 比「内存里挪一下数据」贵得多？", "options": ["它跨网络、要序列化/反序列化、可能 spill 磁盘", "它不改变数据", "它只排序", "它很快"], "correct_index": 0, "explanation": "Shuffle 是多环节重活，涉及网络与序列化，还可能 spill，远非零成本内存操作。", "dimension": "why"},
        {"type": "single_choice", "prompt": "写下 df.groupBy('city').sum('amount')，Shuffle 在 map/reduce 端各做什么？", "options": ["map 端分区+排序+combine，reduce 端 fetch+反序列化+归并", "两端都不动", "只 reduce 端排序", "只 map 端读"], "correct_index": 0, "explanation": "map 端按 key 分区、排序/combine、写块；reduce 端 fetch、反序列化、归并。", "dimension": "mechanism"},
        {"type": "single_choice", "prompt": "想直观感受 Shuffle 代价，看计划里哪个节点？", "options": ["Exchange（背后即序列化+网络+重排）", "Scan", "Project", "Filter"], "correct_index": 0, "explanation": "Exchange 即 Shuffle，其背后是一串跨节点开销。", "dimension": "apply"},
        {"type": "single_choice", "prompt": "关于 spill 到磁盘，正确的是？", "options": ["内存不足时 spill，磁盘 I/O 慢几个数量级，放大代价", "spill 让 Shuffle 更快", "spill 不会发生", "spill 只影响显示"], "correct_index": 0, "explanation": "spill 把中间结果写磁盘，I/O 远慢于内存，是 Shuffle 贵的重要放大器。", "dimension": "comparison"},
        {"type": "single_choice", "prompt": "本课对 spark.shuffle.file.buffer / compression 等参数怎么处理？", "options": ["只讲原理，具体调优参数留 Level 7", "本课就教怎么调", "不需要这些参数", "参数已最优"], "correct_index": 0, "explanation": "本课只建立「贵在哪」的原理直觉，具体调优参数留 L7。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "数据倾斜为什么会放大 Shuffle 代价？", "options": ["少数 key 的货极多，单节点被压垮拖慢整体", "倾斜让 Shuffle 消失", "倾斜只影响显示", "倾斜加快网络"], "correct_index": 0, "explanation": "倾斜时某些 key 的 Shuffle 块远超其他，单节点瓶颈拖垮整体（调优留 L7）。", "dimension": "why"},
        {"type": "single_choice", "prompt": "reduce 端拉取（fetch）属于 Shuffle 的哪类开销？", "options": ["网络传输环节（跨节点拉取自己负责的分区）", "本地排序", "Driver 计算", "结果显示"], "correct_index": 0, "explanation": "reduce 端通过网络 fetch 属于自己的分区数据，是网络传输环节。", "dimension": "mechanism"},
        {"type": "single_choice", "prompt": "评估一段作业是否受 Shuffle 主导，应关注？", "options": ["Exchange 数量与数据量（计划/UI）", "文件大小", "SQL 长度", "显示效果"], "correct_index": 0, "explanation": "Shuffle 主导的作业通常 Exchange 多、传输量大，可在计划与 Spark UI 观察。", "dimension": "apply"},
        {"type": "single_choice", "prompt": "关于 Shuffle 代价环节，正确的是？", "options": ["map 端排序+combine，reduce 端 fetch+归并，都花钱", "只有网络花钱", "只有排序花钱", "都不花钱"], "correct_index": 0, "explanation": "排序、combine、序列化、网络、归并每个环节在大数据量下都可能是瓶颈。", "dimension": "comparison"}
    ]},
    {"lesson_slug": "l5-narrow-wide-partition", "questions": [
        {"type": "single_choice", "prompt": "在分区层面，窄依赖意味着？", "options": ["子分区只依赖父局部分区，无需重排", "子分区依赖父全部分区", "必 Shuffle", "跨节点"], "correct_index": 0, "explanation": "窄依赖中子分区只由有限个（通常 1 个）父分区计算，无需跨节点重排。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "为什么宽依赖处必然切 Stage？", "options": ["子分区要等所有上游同 key 货到齐，天然跨节点", "宽依赖更快", "宽依赖无 Shuffle", "随机切"], "correct_index": 0, "explanation": "宽依赖的子分区依赖全局同 key 数据，必须跨节点重分布，无法留在同一段连续工序。", "dimension": "why"},
        {"type": "single_choice", "prompt": "写下 df.filter(...).select(...) 与 df.groupBy('city').count()，Stage 划分有何不同？", "options": ["前者无 Exchange 同 Stage，后者有 Exchange 切 Stage", "两者都切 Stage", "两者都不切", "前者切后者不切"], "correct_index": 0, "explanation": "filter/select 是窄依赖，同 Stage 融合；groupBy 是宽依赖，Exchange 处切 Stage。", "dimension": "mechanism"},
        {"type": "single_choice", "prompt": "想判断「分区会不会被重分配」，应看？", "options": ["依赖类型（窄/宽）与是否需全局重分布", "文件大小", "SQL 行数", "显示设置"], "correct_index": 0, "explanation": "宽依赖（需全局按 key 汇聚）才会重分配分区，窄依赖就地处理。", "dimension": "apply"},
        {"type": "single_choice", "prompt": "关于「Stage 边界 = Shuffle 切口」，正确的是？", "options": ["宽依赖处的 Shuffle 就是 Stage 边界", "窄依赖切 Stage", "Stage 由 Executor 数决定", "Stage 与 Shuffle 无关"], "correct_index": 0, "explanation": "宽依赖处的 Exchange（Shuffle）即 Stage 边界，也是融合断点。", "dimension": "comparison"},
        {"type": "single_choice", "prompt": "L5 对窄/宽依赖的「定义」怎么处理？", "options": ["定义 L4 已讲，L5 只延展到分区物化与 Stage 切口", "L5 重讲定义", "定义已过时", "不再提及"], "correct_index": 0, "explanation": "L5 重点在分区如何被重新分配与 Stage 边界，不重复 L4 定义。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "为什么宽依赖失败恢复比窄依赖贵？", "options": ["下游依赖全局重排，上游任何分区丢都要整体重算", "宽依赖不恢复", "一样贵", "窄依赖更贵"], "correct_index": 0, "explanation": "宽依赖下游依赖全局按 key 汇聚，上游丢失需整体重算，代价大（呼应 L4）。", "dimension": "why"},
        {"type": "single_choice", "prompt": "groupBy 在分区层面属于？", "options": ["宽依赖，父分区数据发往多个子分区（必 Shuffle）", "窄依赖", "不分配", "本地"], "correct_index": 0, "explanation": "groupBy 需跨节点按 key 重分布，父分区数据发往多个子分区。", "dimension": "mechanism"},
        {"type": "single_choice", "prompt": "评估「某算子是否切 Stage」应看？", "options": ["有没有 Exchange（宽依赖），而非算子数量", "代码行数", "文件数", "显示效果"], "correct_index": 0, "explanation": "只有宽依赖（Exchange）切 Stage，窄算子在同一 Stage 融合。", "dimension": "apply"},
        {"type": "single_choice", "prompt": "关于窄依赖与分区，正确的是？", "options": ["父→子分区是局部分配，无跨节点重排", "窄依赖也跨节点", "窄依赖必 Shuffle", "窄依赖切 Stage"], "correct_index": 0, "explanation": "窄依赖中父→子分区是局部分配，不触发跨节点重分布。", "dimension": "comparison"}
    ]},
    {"lesson_slug": "l5-shuffle-trigger-operators", "questions": [
        {"type": "single_choice", "prompt": "以下哪组算子通常一定触发 Shuffle？", "options": ["groupBy / orderBy / distinct / join", "select / filter / map", "union（同 schema）", "cache"], "correct_index": 0, "explanation": "这些操作需全局按 key 汇聚或全局有序，必然或通常触发 Shuffle。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "判断一个算子是否 Shuffle 的真正判据是？", "options": ["是否需要全局按 key 汇聚 / 全局有序", "算子名字好不好听", "代码行数", "是否用了 SQL"], "correct_index": 0, "explanation": "是否需全局重分布才是判据，不是算子名本身。", "dimension": "why"},
        {"type": "single_choice", "prompt": "写下 dfA.join(dfB, 'id').explain()，计划里出现什么？", "options": ["Exchange（两表按 id 重分布，Shuffle）", "无 Exchange", "只在 Driver 算", "不重排"], "correct_index": 0, "explanation": "join 按 key 重分布两表，产生 Exchange（Shuffle）。", "dimension": "mechanism"},
        {"type": "single_choice", "prompt": "想减少不必要的 Shuffle，第一步该？", "options": ["认出触发 Shuffle 的算子清单", "加大内存", "加分区", "改 SQL 方言"], "correct_index": 0, "explanation": "先认得哪些操作会叫空中货运，才能有意识地避开不必要的飞货。", "dimension": "apply"},
        {"type": "single_choice", "prompt": "关于 union（同 schema），正确的是？", "options": ["通常只拼接分区，不 Shuffle", "一定 Shuffle", "比 join 更易 Shuffle", "必须排序"], "correct_index": 0, "explanation": "同 schema union 只是拼接分区，通常不触发 Shuffle。", "dimension": "comparison"},
        {"type": "single_choice", "prompt": "本课对 join 的策略（broadcast/sort-merge）怎么处理？", "options": ["只点 join 是宽依赖会 Shuffle，深类型留 Level 6", "本课展开所有 join 策略", "join 不 Shuffle", "join 只 broadcast"], "correct_index": 0, "explanation": "join 深类型（broadcast 等怎么选）是 Level 6 内容，本课只点「会 Shuffle」。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "为什么 repartition 会 Shuffle？", "options": ["它强制跨节点重分布数据", "它只读数据", "它排序不重排", "它不移动数据"], "correct_index": 0, "explanation": "repartition 通过对数据 hash 重分布改分区数，必然触发 Shuffle。", "dimension": "why"},
        {"type": "single_choice", "prompt": "reduceByKey / aggregateByKey 通常属于？", "options": ["按 key，通常需跨节点合并（Shuffle）", "绝不 Shuffle", "只本地", "只排序"], "correct_index": 0, "explanation": "按 key 的聚合通常需在 reduce 端跨节点合并，属 Shuffle 算子。", "dimension": "mechanism"},
        {"type": "single_choice", "prompt": "评估「某个可能 Shuffle 的算子是否真 Shuffle」，应看？", "options": ["计划里有无 Exchange，取决于上游分区分布", "只听名字", "文件大小", "显示设置"], "correct_index": 0, "explanation": "是否实际 Shuffle 取决于上游是否已是目标分区分布，看计划最准。", "dimension": "apply"},
        {"type": "single_choice", "prompt": "关于「触发 Shuffle 的清单」，正确的是？", "options": ["是『需要全局重分布』的算子集合，非死记名字", "背名字即可无需理解", "只有 groupBy", "只有 join"], "correct_index": 0, "explanation": "清单的本质是「需全局按 key 汇聚/有序」，理解判据比背名字重要。", "dimension": "comparison"}
    ]},
    {"lesson_slug": "l5-reducebykey-vs-groupbykey", "questions": [
        {"type": "single_choice", "prompt": "reduceByKey 比 groupByKey 省 Shuffle 的根本原因是？", "options": ["map 端先做本地 combine，传输量小", "reduceByKey 不 Shuffle", "groupByKey 排序", "reduceByKey 更快的网络"], "correct_index": 0, "explanation": "reduceByKey 在 map 端本地聚合（combine），只传部分和，跨网络传输量远小于原始记录数。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "为什么 groupByKey 传输量大？", "options": ["不做 combine，所有 value 原样 Shuffle", "它不聚合", "它只排序", "它更快"], "correct_index": 0, "explanation": "groupByKey 不做 map 端 combine，每个 key 的全部 value 原样飞到目标端再分组。", "dimension": "why"},
        {"type": "single_choice", "prompt": "写下 rdd.map(...).reduceByKey(_+_) 触发 Action 时，map 端发生什么？", "options": ["同 key 先在本地相加成部分和，再 Shuffle 部分和", "所有 value 原样飞走", "不聚合", "只排序"], "correct_index": 0, "explanation": "每个 Executor 先在本地把同 key 的 value 相加成部分和，Shuffle 时只传这些部分和。", "dimension": "mechanism"},
        {"type": "single_choice", "prompt": "可换的聚合优先用哪个以减少飞货？", "options": ["reduceByKey / aggregateByKey", "groupByKey", "collect 后 Python 算", "不限"], "correct_index": 0, "explanation": "可换的聚合优先 reduceByKey / aggregateByKey，利用 map 端 combine 省传输。", "dimension": "apply"},
        {"type": "single_choice", "prompt": "关于 combine 的前提，正确的是？", "options": ["聚合函数须可交换、可结合（如 sum/min/max）", "任何聚合都能 combine", "只有 groupByKey 能 combine", "combine 不需要前提"], "correct_index": 0, "explanation": "只有可交换可结合的聚合才能安全地在 map 端预聚合，否则会算错。", "dimension": "comparison"},
        {"type": "single_choice", "prompt": "reduceByKey 是否完全消除 Shuffle？", "options": ["否，仍有一次 Shuffle，只是传输量小", "是，零 Shuffle", "从不 Shuffle", "只排序不 Shuffle"], "correct_index": 0, "explanation": "reduceByKey 优化的是 Shuffle 传输体积，仍至少有一次 Shuffle。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "为什么不能对所有聚合都用 map 端 combine？", "options": ["依赖全局顺序的聚合不可结合（如中位数）", "combine 总是错", "Spark 不支持", "只有 sum 能用"], "correct_index": 0, "explanation": "依赖全局顺序的聚合不满足可结合性，本地先聚合会得到错误结果。", "dimension": "why"},
        {"type": "single_choice", "prompt": "groupByKey 在 Shuffle 阶段传输的是什么？", "options": ["每个 key 的全部 value（原样）", "部分和", "只 key", "排序结果"], "correct_index": 0, "explanation": "groupByKey 不做 combine，传输量 = 原始 value 总数。", "dimension": "mechanism"},
        {"type": "single_choice", "prompt": "评估「能否用 reduceByKey 替代 groupByKey」，应看？", "options": ["聚合是否可交换可结合", "文件大小", "SQL 长度", "显示设置"], "correct_index": 0, "explanation": "可换的聚合（sum/min/max 等）可改 reduceByKey 省飞货；不可结合的不能。", "dimension": "apply"},
        {"type": "single_choice", "prompt": "关于本课 tuning 代码（partitioner/分区数），正确的是？", "options": ["只讲原理，调优代码留 Level 7", "本课就教怎么调最优", "不需要", "已最优"], "correct_index": 0, "explanation": "本课只讲「为什么 reduceByKey 更省」，设 partitioner/调分区数留 L7。", "dimension": "comparison"}
    ]},
    {"lesson_slug": "l5-repartition-coalesce", "questions": [
        {"type": "single_choice", "prompt": "repartition 与 coalesce 的核心区别是？", "options": ["repartition 必 Shuffle 可增可减；coalesce 默认不 Shuffle 只能减", "两者都必 Shuffle", "两者都不 Shuffle", "coalesce 能增分区"], "correct_index": 0, "explanation": "repartition 一定 Shuffle、可增可减；coalesce 默认窄合并不 Shuffle、只能减。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "为什么「想减分区又不想白付 Shuffle」选 coalesce？", "options": ["coalesce 默认走窄依赖合并，不触发 Shuffle", "coalesce 更快的网络", "repartition 不能减", "coalesce 必 Shuffle"], "correct_index": 0, "explanation": "coalesce 默认 shuffle=False，合并相邻分区，不触发 Shuffle，适合纯减分区。", "dimension": "why"},
        {"type": "single_choice", "prompt": "写下 df.repartition(200) 与 df.coalesce(2)，计划里 Exchange 有何不同？", "options": ["repartition 有 Exchange（Shuffle），coalesce 无", "两者都有", "两者都无", "coalesce 有 repartition 无"], "correct_index": 0, "explanation": "repartition 必产生 Exchange；coalesce 默认不 Shuffle，无 Exchange。", "dimension": "mechanism"},
        {"type": "single_choice", "prompt": "想增加分区数，应该用？", "options": ["repartition（coalesce 不能增）", "coalesce", "limit", "cache"], "correct_index": 0, "explanation": "coalesce 只合并、不能凭空增多分区，增分区必须用 repartition。", "dimension": "apply"},
        {"type": "single_choice", "prompt": "关于 coalesce 不能增分区，正确的是？", "options": ["它只合并现有分区，无法创造新分区", "它能增但很慢", "它能随意增", "增分区用 coalesce"], "correct_index": 0, "explanation": "coalesce 是合并操作，分区数只能减少不能增加。", "dimension": "comparison"},
        {"type": "single_choice", "prompt": "repartition(n) 是否会触发 Shuffle？", "options": ["一定触发（无论增还是减）", "从不", "只在减时", "只在增时"], "correct_index": 0, "explanation": "repartition 通过 hash 重分布改分区数，任何方向都付一次 Shuffle。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "为什么 repartition 任何方向都 Shuffle？", "options": ["它要对数据做 hash 重分布到新分区数", "它读数据", "它只排序", "它不移动"], "correct_index": 0, "explanation": "repartition 必须跨节点重分布数据以达到目标分区数，必然 Shuffle。", "dimension": "why"},
        {"type": "single_choice", "prompt": "coalesce 跨节点合并时，数据会怎样？", "options": ["仍可能移动数据（shuffle=False 主要同节点合并）", "绝对零移动", "必回 Driver", "只排序"], "correct_index": 0, "explanation": "coalesce 默认同节点合并，但跨节点合并仍可能移动数据，并非绝对零移动。", "dimension": "mechanism"},
        {"type": "single_choice", "prompt": "评估「减分区该用哪个」，应看？", "options": ["是否想避免 Shuffle → 优先 coalesce", "文件大小", "SQL 长度", "显示设置"], "correct_index": 0, "explanation": "纯减分区且不想付 Shuffle，优先 coalesce。", "dimension": "apply"},
        {"type": "single_choice", "prompt": "关于两者与不可变语义，正确的是？", "options": ["都返回新 DataFrame，原 DataFrame 不变", "会改原 DataFrame", "两者都改原", "不支持链式"], "correct_index": 0, "explanation": "repartition/coalesce 都返回新的 DataFrame，遵循不可变语义。", "dimension": "comparison"}
    ]},
    {"lesson_slug": "l5-comprehensive", "questions": [
        {"type": "single_choice", "prompt": "综合读图的第一步是？", "options": ["找 Shuffle（空中飞货：groupBy/orderBy/join）", "数 Task", "打开 UI", "改代码"], "correct_index": 0, "explanation": "先找触发 Shuffle 的算子，它们是性能重点信号与 Stage 边界。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "数 Stage 的公式是？", "options": ["Shuffle 数 + 1", "分区数", "Task 数", "Action 数"], "correct_index": 0, "explanation": "Stage 数 = Shuffle（Exchange）数 + 1。", "dimension": "apply"},
        {"type": "single_choice", "prompt": "一段 logs.groupBy('city').count().orderBy(desc).limit(10) 通常有几处 Shuffle？", "options": ["2（groupBy + orderBy；limit 不 Shuffle）", "1", "3", "0"], "correct_index": 0, "explanation": "groupBy 与 orderBy 各一处 Exchange，limit 不 Shuffle，共 2 处。", "dimension": "mechanism"},
        {"type": "single_choice", "prompt": "如何估计一段作业的并行度？", "options": ["看分区数（Task 数 = 分区数）", "看 SQL 行数", "看文件大小", "看显示"], "correct_index": 0, "explanation": "并行度 ≈ 该 Stage 的分区数，即 Task 数。", "dimension": "apply"},
        {"type": "single_choice", "prompt": "为什么「计划相同 ≠ 运行时性能相同」？", "options": ["数据倾斜、分区数等运行时因素影响真实耗时", "计划本身有错", "两者无关", "Spark 随机变慢"], "correct_index": 0, "explanation": "同样计划在不同数据分布/分区数下真实耗时差异大，倾斜等是运行时因素（L7）。", "dimension": "why"},
        {"type": "single_choice", "prompt": "Level 5 综合练习的达标标准是？", "options": ["读懂：认 Shuffle、数 Stage、估并行度、指出 reduceByKey 优化点", "把代码改快", "完全重写", "立即调优"], "correct_index": 0, "explanation": "综合只验收「看得懂分区与 Shuffle、能识别触发点」，不要求调优。", "dimension": "comparison"},
        {"type": "single_choice", "prompt": "看到 groupByKey 后 sum，可指出什么优化点（原理）？", "options": ["改用 reduceByKey 类做 map 端 combine，减少飞货", "加大内存", "加分区", "改 SQL 方言"], "correct_index": 0, "explanation": "可换的聚合优先 reduceByKey，利用 combine 省 Shuffle（只点原理，不写 tuning）。", "dimension": "mechanism"},
        {"type": "single_choice", "prompt": "综合读图练习用什么工具最划算？", "options": ["explain()（不执行，零成本）", "show()", "write()", "collect()"], "correct_index": 0, "explanation": "explain() 不触发执行，是随时可做、零成本的读图手段。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "关于「综合练习与调优」，正确的是？", "options": ["综合只验读懂，调优留 L6/L7", "必须当场调优", "不用读图", "读图无用"], "correct_index": 0, "explanation": "本课目标是「看得懂分区与 Shuffle」，定量调优在 L6（Join）/L7（性能）。", "dimension": "comparison"},
        {"type": "single_choice", "prompt": "数 Stage 时容易漏算什么？", "options": ["初始 Stage（Stage 数 = Shuffle 数 + 1，从 1 起算）", "最后的 Stage", "中间的 Stage", "都不易漏"], "correct_index": 0, "explanation": "易漏「初始 Stage」，记住从 1 开始加，Shuffle 数 + 1。", "dimension": "mechanism"}
    ]}
]


def upsert():
    # 1) 合并进 course_seed.json
    with open(SEED, encoding="utf-8") as f:
        data = json.load(f)
    exists = any(lv.get("order_index") == 5 for lv in data["levels"])
    if not exists:
        data["levels"].append(LEVEL5)
        with open(SEED, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print("已写入 course_seed.json（Level 5）")
    else:
        print("course_seed.json 已存在 Level 5，跳过 JSON 写入")

    # 2) 合并进 quiz_seed.json
    with open(QUIZ, encoding="utf-8") as f:
        qdata = json.load(f)
    qentries = qdata.setdefault("quizzes", [])
    existing = {e["lesson_slug"] for e in qentries}
    added_q = 0
    for entry in LEVEL5_QUIZZES:
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
        print("quiz_seed.json 已包含 Level 5 题库，跳过")

    # 3) upsert 进数据库
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT id,title FROM course_levels WHERE order_index=5")
    row = cur.fetchone()
    if row:
        level_id = row[0]
        print(f"Level 5 已存在于 DB (id={level_id})，仅补充缺失 lesson")
    else:
        cur.execute(
            "INSERT INTO course_levels (title, description, order_index, status) VALUES (?,?,?,?)",
            (LEVEL5["title"], LEVEL5["description"], LEVEL5["order_index"], "active"))
        level_id = cur.lastrowid
        print(f"已插入 Level 5 (id={level_id})")

    inserted_lessons = 0
    for ls in LEVEL5["lessons"]:
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
    for entry in LEVEL5_QUIZZES:
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
