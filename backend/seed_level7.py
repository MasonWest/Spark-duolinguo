# -*- coding: utf-8 -*-
"""一次性脚本：把 Level 7（性能调优，9 课）合并进 course_seed.json 与 quiz_seed.json，
并幂等地 upsert 进 spark_quest.db 的 course_levels / lessons / quizzes 表。
不修改 Level 0/1/2/3/4/5/6 与已有的 lesson_mastery 进度数据。

运行：cd backend && python seed_level7.py
"""
import sqlite3, json, os

BASE = os.path.dirname(os.path.abspath(__file__))
SEED = os.path.join(BASE, "app", "course_seed.json")
QUIZ = os.path.join(BASE, "app", "quiz_seed.json")
DB = os.path.join(BASE, "spark_quest.db")

LEVEL7 = {
    "title": "Level 7：性能调优",
    "description": "教读者「怎么让 Spark 作业真的跑得快」——把 Level 3 埋下的 UDF 慢、Level 4 埋下的 Tungsten/WholeStageCodegen 内存细节、Level 5 埋下的 shuffle 分区数与 spill、Level 6 埋下的广播阈值与 skew 深调优，全部收口到一套「先度量、再定位瓶颈、改一处、复测」的调优方法论。覆盖调优方法论、Tungsten 编码字节级与堆外、Executor 内存模型与 OOM 根因、shuffle 分区数怎么定、广播阈值调优、AQE 自适应查询执行、数据倾斜实战处理、少读少传少算、综合诊断清单。明确不越界到集群运维（YARN/K8s 资源队列、动态资源分配）、不展开 GC 调优、不给万能最优参数值。",
    "order_index": 7,
    "lessons": [
        {
            "title": "性能调优是什么（度量驱动的闭环）",
            "slug": "l7-what-is-tuning",
            "description": "建立调优方法论：先度量找瓶颈 → 改一处 → 复测验证；认识常见瓶颈位置（读太多 / 传太多 / 内存不够 / 倾斜 / CPU 开销）。",
            "objective": "学完本课，你应该能够：说清性能调优是「度量驱动的闭环」而非「堆参数」；列举五类常见瓶颈（读太多 / 传太多 / 内存不够 / 倾斜 / CPU 开销）及其典型症状；知道用 Spark UI 与 explain 做度量、按「改一处、测一次」的节奏推进；理解本课只建方法论，具体旋钮在第 4–8 课，且集群资源层（YARN/K8s 队列、动态资源分配）不在本课程范围。",
            "estimated_minutes": 13,
            "order_index": 0,
            "prerequisites": "",
            "content": {
                "explanation": "【先用人话理解】\n\n很多人的调优方式是「听说这个参数能提速，加上试试」。这跟生病不去检查、专吃偏方一个道理。Spark 的调优只有一条正路：**先量出来哪里慢，改那一处，再量一次看有没有变好**。\n\n【一个直观的心智模型】\n\n复用 L4/L5 的「工厂流水线」：整条线的产出速度由**最慢的那道工序**决定（木桶效应）。\n- 你把 10 道工序里的 9 道都提速一倍，只要第 10 道没动，总耗时几乎不变；\n- 所以第一步永远是**找出那道最慢的工序**，而不是全线提速；\n- 找到之后**只改一处、测一次**——一次改五个参数，变快了你也不知道是谁的功劳，变慢了你得一个个退回去。\n\n⚠️ 比喻的边界（很重要）：\n① 「最慢的那道工序」在 Spark 里可能是**一个 Stage、甚至一个 Task**——两个 Stage 的计划一模一样，一个 30 秒、一个 40 分钟（倾斜），所以只看计划不够，得看运行时分布。\n② 瓶颈不是固定的：你把 Shuffle 减半之后，瓶颈可能就转移到读取或 CPU 上了，所以要**重新度量**。\n③ 调优的上限是「数据规模」本身：能不读的数据就别读（第 8 课），这比任何参数都有效——减量优先于调速。\n④ 集群层面的事（队列配额、节点数、动态资源分配）是运维的地盘，本课只讲你**在自己作业里能改的东西**。\n\n【正式的技术定义】\n\n性能调优（Performance Tuning）是针对具体作业，通过度量定位瓶颈、施加最小改动、复测验证的迭代过程。Spark 作业的主要瓶颈类别：\n- **读太多**：扫描了不需要的列 / 分区 / 文件（对应第 8 课的减量手段）；\n- **传太多**：Shuffle 数据量大、次数多（复用 L5 空中飞货、L6 JOIN 策略）；\n- **内存不够**：spill 到磁盘、Executor OOM（第 3 课）；\n- **倾斜**：少数 Task 数据量爆炸、长尾拖尾（第 7 课）；\n- **CPU 开销**：UDF 跨 JVM 序列化、复杂表达式、重复计算（复用 L3 UDF 伏笔）。\n度量的两个基本工具：`explain()`（看计划，零成本，复用 L4）与 Spark UI（看运行时：各 Stage/Task 的耗时、Shuffle 读写量、spill 情况）。\n\n【写下代码后，Spark 内部发生了什么】\n\n你运行 `df.groupBy('city').count().show()` 并觉得慢，正确的动作序列是：\n1. `explain()` 看计划：找 Exchange 有几处、有没有走广播、有没有谓词下推（这一步不执行，零成本）；\n2. 打开 Spark UI（作业运行时 `http://<driver>:4040`）：看哪个 Stage 最慢、Task 耗时是否均匀、Shuffle Read/Write 有多大、有没有 spill；\n3. 归类是「读太多 / 传太多 / 内存 / 倾斜 / CPU」中的哪一类；\n4. **只改一处**，重跑，对比耗时；\n5. 有改善就保留并回到第 1 步重新找下一个瓶颈，没改善就回滚换思路。\n这套闭环，就是本课程后面八课要逐个填充的「诊断 → 处方」对照表。",
                "examples": [
                    {
                        "title": "第一步：零成本看计划",
                        "code": "df.groupBy('city').count().explain()\n# 找三样东西：Exchange 有几处、有没有 BroadcastExchange、过滤有没有下推",
                        "note": "explain 不执行（复用 L4），是成本最低的第一步，任何慢查询都先看它。"
                    },
                    {
                        "title": "第二步：看运行时，找最慢的 Stage",
                        "code": "# 作业运行时打开 Spark UI（默认 http://<driver>:4040）\n# 看三个数：\n#   1) 哪个 Stage 耗时最长\n#   2) Task 耗时是否均匀（最大值 >> 中位数 = 倾斜嫌疑）\n#   3) Shuffle Read/Write 与 Spill 大小",
                        "note": "计划相同 ≠ 运行时相同（L4 埋下的伏笔）。分布不均只有 UI 能告诉你。"
                    },
                    {
                        "title": "第三步：一次只改一处，再测",
                        "code": "# 反例：一次改五个参数\nspark.conf.set('spark.sql.shuffle.partitions', 400)\nspark.conf.set('spark.sql.autoBroadcastJoinThreshold', 50 * 1024 * 1024)\n# ...再改三个 —— 变快了也不知道是谁的功劳\n\n# 正例：改一处 → 记录耗时 → 再改下一处",
                        "note": "参数之间是互相影响的（分区数变了，广播与否的判断也可能变），一次只动一个变量才能归因。"
                    },
                    {
                        "title": "反面教材：没度量就调参",
                        "code": "# 作业慢的真实原因：读了 200 列里的 200 列、没做分区裁剪\n# 却在那儿把 shuffle 分区从 200 调到 2000 —— 完全打偏\nspark.conf.set('spark.sql.shuffle.partitions', 2000)",
                        "note": "瓶颈在读，你去调 Shuffle，再怎么调也是白调。先量，再动。"
                    }
                ],
                "key_points": [
                    "调优 = 度量 → 定位瓶颈 → 改一处 → 复测 的闭环，不是堆参数",
                    "整条线的速度由最慢的 Stage / Task 决定；改非瓶颈处等于白改",
                    "五类瓶颈：读太多 / 传太多 / 内存不够 / 倾斜 / CPU 开销",
                    "两个度量工具：explain（看计划、零成本）+ Spark UI（看运行时分布）",
                    "减量优先于调速；集群资源层（队列/节点）属运维，不在本课范围"
                ],
                "common_mistakes": [
                    {
                        "mistake": "一上来就调 spark.sql.shuffle.partitions 这类参数，指望「调大就快」。",
                        "why": "瓶颈可能根本不在 Shuffle，而在读太多或倾斜；不度量的调参是碰运气。",
                        "fix": "先 explain + Spark UI 定位是哪一类瓶颈，再对症下药。"
                    },
                    {
                        "mistake": "一次改五个参数，跑完发现快了就全部保留。",
                        "why": "无法归因；其中某些参数可能在别的数据量下变成负担。",
                        "fix": "一次只改一处、测一次，用耗时对比决定是否保留。"
                    },
                    {
                        "mistake": "只看 explain 就认定瓶颈。",
                        "why": "计划相同 ≠ 运行时性能相同：倾斜、数据分布、spill 都只有运行时才看得见。",
                        "fix": "explain 定方向，Spark UI 定位置，两者结合。"
                    }
                ],
                "review": "Level 6 收尾时我们说：你现在能在计划里认出 JOIN 策略、懂得用广播省下大表那次昂贵的空中飞货、也认得出倾斜长尾——至于「内存里到底怎么存、分区数到底设多少、倾斜怎么系统调优」，全部留到了 Level 7。",
                "problem": "可面对一个真的跑得很慢的作业，第一步该做什么？是调参数，还是先搞清楚它慢在哪？",
                "preview": "先建方法论，再逐个拆旋钮。下集从最底层开始——Spark 在内存里到底是怎么存数据的：Tungsten 的紧凑二进制与堆外内存。"
            }
        },
        {
            "title": "Tungsten 与编码字节级",
            "slug": "l7-tungsten-encoding",
            "description": "理解 Tungsten 三件事：紧凑二进制行（UnsafeRow）、堆外内存、缓存友好计算；知道它为什么省内存、省 GC、比对象快。",
            "objective": "学完本课，你应该能够：说清 Tungsten 要解决的核心问题（JVM 对象开销与 GC）；解释紧凑二进制行（UnsafeRow）+ 堆外内存 + 缓存友好计算 + 代码生成四件事各自解决什么；知道「内存布局是逻辑 Schema 的物理实现」这一层关系（呼应 L2 Schema 边界）；并明确不展开内存管理器源码、不要求算字节偏移，实现细节随版本演进。",
            "estimated_minutes": 14,
            "order_index": 1,
            "prerequisites": "",
            "content": {
                "explanation": "【先用人话理解】\n\n在 JVM 里存一行数据，代价远比你想象的高：一个 Integer 对象除了那 4 个字节的 int，还背着对象头、引用、可能的装箱；一个短字符串可能比它本身的字符多占好几倍。数据一多，这些「包装」吃掉的 memory 比数据本身还多，而且 GC 要一遍遍扫描它们。Tungsten 项目干的事就是：**把这些包装全拆掉，直接操作字节**。\n\n【一个直观的心智模型】\n\n把 JVM 对象想成「带包装箱运家具」：\n- 一把椅子（一个 int）也要一个箱子（对象头）+ 一张快递单（引用）+ 填充泡沫（对齐填充）——箱子比椅子还占地方；\n- JVM 垃圾回收（GC）像是仓库管理员，要挨个箱子检查「还要不要」，箱子越多他越累，干活时全场停工（STW）。\n\nTungsten 的做法是**真空压缩袋 + 拆板件平铺**：\n- 把家具拆成板件，抽掉空气压成一片（紧凑二进制行 UnsafeRow），一个挨一个平铺在地板上；\n- 没有包装箱、没有快递单，占地小、还能一口气扫一大片（缓存友好）；\n- 地板还能铺在仓库外面（堆外内存 off-heap），管理员（GC）根本不用管它。\n\n⚠️ 比喻的边界（很重要）：\n① 拆成字节不等于「零成本」：读写它要有 Schema 才知道第几个字节是什么（复用 L2 的「Schema=宜家零件清单」），没了清单就是一堆乱码。\n② 不是所有算子都能全程走二进制：有些操作（如复杂 UDF）仍要把字节还原成对象，这一进一出就是 L3 说过的 UDF 慢的根源。\n③ 堆外内存不受 GC 管，但也意味着**你得自己算着用**——分配与回收由 Spark 的内存管理器负责，超了就是 OOM（第 3 课）。\n④ 具体内存布局（页大小、偏移怎么算）随 Spark 版本演进，**别背实现细节**，记住「紧凑 + 堆外 + 缓存友好」这三件事就够用。\n\n【正式的技术定义】\n\nTungsten 是 Spark 的内存与执行优化工程，核心包含四点：\n- **紧凑二进制表示**：用 UnsafeRow 等结构把一行数据编码成连续字节，避免 JVM 对象头与引用开销；\n- **堆外内存管理**：把数据放在 JVM 堆之外（off-heap），由 Spark 自己管理分配与回收，绕开 GC 压力；\n- **缓存友好计算**：数据连续存放、按批访问，提高 CPU 缓存命中；\n- **代码生成**：复用 L4 的 WholeStageCodegen，把相邻算子「焊成一体化机器」直接对字节运算。\n它是 L2 所说「Schema 是逻辑约定、底层是紧凑二进制」的物理落地。\n\n【写下代码后，Spark 内部发生了什么】\n\n你写 `df = spark.read.parquet('sales')`：Parquet 读出的数据被直接组织成 Tungsten 的紧凑二进制行，在 Executor 内存里连续排列。之后 `df.filter(...).select(...)` 经 WholeStageCodegen 生成的代码**直接在字节上做判断与取列**，不产生中间 Java 对象，也不触发大量 GC。只有当你调用 UDF、或把数据 `collect()` 回 Driver 时，才会把字节还原成对象——这也解释了为什么「能用内置函数就别写 UDF」。",
                "examples": [
                    {
                        "title": "Schema 是读字节的钥匙",
                        "code": "df.printSchema()\n# 逻辑上：id: long, name: string\n# 物理上：一段连续的 Tungsten 二进制，靠 Schema 才知道第几位是什么",
                        "note": "呼应 L2 的「Schema=宜家零件清单」——没有清单，压缩袋里的板件拼不回家具。"
                    },
                    {
                        "title": "内置函数在字节上跑，UDF 要还原成对象",
                        "code": "from pyspark.sql import functions as F\n\n# 好：内置函数，Catalyst 认得、直接在 Tungsten 字节上算\ndf.withColumn('amt2', F.col('amount') * 2)\n\n# 差：Python UDF，每行要序列化跨 JVM 还原成对象再算（复用 L3）",
                        "note": "这正是 L3 埋下的「UDF 慢」的物理原因：跨 JVM 边界 + 无法在字节上直接算。"
                    },
                    {
                        "title": "堆外内存绕开 GC",
                        "code": "# Tungsten 可以把数据放在 JVM 堆之外，GC 不再扫描它\n# 代价：由 Spark 自己管理，超了就是 OOM（见下一课）\nprint(spark.conf.get('spark.memory.offHeap.enabled', 'false'))",
                        "note": "堆外不是「无限内存」，只是把账本从 GC 手里拿回到 Spark 手里。"
                    },
                    {
                        "title": "collect() 会把字节还原成对象并拉回 Driver",
                        "code": "# 危险：把紧凑二进制还原成海量对象，还全塞进 Driver 内存\nrows = df.collect()\n# 大数据量下直接 OOM（复用 L2 的 collect 边界）",
                        "note": "想看数据用 show()/采样；collect 只适合结果确实很小的情况。"
                    }
                ],
                "key_points": [
                    "Tungsten 解决的是 JVM 对象开销与 GC 压力",
                    "四件事：紧凑二进制行（UnsafeRow）/ 堆外内存 / 缓存友好计算 / 代码生成",
                    "Schema 是读这些字节的钥匙：没有 Schema，二进制就是乱码",
                    "内置函数能在字节上直接算；UDF 要还原成对象，这就是它慢的物理根源",
                    "内存布局细节随版本演进，别背实现，记住三件事就够"
                ],
                "common_mistakes": [
                    {
                        "mistake": "以为 Tungsten 让 Spark「零内存开销」。",
                        "why": "紧凑只是省掉了对象头与引用，数据本身的字节还在，堆外分配超了照样 OOM。",
                        "fix": "省的是「包装」，不是数据本身；容量仍要按数据量估。"
                    },
                    {
                        "mistake": "以为用了堆外内存就不会 OOM。",
                        "why": "堆外只是绕开 GC，分配与回收由 Spark 管理，超额依然失败。",
                        "fix": "按数据量估内存需求，别把堆外当成无限空间（见下节课的内存模型）。"
                    },
                    {
                        "mistake": "死磕 UnsafeRow 的字节偏移与页结构。",
                        "why": "这些是实现细节，随版本演进，对写业务代码没有直接帮助。",
                        "fix": "掌握「紧凑+堆外+缓存友好」的概念与「UDF 慢」的成因即可。"
                    }
                ],
                "review": "上一课我们立了规矩：调优是「先度量、再定位、改一处、复测」的闭环，而第一步是搞清楚数据到底在哪儿慢。最底层的问题，往往出在内存里。",
                "problem": "Spark 在 Executor 内存里到底是怎么存一行数据的？为什么 JVM 对象的开销能让 GC 拖垮整个作业？",
                "preview": "知道了数据以紧凑字节躺在内存里，下一个问题自然是：这块内存是怎么划分的、哪儿最容易撑爆？下集讲 Executor 内存模型与 OOM 的五大根因。"
            }
        },
        {
            "title": "Executor 内存模型与 OOM 根因",
            "slug": "l7-executor-memory",
            "description": "理解 Executor 内存分区（Execution / Storage / User / Reserved）与统一内存管理的借用规则；能定位常见 OOM 根因（单分区过大、collect 回 Driver、广播过大、UDF 存大对象、倾斜）。",
            "objective": "学完本课，你应该能够：说清 Executor 堆内存的四块划分（Execution / Storage / User Memory / Reserved）与各自用途；理解统一内存管理下 Execution 与 Storage 互相借用的规则；列举并定位五类常见 OOM 根因；知道堆外内存（off-heap）与堆内是两套账；并明确具体堆大小配置与 GC 调优不在本课范围。",
            "estimated_minutes": 14,
            "order_index": 2,
            "prerequisites": "",
            "content": {
                "explanation": "【先用人话理解】\n\nExecutor 不是拿到一整块内存随便用。它要把内存分成几块，各管各的事：算聚合/排序/join 用一块，缓存数据用一块，你自己代码里 new 出来的东西用一块，还要留出系统保留。分不清楚的结果就是——**明明还有内存，却报 OOM**。\n\n【一个直观的心智模型】\n\n把 Executor 想成一辆货车的总容积，车厢被隔成了四格：\n- **货厢（Execution Memory）**：干活区——Shuffle、排序、聚合、join 的哈希表都在这儿用；活最多、最容易爆；\n- **冷藏箱（Storage Memory）**：缓存区——cache() / persist() 的数据和被广播的小表住这儿；\n- **驾驶室杂物（User Memory）**：你自己代码里建的数据结构、UDF 里的对象、Python 侧的中间变量；\n- **备用油箱（Reserved Memory）**：系统保留，谁都不许动。\n\n统一内存管理的意思是：货厢和冷藏箱之间的隔板**可以挪**——冷藏箱空着时货厢可以借来用；反过来货厢紧张时，可以把冷藏箱里的数据挤出去（缓存丢掉或落盘）。但驾驶室那格不参与借用。\n\n⚠️ 比喻的边界（很重要）：\n① 「隔板能挪」不等于「没有边界」：借用有上限，缓存被逐出后可能要重算——这就是 cache() 未必划算的原因（第 8 课）。\n② 堆外内存（off-heap）是**另一本账**：它不在 JVM 堆里，GC 不管，但也要单独配置与估量，用超了照样失败。\n③ OOM 的位置很关键：**Executor 端 OOM** 多半是单分区数据太大或倾斜；**Driver 端 OOM** 多半是你把数据 collect() 回去了（复用 L2/L7 上节课）。\n④ 具体堆大小怎么配、GC 怎么调，是集群与 JVM 调优的范畴，本课只讲结构与诊断思路。\n\n【正式的技术定义】\n\nSpark Executor 的堆内存划分为：\n- **Execution Memory**：用于 Shuffle、排序、聚合、join 哈希表等计算过程；\n- **Storage Memory**：用于缓存 RDD/DataFrame（cache/persist）与广播块；\n- **User Memory**：用户自定义数据结构、UDF 内部对象等；\n- **Reserved Memory**：系统保留（固定量）。\n统一内存管理（Unified Memory Manager）下，Execution 与 Storage 之间可互相借用：Storage 空间可被执行内存挤占（缓存按策略逐出或落盘），反之亦然。堆外内存（off-heap）由 Spark 自行管理、不受 GC 管辖，需单独估量。\n常见 OOM 根因：① 单个分区数据量过大；② collect() 把数据拉回 Driver；③ 广播的表超出预期；④ UDF / 用户代码持有大对象；⑤ 数据倾斜导致个别 Task 数据量爆炸。\n\n【写下代码后，Spark 内部发生了什么】\n\n你写 df.groupBy('city').agg(F.collect_list('order_id')) 并触发 Action：\n1. 每个 Task 在 Execution Memory 里维护聚合哈希表；\n2. 若 collect_list 把某 key 的所有值都堆在内存里，而该 key 又特别大（倾斜或本来就是大分组），这块 Execution Memory 就会撑爆 → Executor OOM；\n3. 若此时还有 cache() 的数据占着 Storage Memory，统一内存管理会尝试逐出缓存来救场——但如果数据量本身就超出容器，救不回来；\n4. 另一条常见路径是 df.collect()：所有分区的紧凑二进制被还原成对象、全部拉回 Driver 内存 → **Driver 端 OOM**。",
                "examples": [
                    {
                        "title": "典型 Executor OOM：大分组聚合",
                        "code": "from pyspark.sql import functions as F\n# collect_list 会把每个 key 的所有值堆在内存里\ndf.groupBy('city').agg(F.collect_list('order_id')).show()\n# 某 city 的记录特别多 → 该 Task 的 Execution Memory 撑爆",
                        "note": "能聚合就别收集：用 count/sum 这类可合并的聚合，或先过滤、先降维。"
                    },
                    {
                        "title": "典型 Driver OOM：collect 回 Driver",
                        "code": "# 危险：把全量数据还原成对象拉回 Driver\nrows = df.collect()\n# 安全：只看样本\ndf.show(20)",
                        "note": "Driver 只管调度、不抱数据（L0 就定下的规矩），collect 是少数会打破它的操作。"
                    },
                    {
                        "title": "缓存与执行内存的借用",
                        "code": "df.cache()\ndf.count()          # 触发缓存，数据进 Storage Memory\ndf.groupBy('city').count().show()   # 执行内存紧张时会挤占/逐出缓存",
                        "note": "缓存不保证常驻：被逐出后要重算。别把 cache 当成「一定更快」（见第 8 课）。"
                    },
                    {
                        "title": "定位 OOM 先看是 Executor 还是 Driver",
                        "code": "# Executor 端 OOM：看 Spark UI 里失败 Task 所在 Stage 的输入数据量\n# Driver 端 OOM：多半是代码里出现了 collect() / toPandas() 之类",
                        "note": "位置决定病因：Executor 看分区与倾斜，Driver 看有没有把数据拉回来。"
                    }
                ],
                "key_points": [
                    "Executor 内存四格：Execution（干活）/ Storage（缓存）/ User（用户代码）/ Reserved（系统保留）",
                    "统一内存管理：Execution 与 Storage 可互相借用，缓存可能被逐出或落盘",
                    "堆外内存是另一本账：不受 GC 管，但也要单独估量",
                    "五类 OOM 根因：单分区过大 / collect 回 Driver / 广播过大 / UDF 存大对象 / 倾斜",
                    "定位先看位置：Executor OOM 查分区与倾斜，Driver OOM 查有没有拉数据回来"
                ],
                "common_mistakes": [
                    {
                        "mistake": "内存不够就只想到「加大 Executor 内存」。",
                        "why": "根因可能是单分区过大或倾斜——加内存只是推迟爆掉的时间，数据量一涨照样 OOM。",
                        "fix": "先看是哪种 OOM 根因：调分区数、处理倾斜、或改写聚合方式，通常比加内存有效。"
                    },
                    {
                        "mistake": "什么数据都 cache 一遍，觉得能提速。",
                        "why": "缓存占 Storage Memory，可能被逐出；重算有时比读缓存更快。",
                        "fix": "只缓存会被多次复用且计算代价高的数据（第 8 课展开）。"
                    },
                    {
                        "mistake": "在 UDF 里持有大对象（如加载整张字典表到内存）。",
                        "why": "User Memory 那格不参与借用，而且每个 Task 都可能持有副本，内存被悄悄吃光。",
                        "fix": "用 broadcast 变量或 join 代替在 UDF 里塞大对象。"
                    }
                ],
                "review": "上一课我们知道 Tungsten 把数据压成紧凑字节、甚至放到堆外绕开 GC——可这块内存究竟是怎么分配的，为什么有时候「明明还有内存却报 OOM」？",
                "problem": "Executor 的内存被分成了哪几块？各自装什么？哪些操作最容易把某一格撑爆？",
                "preview": "内存这块搞清楚了，接下来是最常用的那个旋钮——shuffle 之后的分区数到底该定多少。"
            }
        },
        {
            "title": "Shuffle 分区数怎么定",
            "slug": "l7-shuffle-partitions",
            "description": "掌握 spark.sql.shuffle.partitions 的作用与取舍；理解太少（并行度不足/spill/OOM）与太多（调度开销/小文件）的两侧代价；给出「按数据量估起点 + 实测收敛」的思路。",
            "objective": "学完本课，你应该能够：说清 spark.sql.shuffle.partitions 决定什么（shuffle 之后的分区数，即后续 Task 数）；列举太少与太多各自的代价；用「按 shuffle 数据量估起点、让单个分区落在百 MB 量级」的思路定初始值，再靠实测收敛；知道它同时决定输出文件数（小文件副作用）；并明确不给万能数值、AQE 的自动合并属于下一课。",
            "estimated_minutes": 14,
            "order_index": 3,
            "prerequisites": "",
            "content": {
                "explanation": "【先用人话理解】\n\nShuffle 之后数据要重新切成 N 份，这个 N 就是 `spark.sql.shuffle.partitions`（默认 200）。它是你最常动、也最容易乱动的旋钮：N 太小，一个 Task 扛太多数据（慢、spill、甚至 OOM）；N 太大，光是派活收活的管理开销就吃掉了收益，还会产出一地小文件。\n\n【一个直观的心智模型】\n\n把 Shuffle 想成「一批货要过 N 条车道」（复用 L5 的空中飞货）：\n- **车道太少**：所有车挤在两三条道上，每条道堵死，别的道空着——工人忙的忙死、闲的闲死，还可能把车（内存）压垮；\n- **车道太多**：几百条道每条只过几辆车，可每条道都要配收费员（Task 调度）和出货单（输出文件），管理成本比运输本身还高。\n\n合理的目标是：**每条车道上的货量适中、车道数又能让工人都忙起来**。\n\n⚠️ 比喻的边界（很重要）：\n① **没有万能值**：它取决于 shuffle 数据量、单条记录大小、集群并行能力。本课只给「估起点」的思路（让单个分区落在**百 MB 量级**），最终必须实测收敛。\n② 这个参数影响**所有** shuffle 类操作的后续分区数，改它是全局影响——不是针对某一个 join 的精细调节（那要靠 broadcast 或 hint，见 L6）。\n③ 它同时决定**输出文件数**：分区多 → 文件多 → 小文件问题（复用 L2 write 与 L5 的坑）。\n④ 分区数不是越多越并行：集群核数才是并行上限，车道再多、工人只有 8 个，也只能同时开 8 条（复用 L5 分区与并行度）。\n\n【正式的技术定义】\n\n`spark.sql.shuffle.partitions` 控制 Shuffle 类操作（join / groupBy / distinct / orderBy 等）之后生成的目标分区数，其默认值（常见为 200）只是通用起点。取值过少会导致：并行度不足、单 Task 数据量大、spill 到磁盘、OOM 风险上升；取值过多会导致：Task 调度与启动开销累积、输出小文件增多、聚合类操作的元数据膨胀。合理的定法：先估算参与 Shuffle 的数据量，让单分区数据量落在百 MB 量级作为起点，再结合集群并行能力与实测耗时收敛。\n\n【写下代码后，Spark 内部发生了什么】\n\n你写 `spark.conf.set('spark.sql.shuffle.partitions', 400)` 再跑 `df.groupBy('city').count()`：\n1. Shuffle 时，各 map 端按 `city` 哈希成 400 份写出；\n2. reduce 端起 400 个 Task，各拉取属于自己的那一小块；\n3. 若原本 200 分区时每个 Task 要处理 1 GB（会 spill），改成 400 后降到约 500 MB，可能就不 spill 了 → 变快；\n4. 但如果你调到 4000，每个 Task 只处理 25 MB，调度 4000 个 Task 的开销与 4000 个输出文件反而让整体变慢；\n5. 所以动作是：估起点 → 跑 → 看 Spark UI（Task 耗时与 spill）→ 收敛。",
                "examples": [
                    {
                        "title": "设置 shuffle 分区数（全局生效）",
                        "code": "spark.conf.set('spark.sql.shuffle.partitions', 400)\ndf.groupBy('city').count().explain()\n# 计划里 shuffle 分区数随之变化",
                        "note": "这是全局配置，会影响该 session 内所有后续 shuffle 操作，不是只针对某一条语句。"
                    },
                    {
                        "title": "估起点的思路：让单分区落在百 MB 量级",
                        "code": "# 假设参与 shuffle 的数据约 40 GB\n# 目标单分区 ~100-200 MB → 起点约 200-400 个分区\n# 再按实测收敛（本例仅示意思路，不是公式）",
                        "note": "先看 shuffle 数据量，再定起点；没有放之四海皆准的数字。"
                    },
                    {
                        "title": "分区过少的代价：spill 与 OOM",
                        "code": "spark.conf.set('spark.sql.shuffle.partitions', 8)\ndf.groupBy('city').count().show()\n# 每个 Task 数据量巨大 → Spark UI 里能看到 spill(Memory/Disk) 激增",
                        "note": "复�� L5：spill 意味着内存放不下、落到磁盘，I/O 慢几个数量级。"
                    },
                    {
                        "title": "分区过多的代价：调度与小文件",
                        "code": "spark.conf.set('spark.sql.shuffle.partitions', 5000)\ndf.write.parquet('out')\n# 输出目录下可能出现数千个小文件（复用 L2 write 的小文件坑）",
                        "note": "分区数不仅影响计算，也影响落盘文件数——写之前先想清楚要多少个文件。"
                    }
                ],
                "key_points": [
                    "spark.sql.shuffle.partitions 决定 shuffle 之后的分区数（即后续 Task 数）",
                    "太少：并行度不足、单 Task 过大 → spill / OOM；太多：调度开销 + 小文件",
                    "估起点思路：按 shuffle 数据量让单分区落在百 MB 量级，再实测收敛",
                    "它是全局旋钮，同时决定输出文件数",
                    "并行上限是集群核数，分区再多也开不出更多并行"
                ],
                "common_mistakes": [
                    {
                        "mistake": "背一个「最佳实践值」，所有作业都设成同一个数。",
                        "why": "合适的值取决于数据量、记录大小与集群规模，换份数据就不再适用。",
                        "fix": "用「估起点 + 实测收敛」的思路，并写进作业注释里说明依据。"
                    },
                    {
                        "mistake": "作业一慢就把分区数往上翻十倍。",
                        "why": "如果瓶颈是读太多或倾斜，调分区数完全打偏；即便瓶颈真是分区，过多也会反噬。",
                        "fix": "先定位瓶颈类型（第 1 课），确认是 shuffle 并行度问题再动它。"
                    },
                    {
                        "mistake": "只盯着计算速度，忘了输出文件数。",
                        "why": "每个分区通常落一个文件，分区过多会产生海量小文件，拖垮后续读取。",
                        "fix": "写之前先决定要多少个输出文件，必要时先 coalesce 再写出。"
                    }
                ],
                "review": "上一课我们摸清了 Executor 内存的四个格子，知道单 Task 数据过大就会撑爆 Execution Memory、或者 spill 到磁盘拖慢一切。",
                "problem": "那「单个 Task 扛多少数据」这个量，到底是谁决定的？最常用的那个旋钮该怎么拧？",
                "preview": "分区数之外，L6 还留了一个只讲了概念的旋钮——「多大算小」的那把秤。下集讲广播阈值怎么调、以及为什么修统计信息常常比调阈值更优先。"
            }
        },
        {
            "title": "广播阈值调优",
            "slug": "l7-broadcast-threshold",
            "description": "掌握 spark.sql.autoBroadcastJoinThreshold 的取舍（默认阈值的概念、调大/调小/禁用的场景与代价）；知道先修统计信息比调阈值更优先。",
            "objective": "学完本课，你应该能够：说清 spark.sql.autoBroadcastJoinThreshold 是什么（判断「多大算小」的阈值）；列举调大 / 调小 / 禁用三类场景及各自代价；理解阈值比的是**统计估计的大小**而非真实大小，因此「先修统计信息（ANALYZE）」通常比调阈值更优先；知道广播的账单是「每个 Executor 各存一份完整副本」；并明确具体配置配方不在本课范围。",
            "estimated_minutes": 13,
            "order_index": 4,
            "prerequisites": "",
            "content": {
                "explanation": "【先用人话理解】\n\nL6 只告诉你「存在一把尺子决定多大算小」，没说这把尺子怎么调。它叫 `spark.sql.autoBroadcastJoinThreshold`。但先说结论：**多数时候你不该先动它**——因为尺子量的是「估计值」，估计本身错了，你把刻度调来调去只是在错误的读数上做微调。\n\n【一个直观的心智模型】\n\n把阈值想成**秤上的刻度**：\n- 秤上放着一张表，Spark 看读数决定「这张算轻还是算重」；轻 → 广播（复印小册子，复用 L6）；重 → 老实走 Sort-Merge Join；\n- 刻度调大：更多表被判为「轻」，但每辆车上都要多载一份副本（每个 Executor 内存各一份）；\n- 刻度调小或关掉（-1）：更保守，明明很轻的表也走 SMJ，白白付两次 Shuffle 的钱。\n\n关键在于：**秤的读数准不准**。一张表经过复杂变换后，Spark 可能压根估不出它的重量，只能按「很重」处理——这时候你要做的不是把刻度调到无限大，而是**先给它补一张准确的磅单**（统计信息）。\n\n⚠️ 比喻的边界（很重要）：\n① 阈值比的是**统计估计的大小**，不是真实大小（复用 L6 第 6 课）。估计缺失时，再怎么调阈值都可能判错。\n② 广播的账单不是「一次传输」，而是**每个 Executor 各存一份完整副本**——同时广播多张表，或广播的表其实不小，内存会被吃光（L6 第 7 课的反噬）。\n③ 禁用广播（-1）不是「更稳」：它会让所有 join 走 Shuffle，小维表场景直接慢一大截。\n④ 具体配多少字节、怎么配，没有通用答案——取决于 Executor 内存与并发作业数，别抄别人的配置。\n\n【正式的技术定义】\n\n`spark.sql.autoBroadcastJoinThreshold` 是 Spark 判断「某侧是否小到可以广播」的大小阈值（设为 -1 表示禁用自动广播）。判断依据是该侧数据的**统计大小估计**。\n- **调大**：让更大的表也能走 Broadcast Hash Join，省掉大表那次 Shuffle；代价是广播块占用每个 Executor 的内存（Storage Memory）与网络分发开销。\n- **调小 / 禁用**：更保守，避免内存压力；代价是本可广播的小表也走 Sort-Merge Join，多付两侧 Shuffle。\n- **更优先的手段**：先通过统计信息收集（如 `ANALYZE TABLE ... COMPUTE STATISTICS`）让估计变准，再谈调阈值。\n\n【写下代码后，Spark 内部发生了什么】\n\n维表明明很小，`explain` 却显示 SortMergeJoin：\n1. 先看这一步——Spark 有没有这张表的统计信息？没有的话，它只能按保守估计当成大表；\n2. 补统计信息：`spark.sql('ANALYZE TABLE dim COMPUTE STATISTICS')`，再 explain，可能**不用调阈值**就自动广播了；\n3. 若统计已准、表确实略超阈值且 Executor 内存充裕，才考虑适度调大阈值；\n4. 调完再 explain 确认真的出现 BroadcastExchange（hint 与阈值都要复核，复用 L6 的规矩）；\n5. 同时盯住 Spark UI：广播块大小、Executor 内存占用有没有异常。",
                "examples": [
                    {
                        "title": "先看当前阈值（概念验证）",
                        "code": "print(spark.conf.get('spark.sql.autoBroadcastJoinThreshold'))\n# 输出的是阈值设置；-1 表示禁用自动广播",
                        "note": "先知道当前刻度是多少，再谈要不要动。"
                    },
                    {
                        "title": "更优先：先补统计信息",
                        "code": "spark.sql('ANALYZE TABLE dim COMPUTE STATISTICS')\nbig.join(dim, 'city_id').explain()\n# 估计变准后，可能无需调阈值就自动走 BroadcastHashJoin",
                        "note": "估计准了，判断自然准。调阈值前先做这一步，往往能省掉后面所有折腾。"
                    },
                    {
                        "title": "确实需要时再调大阈值",
                        "code": "spark.conf.set('spark.sql.autoBroadcastJoinThreshold', 50 * 1024 * 1024)\nbig.join(mid_dim, 'city_id').explain()\n# 确认：BroadcastExchange 出现 + 关注 Executor 内存占用",
                        "note": "每个 Executor 都会存一份完整副本，调大前先确认内存扛得住。"
                    },
                    {
                        "title": "禁用广播的代价",
                        "code": "spark.conf.set('spark.sql.autoBroadcastJoinThreshold', -1)\nbig.join(dim, 'city_id').explain()\n# 小维表也被迫走 SortMergeJoin：两个 Exchange，白付两次 Shuffle",
                        "note": "关掉广播不是「更稳」，而是把小表场景的性能直接扔掉。"
                    }
                ],
                "key_points": [
                    "autoBroadcastJoinThreshold 是判断「多大算小」的阈值，-1 为禁用",
                    "它比的是统计估计的大小，不是真实大小",
                    "更优先的手段：先 ANALYZE 补统计信息，再谈调阈值",
                    "调大的代价：每个 Executor 各存一份完整副本（内存账单）",
                    "禁用不是更稳：小维表会被迫走 SMJ，多付两次 Shuffle"
                ],
                "common_mistakes": [
                    {
                        "mistake": "表没被广播，第一反应就是调大阈值。",
                        "why": "根因往往是统计信息缺失导致估计失真，调阈值只是掩盖问题。",
                        "fix": "先 ANALYZE 补统计信息，再 explain 看是否自动广播。"
                    },
                    {
                        "mistake": "把阈值调得很大，好让所有维表都走广播。",
                        "why": "每广播一张表，每个 Executor 就多一份常驻副本，多了直接挤爆 Storage/Execution 内存。",
                        "fix": "只在确认表真的小、且能省掉最大那次 Shuffle 时才调。"
                    },
                    {
                        "mistake": "内存一紧张就把广播禁掉（-1）。",
                        "why": "一刀切会让本该广播的小表也走 SMJ，整体反而更慢。",
                        "fix": "按表逐个判断：该广播的用 hint 精确指定，不该广播的保持默认。"
                    }
                ],
                "review": "上一课我们学会了按数据量估 shuffle 分区数，知道太多太少都付代价。另一个 L6 只讲了概念的旋钮，也该落地了。",
                "problem": "「多大算小」的那把秤，刻度该怎么定？为什么大多数时候你其实不该先去动它？",
                "preview": "手动拧旋钮终究是在「出发前猜」。可 Spark 还能边跑边看路况、随时改路线——下集讲 AQE 自适应查询执行。"
            }
        },
        {
            "title": "AQE：让 Spark 在运行时自我修正",
            "slug": "l7-aqe",
            "description": "理解自适应查询执行（AQE）的动机（规划期估计不可靠）与三大能力：动态合并小分区、运行时切换 JOIN 策略、自动处理倾斜 join。",
            "objective": "学完本课，你应该能够：说清 AQE 存在的动机（规划期靠估计、运行时才有真相）；列举三大能力（动态合并小分区 / 运行时切换 JOIN 策略 / 自动处理倾斜 join）；知道 AQE 以 Shuffle 作为「观察点」，因此并非万能；理解开关只讲概念、具体配方与全部子开关不在本课范围；并知道开启后仍要用 explain 与 Spark UI 验证实际效果。",
            "estimated_minutes": 14,
            "order_index": 5,
            "prerequisites": "",
            "content": {
                "explanation": "【先用人话理解】\n\n前面所有优化（Catalyst 改写、选 JOIN 策略、定分区数）都发生在**出发之前**——Spark 只能靠统计信息**猜**数据有多大。猜错了就白优化：以为是大表走了 SMJ，其实它小得能广播；以为是 200 个 Task 刚好，结果 180 个只跑了 3 秒。\n\nAQE（Adaptive Query Execution，自适应查询执行）的思路是：**别在出发前把路线定死，边跑边看路况，发现堵车就改道**。\n\n【一个直观的心智模型】\n\n把执行计划想成导航给的路线：\n- 传统方式：出发前根据历史路况（统计信息）规划一整条路线，之后一路走到底，堵死也不改；\n- AQE：导航**边开边看实时路况**——\n  - 发现很多车道几乎没车（大量小分区）→ 把车道合并，减少收费员（**动态合并分区**）；\n  - 发现原本以为很大的那张表其实很小（Shuffle 后看到真实大小）→ 立刻改走广播（**运行时切换 JOIN 策略**）；\n  - 发现某条车道堵死了（某个分区特别大）→ 把这一条拆成多条匝道分流（**自动处理倾斜 join**）。\n\n⚠️ 比喻的边界（很重要）：\n① AQE 的观察点是 **Shuffle**：它要等 shuffle 写出后才知道每个分区真实多大。没有 shuffle 的地方，它看不到真相。\n② 它不是万能药：合并分区解决不了「根本没读对数据」的问题，倾斜处理也有适用条件（例如需要能拆分的处理方式）。\n③ 「边跑边改」意味着**最终计划可能和 explain 出来的不完全一样**：开了 AQE 后，要看 Spark UI 里的实际执行图，而不是只信静态计划。\n④ 具体开关与其子配置项只讲概念，不给配方——不同版本支持的能力与默认值不同，照抄配置容易踩坑。\n\n【正式的技术定义】\n\nAdaptive Query Execution（AQE，自适应查询执行）是 Spark 在**运行时**依据真实 Shuffle 统计信息重新优化剩余执行计划的机制。它把一次查询拆成多个阶段执行，每完成一个 Shuffle 就获得真实的分区大小统计，据此进行三类典型优化：\n- **动态合并 Shuffle 分区**：把大量过小的分区合并成少量合适大小的分区，降低调度开销；\n- **动态切换 JOIN 策略**：运行时发现一侧实际很小，把原计划的 Sort-Merge Join 改为 Broadcast Hash Join；\n- **动态优化倾斜 JOIN**：识别出异常大的分区，将其拆分并由多个 Task 并行处理（配合第 7 课）。\n开启 AQE 后，静态 `explain()` 结果可能与实际执行计划不同，应以 Spark UI 的实际执行图为准。\n\n【写下代码后，Spark 内部发生了什么】\n\n你开启 AQE 后跑 `big.join(dim, 'city_id').groupBy('k').count()`：\n1. 规划阶段先按统计估计给出初始计划（可能仍写成 SortMergeJoin）；\n2. 当某个 Shuffle 完成，Spark 拿到各分区的**真实**大小；\n3. 若发现 dim 侧实际很小 → 把后续 join 换成 Broadcast Hash Join（省掉大表 Shuffle）；\n4. 若发现大量分区只有几 MB → 合并它们，减少 Task 数；\n5. 若发现某分区异常巨大 → 按倾斜策略拆分处理；\n6. 最终你在 Spark UI 看到的 stage 数与 Task 分布，可能和一开始 `explain()` 的估计完全不同——这就是「运行时自我修正」。",
                "examples": [
                    {
                        "title": "开启 AQE（概念验证，具体开关以实际版本为准）",
                        "code": "spark.conf.set('spark.sql.adaptive.enabled', 'true')\nbig.join(dim, 'city_id').groupBy('k').count().show()\n# 再看 Spark UI：实际执行图可能与静态 explain 不同",
                        "note": "开了 AQE 就别只信 explain 的静态计划，要看 UI 里的真实执行图。"
                    },
                    {
                        "title": "能力一：动态合并小分区",
                        "code": "# shuffle 分区设得偏多时，AQE 会把大量小分区合并\nspark.conf.set('spark.sql.shuffle.partitions', 2000)\nspark.conf.set('spark.sql.adaptive.enabled', 'true')\ndf.groupBy('k').count().show()\n# UI 里实际 Task 数可能远小于 2000",
                        "note": "这补上了手动调分区数的盲区：不用再为「设多少」纠结到极致。"
                    },
                    {
                        "title": "能力二：运行时改走广播",
                        "code": "# 规划期估不出 dim 的真实大小 → 计划是 SMJ\n# 运行时发现它其实很小 → AQE 改成 BHJ\nbig.join(dim, 'city_id').explain()\n# 注意：开了 AQE 后，explain 显示的是「初始计划」，实际可能被改",
                        "note": "这正是 L6 第 6 课「估计会误判」的兜底方案：让运行时来纠正。"
                    },
                    {
                        "title": "AQE 不是万能的",
                        "code": "# 如果慢的原因是读了 200 列、没做分区裁剪\n# AQE 帮不了你——它优化的是「已读进来的数据怎么跑」\nspark.read.parquet('fact').groupBy('k').count().show()",
                        "note": "减量优先于调速（第 1 课的结论）。AQE 修不了「读太多」。"
                    }
                ],
                "key_points": [
                    "AQE = 运行时依据真实 Shuffle 统计重新优化剩余计划",
                    "三大能力：动态合并小分区 / 运行时切换 JOIN 策略 / 自动处理倾斜 join",
                    "观察点是 Shuffle：没有 shuffle 的地方拿不到真实数据分布",
                    "开启后 explain 的静态计划可能与实际执行不同，以 Spark UI 为准",
                    "不是万能药：修不了「读太多」，具体开关配置以实际版本为准"
                ],
                "common_mistakes": [
                    {
                        "mistake": "开了 AQE 就认为调优结束了。",
                        "why": "它优化的是已读入数据的执行方式，解决不了读太多、UDF 太慢、SQL 写得太差。",
                        "fix": "AQE 是兜底与增益，不是替代「减量与重写」的手段（见第 8 课）。"
                    },
                    {
                        "mistake": "开了 AQE 仍然只信 explain 的输出。",
                        "why": "AQE 会在运行时改计划，静态 explain 展示的是初始计划。",
                        "fix": "以 Spark UI 的实际执行图与 Task 分布为准来判断效果。"
                    },
                    {
                        "mistake": "照抄一套 AQE 相关配置当「标准答案」。",
                        "why": "不同 Spark 版本支持的能力、默认值与开关名都可能不同。",
                        "fix": "理解三类能力的原理，具体配置查你所使用版本的官方文档。"
                    }
                ],
                "review": "上一课我们拧完了广播阈值这把秤。可手动拧旋钮本质上还是在出发前猜——猜错了就得重跑。",
                "problem": "有没有办法让 Spark 别在出发前把路线定死，而是边跑边看真实路况、随时改道？",
                "preview": "AQE 能自动处理一部分倾斜，但不是所有倾斜它都救得回来。下集讲最难也最值钱的一课：数据倾斜的实战处理，从诊断到 salting 完整写法。"
            }
        },
        {
            "title": "数据倾斜实战处理",
            "slug": "l7-skew-tuning",
            "description": "能诊断倾斜（Spark UI 的 Task 耗时/Shuffle Read 分布），并按优先级选择手段：AQE 倾斜处理 → 隔离大 key → salting 加盐（完整写法）→ 广播绕过 → 过滤异常 key。",
            "objective": "学完本课，你应该能够：用 Spark UI 诊断倾斜（Task 耗时最大值远大于中位数、Shuffle Read 分布不均）；按优先级选择五种手段（AQE 自动处理 / 隔离大 key 单独处理 / salting 加盐 / 广播绕过 / 过滤异常 key）；写出 salting 的完整写法（一侧加盐、另一侧膨胀）并说清它的数据膨胀代价；知道改 key 有语义风险、必须验证结果正确性；并明确具体倾斜开关的配方不在本课范围。",
            "estimated_minutes": 15,
            "order_index": 6,
            "prerequisites": "",
            "content": {
                "explanation": "【先用人话理解】\n\nL6 你已经知道倾斜是什么：某些 key 的记录特别多，同 key 必须到同一分区（复用 L6「某把椅子挤满 90% 的人」），于是那个 Task 扛下绝大多数数据，整体被它拖住。这一课讲的是**怎么治**。\n\n治疗有优先级，别一上来就加盐——加盐要把另一侧数据放大 N 倍，是最重的一味药。\n\n【一个直观的心智模型】\n\n把 Shuffle 想成收费站（复用上一课的车道比喻）：某条车道堵了 500 辆车，其他车道各 3 辆。**交警（你）有五招**：\n1. **让系统自动分流（AQE）**：开自动倾斜处理，让 Spark 自己把堵死的车道拆成几条匝道——最省事，优先试；\n2. **把大货车单独引走（隔离大 key）**：把那几个巨型 key 的数据单独拎出来，用不同方式处理，剩下的走常规路线；\n3. **发多张通行证（salting 加盐）**：给堵死那条的每辆车随机分一张 0~N-1 的通行证，让它们分散到 N 条匝道；对面车道要配合——把对应 key 的数据复制 N 份，每张通行证各一份；\n4. **干脆不收费（广播绕过）**：如果一侧够小，广播它，大表根本不用按 key 重排，堵点自然消失；\n5. **劝返异常车辆（过滤异常 key）**：那些 null / 未知 / 默认值造成的巨型 key，很多时候本来就不该进结果——先过滤掉。\n\n⚠️ 比喻的边界（很重要）：\n① **加盐是有代价的**：另一侧要膨胀 N 倍，key 一多就得不偿失——它只适合「少数巨型 key」。\n② **改 key 有语义风险**：加盐后两侧必须严格对应（一侧加后缀、另一侧复制膨胀），写错了结果会多或少行，**必须验证结果正确性**（比如对比加盐前后的 count）。\n③ 广播绕过只在一侧**真的够小**时有效，否则就是把账单从网络转到内存（L6 的反噬）。\n④ 具体的倾斜开关与其参数配方不在本课范围（不同版本支持不同），本课给的是**手段与优先级**。\n\n【正式的技术定义】\n\n数据倾斜（Data Skew）的处理手段，按代价从低到高：\n- **AQE 自动倾斜处理**：运行时识别异常大的分区并拆分，交由多个 Task 并行处理（第 6 课）；\n- **隔离大 key**：先统计 key 分布找出巨型 key，把它们过滤出来单独处理，其余数据走常规路径，最后合并结果；\n- **Salting（加盐）**：给大 key 侧加上随机前缀 `key_0 ~ key_{N-1}` 将其打散到 N 个分区，另一侧对应地把该 key 的记录复制 N 份以匹配；代价是另一侧数据膨胀，只适合少数大 key；\n- **广播绕过**：一侧足够小时改用 Broadcast Hash Join，大表不按 key 重排，倾斜无从产生；\n- **过滤异常 key**：若倾斜源于 null / 默认值 / 脏数据且业务上不需要，直接过滤。\n诊断手段：Spark UI 中 Task 耗时最大值远大于中位数、Shuffle Read 大小分布不均，即为倾斜信号。\n\n【写下代码后，Spark 内部发生了什么】\n\n你怀疑 join 倾斜，按优先级推进：\n1. **先确认**：UI 里 199 个 Task 20 秒完成、1 个跑了 40 分钟 → 确认倾斜；再用 `df.groupBy('key').count().orderBy(F.desc('count')).show(10)` 找出是哪些 key；\n2. **优先试 AQE 自动处理**：开启后重跑，看 UI 里那个巨大分区有没有被拆开；\n3. **不行就隔离大 key**：把 top-N 巨型 key 单独 filter 出来处理，其余走原逻辑，最后 union；\n4. **再不行才加盐**：大 key 侧 `concat(key, '_', floor(rand()*N))`，另一侧把该 key 记录 explode 成 N 份同样加后缀，join 后核对 count 与预期一致；\n5. **最省事的旁路**：若一侧其实很小，直接 `F.broadcast()`，大表不重排 → 倾斜消失。",
                "examples": [
                    {
                        "title": "诊断：先找出是哪个 key 撑爆的",
                        "code": "from pyspark.sql import functions as F\ndf.groupBy('city_id').count().orderBy(F.desc('count')).show(10)\n# 若某个 city_id（常见是 null / 未知 / 默认值）占绝对多数 → 就是它",
                        "note": "先定位具体 key，再谈怎么治。倾斜最常见的元凶是 null 与默认值。"
                    },
                    {
                        "title": "手段一（优先）：交给 AQE 自动处理",
                        "code": "spark.conf.set('spark.sql.adaptive.enabled', 'true')\nbig.join(dim, 'city_id').show()\n# 看 UI：巨大分区是否被拆成多个 Task 并行处理",
                        "note": "最省事的一招，先试它；不行再上重手段。"
                    },
                    {
                        "title": "手段二：隔离大 key 单独处理",
                        "code": "from pyspark.sql import functions as F\nBIG_KEYS = [0, -1]   # 先查出来的巨型 key\nhot  = df.filter(F.col('city_id').isin(BIG_KEYS))\nnorm = df.filter(~F.col('city_id').isin(BIG_KEYS))\n# hot 与 norm 分别 join，最后 union 合并结果",
                        "note": "把「极端少数」与「正常多数」分开，各自用最合适的策略，比一刀切划算。"
                    },
                    {
                        "title": "手段三：salting 加盐（完整写法）",
                        "code": "from pyspark.sql import functions as F\nN = 8\n# 大 key 侧：加随机后缀，把巨型 key 打散成 N 份\na_salt = (a.withColumn('salt', F.floor(F.rand() * N))\n           .withColumn('k_salt', F.concat(F.col('k'), F.lit('_'), F.col('salt'))))\n# 另一侧：把每条记录膨胀成 N 份，分别对应 0~N-1 号后缀\nb_salt = (b.withColumn('salt', F.explode(F.array([F.lit(i) for i in range(N)])))\n           .withColumn('k_salt', F.concat(F.col('k'), F.lit('_'), F.col('salt'))))\nout = a_salt.join(b_salt, 'k_salt')\n# 代价：b 侧膨胀 N 倍；改 key 有语义风险，务必核对 count 是否符合预期",
                        "note": "最重的一味药。只用于少数巨型 key，写完必须验证结果行数与加盐前一致。"
                    },
                    {
                        "title": "手段四/五：广播绕过与过滤异常 key",
                        "code": "from pyspark.sql import functions as F\n# 若一侧够小：广播它，大表不按 key 重排，倾斜自然消失\nbig.join(F.broadcast(dim), 'city_id')\n\n# 若倾斜源于 null/默认值且业务不需要：先过滤\ndf.filter(F.col('city_id').isNotNull())",
                        "note": "最省事的两种：能让系统别重排就别重排，能不处理的脏数据就先扔掉。"
                    }
                ],
                "key_points": [
                    "诊断信号：Task 耗时最大值 >> 中位数、Shuffle Read 分布不均",
                    "手段优先级：AQE 自动处理 → 隔离大 key → salting 加盐 → 广播绕过 → 过滤异常 key",
                    "salting：一侧加随机后缀打散，另一侧复制膨胀匹配；代价是数据放大 N 倍",
                    "改 key 有语义风险，加盐后必须核对结果行数与预期一致",
                    "倾斜最常见的元凶是 null / 未知 / 默认值类的巨型 key"
                ],
                "common_mistakes": [
                    {
                        "mistake": "一说倾斜就立刻加盐。",
                        "why": "加盐要把另一侧膨胀 N 倍，是最重的手段；AQE 或隔离大 key 往往更划算。",
                        "fix": "按优先级推进：先试 AQE，再隔离，最后才加盐。"
                    },
                    {
                        "mistake": "加盐后不验证结果，直接交付。",
                        "why": "两侧改写方式不匹配会导致结果多算或少算，而倾斜场景下「看起来跑完了」不等于「算对了」。",
                        "fix": "加盐前后对比 count / 关键指标，确认语义一致再上线。"
                    },
                    {
                        "mistake": "对所有 key 无差别加盐。",
                        "why": "膨胀 N 倍的数据量可能远超倾斜带来的损失。",
                        "fix": "只对少数巨型 key 加盐，或配合隔离手段只对那一小撮数据加盐。"
                    }
                ],
                "review": "上一课我们让 Spark 学会了边跑边改路线（AQE），它能自动拆分一部分被堵死的分区。可并非所有倾斜它都救得回来。",
                "problem": "真遇到一个把作业拖到 40 分钟的巨型 key，你有哪些手段？先动哪一招，代价分别是什么？",
                "preview": "倾斜是最难的一关，但最有效的调优往往不是拧旋钮，而是根本别让那么多数据进到流水线里。下集讲「少读、少传、少算」。"
            }
        },
        {
            "title": "最优先的调优：少读、少传、少算",
            "slug": "l7-read-less-data",
            "description": "掌握减量三层次：少读（列裁剪/分区裁剪/谓词下推/列式格式/bucketing 概念）、少传（提前过滤聚合/map-side combine/广播）、少算（内置函数替代 UDF、慎用 cache 的取舍）。",
            "objective": "学完本课，你应该能够：按「少读 / 少传 / 少算」三层次系统性地减少工作量；举例说明列裁剪、分区裁剪、谓词下推、列式格式（Parquet/ORC）与分桶（bucketing）概念各自省在哪；说清 map-side combine 与广播如何减少传输；解释为什么内置函数优于 UDF（复用 L3），以及 cache/persist 的真实取舍；并明确不展开文件格式压缩参数配方，小文件问题点出即可。",
            "estimated_minutes": 14,
            "order_index": 7,
            "prerequisites": "",
            "content": {
                "explanation": "【先用人话理解】\n\n前面几课都在讲「怎么让已有的工作跑得更快」。但最有效的一招永远是：**让根本不必要的工作不要发生**。一份 200 列的表你只用 3 列，一年数据你只要一天——把这两件事做对，比后面所有参数加起来都管用。\n\n【一个直观的心智模型】\n\n复用 L4 的「滤网瞬移到河口（谓词下推）」与 L5 的「车间本地先捆小包再空运（map-side combine）」，三层减量分别是：\n- **少读**：仓库发货时就只装你要的那 3 列、只取你要的那一天的货（列裁剪 + 分区裁剪 + 谓词下推），并用整齐的标准化箱子（Parquet 这类列式格式）存放；\n- **少传**：能在本车间先捆成小包就别散着空运（map-side combine），能让小册子飞就别让大表飞（广播，复用 L6）；\n- **少算**：用流水线上的标准加工臂（内置函数），别临时外聘手艺人（UDF，复用 L3）；同一个结果要被多次复用时才缓存（cache），否则重算可能更便宜。\n\n⚠️ 比喻的边界（很重要）：\n① **下推取决于数据源**：Parquet/ORC 这类列式格式能真正少读字节，CSV 能做的有限（复用 L4 Catalyst 优化规则的边界）。\n② **cache 不是免费的**：它占 Storage Memory，可能被逐出（第 3 课），而且重算有时比读缓存更快——只缓存「会被多次复用且计算代价高」的数据。\n③ **分桶（bucketing）是写入侧的布局约定**：它让「按同一 key 反复 join」省去一次 Shuffle，但要提前按桶写出，属于建模决策而不是随手能开的开关。\n④ 减量的副作用也要看：过度分区裁剪会产生大量小目录/小文件；列裁剪省 I/O 但对已缓存的数据无效。\n\n【正式的技术定义】\n\n减量（Data Reduction）优先于调速，分三个层次：\n- **少读**：列裁剪（只读需要的列）、分区裁剪（只读命中的分区目录）、谓词下推（把过滤条件下推到数据源）、列式存储（Parquet/ORC 按列读取与压缩）、分桶（bucketing，按 key 预先分桶写出以便后续 join 免 Shuffle）；\n- **少传**：先过滤再 join / 先聚合再 join（减少参与 Shuffle 的数据量）、map-side combine（本地预聚合）、广播小表避免大表 Shuffle；\n- **少算**：用内置函数替代 UDF（避免跨 JVM 序列化与优化器失明，复用 L3）、避免重复计算（复用中间结果或用缓存）、谨慎使用 `cache`/`persist`（只在多次复用且重算更贵时使用）。\n\n【写下代码后，Spark 内部发生了什么】\n\n你写 `spark.read.parquet('fact').select('id','amount').filter('dt = 2026-01-01').groupBy('id').sum('amount')`：\n1. Catalyst 把 `select` 变成列裁剪、把 `filter` 下推到 Parquet 读取层——磁盘上只扫 `dt=2026-01-01` 这个分区的两列；\n2. 读进来的数据直接以 Tungsten 紧凑字节参与计算（第 2 课）；\n3. `groupBy` 的预聚合在 map 端先把同 key 的 amount 累加成小包（map-side combine），Shuffle 只飞小包；\n4. 全程用的是内置函数，Catalyst 能全程优化，没有跨 JVM 的对象还原（L3 UDF 的反面）；\n5. 对比「先读全表 200 列、join 完再过滤」的写法，这里省掉的是**数量级**的 I/O 与传输——这才是调优里最大的杠杆。",
                "examples": [
                    {
                        "title": "少读：列裁剪 + 分区裁剪 + 谓词下推",
                        "code": "df = (spark.read.parquet('fact')\n        .select('id', 'amount', 'dt')      # 列裁剪：只读需要的列\n        .filter(\"dt = '2026-01-01'\"))      # 谓词下推 + 分区裁剪\ndf.explain()\n# 计划里能看到 PushedFilters 与只扫命中的分区",
                        "note": "下推能否真正生效取决于数据源格式：Parquet/ORC 效果好，CSV 有限。"
                    },
                    {
                        "title": "少传：先过滤/先聚合，再 join",
                        "code": "from pyspark.sql import functions as F\n# 坏：先把两整张表 join 起来再过滤\nbig.join(dim, 'id').filter(\"dt = '2026-01-01'\")\n\n# 好：先各自裁剪、先聚合，再 join（参与 Shuffle 的数据量骤减）\nb1 = big.filter(\"dt = '2026-01-01'\").groupBy('id').agg(F.sum('amount'))\nb1.join(dim, 'id')",
                        "note": "join 前先把数据量降下来，是最划算的一步——复用 L5 的「本地先捆小包」。"
                    },
                    {
                        "title": "少算：内置函数替代 UDF",
                        "code": "from pyspark.sql import functions as F\n# 差：Python UDF，每行跨 JVM 序列化，Catalyst 看不懂无法优化\ndf.withColumn('amt2', my_udf(F.col('amount')))\n\n# 好：内置表达式，Catalyst 认得、全程在 Tungsten 字节上算\ndf.withColumn('amt2', F.round(F.col('amount') * 1.13, 2))",
                        "note": "这正是 L3 埋下的伏笔：能用内置函数就别写 UDF，是「少算」里最容易被忽略的一条。"
                    },
                    {
                        "title": "cache 的取舍：只缓存值得缓存的",
                        "code": "# 值得缓存：会被多次复用、且重算代价高\ndf_cached = df.filter('amount > 0').cache()\ndf_cached.count()            # 触发物化\ndf_cached.groupBy('k').count().show()\ndf_cached.groupBy('k2').sum('amount').show()\n\n# 不值得：只用一次的中间结果 —— 重算往往比占内存更便宜",
                        "note": "缓存占 Storage Memory 且可能被逐出；用之前先问「它会被复用几次」。"
                    }
                ],
                "key_points": [
                    "减量优先于调速：少读 > 少传 > 少算",
                    "少读：列裁剪 / 分区裁剪 / 谓词下推 / 列式格式 / 分桶（bucketing）",
                    "少传：先过滤先聚合再 join、map-side combine、广播小表",
                    "少算：内置函数替代 UDF、避免重复计算、谨慎用 cache",
                    "cache 不是免费：占 Storage Memory、可能被逐出，只缓存多次复用且重算更贵的数据"
                ],
                "common_mistakes": [
                    {
                        "mistake": "先 join 再过滤，或者 select 里带上所有列「反正后面可能要用」。",
                        "why": "多读多传的数据会成倍放大 Shuffle 与内存压力，后面的参数怎么调都补不回来。",
                        "fix": "先裁剪（列/行/分区）再关联；只保留真正需要的列。"
                    },
                    {
                        "mistake": "随手给中间结果加 cache，以为能提速。",
                        "why": "缓存占内存、可能被逐出；只用一次时重算通常更快。",
                        "fix": "只在「多次复用 + 重算代价高」时才缓存，用完记得 unpersist。"
                    },
                    {
                        "mistake": "用 CSV 存大数据，指望 Catalyst 帮你下推。",
                        "why": "行式格式无法按列读取，下推能力有限，I/O 省不下来。",
                        "fix": "大数据场景用 Parquet/ORC 这类列式格式（具体压缩参数以实际场景为准）。"
                    }
                ],
                "review": "上一课我们啃下了最难的倾斜：从 AQE 自动分流、隔离大 key，到最重的加盐。可回头看，这些招数都在假设「数据已经读进来了」。",
                "problem": "如果根本不该读那么多数据，再怎么调速都是白费——减量这条路具体能减在哪几层？",
                "preview": "最后一课：把九课的道具串成一张「调优检查单」，从度量到定位到按优先级下手，走完一个完整的诊断案例。"
            }
        },
        {
            "title": "综合练习（诊断清单与优先级）",
            "slug": "l7-comprehensive",
            "description": "给一个慢作业场景，按「度量 → 定位瓶颈 → 按优先级改（少读 > 少传 > 少算 > 调旋钮）→ 复测」输出方案；能说清每步的理由与代价。",
            "objective": "学完本课，你应该能够：拿到一个慢作业，按「度量 → 定位瓶颈类别 → 按优先级给方案（少读 > 少传 > 少算 > 调旋钮）→ 改一处测一次」输出完整诊断；说清每条建议的理由与代价；知道何时该用 AQE / 广播 / 加盐 / 调分区数，何时该回去改 SQL 写法；并明确本课只验证「会诊断、知道优先级、能给方向」，不要求背参数值。",
            "estimated_minutes": 15,
            "order_index": 8,
            "prerequisites": "",
            "content": {
                "explanation": "【先用人话理解】\n\nLevel 7 到这儿就齐了。回头看，我们给了你一张**检查单**：先看清楚慢在哪，再按「少读 → 少传 → 少算 → 最后才拧旋钮」的顺序下手。记住这个顺序——**能在数据量上解决的问题，就别去动参数**；能调参数解决的，也别一上来就加盐改 key。\n\n【一个直观的心智模型】\n\n把九课的道具串成一张**调优检查单**（问诊流程）：\n1. **量**：`explain()` 看计划（零成本）+ Spark UI 看运行时（哪个 Stage 慢、Task 均不均、有没有 spill）；\n2. **归类**：是读太多 / 传太多 / 内存不够 / 倾斜 / CPU 开销 中的哪一类（第 1 课）；\n3. **按优先级下手**：\n   - **少读**（第 8 课）：列裁剪、分区裁剪、谓词下推、列式格式、分桶；\n   - **少传**：先过滤先聚合、map-side combine、广播小表（L6）、调广播阈值（第 5 课）；\n   - **少算**：内置函数替 UDF、慎用 cache（第 8 课）；\n   - **调旋钮**：shuffle 分区数（第 4 课）、开 AQE（第 6 课）；\n   - **处理倾斜**（第 7 课）：AQE → 隔离大 key → 加盐 → 广播绕过 → 过滤异常 key；\n4. **改一处、测一次**（第 1 课）：记录耗时，有改善就保留并回到第 1 步，没改善就回滚换路。\n\n⚠️ 比喻的边界（很重要）：\n① 这张检查单是**诊断清单**，不是配置清单——本课不要求你背任何参数值，只要求你能说出「为什么动它、动了会付什么代价」。\n② 优先级不是死的：如果你已经确认瓶颈就是 shuffle 并行度，那调分区数就是当下最优；优先级指的是**同等条件下先试代价更小的手段**。\n③ 改 SQL 写法（少读少传）的收益通常远大于调参数，**参数调优是最后一道工序，不是第一步**。\n④ 任何改动都要复测：Spark 的估算是估计，你的直觉更是估计——只有耗时数字说了算。\n\n【正式的技术定义】\n\nSpark 性能诊断的标准化流程：\n（1）用 `explain()` 与 Spark UI 做度量，定位最慢的 Stage 与瓶颈类别；\n（2）按优先级施加改动：数据减量（列/行/分区裁剪、列式格式、分桶）→ 传输减量（提前过滤聚合、map-side combine、广播）→ 计算减量（内置函数替代 UDF、避免重复计算、审慎缓存）→ 参数调节（shuffle 分区数、广播阈值、AQE）→ 倾斜专项处理（AQE 自动 / 隔离大 key / salting / 广播绕过 / 过滤异常 key）；\n（3）每次只改一处，复测对比耗时，保留改善项并重新度量，无改善则回滚；\n（4）涉及改 key（如 salting）时必须验证结果语义一致。\n该流程强调「度量驱动 + 最小改动 + 优先级」，而非参数堆叠。\n\n【写下代码后，Spark 内部发生了什么】\n\n假设 `fact`（50 亿行、200 列）join `dim`（10 万行）再 groupBy 聚合，跑了 40 分钟：\n1. **量**：explain 发现计划里是两个 Exchange + SortMergeJoin（dim 没被广播，估计问题）；UI 里某 Stage 的 Task 最大耗时是中位数的 50 倍（倾斜）；\n2. **归优先级**：\n   - 先做**少读**：`select` 只留 5 列 + `filter` 分区裁剪 → I/O 骤降；\n   - 再做**少传**：补 `ANALYZE` 让 dim 的大小估计变准（或直接 `F.broadcast(dim)`）→ 大表免 Shuffle；\n   - 再**调旋钮**：按 shuffle 数据量重估分区数，或开 AQE 让运行时合并/切换；\n   - 最后**治倾斜**：查 key 分布，若是 null 造成就过滤；若是真实大 key 就 AQE 或隔离处理；\n3. **每步复测**：改完一处就记一次耗时，看改善来自哪一步；\n4. 最后确认：结果行数与加盐前（若用过）一致，语义未变。\n走完这一轮，这个作业你已经能讲清楚「它为什么慢、我动了什么、省掉了什么」。",
                "examples": [
                    {
                        "title": "第一步：explain + UI 双管齐下",
                        "code": "q = fact.join(dim, 'city_id').groupBy('k').count()\nq.explain()\n# 计划：几个 Exchange？有没有 BroadcastExchange？下推了吗？\n# UI：哪个 Stage 最慢？Task 耗时最大值 vs 中位数？有 spill 吗？",
                        "note": "explain 定方向、UI 定位置，两者缺一不可（第 1 课的闭环）。"
                    },
                    {
                        "title": "先减量，再谈参数",
                        "code": "from pyspark.sql import functions as F\n# 少读：只取需要的列 + 分区裁剪\nf = spark.read.parquet('fact').select('city_id', 'k', 'amount').filter(\"dt='2026-01-01'\")\n# 少传：先聚合再 join\ng = f.groupBy('city_id', 'k').agg(F.sum('amount').alias('s'))\ng.join(F.broadcast(dim), 'city_id').show()",
                        "note": "同样的结果，数据量降一个数量级——这比任何参数都有效。"
                    },
                    {
                        "title": "再调旋钮：分区数与 AQE",
                        "code": "spark.conf.set('spark.sql.shuffle.partitions', 400)   # 按数据量估起点\nspark.conf.set('spark.sql.adaptive.enabled', 'true')  # 让运行时自己修正",
                        "note": "旋钮是最后一道工序；开了 AQE 记得以 UI 的实���执行图为准，而不是静态 explain。"
                    },
                    {
                        "title": "改一处、测一次",
                        "code": "# 记录基线耗时 → 只改一处 → 复测 → 对比\n# 改善则保留并重新度量找下一个瓶颈；无改善则回滚换思路",
                        "note": "一次改五个参数，变快了也不是你的功劳——你无法归因，也无法迁移到下一个作业。"
                    }
                ],
                "key_points": [
                    "检查单：量（explain+UI）→ 归类 → 按优先级改 → 改一处测一次",
                    "优先级：少读 > 少传 > 少算 > 调旋钮；倾斜专项放最后",
                    "参数调优是最后一道工序，不是第一步",
                    "凡改 key（加盐）必须验证结果语义一致",
                    "综合只验证「会诊断、知道优先级、能给方向」，不要求背参数值"
                ],
                "common_mistakes": [
                    {
                        "mistake": "把综合练习当配置考试，背一堆参数值。",
                        "why": "参数值依赖数据量与集群，背下来换个场景就失效。",
                        "fix": "记住「诊断流程 + 优先级 + 每项代价」，具体数值现场估、现场测。"
                    },
                    {
                        "mistake": "跳过减量直接调参数。",
                        "why": "读太多、传太多的问题不解决，调参数只是在错误的量级上做微调。",
                        "fix": "每次都先从「这份数据里有多少是必需的」开始问。"
                    },
                    {
                        "mistake": "一次改完所有想到的优化，跑通就交付。",
                        "why": "无法归因，也无法知道哪一步真的有效；某些改动在其他数据量下可能变成负担。",
                        "fix": "改一处、测一次、记录耗时，用数据决定保留还是回滚。"
                    }
                ],
                "review": "九课走完，你已经握住了 Spark 调优的完整工具箱：度量驱动的闭环、Tungsten 的紧凑字节、Executor 内存四格与 OOM 根因、shuffle 分区数、广播阈值、AQE 的边跑边改、倾斜的五招、以及最优先的减量三层次。",
                "problem": "把这套本事压到一张检查单上：面对一个慢作业，你按什么顺序问问题、动哪几处、怎么证明有效？",
                "preview": "恭喜走完 Level 7——Spark Quest 课程主线（Level 0 到 Level 7）到此全部走完。你现在既能看懂 Spark 在干什么，也能让���干得更快。去测验检验自己吧。🏁"
            }
        }
    ]
}

LEVEL7_QUIZZES = [
    {"lesson_slug": "l7-what-is-tuning", "questions": [
        {"type": "single_choice", "prompt": "性能调优最准确的定位是？", "options": ["把能找到的加速参数全加上", "换更快的机器就能解决", "度量驱动的闭环：先量出瓶颈、改一处、再复测", "把 Spark 升级到最新版本"], "correct_index": 2, "explanation": "调优的核心是「定位瓶颈 → 最小改动 → 复测验证」的迭代，不是堆参数；换机器与升级属运维/版本范畴。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "为什么不能一上来就调 spark.sql.shuffle.partitions 这类参数？", "options": ["瓶颈可能根本不在 Shuffle；不度量的调参是碰运气，而且无法归因", "这个参数已经废弃", "调了一定会变慢", "只有集群管理员能调"], "correct_index": 0, "explanation": "作业慢的原因可能是读太多、倾斜、UDF 等；先量清楚是哪一类瓶颈，再对症下药。", "dimension": "why"},
        {"type": "single_choice", "prompt": "关于 explain() 在调优中的作用，正确的是？", "options": ["会执行一遍并输出真实耗时", "能显示每个 key 有多少条数据", "能自动帮你优化代码", "只打印执行计划、不触发执行，零成本"], "correct_index": 3, "explanation": "explain 是静态窥视（复用 L4），不执行、零成本；key 分布这类运行时信息它看不到。", "dimension": "mechanism"},
        {"type": "single_choice", "prompt": "在 Spark UI 里看到「Task 耗时最大值远大于中位数」，最可能的结论是？", "options": ["分区数太少", "存在数据倾斜（个别 Task 数据量爆炸）", "代码有语法错误", "网络带宽不足"], "correct_index": 1, "explanation": "耗时分布极不均是倾斜的典型信号；分区太少会表现为并行度不足而非长尾。", "dimension": "apply"},
        {"type": "single_choice", "prompt": "explain 与 Spark UI 的分工，正确的是？", "options": ["explain 看静态计划（零成本），Spark UI 看运行时（耗时分布/spill/Shuffle 量）", "两者完全等价，看一个就够", "explain 更准，UI 只是参考", "UI 只能在作业失败后查看"], "correct_index": 0, "explanation": "计划相同 ≠ 运行时相同（L4 埋下的伏笔）：explain 定方向，UI 定位置。", "dimension": "comparison"},
        {"type": "single_choice", "prompt": "本课归纳的 Spark 作业瓶颈类别有哪几类？", "options": ["CPU / 内存 / 磁盘 / 网络", "语法 / 语义 / 运行时 / 逻辑", "Driver / Executor / Shuffle / Storage", "读太多 / 传太多 / 内存不够 / 倾斜 / CPU 开销"], "correct_index": 3, "explanation": "这五类对应后续几课的处方：减量（第 8 课）、内存（第 3 课）、倾斜（第 7 课）、UDF（复用 L3）。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "为什么改非瓶颈处等于白改？", "options": ["因为 Spark 会忽略你的改动", "木桶效应：整体耗时由最慢的 Stage/Task 决定，其他处提速不改善总耗时", "因为参数有缓存", "因为改动会被 Catalyst 回滚"], "correct_index": 1, "explanation": "先找出最慢的那道工序；改完一处还要重新度量，因为瓶颈会转移。", "dimension": "why"},
        {"type": "single_choice", "prompt": "一次改五个参数后作业变快了，最大的问题是什么？", "options": ["没什么问题，结果好就行", "Spark 会拒绝应用多个配置", "无法归因：不知道是哪一项起了作用，也难以迁移到其他作业", "会导致结果不正确"], "correct_index": 2, "explanation": "无法归因就无法沉淀经验；正确做法是改一处、测一次、用耗时决定是否保留。", "dimension": "mechanism"},
        {"type": "single_choice", "prompt": "面对一个跑得慢的作业，第一步应该做？", "options": ["把 shuffle 分区数翻倍", "给所有表加 cache", "重启集群", "explain 看计划 + Spark UI 看运行时，先定位瓶颈类别"], "correct_index": 3, "explanation": "先量后动是第 1 课的核心：explain 零成本看方向，UI 看真实耗时与分布。", "dimension": "apply"},
        {"type": "single_choice", "prompt": "关于「减量」与「调速」的关系，正确的是？", "options": ["两者收益相当，先做哪个都行", "减量优先：能不读的数据就别读，这通常比任何参数都有效", "调速优先，减量只影响代码美观", "减量只对小数据集有效"], "correct_index": 1, "explanation": "少读少传省的是数量级的 I/O 与网络，远大于参数微调，这是第 8 课的主题。", "dimension": "comparison"}
    ]},
    {"lesson_slug": "l7-tungsten-encoding", "questions": [
        {"type": "single_choice", "prompt": "Tungsten 要解决的核心问题是？", "options": ["网络传输太慢", "SQL 解析太慢", "磁盘容量不足", "JVM 对象开销与 GC 压力"], "correct_index": 3, "explanation": "对象头、引用、装箱让存储成本远超数据本身，GC 还要反复扫描；Tungsten 直接操作字节来绕开它们。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "为什么在 JVM 里存一行数据的代价比直觉高？", "options": ["因为 JVM 只支持字符串", "每行要额外背对象头、引用与对齐填充，短字符串尤其吃亏", "因为数据会被复制三份", "因为 JVM 不支持数组"], "correct_index": 1, "explanation": "包装比数据本身还占地方，数据一多，GC 扫描这些对象的成本就拖垮作业。", "dimension": "why"},
        {"type": "single_choice", "prompt": "关于紧凑二进制行（UnsafeRow），正确的是？", "options": ["它把一行编码成连续字节，需要 Schema 才能解读", "它是一种压缩文件格式", "它只对字符串有效", "它会自动丢弃 null 值"], "correct_index": 0, "explanation": "呼应 L2：Schema 是读这些字节的钥匙，没有 Schema，二进制就是乱码。", "dimension": "mechanism"},
        {"type": "single_choice", "prompt": "想减少内存与 GC 压力，优先应该？", "options": ["把所有数据 collect 回来处理", "把数据写成 CSV 再读", "用内置函数替代 UDF，让计算留在 Tungsten 字节上", "给每行加索引列"], "correct_index": 2, "explanation": "内置函数 Catalyst 认得、直接在字节上算；UDF 要把字节还原成对象，正是它慢的物理根源。", "dimension": "apply"},
        {"type": "single_choice", "prompt": "内置函数与 UDF 在 Tungsten 层面的差异是？", "options": ["两者完全一样", "内置函数可在字节上直接运算；UDF 要还原成对象、跨 JVM 序列化", "UDF 更快因为它是手写的", "内置函数只能在 SQL 里用"], "correct_index": 1, "explanation": "这正是 L3 埋下的「UDF 慢」的物理原因，也是「能用内置就别写 UDF」的根据。", "dimension": "comparison"},
        {"type": "single_choice", "prompt": "Tungsten 包含哪几件事？", "options": ["紧凑二进制表示 / 堆外内存 / 缓存友好计算 / 代码生成", "列裁剪 / 谓词下推 / 分区裁剪 / 分桶", "广播 / Shuffle / 排序 / 聚合", "Driver / Executor / Stage / Task"], "correct_index": 0, "explanation": "前三者是内存与执行层，代码生成即 L4 已讲的 WholeStageCodegen。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "堆外内存（off-heap）的价值在于？", "options": ["它比堆内快十倍", "它容量无限", "它不在 JVM 堆里，GC 不再扫描它，由 Spark 自行管理", "它会自动压缩数据"], "correct_index": 2, "explanation": "堆外不是无限空间，只是把账本从 GC 手里拿回 Spark 手里，超了照样 OOM。", "dimension": "why"},
        {"type": "single_choice", "prompt": "调用 df.collect() 时，内存层面发生了什么？", "options": ["只把 Schema 拉回 Driver", "数据在 Executor 之间重分布", "什么都没发生，只是打印", "紧凑字节被还原成对象并全部拉回 Driver 内存，大数据量下直接 OOM"], "correct_index": 3, "explanation": "复用 L2 的 collect 边界：Driver 不抱数据，collect 是少数打破这条规矩的操作。", "dimension": "mechanism"},
        {"type": "single_choice", "prompt": "printSchema() 在 Tungsten 语境下的意义是？", "options": ["Schema 是解读紧凑二进制的钥匙：没有它，字节流无法还原成字段", "只是给开发者看字段", "它会触发一次全表扫描", "它会把数据缓存下来"], "correct_index": 0, "explanation": "逻辑 Schema 与物理字节是一对：Schema 定含义，Tungsten 定存放。", "dimension": "apply"},
        {"type": "single_choice", "prompt": "关于堆内与堆外内存，正确的是？", "options": ["堆外由 GC 管理，更安全", "两者完全一样", "堆内受 GC 管理；堆外不受 GC 管，但需单独估量，超额同样 OOM", "堆外只能存缓存数据"], "correct_index": 2, "explanation": "绕开 GC 不等于免死金牌：堆外的分配与回收由 Spark 负责，用超了照样失败。", "dimension": "comparison"}
    ]},
    {"lesson_slug": "l7-executor-memory", "questions": [
        {"type": "single_choice", "prompt": "Executor 堆内存的四块划分是？", "options": ["Execution / Storage / User Memory / Reserved", "Driver / Executor / Stage / Task", "Heap / Off-heap / Disk / Network", "Cache / Shuffle / Sort / Join"], "correct_index": 0, "explanation": "干活区（Execution）、缓存区（Storage）、用户代码（User）、系统保留（Reserved）各管各的。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "为什么会出现「明明还有内存却报 OOM」？", "options": ["Spark 统计有误", "磁盘满了", "各格用途不同且 User/Reserved 不参与借用，某一格撑爆就会失败", "网络超时"], "correct_index": 2, "explanation": "统一内存管理只让 Execution 与 Storage 互相借用；User 与 Reserved 不参与，所以某一格爆了就是爆了。", "dimension": "why"},
        {"type": "single_choice", "prompt": "统一内存管理下，Execution 与 Storage 的关系是？", "options": ["完全隔离，互不影响", "可互相借用：执行内存紧张时缓存可能被逐出或落盘", "Storage 优先，Execution 只能等", "使用同一块空间无法区分"], "correct_index": 1, "explanation": "缓存不保证常驻——被逐出后要重算，这正是 cache 未必划算的原因。", "dimension": "mechanism"},
        {"type": "single_choice", "prompt": "遇到 Driver 端 OOM，最该先查什么？", "options": ["分区数是否太少", "Executor 内存配置", "数据文件格式", "代码里有没有 collect() / toPandas() 把数据拉回 Driver"], "correct_index": 3, "explanation": "位置决定病因：Driver 端 OOM 多半是有人把数据拉了回来，而不是计算本身太大。", "dimension": "apply"},
        {"type": "single_choice", "prompt": "对比两类 OOM 的根因，正确的是？", "options": ["两者根因相同", "Executor 端一定是配置问题", "Executor 端多半是单分区过大/倾斜；Driver 端多半是 collect 拉数据回来", "Driver 端不会 OOM"], "correct_index": 2, "explanation": "先看位置再定病因：Executor 查分区与倾斜，Driver 查有没有拉数据。", "dimension": "comparison"},
        {"type": "single_choice", "prompt": "关于堆外内存与堆内内存的关系，正确的是？", "options": ["堆外包含在堆内配额里", "堆外是另一本账：不在 JVM 堆里、GC 不管，但也要单独配置与估量", "堆外只能用于广播", "开了堆外就不用管内存了"], "correct_index": 1, "explanation": "两本账都要估量；只盯着堆内会低估实际内存占用。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "为什么 cache() 不一定能提速？", "options": ["cache 有 bug", "cache 会改变结果", "cache 只对 RDD 有效", "缓存占 Storage Memory 且可能被逐出；重算有时比读缓存更便宜"], "correct_index": 3, "explanation": "只缓存「会被多次复用且重算代价高」的数据，其余场景重算往往更快（第 8 课展开）。", "dimension": "why"},
        {"type": "single_choice", "prompt": "groupBy 后接 collect_list 为什么容易 OOM？", "options": ["它把每个 key 的所有值堆在内存里，遇到大分组就会撑爆 Execution Memory", "collect_list 会触发 Shuffle", "它不支持字符串", "它会把数据写到磁盘"], "correct_index": 0, "explanation": "能聚合就别收集：用 count/sum 这类可合并的聚合，或先过滤降维。", "dimension": "mechanism"},
        {"type": "single_choice", "prompt": "在 UDF 里加载整张字典表持有引用，会带来什么问题？", "options": ["没有任何问题", "User Memory 那格不参与借用，且每个 Task 都可能持有副本，内存被悄悄吃光", "会让代码更快", "会触发 Shuffle"], "correct_index": 1, "explanation": "改用 broadcast 变量或 join，别在 UDF 里塞大对象。", "dimension": "apply"},
        {"type": "single_choice", "prompt": "内存不足时，更优先的做法通常是？", "options": ["直接加大 Executor 内存", "关掉广播功能", "减少并行度", "先查根因：调分区数、处理倾斜、改写聚合方式，通常比加内存有效"], "correct_index": 3, "explanation": "加内存只是推迟爆掉的时间；数据量一涨，未解决的单分区过大或倾斜照样 OOM。", "dimension": "comparison"}
    ]},
    {"lesson_slug": "l7-shuffle-partitions", "questions": [
        {"type": "single_choice", "prompt": "spark.sql.shuffle.partitions 决定什么？", "options": ["读取文件时的输入切片数", "Shuffle 之后生成的目标分区数（即后续 Task 数）", "Executor 的数量", "广播块的大小"], "correct_index": 1, "explanation": "它控制 join/groupBy/distinct/orderBy 等 shuffle 类操作后数据被切成多少份。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "shuffle 分区数太少会带来什么？", "options": ["结果不正确", "输出文件过多", "网络带宽浪费", "并行度不足、单 Task 数据量过大 → spill 到磁盘甚至 OOM"], "correct_index": 3, "explanation": "复用 L5：内存放不下就 spill，磁盘 I/O 比内存慢几个数量级。", "dimension": "why"},
        {"type": "single_choice", "prompt": "shuffle 分区数太多会带来什么？", "options": ["结果重复", "自动触发广播", "Task 调度与启动开销累积、输出小文件增多", "内存必然溢出"], "correct_index": 2, "explanation": "复用 L2/L5 的小文件坑：每个分区通常落一个文件，分区过多会拖垮后续读取。", "dimension": "mechanism"},
        {"type": "single_choice", "prompt": "给 shuffle 分区数估起点的合理思路是？", "options": ["按参与 shuffle 的数据量，让单个分区落在百 MB 量级，再实测收敛", "固定设成 2000", "设成集群核数的一半", "设成与输入文件数相同"], "correct_index": 0, "explanation": "先估起点再实测收敛；没有放之四海皆准的数字，换份数据结论就变。", "dimension": "apply"},
        {"type": "single_choice", "prompt": "关于分区数与并行上限，正确的是？", "options": ["分区越多并行度越高，没有上限", "并行度与核数无关", "分区数必须等于核数", "并行上限是集群核数：车道再多，工人只有 8 个也只能同时开 8 条"], "correct_index": 3, "explanation": "复用 L5 分区与并行度：分区数决定理论并行度，实际并行受可用核数约束。", "dimension": "comparison"},
        {"type": "single_choice", "prompt": "spark.sql.shuffle.partitions 的默认值（常见为 200）应如何看待？", "options": ["是经过验证的最优值", "必须保持不动", "只是通用起点，未必适合你的数据量与集群", "只在本地模式生效"], "correct_index": 2, "explanation": "默认值是「能跑起来」的起点，不是「跑得快」的保证。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "为什么这个参数没有万能最优值？", "options": ["它取决于 shuffle 数据量、单条记录大小与集群并行能力", "因为 Spark 实现有缺陷", "因为参数名会变", "因为只能由管理员设置"], "correct_index": 0, "explanation": "所以正确做法是「按数据量估起点 + 实测收敛」，并把依据写进作业注释。", "dimension": "why"},
        {"type": "single_choice", "prompt": "修改 spark.sql.shuffle.partitions 的影响范围是？", "options": ["只对下一条语句生效", "全局生效：影响该 session 内所有 shuffle 操作，并决定输出文件数", "只影响 join 不影响 groupBy", "只在写入时生效"], "correct_index": 1, "explanation": "它是全局旋钮，不是针对某一条语句的精细调节——那是 hint 的职责。", "dimension": "mechanism"},
        {"type": "single_choice", "prompt": "把结果写出到 Parquet 之前，应该先考虑？", "options": ["文件越多越好", "必须设成 1 个文件", "分区数决定输出文件数，先想清楚要多少个文件", "输出文件数与分区数无关"], "correct_index": 2, "explanation": "写之前先决定文件数，必要时先 coalesce 再写出（复用 L5 的 repartition/coalesce）。", "dimension": "apply"},
        {"type": "single_choice", "prompt": "同样是「让 Shuffle 更快」，更优先的手段通常是？", "options": ["先裁剪数据（少读）或广播小表（少传），再考虑调分区数", "把分区数调大", "禁用广播", "增加 Executor 数量"], "correct_index": 0, "explanation": "减量优先于调速：参与 shuffle 的数据少了，分区数怎么设都更轻松。", "dimension": "comparison"}
    ]},
    {"lesson_slug": "l7-broadcast-threshold", "questions": [
        {"type": "single_choice", "prompt": "spark.sql.autoBroadcastJoinThreshold 是什么？", "options": ["广播块的最大数量", "广播的超时时间", "判断「某侧多大算小、能否广播」的大小阈值（-1 为禁用）", "广播表的最大行数"], "correct_index": 2, "explanation": "它就是 L6 只讲了概念的那把「秤」，用来判断能不能走 Broadcast Hash Join。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "为什么表没被广播时，通常不该先去调大阈值？", "options": ["阈值比的是统计估计的大小；估计失真时调阈值只是掩盖问题，应先 ANALYZE 补统计信息", "阈值不允许修改", "调大一定会 OOM", "调大只影响 SQL 写法"], "correct_index": 0, "explanation": "估计准了判断自然准——先 ANALYZE，往往不用调阈值就自动广播了。", "dimension": "why"},
        {"type": "single_choice", "prompt": "把 autoBroadcastJoinThreshold 设为 -1 会怎样？", "options": ["广播所有表", "自动选择最优策略", "只在本地模式生效", "禁用自动广播：小维表也会被迫走 Sort-Merge Join，多付两侧 Shuffle"], "correct_index": 3, "explanation": "关掉广播不是更稳，而是把小表场景的性能直接扔掉——代价是两次 Exchange。", "dimension": "mechanism"},
        {"type": "single_choice", "prompt": "维表很小但 explain 显示 SortMergeJoin，第一步应该？", "options": ["把阈值调到很大", "先 ANALYZE TABLE 补统计信息，再 explain 看是否自动广播", "改成 crossJoin", "重启 SparkSession"], "correct_index": 1, "explanation": "统计信息缺失会让优化器保守按大表处理，补上统计往往一步解决。", "dimension": "apply"},
        {"type": "single_choice", "prompt": "「调大阈值」与「禁用广播」的代价分别是？", "options": ["调大：每个 Executor 多一份常驻副本；禁用：小表也走 SMJ，多付两次 Shuffle", "两者都没有代价", "调大：结果变错；禁用：变快", "两者等价"], "correct_index": 0, "explanation": "一个是内存账单，一个是网络账单，都不免费——按表逐个判断才对。", "dimension": "comparison"},
        {"type": "single_choice", "prompt": "广播的内存账单是怎样的？", "options": ["只在 Driver 存一份", "只在网络传输，不占内存", "按分区数分摊，总量不变", "每个 Executor 各存一份被广播表的完整副本"], "correct_index": 3, "explanation": "复用 L6：广播反噬就来自「每个 Executor 各一份」这份常驻内存账。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "把广播阈值调得很大的主要风险是？", "options": ["结果行数变多", "很多表被判为小表全部广播，每个 Executor 内存被吃光甚至 OOM", "计划变得更复杂", "会禁用 AQE"], "correct_index": 1, "explanation": "只在确认表真的小、且能省掉最大那次 Shuffle 时才调。", "dimension": "why"},
        {"type": "single_choice", "prompt": "调整阈值或加了 hint 之后，必须做什么？", "options": ["直接上线", "清空缓存", "再 explain 复核：确认计划里真的出现了 BroadcastExchange", "重启 Executor"], "correct_index": 2, "explanation": "hint 与阈值都可能不生效或被忽略（L6 的规矩），不复核等于没做。", "dimension": "mechanism"},
        {"type": "single_choice", "prompt": "Executor 内存紧张时的正确做法是？", "options": ["把广播一刀切禁掉", "把所有表都广播", "把阈值设为 0", "按表逐个判断：该广播的用 hint 精确指定，不该广播的保持默认"], "correct_index": 3, "explanation": "一刀切会误伤本该广播的小表；精确指定才是控制内存的正解。", "dimension": "apply"},
        {"type": "single_choice", "prompt": "调阈值与加 broadcast hint 的区别是？", "options": ["完全等价", "阈值改的是全局判定标准；hint 是对某一次 join 精确表达倾向", "hint 更粗暴", "阈值只对 SQL 生效"], "correct_index": 1, "explanation": "先用统计信息让全局判断变准，个别场景再用 hint 精确干预。", "dimension": "comparison"}
    ]},
    {"lesson_slug": "l7-aqe", "questions": [
        {"type": "single_choice", "prompt": "AQE（自适应查询执行）指的是？", "options": ["一种新的文件格式", "自动加索引的功能", "把作业拆成多个作业并行跑", "运行时依据真实 Shuffle 统计重新优化剩余执行计划的机制"], "correct_index": 3, "explanation": "它把「出发前定死路线」改成「边跑边看路况再改道」。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "为什么需要 AQE？", "options": ["因为 explain 太慢", "因为规划期只能靠统计估计，估计错了优化就白做；运行时才有真相", "因为集群不稳定", "因为 SQL 太复杂"], "correct_index": 1, "explanation": "这正是 L6 第 6 课「估计会误判」的兜底方案。", "dimension": "why"},
        {"type": "single_choice", "prompt": "AQE 的「观察点」是什么？", "options": ["Shuffle 完成后拿到各分区的真实大小", "读取文件时", "Action 返回结果时", "广播分发时"], "correct_index": 0, "explanation": "没有 shuffle 的地方拿不到真实分布，所以 AQE 在那里也无从优化。", "dimension": "mechanism"},
        {"type": "single_choice", "prompt": "开启 AQE 后，验证效果应看？", "options": ["只看 explain 的静态输出", "只看代码", "Spark UI 的实际执行图与 Task 分布", "看输出文件数"], "correct_index": 2, "explanation": "AQE 会在运行时改计划，静态 explain 展示的是初始计划，不再是最终真相。", "dimension": "apply"},
        {"type": "single_choice", "prompt": "静态计划与 AQE 最终执行计划的关系是？", "options": ["永远一致", "可能不同：AQE 会在运行时改写剩余计划（合并分区/切广播/拆倾斜）", "静态计划优先，AQE 不能改", "只在本地模式会不同"], "correct_index": 1, "explanation": "开 AQE 后要以实际执行图为准，别只信 explain。", "dimension": "comparison"},
        {"type": "single_choice", "prompt": "AQE 的三大典型能力是？", "options": ["动态合并小分区 / 运行时切换 JOIN 策略 / 自动处理倾斜 join", "列裁剪 / 谓词下推 / 常量折叠", "广播 / 排序 / 聚合", "缓存 / 重试 / 推测执行"], "correct_index": 0, "explanation": "前两项分别补上了手动调分区数与手动调广播阈值的盲区，第三项是第 7 课的手段之一。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "为什么 AQE 不是万能的？", "options": ["它经常算错结果", "它只支持 SQL", "它优化的是已读入数据的执行方式，解决不了「读太多」或 UDF 太慢", "它只能用于小数据集"], "correct_index": 2, "explanation": "减量优先于调速（第 1 课结论）：AQE 修不了没读对数据的问题。", "dimension": "why"},
        {"type": "single_choice", "prompt": "AQE 的动态合并分区主要解决什么问题？", "options": ["数据倾斜", "广播太慢", "结果文件太大", "分区设得过多时产生的大量小 Task 与调度开销"], "correct_index": 3, "explanation": "它让你不必把「分区数设多少」纠结到极致——过多时运行时会自动合并。", "dimension": "mechanism"},
        {"type": "single_choice", "prompt": "运行时发现原本以为很大的一侧其实很小，AQE 会？", "options": ["把后续 join 改走 Broadcast Hash Join，省掉大表那次 Shuffle", "保持 Sort-Merge Join 不变", "报错并中止", "自动重新读取一次数据"], "correct_index": 0, "explanation": "这正是「估计会误判」的运行时纠正，也是 L6 手动 hint 的自动化版本。", "dimension": "apply"},
        {"type": "single_choice", "prompt": "AQE 与手动调参相比，正确的理解是？", "options": ["有了 AQE 就不用学手动调优了", "手动调参一定比 AQE 准", "AQE 是兜底与增益，减量与 SQL 改写仍是收益最大的手段", "两者互斥，只能选一个"], "correct_index": 2, "explanation": "AQE 不替代「少读少传少算」，它是在此之上的运行时增强。", "dimension": "comparison"}
    ]},
    {"lesson_slug": "l7-skew-tuning", "questions": [
        {"type": "single_choice", "prompt": "在 Spark UI 里判断数据倾斜，最直接的指标是？", "options": ["Task 耗时最大值远大于中位数 / Shuffle Read 分布极不均", "Stage 数量很多", "计划里 Exchange 数量", "输出文件数量"], "correct_index": 0, "explanation": "计划里看不出倾斜（L6 的边界），只有运行时分布能暴露它。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "为什么不该一说倾斜就立刻加盐？", "options": ["加盐会报错", "加盐只适用于 groupBy", "加盐要把另一侧膨胀 N 倍，是最重的手段；AQE 或隔离大 key 往往更划算", "加盐需要管理员权限"], "correct_index": 2, "explanation": "手段有优先级：先试代价小的，最后才上重手段。", "dimension": "why"},
        {"type": "single_choice", "prompt": "salting 加盐的机制是？", "options": ["给两侧都加随机后缀", "大 key 侧加随机后缀打散成 N 份，另一侧把该 key 记录复制 N 份以匹配", "把大 key 直接删掉", "把 key 换成行号"], "correct_index": 1, "explanation": "两侧必须严格对应：一侧加后缀、另一侧膨胀匹配，写错了结果会多算或少算。", "dimension": "mechanism"},
        {"type": "single_choice", "prompt": "怀疑 join 倾斜时，第一步应该？", "options": ["立刻写 salting 代码", "把分区数调大", "禁用广播", "先用 groupBy key 看分布，确认是哪些 key 撑爆的"], "correct_index": 3, "explanation": "先定位具体 key（常见元凶是 null/未知/默认值），再谈怎么治。", "dimension": "apply"},
        {"type": "single_choice", "prompt": "「隔离大 key」与「全量加盐」相比？", "options": ["两者代价相同", "隔离大 key 会改变结果", "隔离大 key 只处理极少数巨型 key，代价远小于把整侧数据膨胀 N 倍", "全量加盐一定更快"], "correct_index": 2, "explanation": "把极端少数与正常多数分开处理，通常比一刀切加盐划算得多。", "dimension": "comparison"},
        {"type": "single_choice", "prompt": "加盐最主要的代价是？", "options": ["需要额外的磁盘空间存中间结果", "另一侧数据要膨胀 N 倍，key 一多就得不偿失", "结果会变错", "会禁用 AQE"], "correct_index": 1, "explanation": "所以它只适合少数巨型 key，或配合隔离只对那一小撮数据使用。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "造成倾斜最常见的元凶是？", "options": ["文件太大", "集群节点太少", "使用了 Parquet 格式", "null / 未知 / 默认值这类被大量记录共用的 key"], "correct_index": 3, "explanation": "这类 key 常常业务上也不需要，先过滤掉往往就解决了大半。", "dimension": "why"},
        {"type": "single_choice", "prompt": "用广播绕过倾斜为什么有效？", "options": ["大表不再按 key 重排，自然不存在「某 key 撑爆某分区」", "广播会自动过滤大 key", "广播会重写数据分布", "广播会减少行数"], "correct_index": 0, "explanation": "倾斜是「按 key 重分布」的副产品；取消大表那次重排，倾斜无从谈起。", "dimension": "mechanism"},
        {"type": "single_choice", "prompt": "使用 salting 之后必须做什么？", "options": ["直接交付", "核对结果行数/关键指标，确认与加盐前语义一致", "立刻清理缓存", "把随机种子固定下来即可"], "correct_index": 1, "explanation": "改 key 有语义风险：「看起来跑完了」不等于「算对了」。", "dimension": "apply"},
        {"type": "single_choice", "prompt": "AQE 自动倾斜处理与手动加盐的关系是？", "options": ["完全等价", "AQE 内部就是加盐", "开了 AQE 就不能加盐", "优先试 AQE（代价低、零代码改动）；不奏效再考虑隔离或加盐"], "correct_index": 3, "explanation": "按代价从低到高推进：AQE → 隔离大 key → 加盐 → 广播绕过 → 过滤异常 key。", "dimension": "comparison"}
    ]},
    {"lesson_slug": "l7-read-less-data", "questions": [
        {"type": "single_choice", "prompt": "本课归纳的减量三层次是？", "options": ["多核 / 多机 / 多磁盘", "少读 / 少传 / 少算", "缓存 / 广播 / 加盐", "读 / 写 / 同步"], "correct_index": 1, "explanation": "三个层次对应「进来的数据、传的数据、算的次数」，逐层递进。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "为什么「减量」优先于「调速」？", "options": ["减量更容易实现", "参数调优已废弃", "减量不会出错", "少读少传省的是数量级的 I/O 与网络，收益通常远大于参数微调"], "correct_index": 3, "explanation": "在错误的量级上做参数微调，怎么调都是原地打转。", "dimension": "why"},
        {"type": "single_choice", "prompt": "谓词下推能否真正生效，主要取决于？", "options": ["SQL 写得是否整齐", "集群节点数", "数据源格式：Parquet/ORC 这类列式格式效果好，CSV 有限", "分区数设置"], "correct_index": 2, "explanation": "复用 L4 的边界：下推能否发生取决于数据源。", "dimension": "mechanism"},
        {"type": "single_choice", "prompt": "一份 200 列、按天分区的事实表只要其中 5 列和一天数据，应该先做？", "options": ["列裁剪（只 select 需要的列）+ 分区裁剪与谓词下推", "先把分区数调大", "先 cache 起来", "先 join 再过滤"], "correct_index": 0, "explanation": "这是收益最大的一步：直接从磁盘少读掉绝大部分字节。", "dimension": "apply"},
        {"type": "single_choice", "prompt": "在「少算」这一层，内置函数优于 UDF 的原因是？", "options": ["内置函数名字更短", "UDF 不支持 Python", "内置函数会缓存结果", "内置函数 Catalyst 认得、可优化且直接在 Tungsten 字节上算；UDF 要跨 JVM 还原对象"], "correct_index": 3, "explanation": "这正是 L3 埋下的伏笔，在第 8 课被归到「少算」这一层。", "dimension": "comparison"},
        {"type": "single_choice", "prompt": "map-side combine 属于减量的哪一层？", "options": ["少读", "少算", "少传（本地先聚合，只把小包空运）", "不属于减量"], "correct_index": 2, "explanation": "复用 L5 的「车间本地先捆小包再空运」：省的是网络传输量。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "为什么 cache() 未必划算？", "options": ["它占 Storage Memory、可能被逐出；只用一次时重算往往比读缓存更便宜", "cache 会改变结果", "cache 只对小表有效", "cache 会触发 Shuffle"], "correct_index": 0, "explanation": "只在「会被多次复用且重算代价高」时才缓存，用完记得 unpersist。", "dimension": "why"},
        {"type": "single_choice", "prompt": "关于分桶（bucketing），正确的是？", "options": ["它是随手能开的加速开关", "它是写入侧的布局约定：按 key 预先分桶写出，可让后续按同 key 的 join 省去一次 Shuffle", "它等同于分区目录", "它只影响文件大小"], "correct_index": 1, "explanation": "分桶是建模决策，需要在写入时就规划好，不是运行时开关。", "dimension": "mechanism"},
        {"type": "single_choice", "prompt": "「先 join 再过滤」与「先过滤再 join」，后者好在？", "options": ["代码更短", "结果更准确", "参与 Shuffle 的数据量骤减，网络与内存压力大幅下降", "可以避免 Shuffle"], "correct_index": 2, "explanation": "先裁剪再关联是最划算的一步，属于「少传」。", "dimension": "apply"},
        {"type": "single_choice", "prompt": "判断该不该 cache 一个中间结果，关键问题是？", "options": ["它会被复用几次？重算代价高不高？", "它有多少列", "它是否来自 Parquet", "它的分区数是多少"], "correct_index": 0, "explanation": "多次复用且重算昂贵 → 值得缓存；只用一次 → 重算通常更便宜。", "dimension": "comparison"}
    ]},
    {"lesson_slug": "l7-comprehensive", "questions": [
        {"type": "single_choice", "prompt": "本课给出的调优检查单顺序是？", "options": ["调参 → 减量 → 倾斜 → 复测", "先加盐 → 再调分区 → 最后 explain", "量（explain+UI）→ 归类 → 按优先级改（少读>少传>少算>调旋钮，倾斜专项在后）→ 改一处测一次", "先换集群 → 再改代码"], "correct_index": 2, "explanation": "这张单子是九课的收口：诊断流程 + 优先级 + 每次只改一处。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "为什么优先级是「少读 > 少传 > 少算 > 调旋钮」？", "options": ["越靠前省掉的工作量越大、代价越小；参数调优是最后一道工序", "按字母顺序排列", "因为参数很难记", "因为后面的手段容易出错"], "correct_index": 0, "explanation": "能在数据量上解决的问题，就别去动参数——这是全课的结论。", "dimension": "why"},
        {"type": "single_choice", "prompt": "「改一处、测一次」的意义在于？", "options": ["显得专业", "Spark 要求这么做", "可以少写代码", "能归因：知道改善来自哪一步，经验可迁移；无改善则回滚换路"], "correct_index": 3, "explanation": "一次改五个参数，就算变快也无法归因，更无法沉淀为下个作业的经验。", "dimension": "mechanism"},
        {"type": "single_choice", "prompt": "拿到一个跑了 40 分钟的慢作业，第一步是？", "options": ["把 shuffle 分区数翻倍", "explain 看计划 + Spark UI 看运行时，先定位最慢的 Stage 与瓶颈类别", "给所有表加 cache", "直接重写成 SQL"], "correct_index": 1, "explanation": "先量后动是第 1 课立下的规矩，也是整张检查单的起点。", "dimension": "apply"},
        {"type": "single_choice", "prompt": "在诊断流程中，explain 与 Spark UI 的分工是？", "options": ["explain 看静态计划（零成本、定方向），UI 看运行时（耗时分布/spill/Shuffle 量、定位置）", "两者完全等价", "UI 只能看失败的作业", "explain 会执行作业"], "correct_index": 0, "explanation": "计划相同 ≠ 运行时相同；倾斜与 spill 只有 UI 能告诉你。", "dimension": "comparison"},
        {"type": "single_choice", "prompt": "参数调优在整个流程中处于什么位置？", "options": ["第一步就该做", "永远不需要", "只在大集群才做", "最后一道工序：先减量、再治倾斜，参数调节放在后面"], "correct_index": 3, "explanation": "参数是在「已经读对、传对、算对」之后做微调，不是第一步。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "一次改完全部想到的优化并跑通就交付，最大的隐患是？", "options": ["代码变长", "无法归因，且某些改动在其他数据量下可能变成负担", "Spark 会拒绝执行", "结果一定会错"], "correct_index": 1, "explanation": "没有逐项度量，你就不知道哪一步真的有效，也不知道哪一步有副作用。", "dimension": "why"},
        {"type": "single_choice", "prompt": "方案中用到了 salting，交付前必须验证？", "options": ["集群负载", "文件数量", "结果行数与关键指标是否与加盐前一致（语义未变）", "缓存命中率"], "correct_index": 2, "explanation": "改 key 有语义风险，必须验证结果正确性——这是第 7 课的硬要求。", "dimension": "mechanism"},
        {"type": "single_choice", "prompt": "50 亿行事实表 join 10 万行维表，合理的推进顺序是？", "options": ["先加盐处理倾斜", "先把分区数调到 5000", "先把维表 cache 起来", "先列裁剪与分区裁剪 → 补统计信息或广播维表 → 再考虑分区数/AQE → 最后查倾斜"], "correct_index": 3, "explanation": "减量 → 少传（广播）→ 调旋钮 → 倾斜专项，正是检查单的顺序。", "dimension": "apply"},
        {"type": "single_choice", "prompt": "关于「减量」与「参数调优」的收益对比，正确的是？", "options": ["两者收益相当", "减量通常带来数量级的改善，参数调优多是在此基础上做微调", "参数调优收益更大", "减量只对小作业有效"], "correct_index": 1, "explanation": "这是全课最该带走的一条：先问「这份数据里有多少是必需的」。", "dimension": "comparison"}
    ]}
]


def upsert():
    # 1) 合并进 course_seed.json
    with open(SEED, encoding="utf-8") as f:
        data = json.load(f)
    exists = any(lv.get("order_index") == 7 for lv in data["levels"])
    if not exists:
        data["levels"].append(LEVEL7)
        with open(SEED, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print("已写入 course_seed.json（Level 7）")
    else:
        print("course_seed.json 已存在 Level 7，跳过 JSON 写入")

    # 2) 合并进 quiz_seed.json
    with open(QUIZ, encoding="utf-8") as f:
        qdata = json.load(f)
    qentries = qdata.setdefault("quizzes", [])
    existing = {e["lesson_slug"] for e in qentries}
    added_q = 0
    for entry in LEVEL7_QUIZZES:
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
        print("quiz_seed.json 已包含 Level 7 题库，跳过")

    # 3) upsert 进数据库
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT id,title FROM course_levels WHERE order_index=7")
    row = cur.fetchone()
    if row:
        level_id = row[0]
        print(f"Level 7 已存在于 DB (id={level_id})，仅补充缺失 lesson")
    else:
        cur.execute(
            "INSERT INTO course_levels (title, description, order_index, status) VALUES (?,?,?,?)",
            (LEVEL7["title"], LEVEL7["description"], LEVEL7["order_index"], "active"))
        level_id = cur.lastrowid
        print(f"已插入 Level 7 (id={level_id})")

    inserted_lessons = 0
    for ls in LEVEL7["lessons"]:
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
    for entry in LEVEL7_QUIZZES:
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
