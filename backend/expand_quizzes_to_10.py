"""Phase 6.1/6.2 — expand L0/L1 (4->10) and L2 (5->10) quiz banks.

This script:
  1. Updates `app/quiz_seed.json` for the 11 L0/L1 (4->10) and 10 L2 (5->10) lessons:
        - tags the existing questions with a `dimension`
        - appends new questions (also dimension-tagged) up to 10 total
      Idempotent: only appends when a lesson has < 10 questions.
  2. Updates the running database (if present):
        - backfills `dimension` on the existing L0/L1/L2 quiz rows
        - inserts the new questions per lesson (dedup by prompt)

Dimension vocabulary is open (concept / why / mechanism / apply / comparison /
debug, ...). We do NOT force every lesson to cover a fixed set; we just keep a
reasonable variety. Sampling (in routers/quizzes.py) prefers dimension diversity
but without a hard constraint.

Run from the backend directory:
    cd backend
    python expand_quizzes_to_10.py
"""

import json
import os
import sys

# Allow `from app...` imports when run as a plain script from backend/.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import select, func

from app.database import SessionLocal, engine
from app.models import Lesson, QuizQuestion

SEED_FILE = os.path.join(os.path.dirname(__file__), "app", "quiz_seed.json")

# The 11 L0/L1 lesson slugs we expand in this phase.
L0L1_SLUGS = [
    "l0-what-is-spark",
    "l0-what-problem-spark-solves",
    "l0-driver-executor",
    "l0-sparksession",
    "l0-first-pyspark-program",
    "l1-what-is-rdd",
    "l1-transformation",
    "l1-action",
    "l1-lazy-evaluation",
    "l1-why-dataframe-replaces-rdd",
    "l1-rdd-exercise",
]

# The 10 Level 2 lesson slugs expanded in Phase 6.2.
L2_SLUGS = [
    "l2-what-is-dataframe",
    "l2-create-dataframe",
    "l2-schema-types",
    "l2-inspect",
    "l2-select-filter",
    "l2-withcolumn",
    "l2-sort-dedup",
    "l2-groupby-agg",
    "l2-write-data",
    "l2-comprehensive",
]

# All lessons handled by this (idempotent) expansion script.
ALL_SLUGS = L0L1_SLUGS + L2_SLUGS

# Dimension tags for the EXISTING questions (L0/L1: 4 each; L2: 5 each), in order.
EXISTING_DIM = {
    "l0-what-is-spark": ["concept", "concept", "apply", "concept"],
    "l0-what-problem-spark-solves": ["concept", "why", "comparison", "comparison"],
    "l0-driver-executor": ["concept", "concept", "mechanism", "debug"],
    "l0-sparksession": ["concept", "apply", "concept", "apply"],
    "l0-first-pyspark-program": ["debug", "apply", "apply", "debug"],
    "l1-what-is-rdd": ["concept", "mechanism", "mechanism", "why"],
    "l1-transformation": ["concept", "mechanism", "apply", "comparison"],
    "l1-action": ["concept", "mechanism", "apply", "concept"],
    "l1-lazy-evaluation": ["why", "mechanism", "concept", "debug"],
    "l1-why-dataframe-replaces-rdd": ["why", "concept", "comparison", "comparison"],
    "l1-rdd-exercise": ["apply", "apply", "apply", "mechanism"],
    # ---- Level 2 (Phase 6.2): tag the existing 5 questions each ----
    "l2-what-is-dataframe": ["concept", "why", "mechanism", "apply", "comparison"],
    "l2-create-dataframe": ["concept", "apply", "mechanism", "apply", "debug"],
    "l2-schema-types": ["concept", "why", "debug", "apply", "concept"],
    "l2-inspect": ["concept", "debug", "debug", "apply", "concept"],
    "l2-select-filter": ["concept", "mechanism", "mechanism", "apply", "concept"],
    "l2-withcolumn": ["concept", "mechanism", "apply", "apply", "concept"],
    "l2-sort-dedup": ["concept", "mechanism", "apply", "apply", "concept"],
    "l2-groupby-agg": ["concept", "mechanism", "concept", "apply", "concept"],
    "l2-write-data": ["concept", "debug", "apply", "apply", "concept"],
    "l2-comprehensive": ["concept", "apply", "concept", "apply", "concept"],
}

# 6 new questions per lesson (dimension-tagged). Keeps existing natural variety;
# not forced to a fixed dimension set.
NEW_QUESTIONS = {
    "l0-what-is-spark": [
        {
            "type": "single_choice",
            "dimension": "why",
            "prompt": "为什么数据大到一定程度，pandas 会越来越吃力？",
            "options": [
                "Python 的 GIL 让它基本只能单核，且数据超出本机内存就无处可放",
                "pandas 不支持任何文件格式",
                "pandas 必须联网才能运行",
                "pandas 只能处理字符串，不能处理数字",
            ],
            "correct_index": 0,
            "explanation": "pandas 受 GIL 限制基本单线程，且数据需放进本机内存；数据超过内存或需要并行时力不从心，这正是 Spark 的用武之地。",
        },
        {
            "type": "single_choice",
            "dimension": "mechanism",
            "prompt": "Spark 把一份大数据切成很多「分区」，主要目的是？",
            "options": [
                "让多台机器的 CPU/内存可以并行处理不同分区",
                "为了让文件看起来更小",
                "为了禁止用户看到全部数据",
                "为了把数据全部集中到 Driver 一个进程",
            ],
            "correct_index": 0,
            "explanation": "分区是 Spark 并行的基础：每个分区可被不同 Executor 并行处理，从而把大任务拆到多机多核上。",
        },
        {
            "type": "single_choice",
            "dimension": "comparison",
            "prompt": "Spark 与传统的单机 Python（pandas）最本质的区别是？",
            "options": [
                "Spark 为分布式、可横向扩展；pandas 为单机、受本机资源限制",
                "Spark 只能处理文本，pandas 只能处理数字",
                "两者完全相同，只是名字不同",
                "Spark 不需要数据，pandas 需要数据",
            ],
            "correct_index": 0,
            "explanation": "本质区别在架构：Spark 分布式、可水平扩展；pandas 单机、受单机内存与单线程限制。",
        },
        {
            "type": "single_choice",
            "dimension": "apply",
            "prompt": "下面哪个信号提示「该考虑上 Spark 了」？",
            "options": [
                "处理时间随数据量线性变长，单机内存开始报警",
                "代码里 print 太多",
                "变量名太长",
                "用了太多循环",
            ],
            "correct_index": 0,
            "explanation": "当单机资源（内存/CPU）成为瓶颈、数据装不下或算不动时，就是引入 Spark 的信号。",
        },
        {
            "type": "single_choice",
            "dimension": "debug",
            "prompt": "初次运行 Spark 程序卡在「JVM 启动 / 申请资源」，最可能的原因是？",
            "options": [
                "本机没装 Java，或 JAVA_HOME 没配置对",
                "Python 版本太低导致语法错误",
                "没写 import pandas",
                "网络断了连不上数据库",
            ],
            "correct_index": 0,
            "explanation": "Spark 运行在 JVM 上，Java 缺失或 JAVA_HOME 配置错误会导致连启动都失败；这是新手最常见的环境坑。",
        },
        {
            "type": "single_choice",
            "dimension": "concept",
            "prompt": "关于「分布式计算」，最准确的说法是？",
            "options": [
                "把一个大计算拆到多台机器上并行完成，再汇总结果",
                "把一台机器拆成多台",
                "只用一台机器但开很多窗口",
                "把数据全部删掉再算",
            ],
            "correct_index": 0,
            "explanation": "分布式计算=把任务分到多机并行、最后汇总；Spark 正是为此而生。",
        },
    ],
    "l0-what-problem-spark-solves": [
        {
            "type": "single_choice",
            "dimension": "mechanism",
            "prompt": "MapReduce 为什么慢？Spark 又是怎么改进的？",
            "options": [
                "MapReduce 每阶段结果都落盘；Spark 用内存 + DAG 减少落盘",
                "MapReduce 太快导致没人用",
                "Spark 把数据全部删了重算",
                "两者速度一样",
            ],
            "correct_index": 0,
            "explanation": "MapReduce 每阶段中间结果写磁盘，I/O 重；Spark 用内存缓存 + DAG 整体调度，大幅减少落盘。",
        },
        {
            "type": "single_choice",
            "dimension": "apply",
            "prompt": "公司每天有 5 亿条用户日志要统计，最合适的处理方式是？",
            "options": [
                "用 Spark 做分布式批处理",
                "用 Excel 打开统计",
                "用记事本逐行看",
                "用手机计算器加总",
            ],
            "correct_index": 0,
            "explanation": "这种远超单机能力、且持续产生的数据，正是 Spark 分布式批处理的典型场景。",
        },
        {
            "type": "single_choice",
            "dimension": "debug",
            "prompt": "集群里某台机器宕机，Spark 作业却没失败，靠的是？",
            "options": [
                "血缘（lineage）重算丢失的分区，容错恢复",
                "把数据复制了 100 份",
                "人工重启",
                "自动删除该数据",
            ],
            "correct_index": 0,
            "explanation": "Spark 靠 lineage 在分区丢失时自动重算，无需数据副本也能容错，这是弹性的来源。",
        },
        {
            "type": "single_choice",
            "dimension": "concept",
            "prompt": "大数据三难中的「Velocity（来得快）」指的是？",
            "options": [
                "数据以很高速度持续产生，需要近实时处理",
                "数据移动速度受网线限制",
                "硬盘转速",
                "CPU 频率",
            ],
            "correct_index": 0,
            "explanation": "Velocity 指数据高速、持续地产生（如日志、点击流），要求系统能近实时地承接。",
        },
        {
            "type": "single_choice",
            "dimension": "comparison",
            "prompt": "Spark 与 MapReduce 相比，定位更接近？",
            "options": [
                "MapReduce 是早期批处理框架；Spark 在其上做了内存与 DAG 优化，更快更通用",
                "两者毫无关系",
                "MapReduce 比 Spark 新",
                "Spark 只能画图",
            ],
            "correct_index": 0,
            "explanation": "Spark 不是推翻 MapReduce，而是在其编程模型上用内存与 DAG 引擎做了性能与易用性升级。",
        },
        {
            "type": "single_choice",
            "dimension": "why",
            "prompt": "为什么「水平扩展」（加机器）比「垂直扩展」（换大机器）更可持续？",
            "options": [
                "加普通机器成本线性、可近乎无限扩展，且避免单点故障",
                "垂直扩展更便宜",
                "水平扩展会丢失数据",
                "垂直扩展没有上限",
            ],
            "correct_index": 0,
            "explanation": "垂直扩展有物理/成本上限且单机挂掉全完蛋；水平扩展用廉价机器堆叠，容错与扩展性都更好。",
        },
    ],
    "l0-driver-executor": [
        {
            "type": "single_choice",
            "dimension": "apply",
            "prompt": "想让 Spark 真正开始算并拿到结果，应该调用？",
            "options": [
                "count() / collect() 这类 Action",
                "df.filter(...)",
                "spark.read.csv(...)",
                "定义一个 map 函数",
            ],
            "correct_index": 0,
            "explanation": "只有 Action（如 count/collect）才会触发 Job；filter/read/map 都只是 Transformation，只记账。",
        },
        {
            "type": "single_choice",
            "dimension": "why",
            "prompt": "为什么 Driver 不能也负责「真正执行数据计算」？",
            "options": [
                "数据分散在多机，Driver 单进程无法高效并行处理全量数据",
                "Driver 没有 CPU",
                "Driver 只负责存密码",
                "Executor 不允许计算",
            ],
            "correct_index": 0,
            "explanation": "真正的数据计算被下放到各 Executor 并行执行；Driver 只负责编排与汇总，否则就退回单机了。",
        },
        {
            "type": "single_choice",
            "dimension": "comparison",
            "prompt": "Driver 与 Executor 的关系，正确的是？",
            "options": [
                "Driver 制定计划并分发任务，Executor 执行任务并返回结果",
                "Executor 给 Driver 派活",
                "两者互不通信",
                "Driver 执行、Executor 计划",
            ],
            "correct_index": 0,
            "explanation": "典型主从关系：Driver 是大脑（计划/分发/汇总），Executor 是手脚（执行/返回）。",
        },
        {
            "type": "single_choice",
            "dimension": "concept",
            "prompt": "Executor 在执行期间，数据主要存在于？",
            "options": [
                "它自己负责的内存/磁盘分区上，而非 Driver",
                "全部在 Driver 内存",
                "全部在数据库",
                "全部在屏幕",
            ],
            "correct_index": 0,
            "explanation": "数据以分区形式分布在各 Executor 上就近计算，Driver 只持有计划与最终结果。",
        },
        {
            "type": "single_choice",
            "dimension": "mechanism",
            "prompt": "Task 是 Spark 调度的最小单位，它对应？",
            "options": [
                "某个分区上的一段计算逻辑（如一个 map）",
                "整个作业",
                "一个 DataFrame",
                "一行代码",
            ],
            "correct_index": 0,
            "explanation": "Task = 在一个分区上执行的一段计算（一个 Transformation 步骤），是调度与失败重试的最小单元。",
        },
        {
            "type": "single_choice",
            "dimension": "debug",
            "prompt": "Executor 因 OOM 频繁挂掉，首先应排查？",
            "options": [
                "是否用 collect/toPandas 把过多数据拉回 Driver，或分区是否过大",
                "Python 版本",
                "显示器分辨率",
                "网线颜色",
            ],
            "correct_index": 0,
            "explanation": "Executor OOM 常因单个分区过大或把数据全拉回 Driver；应调分区大小或用 take/write 代替 collect。",
        },
    ],
    "l0-sparksession": [
        {
            "type": "single_choice",
            "dimension": "why",
            "prompt": "为什么 Spark 2.0 之后用 SparkSession 统一入口，而不再直接用 SparkContext？",
            "options": [
                "SparkSession 在一个入口里整合了 SQL / DataFrame / 流处理等能力",
                "SparkContext 被删除了",
                "因为 SparkSession 更快",
                "因为 SparkContext 只能处理图片",
            ],
            "correct_index": 0,
            "explanation": "SparkSession 是统一门面，内部封装 SparkContext，并整合了 SQL、DataFrame、Structured Streaming 等入口。",
        },
        {
            "type": "single_choice",
            "dimension": "mechanism",
            "prompt": "getOrCreate() 的作用是？",
            "options": [
                "已存在则复用，不存在则创建，保证全局唯一、避免重复启动",
                "每次都新建一个",
                "删除已有 session",
                "强制停止",
            ],
            "correct_index": 0,
            "explanation": "getOrCreate 避免重复创建昂贵的 SparkSession；全局共享一个，是标准用法。",
        },
        {
            "type": "single_choice",
            "dimension": "comparison",
            "prompt": "SparkSession 与 SparkContext 的关系是？",
            "options": [
                "SparkSession 内部封装了 SparkContext，是面向用户的统一门面",
                "两者独立、互不相干",
                "SparkContext 包含 SparkSession",
                "两者是同一种东西的不同名字",
            ],
            "correct_index": 0,
            "explanation": "老代码直接操作 SparkContext；新代码用 SparkSession，它背后仍然持有 SparkContext。",
        },
        {
            "type": "single_choice",
            "dimension": "debug",
            "prompt": "程序报 'Unable to instantiate SparkSession' 之类的初始化错误，通常先查？",
            "options": [
                "Java/JVM 是否可用、版本是否匹配、依赖是否装全",
                "是否写了太多注释",
                "变量名是否中文",
                "网络是否连上数据库",
            ],
            "correct_index": 0,
            "explanation": "SparkSession 初始化依赖 JVM 与完整依赖；Java 缺失/版本错是最常见根因。",
        },
        {
            "type": "single_choice",
            "dimension": "concept",
            "prompt": "SparkSession 创建后，我们用它来？",
            "options": [
                "读数据、建 DataFrame、执行 SQL 等一切入口操作",
                "只能关闭程序",
                "只能打印日志",
                "只能连接数据库",
            ],
            "correct_index": 0,
            "explanation": "SparkSession 是总入口：read、createDataFrame、sql、stop 等都通过它。",
        },
        {
            "type": "single_choice",
            "dimension": "apply",
            "prompt": "哪段代码能正确『若不存在则创建、存在则复用』SparkSession？",
            "options": [
                "SparkSession.builder.appName('x').getOrCreate()",
                "SparkSession.new()",
                "spark = open('session')",
                "SparkSession.create()",
            ],
            "correct_index": 0,
            "explanation": "标准写法是用 builder 配置后调用 getOrCreate，保证幂等复用。",
        },
    ],
    "l0-first-pyspark-program": [
        {
            "type": "single_choice",
            "dimension": "concept",
            "prompt": "一个 PySpark 程序的标准生命周期是？",
            "options": [
                "建 session → 读数据 → 变换/统计 → 取结果/写盘 → stop",
                "stop → 读 → 写",
                "读 → 随便 print 变量",
                "装 Java → 跑 SQL",
            ],
            "correct_index": 0,
            "explanation": "所有 Spark 程序都是这一骨架的变体：先有 session，再读、算、取结果，最后 stop 释放资源。",
        },
        {
            "type": "single_choice",
            "dimension": "why",
            "prompt": "为什么读取大文件后不要急于 collect() 到本地？",
            "options": [
                "会把所有 Executor 数据拉回 Driver 单进程，极易 OOM",
                "collect 会删除数据",
                "collect 很慢但安全",
                "本地没有内存也能装",
            ],
            "correct_index": 0,
            "explanation": "collect 把分布式数据全量汇聚到 Driver 一个进程，数据大时直接把 Driver 内存打爆。",
        },
        {
            "type": "single_choice",
            "dimension": "mechanism",
            "prompt": "spark.read.csv(path) 返回 DataFrame 时，数据已经被读进内存了吗？",
            "options": [
                "没有，read 是惰性的，只登记读取计划，真正读取等 Action",
                "已经全部读进内存",
                "已经写回磁盘",
                "已经发到屏幕",
            ],
            "correct_index": 0,
            "explanation": "read 是 Transformation，惰性；只有 show/count/write 等 Action 才真正触发读取与计算。",
        },
        {
            "type": "single_choice",
            "dimension": "apply",
            "prompt": "要把结果保存为 CSV，应该调用？",
            "options": [
                "df.write.csv(path)",
                "df.save()",
                "print(df)",
                "df.to_csv()",
            ],
            "correct_index": 0,
            "explanation": "Spark DataFrame 写出用 df.write.csv(...)；to_csv 是 pandas 的方法，对 Spark DataFrame 不存在。",
        },
        {
            "type": "single_choice",
            "dimension": "comparison",
            "prompt": "PySpark 与 pandas 在『读取并统计』上的区别是？",
            "options": [
                "pandas 单机内存计算；PySpark 分布式，数据可远大于单机内存",
                "两者都只能处理小数据",
                "pandas 更快永远更好",
                "PySpark 不能统计",
            ],
            "correct_index": 0,
            "explanation": "本质区别在规模：pandas 受单机内存限制，PySpark 可处理远超单机内存的数据。",
        },
        {
            "type": "single_choice",
            "dimension": "debug",
            "prompt": "程序一运行就报 Java gateway / JVM 相关错误，首先应？",
            "options": [
                "确认本机已安装匹配版本的 Java 且 JAVA_HOME 指向它",
                "重装 Python",
                "换显示器",
                "删代码",
            ],
            "correct_index": 0,
            "explanation": "PySpark 通过 JVM 通信，Java 缺失或版本不匹配会直接初始化失败。",
        },
    ],
    "l1-what-is-rdd": [
        {
            "type": "single_choice",
            "dimension": "apply",
            "prompt": "要把 [1,2,3,4,5] 变成分布式 RDD，应该？",
            "options": [
                "sc.parallelize([1,2,3,4,5])",
                "pd.DataFrame([1,2,3,4,5])",
                "spark.read.csv(...)",
                "[1,2,3,4,5].rdd",
            ],
            "correct_index": 0,
            "explanation": "sc.parallelize 把本地集合变成分布式 RDD，是学习 RDD 的起点。",
        },
        {
            "type": "single_choice",
            "dimension": "comparison",
            "prompt": "RDD 与 DataFrame 的关系是？",
            "options": [
                "DataFrame 底层仍是 RDD，是带 Schema 的上层抽象",
                "两者完全无关",
                "RDD 比 DataFrame 新",
                "DataFrame 已废弃 RDD",
            ],
            "correct_index": 0,
            "explanation": "DataFrame 是构建在 RDD 之上的声明式 API，底层执行模型仍是 RDD。",
        },
        {
            "type": "single_choice",
            "dimension": "debug",
            "prompt": "代码里对 RDD 调了 map 却『没反应』，原因是？",
            "options": [
                "map 是 Transformation，惰性，没有 Action 就不执行",
                "map 函数写错了",
                "Python 版本不对",
                "数据损坏",
            ],
            "correct_index": 0,
            "explanation": "任何 Transformation 都惰性；看不到计算说明缺 Action，补一个 collect/count 即可触发。",
        },
        {
            "type": "single_choice",
            "dimension": "concept",
            "prompt": "RDD 中的 'Distributed' 指的是？",
            "options": [
                "数据被切分成多个分区，分布在不同节点上",
                "数据只存在 Driver",
                "数据被复制 100 份",
                "只有一个分区",
            ],
            "correct_index": 0,
            "explanation": "分布式 = 数据以分区为单位分散在多机，从而可以并行处理。",
        },
        {
            "type": "single_choice",
            "dimension": "mechanism",
            "prompt": "RDD 的『血缘 lineage』主要用于？",
            "options": [
                "记录数据是怎么算出来的，分区丢失时可重算恢复",
                "记录谁创建了 RDD",
                "加速打印",
                "删除旧数据",
            ],
            "correct_index": 0,
            "explanation": "lineage 保存了从源数据到当前 RDD 的计算路径，是容错重算的依据。",
        },
        {
            "type": "single_choice",
            "dimension": "why",
            "prompt": "为什么说 RDD 是『不可变』很重要？",
            "options": [
                "不可变让 lineage 可重放、失败可重算，且并发安全",
                "不可变让它更快",
                "不可变才能删除数据",
                "不可变是写法限制，没有实际好处",
            ],
            "correct_index": 0,
            "explanation": "不可变保证每次变换都产生新 RDD、旧的不被改， lineage 才能稳定重放。",
        },
    ],
    "l1-transformation": [
        {
            "type": "single_choice",
            "dimension": "why",
            "prompt": "为什么 Spark 把『变换』和『触发』分成 Transformation 与 Action 两类？",
            "options": [
                "为了支持惰性求值，从而能先看完整计划再整体优化",
                "为了多写几行代码",
                "因为 Python 要求这样",
                "为了好看",
            ],
            "correct_index": 0,
            "explanation": "区分两类操作是惰性求值的基础；有了惰性，优化器才能先看完整 DAG 再优化。",
        },
        {
            "type": "single_choice",
            "dimension": "debug",
            "prompt": "写了 long_chain_of_maps.filter，但没看到任何计算发生，是因为？",
            "options": [
                "缺少 Action，所有 Transformation 只是记进计划未执行",
                "代码有语法错误",
                "数据为空",
                "Spark 崩了",
            ],
            "correct_index": 0,
            "explanation": "没有 Action 就没有 Job；整条链只是被 recorded，不会真正跑。",
        },
        {
            "type": "single_choice",
            "dimension": "concept",
            "prompt": "对 RDD 调用 map 后，返回的是什么？",
            "options": [
                "一个新的 RDD（惰性，未执行）",
                "具体计算结果",
                "写入磁盘的文件",
                "报错",
            ],
            "correct_index": 0,
            "explanation": "map 是 Transformation，返回新 RDD 且不触发执行，只把步骤加进计划。",
        },
        {
            "type": "single_choice",
            "dimension": "apply",
            "prompt": "把每个数字平方，应该写？",
            "options": [
                "rdd.map(lambda x: x*x)",
                "rdd.filter(lambda x: x*x)",
                "rdd.reduce(lambda x: x*x)",
                "rdd.collect(lambda x: x*x)",
            ],
            "correct_index": 0,
            "explanation": "map 对每个元素做一一映射，适合「平方」这类逐元素变换。",
        },
        {
            "type": "single_choice",
            "dimension": "comparison",
            "prompt": "Transformation 与 Action 的核心区别是？",
            "options": [
                "Transformation 返回新 RDD（惰性），Action 返回结果/写存储（触发执行）",
                "两者完全相同",
                "Action 更快",
                "Transformation 一定报错",
            ],
            "correct_index": 0,
            "explanation": "判据是返回值：返回 RDD → Transformation；返回结果或写存储 → Action。",
        },
        {
            "type": "single_choice",
            "dimension": "mechanism",
            "prompt": "多个连续 Transformation 在真正执行时通常会？",
            "options": [
                "被融合进同一个 Stage 连续计算，不每步落盘",
                "每步都写磁盘",
                "每步都打印",
                "每步都重启程序",
            ],
            "correct_index": 0,
            "explanation": "窄依赖的连续 Transformation 会被流水线融合，数据流过一次算完，避免中间落盘。",
        },
    ],
    "l1-action": [
        {
            "type": "single_choice",
            "dimension": "why",
            "prompt": "为什么需要 Action 这种『触发』操作？",
            "options": [
                "只有 Action 才真正启动 Job、把惰性计划变成计算",
                "为了多写代码",
                "因为 Transformation 不能返回",
                "为了好看",
            ],
            "correct_index": 0,
            "explanation": "Action 是惰性链条的终点；没有它，前面的 Transformation 永远只是计划。",
        },
        {
            "type": "single_choice",
            "dimension": "comparison",
            "prompt": "count() 与 collect() 的相同点是？",
            "options": [
                "都是 Action，都会触发整条血缘链执行",
                "都是 Transformation",
                "都不触发执行",
                "都只返回新 RDD",
            ],
            "correct_index": 0,
            "explanation": "两者都是 Action，调用即触发一次完整 Job 执行。",
        },
        {
            "type": "single_choice",
            "dimension": "debug",
            "prompt": "对超大 RDD 用 collect() 导致 Driver OOM，正确替代是？",
            "options": [
                "用 take(n) / 先 count 评估量级 / write 落盘，避免全量拉回",
                "再 collect 一次",
                "加更大显示器",
                "删数据",
            ],
            "correct_index": 0,
            "explanation": "collect 全量回 Driver 是 OOM 元凶；调试用 take、产出用 write。",
        },
        {
            "type": "single_choice",
            "dimension": "apply",
            "prompt": "想把 RDD 结果写出到文本文件，应该？",
            "options": [
                "rdd.saveAsTextFile(path)",
                "rdd.collect()",
                "print(rdd)",
                "rdd.show()",
            ],
            "correct_index": 0,
            "explanation": "saveAsTextFile 是 Action，把分区结果写到存储；collect 只是拉回 Driver。",
        },
        {
            "type": "single_choice",
            "dimension": "mechanism",
            "prompt": "没有 cache 时，连续两次 Action 会？",
            "options": [
                "把整条血缘链重新计算两遍",
                "只算一次复用",
                "第二次报错",
                "什么都不做",
            ],
            "correct_index": 0,
            "explanation": "无缓存时每次 Action 都从源 RDD 重跑整条 lineage；要复用中间结果需 cache/persist。",
        },
        {
            "type": "single_choice",
            "dimension": "concept",
            "prompt": "Action 的典型特征是？",
            "options": [
                "返回具体结果或把数据写存储，并触发执行",
                "返回新 RDD，不触发",
                "永远不执行",
                "只能打印",
            ],
            "correct_index": 0,
            "explanation": "Action 的判据：返回具体值或落盘，且会真正启动计算。",
        },
    ],
    "l1-lazy-evaluation": [
        {
            "type": "single_choice",
            "dimension": "apply",
            "prompt": "想立即看某个 Transformation 的结果用于调试，应该接？",
            "options": [
                "一个 Action 如 take(5) / collect()",
                "另一个 map",
                "什么都不接",
                "filter",
            ],
            "correct_index": 0,
            "explanation": "惰性链条要看到结果必须接 Action；调试常用 take(n) 取少量。",
        },
        {
            "type": "single_choice",
            "dimension": "comparison",
            "prompt": "惰性求值与『立即执行（eager）』相比，优势是？",
            "options": [
                "能看到完整计划再整体优化（融合/剪枝），而非一步步算",
                "代码更短",
                "更易出错",
                "不需要 Driver",
            ],
            "correct_index": 0,
            "explanation": "eager 每步立即算，失去全局优化机会；惰性先把整张图交给优化器。",
        },
        {
            "type": "single_choice",
            "dimension": "mechanism",
            "prompt": "Spark 能把 map→map→filter 融成一个 Stage，依赖的是？",
            "options": [
                "惰性收集到的完整执行计划（DAG）",
                "随机顺序",
                "硬盘速度",
                "显示器",
            ],
            "correct_index": 0,
            "explanation": "正因为惰性，Spark 拿到的是完整 DAG，才能做流水线融合等优化。",
        },
        {
            "type": "single_choice",
            "dimension": "why",
            "prompt": "为什么惰性能让『计划剪枝』成为可能？",
            "options": [
                "因为还没真正算，优化器能先去掉无用步骤、合并操作",
                "因为代码更短",
                "因为数据更小",
                "因为 Driver 更快",
            ],
            "correct_index": 0,
            "explanation": "在真正执行前，优化器能分析整张图，删掉无用分支、合并连续操作。",
        },
        {
            "type": "single_choice",
            "dimension": "debug",
            "prompt": "报错出现在 collect 处而非真正出错的 lambda，是因为？",
            "options": [
                "惰性使真正执行延迟到 Action，错误此刻才引爆，需顺血缘回溯",
                "collect 本身有 bug",
                "lambda 没执行",
                "Driver 坏了",
            ],
            "correct_index": 0,
            "explanation": "错误源头在前面的 lambda，但此刻才执行，所以报错在 Action；要往上翻血缘找真因。",
        },
        {
            "type": "single_choice",
            "dimension": "concept",
            "prompt": "Lazy Evaluation 的含义是？",
            "options": [
                "Transformation 只记录计划，直到 Action 才真正执行",
                "永远不执行",
                "每步立即执行",
                "只执行一半",
            ],
            "correct_index": 0,
            "explanation": "惰性求值 = 延迟执行：先把操作记成计划，等 Action 到来才一次性执行。",
        },
    ],
    "l1-why-dataframe-replaces-rdd": [
        {
            "type": "single_choice",
            "dimension": "mechanism",
            "prompt": "Catalyst 优化器拿到 DataFrame 的计划后能做什么？",
            "options": [
                "谓词下推、列裁剪、join 重排等整体优化",
                "只能逐行循环",
                "只能打印",
                "只能删除列",
            ],
            "correct_index": 0,
            "explanation": "Catalyst 像 SQL 优化器一样重写执行计划，能做谓词下推、列裁剪、join 重排。",
        },
        {
            "type": "single_choice",
            "dimension": "apply",
            "prompt": "要对 TB 级结构化数据分组聚合并希望自动优化，应优先？",
            "options": [
                "用 DataFrame 的 groupBy/agg",
                "手写 RDD 循环",
                "用记事本",
                "用 Excel",
            ],
            "correct_index": 0,
            "explanation": "DataFrame 的声明式 API 让 Catalyst 自动优化聚合，是大数据结构化计算的首选。",
        },
        {
            "type": "single_choice",
            "dimension": "debug",
            "prompt": "DataFrame 比 RDD『慢』的误解，根源常是？",
            "options": [
                "误以为底层黑盒 lambda 更快，其实 Catalyst 优化后通常更快",
                "DataFrame 真的更慢",
                "Python 太慢",
                "硬盘问题",
            ],
            "correct_index": 0,
            "explanation": "裸 RDD 的 lambda 对优化器是黑盒无法优化；DataFrame 经 Catalyst 后往往更快更省内存。",
        },
        {
            "type": "single_choice",
            "dimension": "concept",
            "prompt": "DataFrame 之所以能被优化，关键在于？",
            "options": [
                "它是声明式的、带 Schema，优化器能看懂意图",
                "它写法最短",
                "它不用 JVM",
                "它只处理数字",
            ],
            "correct_index": 0,
            "explanation": "声明式 + Schema 让优化器知道『要什么』，从而能重排与裁剪；RDD 的黑盒函数做不到。",
        },
        {
            "type": "single_choice",
            "dimension": "why",
            "prompt": "为什么 DataFrame 比裸 RDD 更省内存？",
            "options": [
                "Tungsten 用二进制列式格式，避免 JVM 对象开销",
                "因为它删数据",
                "因为它不存储",
                "因为 Python 更省",
            ],
            "correct_index": 0,
            "explanation": "Tungsten 的二进制内存格式比一堆 JVM 对象紧凑，减少 GC 与内存占用。",
        },
        {
            "type": "single_choice",
            "dimension": "comparison",
            "prompt": "DataFrame 的『声明式』与 RDD 的『命令式 lambda』区别是？",
            "options": [
                "声明式只说『要什么』可被优化；命令式说『怎么做』对优化器是黑盒",
                "两者都不可优化",
                "命令式更快",
                "声明式更慢",
            ],
            "correct_index": 0,
            "explanation": "声明式描述目标，优化器自由选实现；命令式把实现写死成 lambda，优化器无从下手。",
        },
    ],
    "l1-rdd-exercise": [
        {
            "type": "single_choice",
            "dimension": "concept",
            "prompt": "word count 的本质步骤是？",
            "options": [
                "把文本拆词 → 每词记 1 → 按键求和 → 排序输出",
                "只统计行数",
                "只打印文件",
                "只读取不计算",
            ],
            "correct_index": 0,
            "explanation": "经典 word count = 拆词、标 1、按词聚合、输出，是 MapReduce 范式的最小示范。",
        },
        {
            "type": "single_choice",
            "dimension": "why",
            "prompt": "word count 里要先 flatMap 而不是 map，是因为？",
            "options": [
                "一行可能含多个词，flatMap 把词逐个摊平成独立元素",
                "map 更慢",
                "flatMap 更短",
                "map 不能用",
            ],
            "correct_index": 0,
            "explanation": "map 保留『一行=一个元素』（列表嵌套），flatMap 才把每行的词摊平成独立元素。",
        },
        {
            "type": "single_choice",
            "dimension": "comparison",
            "prompt": "reduceByKey 与 groupByKey + 本地求和，性能上？",
            "options": [
                "reduceByKey 先本地聚合更优；groupByKey 全量 shuffle 易 OOM",
                "groupByKey 更快",
                "两者一样",
                "都不能求和",
            ],
            "correct_index": 0,
            "explanation": "reduceByKey 在 map 端预聚合，shuffle 数据量小；groupByKey 把同 key 全量搬一台机器。",
        },
        {
            "type": "single_choice",
            "dimension": "debug",
            "prompt": "word count 结果对不上预期数量，优先排查？",
            "options": [
                "是否漏了 Action（如 collect）导致链没执行，或 flatMap 切词逻辑错",
                "显示器问题",
                "Java 版本",
                "文件名",
            ],
            "correct_index": 0,
            "explanation": "常见坑：忘了 Action 导致没计算；或 flatMap 分词不对导致词被错误合并/拆开。",
        },
        {
            "type": "single_choice",
            "dimension": "apply",
            "prompt": "把 (词,1) 汇总成词频，正确写法是？",
            "options": [
                "rdd.map(...).reduceByKey(lambda a,b: a+b)",
                "rdd.groupByKey(lambda a,b: a+b)",
                "rdd.map(lambda a,b: a+b)",
                "rdd.filter(lambda a,b: a+b)",
            ],
            "correct_index": 0,
            "explanation": "reduceByKey 接收 (a,b)->a+b 在每个 key 上累加，是词频聚合的标准写法。",
        },
        {
            "type": "single_choice",
            "dimension": "mechanism",
            "prompt": "本次练习从读文本到得到词频，中间经历了？",
            "options": [
                "textFile → flatMap → map → reduceByKey → Action 触发执行",
                "只一步 collect",
                "直接 sum",
                "无需 RDD",
            ],
            "correct_index": 0,
            "explanation": "完整链路：textFile 读入 → flatMap 拆词 → map 标 1 → reduceByKey 聚合 → Action 触发。",
        },
    ],
    # ---- Level 2 (Phase 6.2): 5 new questions each (total 50) ----
    "l2-what-is-dataframe": [
        {
            "type": "single_choice",
            "dimension": "debug",
            "prompt": "你想立刻在控制台看到 DataFrame 的前几行数据，却只看到对象的描述，应该？",
            "options": [
                "调用 df.show() 这类 Action 来真正触发并展示数据",
                "直接 print(df) 就能自动打印全部数据行",
                "重新创建一个 RDD 才能看到",
                "修改 Spark 源码",
            ],
            "correct_index": 0,
            "explanation": "DataFrame 惰性，print(df) 不会触发执行；要看数据需用 show()/take() 等 Action。",
        },
        {
            "type": "single_choice",
            "dimension": "mechanism",
            "prompt": "DataFrame 底层的数据是以什么形式存放和计算的？",
            "options": [
                "按分区分布式存放，底层仍以 RDD 的 Task 机制执行",
                "全部集中在 Driver 单机内存里",
                "只存在于 CSV 文件，不进内存",
                "全部放在客户端浏览器",
            ],
            "correct_index": 0,
            "explanation": "DataFrame 数据按分区分布式存放，底层执行仍由 RDD 分区与 Task 机制驱动。",
        },
        {
            "type": "single_choice",
            "dimension": "apply",
            "prompt": "要得到一个 DataFrame 的「列名 + 类型」概览，应该？",
            "options": [
                "df.printSchema()",
                "df.show()（只看数据行）",
                "df.collect()",
                "df.count()",
            ],
            "correct_index": 0,
            "explanation": "printSchema 打印字段名与数据类型；show 看数据、collect 拉回本地、count 数行数。",
        },
        {
            "type": "single_choice",
            "dimension": "why",
            "prompt": "为什么有了 pandas 这样的单机表，Spark 还要提供 DataFrame？",
            "options": [
                "因为数据可能大到单机内存装不下，且需要集群并行加速",
                "因为 DataFrame 写法更短",
                "因为 pandas 不支持任何列名",
                "因为 DataFrame 不需要数据也能运行",
            ],
            "correct_index": 0,
            "explanation": "核心动机是规模与并行：当数据超内存或需分布式加速时，Spark DataFrame 才派上用场。",
        },
        {
            "type": "single_choice",
            "dimension": "concept",
            "prompt": "关于 DataFrame 这种「表」的说法，正确的是？",
            "options": [
                "它是带 Schema 的二维表抽象，数据按分区分布在集群而非单机数组",
                "它是 Driver 里一个普通的 Python 二维列表",
                "它就是磁盘上的 CSV 文件本身",
                "它只能存一行数据",
            ],
            "correct_index": 0,
            "explanation": "DataFrame 是带列名/类型的二维表抽象，但底层数据按分区分布在集群，并非单机内存里的列表。",
        },
    ],
    "l2-create-dataframe": [
        {
            "type": "single_choice",
            "dimension": "why",
            "prompt": "为什么 spark.read 系列方法返回 DataFrame 是『惰性』的设计？",
            "options": [
                "为了先把读取计划交给 Catalyst 优化，真正读取等 Action 触发",
                "因为 Spark 不支持读文件",
                "为了让代码更短",
                "因为读取不需要任何优化",
            ],
            "correct_index": 0,
            "explanation": "惰性让读取也进入统一优化计划，可与后续过滤/投影一起被下推优化。",
        },
        {
            "type": "single_choice",
            "dimension": "comparison",
            "prompt": "spark.createDataFrame(rows, schema) 与 spark.read.csv(path) 的共同点是？",
            "options": [
                "都返回 DataFrame，且都是惰性的（不立即读取/物化）",
                "都会立刻把全部数据读进 Driver",
                "前者读文件、后者读集合",
                "两者都返回 RDD",
            ],
            "correct_index": 0,
            "explanation": "两者都构造 DataFrame 且不立即物化；createDataFrame 记内存集合，read 记文件来源。",
        },
        {
            "type": "single_choice",
            "dimension": "apply",
            "prompt": "已知 schema=StructType([...])，把一个已有 RDD 转成带结构的 DataFrame，应？",
            "options": [
                "spark.createDataFrame(rdd, schema)",
                "rdd.toDF()（不需要 schema）",
                "spark.read.csv(rdd)",
                "rdd.show()",
            ],
            "correct_index": 0,
            "explanation": "createDataFrame 同时接受集合或 RDD 与 schema，把无结构 RDD 变成有结构的 DataFrame。",
        },
        {
            "type": "single_choice",
            "dimension": "concept",
            "prompt": "spark.read.format('json').load(path) 中 format/load 的作用是？",
            "options": [
                "指定数据源格式为 json 并加载为 DataFrame（仍是惰性）",
                "立即把数据打印出来",
                "删除原文件",
                "转换 Python 类型",
            ],
            "correct_index": 0,
            "explanation": "format 指定数据源类型，load 读取为 DataFrame；依旧惰性，真正读等 Action。",
        },
        {
            "type": "single_choice",
            "dimension": "mechanism",
            "prompt": "用 createDataFrame 时如果不给 schema 而只给元组/Row，Spark 会？",
            "options": [
                "尝试从数据推断列名与类型（如元组默认 _1、_2 命名）",
                "直接报错无法创建",
                "把所有列当成文本且列名为 a、b、c",
                "自动连接数据库补全结构",
            ],
            "correct_index": 0,
            "explanation": "不给 schema 时 Spark 会尽量推断结构（元组用 _1/_2 命名或按 Row 字段推断）。",
        },
    ],
    "l2-schema-types": [
        {
            "type": "single_choice",
            "dimension": "mechanism",
            "prompt": "StructField('age', IntegerType(), True) 三个参数分别指？",
            "options": [
                "列名、数据类型、是否可空",
                "列名、默认值、长度",
                "类型、列名、注释",
                "索引、类型、精度",
            ],
            "correct_index": 0,
            "explanation": "StructField 依次为 name、dataType、nullable，描述单列的结构。",
        },
        {
            "type": "single_choice",
            "dimension": "comparison",
            "prompt": "显式声明 Schema 与完全不声明（让 Spark 推断）相比，主要代价是？",
            "options": [
                "需要多写一些类型定义，换来可控与 fail-fast",
                "运行更慢且更容易出错",
                "无法再读取 CSV",
                "列数会减少",
            ],
            "correct_index": 0,
            "explanation": "代价是多写类型声明，换来的是类型可控、不抽样、错误更早暴露。",
        },
        {
            "type": "single_choice",
            "dimension": "apply",
            "prompt": "要让某列允许为空并声明为整数，应写？",
            "options": [
                "StructField('cnt', IntegerType(), True)",
                "StructField('cnt', IntegerType(), False) 表示可空",
                "StructField('cnt', 'int')",
                "IntegerType('cnt', True)",
            ],
            "correct_index": 0,
            "explanation": "nullable=True 表示允许空值；写法为 StructField(name, type, nullable)。",
        },
        {
            "type": "single_choice",
            "dimension": "concept",
            "prompt": "StringType、IntegerType、BooleanType 等属于？",
            "options": [
                "Spark 的 DataType 体系，用于描述每列的数据类型",
                "Python 的内置类型，可直接当 schema 用",
                "文件名约定",
                "磁盘存储格式",
            ],
            "correct_index": 0,
            "explanation": "这些是 pyspark.sql.types 中的 DataType，组成 Schema 的类型系统。",
        },
        {
            "type": "single_choice",
            "dimension": "why",
            "prompt": "为什么浮点金额不用 DoubleType 而用 DecimalType？",
            "options": [
                "DecimalType 用十进制精度表示，避免二进制浮点的舍入误差",
                "DoubleType 不能存小数",
                "DecimalType 运行更快",
                "DoubleType 已被废弃",
            ],
            "correct_index": 0,
            "explanation": "Double 是二进制浮点会有舍入误差；金额需 DecimalType 的十进制精确表示。",
        },
    ],
    "l2-inspect": [
        {
            "type": "single_choice",
            "dimension": "mechanism",
            "prompt": "show() 与 collect() 在执行上有何关系？",
            "options": [
                "两者都是 Action，都会触发作业执行；show 只取前 n 行打印",
                "collect 是 Transformation",
                "show 不触发执行",
                "两者都不触发执行",
            ],
            "correct_index": 0,
            "explanation": "show 和 collect 都是 Action，都会真正触发计算；show 仅取前若干行展示。",
        },
        {
            "type": "single_choice",
            "dimension": "comparison",
            "prompt": "take(n) 与 show(n) 的区别是？",
            "options": [
                "take(n) 返回 Row 列表供本地使用；show(n) 只打印表格、不返回数据",
                "两者完全相同",
                "take 不触发执行",
                "show 返回列表",
            ],
            "correct_index": 0,
            "explanation": "take(n) 把前 n 行以 Row 列表形式取回本地；show(n) 只打印、不便后续处理。",
        },
        {
            "type": "single_choice",
            "dimension": "apply",
            "prompt": "想在 Notebook 里拿到前 5 行数据做本地处理，应？",
            "options": [
                "df.take(5) 或 df.limit(5).collect()",
                "df.show(5) 然后解析屏幕输出",
                "df.printSchema()",
                "df.count()",
            ],
            "correct_index": 0,
            "explanation": "take/collect 把数据以对象形式取回本地；show 只打印、不便后续处理。",
        },
        {
            "type": "single_choice",
            "dimension": "concept",
            "prompt": "df.dtypes 返回的是什么？",
            "options": [
                "一个 [(列名, 类型字符串), ...] 的列表",
                "行数",
                "数据样本",
                "执行计划",
            ],
            "correct_index": 0,
            "explanation": "dtypes 给出每列的名称与类型（字符串形式），便于快速核对结构。",
        },
        {
            "type": "single_choice",
            "dimension": "why",
            "prompt": "为什么不能依赖 print(df) 来查看数据内容？",
            "options": [
                "DataFrame 惰性，未触发的计算不会被打印成数据行",
                "print 函数对 DataFrame 无效",
                "会删除数据",
                "需要联网才能打印",
            ],
            "correct_index": 0,
            "explanation": "DataFrame 是惰性计划，直接 print 不会执行计算、看不到真实数据行；要看需用 Action。",
        },
    ],
    "l2-select-filter": [
        {
            "type": "single_choice",
            "dimension": "why",
            "prompt": "为什么 select 只选需要的列通常能让作业更快？",
            "options": [
                "因为 Catalyst 可做列裁剪，跳过不需要的列、减少数据量",
                "因为少写几行代码",
                "因为列多了会报错",
                "因为 select 必须放在 filter 之前",
            ],
            "correct_index": 0,
            "explanation": "只选必要列让优化器做列裁剪（column pruning），少读少传数据，提升性能。",
        },
        {
            "type": "single_choice",
            "dimension": "comparison",
            "prompt": "filter 与 where 的关系是？",
            "options": [
                "两者功能完全等价，where 是 filter 的别名",
                "filter 更快",
                "where 只能用于数字列",
                "两者毫无关系",
            ],
            "correct_index": 0,
            "explanation": "在 Spark 中 where 就是 filter 的别名，语义与性能一致。",
        },
        {
            "type": "single_choice",
            "dimension": "debug",
            "prompt": "下面哪段代码一定会在运行时报错？",
            "options": [
                "df.filter(df.age > 18 and df.city == 'BJ')（用 Python and 而非 &）",
                "df.filter((df.age > 18) & (df.city == 'BJ'))",
                "df.filter(df.age > 18)",
                "df.where(df.city == 'BJ')",
            ],
            "correct_index": 0,
            "explanation": "用 Python 的 and/or 会把 Column 当布尔立即求值而报 ValueError；须用 & | ~ 且加括号。",
        },
        {
            "type": "single_choice",
            "dimension": "apply",
            "prompt": "只保留 city 为 'BJ' 且 age 大于 30 的行，正确的是？",
            "options": [
                "df.filter((df.city == 'BJ') & (df.age > 30))",
                "df.filter(df.city == 'BJ' and df.age > 30)",
                "df.select('BJ', 30)",
                "df.where(df.city = 'BJ')",
            ],
            "correct_index": 0,
            "explanation": "多条件用 Column 运算符 &，每个条件单独加括号；Python and 会报错。",
        },
        {
            "type": "single_choice",
            "dimension": "concept",
            "prompt": "select 表达式除了列名，还可以接受？",
            "options": [
                "Column 表达式，如 F.col('a')、df.b、F.expr('a+1')",
                "只能写字符串列名，不能写表达式",
                "只能写数字",
                "只能写 *",
            ],
            "correct_index": 0,
            "explanation": "select 可接受列名字符串或任意 Column 表达式（含运算、函数），非常灵活。",
        },
    ],
    "l2-withcolumn": [
        {
            "type": "single_choice",
            "dimension": "why",
            "prompt": "为什么 DataFrame 提供 withColumn 而不是让你改原表的某一格？",
            "options": [
                "因为 DataFrame 不可变，任何变换都返回新表以保证 lineage/并行安全",
                "因为修改单元格更快",
                "因为 Spark 不允许新增列",
                "因为原表在磁盘上不能改",
            ],
            "correct_index": 0,
            "explanation": "DataFrame 不可变，withColumn 返回新表；这保证了血缘可重放与并发安全。",
        },
        {
            "type": "single_choice",
            "dimension": "comparison",
            "prompt": "withColumn 与 select 增列的区别是？",
            "options": [
                "withColumn 在保留原列基础上加/改一列；select 需显式列出要保留的所有列",
                "两者完全相同",
                "select 不能增列",
                "withColumn 会删除其它列",
            ],
            "correct_index": 0,
            "explanation": "withColumn 自动保留其它列；select 要自己把原有列都写出来才不丢列。",
        },
        {
            "type": "single_choice",
            "dimension": "debug",
            "prompt": "写了 df.withColumn('x', df.a + 1) 却没看到 x 列，是因为？",
            "options": [
                "withColumn 返回新 DataFrame，必须接住返回值（或链式）才生效",
                "withColumn 有 bug",
                "列名非法",
                "a 列不存在所以被忽略",
            ],
            "correct_index": 0,
            "explanation": "DataFrame 不可变，withColumn 返回新对象；不用变量接住或不链式，改动就丢失了。",
        },
        {
            "type": "single_choice",
            "dimension": "mechanism",
            "prompt": "df.withColumn('abs_a', F.abs(df.a)) 中 F.abs 为什么能在集群上执行？",
            "options": [
                "F.abs 是 Spark 函数，把『逐行怎么算』编进执行计划下推到 Executor",
                "因为它在 Driver 上一行行循环",
                "因为 Python 内置 abs 也能分布式",
                "因为数据已全在 Driver",
            ],
            "correct_index": 0,
            "explanation": "Spark 函数把计算描述发到各 Executor 并行执行；Python 内置函数拿不到分布式数据。",
        },
        {
            "type": "single_choice",
            "dimension": "apply",
            "prompt": "把 'name' 列统一转为大写新增为 'name_up'，应？",
            "options": [
                "df.withColumn('name_up', F.upper(df.name))",
                "df.withColumn('name_up', df.name.upper())（Python 字符串方法无效）",
                "df.select(F.upper('name'))",
                "df.addColumn('name_up', F.upper('name'))",
            ],
            "correct_index": 0,
            "explanation": "字符串处理要用 F.upper 等 Spark 函数；df.name.upper() 是 Python 方法，对 Column 无效。",
        },
    ],
    "l2-sort-dedup": [
        {
            "type": "single_choice",
            "dimension": "why",
            "prompt": "为什么去重前常常先思考『按哪些列算重复』？",
            "options": [
                "因为 distinct 看整行、dropDuplicates 只看指定列，语义差别很大",
                "因为去重一定会丢数据",
                "因为不指定列会报错",
                "因为去重更快",
            ],
            "correct_index": 0,
            "explanation": "整行去重与按列去重结果不同；明确维度才能选对 distinct 还是 dropDuplicates。",
        },
        {
            "type": "single_choice",
            "dimension": "comparison",
            "prompt": "limit 与 take 在『取前 N 行』上的区别是？",
            "options": [
                "limit 是 Transformation 返回新 DataFrame；take 是 Action 返回本地列表",
                "两者都返回列表",
                "两者都是 Transformation",
                "take 不触发执行",
            ],
            "correct_index": 0,
            "explanation": "limit 返回新的（惰性）DataFrame；take(n) 是 Action，把前 n 行取回本地。",
        },
        {
            "type": "single_choice",
            "dimension": "debug",
            "prompt": "想按『城市+日期』去重却写成 dropDuplicates()（不传列），会？",
            "options": [
                "按整行完全相同才算重复，可能去不掉真正想去的重复",
                "自动按所有列去重（这就是想要的效果）",
                "直接报错",
                "一行都不去",
            ],
            "correct_index": 0,
            "explanation": "不传列时 dropDuplicates 退化为整行去重；若只想按部分列去重需显式传入列列表。",
        },
        {
            "type": "single_choice",
            "dimension": "mechanism",
            "prompt": "orderBy 触发的 Shuffle 中，数据如何被重新组织？",
            "options": [
                "按排序键分区，使相同/相邻键的数据汇聚，便于全局有序",
                "随机打乱顺序",
                "复制到 Driver",
                "直接落盘不做排序",
            ],
            "correct_index": 0,
            "explanation": "orderBy 通过 Shuffle 按排序键重新分区，把同键数据放一起才能完成全局排序。",
        },
        {
            "type": "single_choice",
            "dimension": "apply",
            "prompt": "要取『金额最高且去重后的前 5 个不同用户』，合理写法是？",
            "options": [
                "df.orderBy(F.desc('amount')).dropDuplicates(['user']).limit(5)",
                "df.limit(5).dropDuplicates(['user'])",
                "df.dropDuplicates(['user']).limit(5)",
                "df.distinct().limit(5)",
            ],
            "correct_index": 0,
            "explanation": "先按金额降序，再按用户去重并取前 5，得到金额最高的 5 个不同用户；顺序很重要。",
        },
    ],
    "l2-groupby-agg": [
        {
            "type": "single_choice",
            "dimension": "why",
            "prompt": "为什么分组聚合是 Spark 中最常见的 Shuffle 来源？",
            "options": [
                "因为需要把相同 key 的行汇聚到同一节点才能聚合",
                "因为聚合要打印结果",
                "因为要重新读取文件",
                "因为要排序",
            ],
            "correct_index": 0,
            "explanation": "聚合要求同 key 同处，必然触发 Shuffle 重新分布数据，故很常见。",
        },
        {
            "type": "single_choice",
            "dimension": "comparison",
            "prompt": "agg(F.sum('a')) 与 groupBy('k').sum('a') 的关系是？",
            "options": [
                "sum 是 agg 的便捷写法，底层都走 agg 聚合",
                "两者完全不同",
                "sum 不触发聚合",
                "agg 不能求和",
            ],
            "correct_index": 0,
            "explanation": "groupBy 后的 .sum/.count 等都是 agg 的语法糖，最终都通过 agg 表达。",
        },
        {
            "type": "single_choice",
            "dimension": "debug",
            "prompt": "groupBy('city').agg(F.avg('amount')) 结果列名叫 'avg(amount)'，下游引用报错，应？",
            "options": [
                "用 alias 改名，如 .agg(F.avg('amount').alias('avg_amt'))",
                "忽略列名直接用",
                "重新 groupBy 一次",
                "改文件名",
            ],
            "correct_index": 0,
            "explanation": "聚合默认列名带表达式，下游难引用；用 alias 起清晰名字是通用做法。",
        },
        {
            "type": "single_choice",
            "dimension": "mechanism",
            "prompt": "在 groupBy 聚合时，Catalyst 通常还会尝试做？",
            "options": [
                "在 map 端预聚合（partial aggregation）以减少 Shuffle 数据量",
                "把数据全部复制到 Driver",
                "禁用优化",
                "先排序再删除",
            ],
            "correct_index": 0,
            "explanation": "Spark 常做部分聚合（如先本地 combine）再 shuffle，显著降低传输量，类似 reduceByKey。",
        },
        {
            "type": "single_choice",
            "dimension": "apply",
            "prompt": "要同时算每个城市的最大金额与行数，应？",
            "options": [
                "df.groupBy('city').agg(F.max('amount').alias('mx'), F.count('*').alias('cnt'))",
                "df.groupBy('city').max('amount')（只能一个聚合）",
                "先 count 再单独做 max",
                "df.agg(F.max('amount'), F.count('*'))（缺 groupBy）",
            ],
            "correct_index": 0,
            "explanation": "agg 可一次声明多个聚合并分别 alias；缺 groupBy 会对全表聚合而非分组。",
        },
    ],
    "l2-write-data": [
        {
            "type": "single_choice",
            "dimension": "why",
            "prompt": "为什么写出默认采用 errorIfExists 而不是覆盖？",
            "options": [
                "为了防误覆盖生产数据，路径已存在就报错提醒你显式决定",
                "因为覆盖更快",
                "因为 Spark 不能覆盖",
                "因为写入不需要确认",
            ],
            "correct_index": 0,
            "explanation": "默认报错而非覆盖，是安全优先：避免一条命令把已有输出悄悄冲掉。",
        },
        {
            "type": "single_choice",
            "dimension": "comparison",
            "prompt": "mode('overwrite') 与 mode('append') 的区别是？",
            "options": [
                "overwrite 先清空目标再写；append 在原有之上追加",
                "两者相同",
                "append 会删旧数据",
                "overwrite 是追加",
            ],
            "correct_index": 0,
            "explanation": "overwrite 覆盖（先删后写），append 追加；语义相反，选错会丢数据或重复。",
        },
        {
            "type": "single_choice",
            "dimension": "debug",
            "prompt": "重复运行同一 write 代码却报『path already exists』，是因为？",
            "options": [
                "默认 mode 是 errorIfExists，路径存在即报错",
                "磁盘满了",
                "Python 版本问题",
                "网络断开",
            ],
            "correct_index": 0,
            "explanation": "这正是默认 errorIfExists 的行为；需显式指定 overwrite 或 append 才能重复运行。",
        },
        {
            "type": "single_choice",
            "dimension": "mechanism",
            "prompt": "partitionBy 写出的目录结构对下游查询有何影响？",
            "options": [
                "按列值分层目录，下游可分区裁剪只扫相关目录",
                "把所有数据写进单个文件",
                "没有任何影响",
                "会打乱数据顺序",
            ],
            "correct_index": 0,
            "explanation": "分区目录让下游按分区列过滤时跳过无关目录（分区裁剪），显著提速。",
        },
        {
            "type": "single_choice",
            "dimension": "apply",
            "prompt": "要把结果以 Parquet 写出到 out/，且允许重复运行覆盖，应？",
            "options": [
                "df.write.mode('overwrite').parquet('out/')",
                "df.write.parquet('out/')（默认会报错若已存在）",
                "df.write.mode('append').csv('out/')",
                "df.write.format('json').save('out/')",
            ],
            "correct_index": 0,
            "explanation": "用 mode('overwrite') + parquet 既用列式高效格式，又允许重复运行覆盖。",
        },
    ],
    "l2-comprehensive": [
        {
            "type": "single_choice",
            "dimension": "mechanism",
            "prompt": "整条 ETL 链路中，发生的 Shuffle 通常来自哪些步骤？",
            "options": [
                "groupBy / orderBy 等需要跨分区重排的操作",
                "read / filter 也会 Shuffle",
                "只有 write 会 Shuffle",
                "全程没有 Shuffle",
            ],
            "correct_index": 0,
            "explanation": "Shuffle 出现在需跨分区重分布处（groupBy、orderBy、按列去重等），而非 read/filter。",
        },
        {
            "type": "single_choice",
            "dimension": "why",
            "prompt": "为什么先 show 验证、确认无误后再 write 是好习惯？",
            "options": [
                "避免把错误/脏数据写入存储，且 write 一旦执行代价高",
                "因为 show 更快",
                "因为 write 不支持大数据",
                "因为 show 必须写在前",
            ],
            "correct_index": 0,
            "explanation": "write 是昂贵的 Action 且会落盘；先 show/limit 抽查可尽早拦截错误。",
        },
        {
            "type": "single_choice",
            "dimension": "comparison",
            "prompt": "『先做 Transformation 链、最后用 Action 触发』与『每步立即执行』相比？",
            "options": [
                "前者能整体优化（下推/裁剪/融合），后者失去这些机会",
                "两者性能一样",
                "后者更快",
                "前者不能优化",
            ],
            "correct_index": 0,
            "explanation": "惰性让优化器拿到完整 DAG 做整体优化；每步即执行则无法全局优化。",
        },
        {
            "type": "single_choice",
            "dimension": "debug",
            "prompt": "链路写好运行却『一直卡着没输出』，最可能的原因是？",
            "options": [
                "整条链全是 Transformation，缺少 Action（write/show）触发",
                "Python 崩溃",
                "数据为空一定这样",
                "显示器问题",
            ],
            "correct_index": 0,
            "explanation": "若只有 Transformation 没有 Action，就不会有任何 Job 执行，看起来像『卡住』。",
        },
        {
            "type": "single_choice",
            "dimension": "apply",
            "prompt": "要读 CSV → 过滤异常行 → 按城市聚合 → 取金额前 10 写出，正确骨架是？",
            "options": [
                "read.csv → filter → groupBy('city').agg(...) → orderBy(desc).limit(10) → write",
                "read.csv → write → filter → groupBy",
                "groupBy → read.csv → write",
                "read.csv → collect → 本地 pandas 聚合",
            ],
            "correct_index": 0,
            "explanation": "典型顺序：读→过滤→聚合→排序取 TopN→写出；write 作 Action 触发整条链。",
        },
    ],
}


def update_seed_json() -> None:
    with open(SEED_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    by_slug = {e["lesson_slug"]: e for e in data["quizzes"]}

    for slug in ALL_SLUGS:
        entry = by_slug.get(slug)
        if entry is None:
            print(f"[seed] WARNING: {slug} not found in quiz_seed.json, skipping")
            continue
        questions = entry["questions"]
        # Tag existing questions with dimension (idempotent: only if missing).
        dims = EXISTING_DIM.get(slug, [])
        for i, q in enumerate(questions):
            if "dimension" not in q and i < len(dims):
                q["dimension"] = dims[i]
        # Append new questions only if below 10.
        if len(questions) < 10:
            for q in NEW_QUESTIONS[slug]:
                questions.append(dict(q))
            print(f"[seed] {slug}: expanded to {len(questions)} questions")
        else:
            print(f"[seed] {slug}: already has {len(questions)} (skipped append)")

    with open(SEED_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("[seed] quiz_seed.json updated.")


def update_database() -> None:
    db = SessionLocal()
    try:
        for slug in ALL_SLUGS:
            lesson = db.scalars(select(Lesson).where(Lesson.slug == slug)).first()
            if lesson is None:
                print(f"[db] WARNING: lesson {slug} not found, skipping")
                continue
            existing = db.scalars(
                select(QuizQuestion).where(QuizQuestion.lesson_id == lesson.id)
            ).all()
            existing_by_prompt = {q.prompt: q for q in existing}
            # Backfill dimension on existing rows.
            dims = EXISTING_DIM.get(slug, [])
            # Build prompt->dim map from the original 4 (by order_index).
            ordered = sorted(existing, key=lambda q: q.order_index)
            changed = False
            for i, q in enumerate(ordered):
                if i < len(dims) and not (q.dimension or "").strip():
                    q.dimension = dims[i]
                    changed = True
            # Insert new questions (dedup by prompt).
            max_order = max((q.order_index for q in existing), default=-1)
            inserted = 0
            for i, q in enumerate(NEW_QUESTIONS[slug]):
                if q["prompt"] in existing_by_prompt:
                    continue
                db.add(
                    QuizQuestion(
                        lesson_id=lesson.id,
                        type=q.get("type", "single_choice"),
                        prompt=q["prompt"],
                        options=json.dumps(q["options"], ensure_ascii=False),
                        correct_index=q["correct_index"],
                        explanation=q["explanation"],
                        order_index=max_order + 1 + i,
                        dimension=q.get("dimension"),
                    )
                )
                inserted += 1
            if changed or inserted:
                db.commit()
            print(f"[db] {slug}: backfilled dims + inserted {inserted} new")
    finally:
        db.close()


if __name__ == "__main__":
    update_seed_json()
    # Only touch the DB if it already exists.
    if os.path.exists(os.path.join(os.path.dirname(__file__), "spark_quest.db")):
        update_database()
    else:
        print("[db] no spark_quest.db found; skipping DB update (fresh DB will seed from JSON).")
    print("Phase 6.1/6.2 expansion done.")
