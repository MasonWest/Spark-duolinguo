# -*- coding: utf-8 -*-
"""一次性脚本：把 Level 2（DataFrame 核心，10 课）合并进 course_seed.json，
并幂等地 upsert 进 spark_quest.db 的 course_levels / lessons 表。
不修改 Level 0 / Level 1 与已有的 lesson_mastery 进度数据。
"""
import sqlite3, json, os

BASE = os.path.dirname(os.path.abspath(__file__))
SEED = os.path.join(BASE, "app", "course_seed.json")
DB = os.path.join(BASE, "spark_quest.db")

LEVEL2 = {
    "title": "Level 2：DataFrame 核心",
    "description": "从「带结构的分布式表」视角掌握 DataFrame：创建、Schema、检视、变换、聚合、读写，为后续 SQL 与执行计划打基础。",
    "order_index": 2,
    "lessons": [
        {
            "title": "DataFrame 是什么",
            "slug": "l2-what-is-dataframe",
            "description": "理解 DataFrame 的本质：带 Schema 的分布式表，以及它和 RDD 的关系。",
            "objective": "学完本课，你应该能够：用自己的话解释 DataFrame 是什么、它和你在 Level 1 学的 RDD 到底是什么关系；说清「行 / 列 / Schema」三个概念；并理解为什么日常开发优先用 DataFrame 而不是 RDD。",
            "estimated_minutes": 12,
            "order_index": 0,
            "prerequisites": "",
            "content": {
                "explanation": "【先用人话理解】\n\nDataFrame 可以理解成「一张带表头、分布式存放的表」。想象一张 Excel 表：每一行是一条记录，每一列是一个字段（比如姓名、年龄、城市），表头告诉 Spark 每一列叫什么、是什么类型。只不过这张表大到一台机器放不下，被 Spark 切成了很多分区，分散在很多机器的内存里——这就是「分布式」。\n\n【它和 RDD 的关系（重要）】\n\n在 Level 1 我们学了 RDD：它是 Spark 最底层的数据抽象，是一批「分布式、容错、只读」的数据，但它是「无类型的」——Spark 不知道里面装的是姓名还是数字。DataFrame 是 RDD 之上的一层「带 Schema 的包装」：① 它底层仍然用 RDD 的那套机制（分区、血缘、Task）在跑；② 但它额外告诉 Spark「每一列叫什么、什么类型」。正是这份额外的结构信息，让 Catalyst 优化器能看懂你的计算并自动优化（详见 Level 4）。一句话：RDD 是地基，DataFrame 是盖在地基上、会自己优化的房子。\n\n【一个直观的心智模型】\n\nRDD 像一箱「没贴标签的货物」（Spark 不知道里面是苹果还是螺丝）；DataFrame 像一份「带装箱清单的货物」——不仅知道有哪些货，还知道每样货的规格。Spark 拿到清单就能聪明地安排搬运。\n\n【正式的技术定义】\n\nDataFrame = 以命名列组织的分布式数据集（Distributed collection of data organized into named columns）。它有 Schema（StructType，描述每一列的字段名与数据类型）；每个元素是 Row；操作同样是惰性的（Transformation 只记账、Action 才触发）；底层执行最终仍翻译为 RDD 的 Task。DataFrame 属于声明式 API：你写「要什么」（df.filter(...).select(...)），Spark 决定「怎么算最快」。\n\n【写下代码后，Spark 内部发生了什么】\n\n当你写 spark.createDataFrame(...) 或 spark.read.csv(...)，Spark 只是「登记」这张表的结构与来源；后续所有变换（select / filter / groupBy）都只是往 DAG 加节点；直到 Action（如 show / count）出现，Spark 才把整条计划和 Schema 一起交给 Catalyst 优化、切成 Task、分发 Executor 执行。",
                "examples": [
                    {
                        "title": "从一个 Python 列表造 DataFrame",
                        "code": "from pyspark.sql import SparkSession\nfrom pyspark.sql.types import *\n\nspark = SparkSession.builder.master(\"local[*]\").appName(\"df-intro\").getOrCreate()\n\nrows = [(\"Alice\", 34), (\"Bob\", 28), (\"Cathy\", 45)]\nschema = StructType([\n    StructField(\"name\", StringType()),\n    StructField(\"age\", IntegerType()),\n])\ndf = spark.createDataFrame(rows, schema)\ndf.show()\ndf.printSchema()",
                        "note": "createDataFrame 把「数据 + 显式 Schema」变成一个 DataFrame；show() 是 Action，会真正触发执行并打印。"
                    },
                    {
                        "title": "对比 RDD（Level 1 回顾）",
                        "code": "# RDD：Spark 不知道里面是什么类型\nrdd = spark.sparkContext.parallelize([(\"Alice\", 34), (\"Bob\", 28)])\n\n# DataFrame：Spark 明确知道 name:string、age:int\ndf = spark.createDataFrame(rdd, [\"name\", \"age\"])",
                        "note": "同样一批数据，DataFrame 多了一份 Schema，这正是优化器能「看懂」你的前提。"
                    }
                ],
                "key_points": [
                    "DataFrame = 带 Schema（列名 + 类型）的分布式表，底层仍是 RDD 那套机制",
                    "Schema 让 Catalyst 优化器能「看懂」计算并自动优化——这是比 RDD 快的根本原因",
                    "DataFrame 是声明式 API：你写「要什么」，Spark 决定「怎么算」",
                    "DataFrame 同样惰性：Transformation 记账，Action 触发执行",
                    "日常优先用 DataFrame；遇到底层控制（自定义分区、非结构化）再用 RDD"
                ],
                "common_mistakes": [
                    {
                        "mistake": "把 Spark DataFrame 当成 pandas DataFrame 直接上手改",
                        "why": "pandas 是单机内存对象，DataFrame 是分布式、不可变的；没有「原地修改」这回事（没有 inplace 参数）。",
                        "fix": "DataFrame 的任何变换都返回一个新的 DataFrame，要用变量接住返回值。"
                    },
                    {
                        "mistake": "以为 df 里「已经有了数据」可以直接打印逐行看",
                        "why": "Driver 上并不持有真实数据，df 只是「数据与计划的描述」。",
                        "fix": "用 show() / take(n) / collect() 触发执行后再查看；不要用 Python 的 for 直接遍历 df。"
                    },
                    {
                        "mistake": "觉得 DataFrame 和 RDD 是「两种互相替代的东西」",
                        "why": "DataFrame 底层执行模型就是 RDD，二者是「上层声明式 API」与「底层抽象」的关系，不是并列替代。",
                        "fix": "把 RDD 当理解 Spark 的地基，DataFrame 当日常工具。"
                    }
                ],
                "review": "在 Level 0 我们用手写 Python 跑通了第一个 Spark 程序，读出来的 df 我们在 Level 1 也提过——它是 Spark 最常用的数据结构。Level 1 我们钻到了更底层，理解了 RDD：Spark 表示「一批分布式、容错、只读数据」的核心抽象。\n\n可你可能会问：既然 RDD 已经能装数据了，为什么 Spark 还要发明 DataFrame？为什么官方一直劝你「优先用 DataFrame」？这一课就来正面回答——DataFrame 到底多了什么，让 Spark 能变得更聪明。",
                "problem": "我们已经知道 RDD 是 Spark 的底层数据抽象。但 RDD 有个硬伤：它不知道自己装着什么类型的数据，于是优化器无从下手。Spark 是怎么在 RDD 之上，加一层「让机器看得懂」的结构、从而既保留分布式能力、又获得自动优化的？这一层，就叫 DataFrame。",
                "preview": "现在我们知道：DataFrame 是「带 Schema 的分布式表」，它在 RDD 之上加了一份结构信息，让 Spark 能自动优化。\n\n可这个 DataFrame 从哪来？我们总得先把数据「装」进来——不管是内存里的列表，还是硬盘上的 CSV、JSON、Parquet 文件。\n\n下一课：创建 DataFrame。"
            }
        },
        {
            "title": "创建 DataFrame",
            "slug": "l2-create-dataframe",
            "description": "从集合、CSV、JSON、Parquet 创建 DataFrame，理解读入时的关键选项。",
            "objective": "学完本课，你应该能够：用三种方式创建 DataFrame（集合、CSV、JSON、Parquet）；说清 option(\"header\") 与 option(\"inferSchema\") 的作用；并知道读文件是一个「惰性」操作、真正读取发生在 Action。",
            "estimated_minutes": 15,
            "order_index": 1,
            "prerequisites": "",
            "content": {
                "explanation": "【先用人话理解】\n\n「创建 DataFrame」就是告诉 Spark：「把这份数据，按表的方式管理起来」。数据可能来自三个最常见的地方：① 你手写的内存集合（学习、造测试数据最方便）；② CSV 文件（最常见的表格文件）；③ JSON / Parquet（大数据里高频的格式）。Spark 都给你准备好了现成的入口。\n\n【三种创建方式】\n\n1) 从集合（parallelize + createDataFrame）：本地小数据变分布式。适合学习和造样例。\n2) 从文件（spark.read.csv / json / parquet）：生产环境的常态。Spark 按文件格式自动解析。\n3) 从其他数据源（JDBC、Avro、ORC 等，本课点到为止，写数据会在第 9 课展开）。\n\n【两个关键选项（读 CSV 必记）】\n\n· option(\"header\", True)：把第一行当表头。不设置，第一行数据会被当成普通数据，出现名为「name」的奇怪取值。\n· option(\"inferSchema\", True)：让 Spark 抽样推断每列类型。不设置，所有列默认都被当成字符串（StringType），后续做数值运算会出错。\n\n【它仍然是惰性的】\n\n无论是 createDataFrame 还是 read.csv，都只是「登记读取计划」，并不会立刻把文件读进内存。真正的读取、解析发生在你写下 Action（show / count）之后。这也解释了为什么读一个 100 GB 文件，程序「瞬间」就返回了——它还没真读。\n\n【写下代码后，Spark 内部发生了什么】\n\nread.csv 的时候，Spark 在 Driver 记下「我要从某路径读 CSV、按这些选项解析」；在你调用 show / count 时，Driver 把任务切成 Task 分发给 Executor，各 Executor 读取自己负责的文件分片、按 Schema 解析、再汇总或打印。所以「读」本身是分布式的，不是 Driver 一个人读。",
                "examples": [
                    {
                        "title": "从集合创建（最快上手）",
                        "code": "from pyspark.sql import SparkSession\nspark = SparkSession.builder.master(\"local[*]\").getOrCreate()\n\n# 直接传列名，Schema 由数据推断（实验/小数据方便）\ndf = spark.createDataFrame(\n    [(\"Alice\", 34), (\"Bob\", 28)], [\"name\", \"age\"])\ndf.show()",
                        "note": "createDataFrame(data, schema)：schema 可以是列名列表（自动推断类型），也可以是 StructType（显式指定）。"
                    },
                    {
                        "title": "从 CSV 读取（生产最常见）",
                        "code": "df = (spark.read\n      .option(\"header\", True)        # 第一行作表头\n      .option(\"inferSchema\", True)   # 抽样推断类型\n      .csv(\"path/to/sales.csv\"))\ndf.printSchema()   # 确认每列类型正确后再继续",
                        "note": "先 printSchema 确认类型，是读 CSV 后的标准动作——类型错了后面全错。"
                    },
                    {
                        "title": "从 JSON / Parquet 读取",
                        "code": "json_df = spark.read.json(\"path/to/events.json\")      # JSON 自带结构，通常无需 inferSchema\nparquet_df = spark.read.parquet(\"path/to/warehouse\")  # Parquet 自带 Schema",
                        "note": "JSON 与 Parquet 自身携带结构信息，Schema 推断比 CSV 可靠得多；Parquet 是 Spark 默认推荐的列式存储格式。"
                    }
                ],
                "key_points": [
                    "三种来源：集合（createDataFrame）、CSV / JSON / Parquet（spark.read.*）、其他数据源",
                    "读 CSV 必须加 option(\"header\", True)，否则表头变数据",
                    "option(\"inferSchema\", True) 推断类型；不推断则全是 StringType，后续数值运算会报错",
                    "创建 / 读取都是惰性的：只是登记计划，真正读发生在 Action",
                    "读文件是分布式的：各 Executor 读自己那份分片，不是 Driver 一人读"
                ],
                "common_mistakes": [
                    {
                        "mistake": "读 CSV 不加 header，表头变成第一行数据",
                        "why": "CSV 默认把每行当数据，于是出现名为「name」的奇怪取值。",
                        "fix": "加 .option(\"header\", True)；不够再加 .option(\"inferSchema\", True)。"
                    },
                    {
                        "mistake": "以为读 CSV 后就能直接做数值运算，结果报类型错",
                        "why": "没开 inferSchema，列全是字符串，对字符串做求和自然失败。",
                        "fix": "读取后先 printSchema 确认类型；或用 schema=StructType 显式声明。"
                    },
                    {
                        "mistake": "以为 read.csv 立刻把整个文件读进内存",
                        "why": "read 是惰性的，只登记计划；否则读 100 GB 岂不是瞬间撑爆 Driver。",
                        "fix": "记住：读是「记账」，Action 才「真读」；想看样本用 df.limit(10).show()。"
                    },
                    {
                        "mistake": "用 pandas 的 read_csv 习惯去读（pd.read_csv）",
                        "why": "那是单机库，读大文件会 OOM；而且返回的是 pandas 对象而非 Spark DataFrame。",
                        "fix": "用 spark.read.csv；若确实要小样本调试，再用 df.limit(n).toPandas() 转回 pandas。"
                    }
                ],
                "review": "上一课我们确认了：DataFrame 是「带 Schema 的分布式表」，它在 RDD 之上加了一份结构信息，让 Spark 能自动优化。\n\n但这张表从哪来？你不可能凭空变出一张表。数据要么是你手写的测试数据，要么是硬盘上的真实文件——CSV、JSON、Parquet，这些才是真实世界的常态。\n\n这一课，我们就把「把数据装进 DataFrame」这件事做一遍。",
                "problem": "要在 Spark 里处理数据，第一步永远是「把数据变成 DataFrame」。那从内存集合、CSV、JSON、Parquet 这几种最常见来源，分别该怎么创建？读的时候有哪些「不加就会踩坑」的选项？为什么读文件看起来「秒回」却还没真读？",
                "preview": "现在我们能把数据装进 DataFrame 了——无论是内存集合还是 CSV / JSON / Parquet。\n\n但有一个隐患一直没解决：刚刚读 CSV 时，我们用 inferSchema「猜」类型。猜，就可能有错；而且很多时候 Spark「猜」出来的类型并不符合你的预期。\n\n有没有一种更可靠的方式，让我自己明确告诉 Spark「每一列到底叫什么、是什么类型」？这正是 Schema 存在的意义，也是理解 DataFrame 的关键支点。\n\n下一课：Schema 与数据类型。"
            }
        },
        {
            "title": "Schema 与数据类型",
            "slug": "l2-schema-types",
            "description": "理解 Schema（StructType）与常见数据类型，学会显式声明与查看。",
            "objective": "学完本课，你应该能够：说出 Schema 是什么、为什么显式声明 Schema 比 inferSchema 更可靠；列举常见 Spark 数据类型；并能在创建 DataFrame 时显式指定 Schema 以避免推断错误。",
            "estimated_minutes": 15,
            "order_index": 2,
            "prerequisites": "",
            "content": {
                "explanation": "【先用人话理解】\n\nSchema 就是「表的说明书」：它告诉你这张表有几列、每列叫什么名字、装的是什么类型的数据（数字？文本？时间？）。就像快递分拣线必须知道「包裹里有几个格子、每个格子放什么」，Spark 也需要这份说明书来判断「我能对这个字段做什么运算、能不能优化」。\n\n【为什么显式声明更好】\n\ninferSchema 是「抽样猜测」——它只读一部分数据来猜类型，可能因为样本偏差猜错（比如某列全是数字字符串被猜成 LongType，出现小数就崩；或者首行是空值被猜成 NullType）。显式用 StructType 声明，等于你亲自拍板：「这一列就是 IntegerType，那一列是 StringType」，彻底避免歧义，且读取时不必再抽样、更快。\n\n【常见数据类型】\n\n· StringType：文本\n· IntegerType / LongType：整型（后者范围更大）\n· DoubleType / FloatType：浮点\n· BooleanType：布尔\n· TimestampType / DateType：时间\n· ArrayType / MapType / StructType：嵌套结构（进阶）\n每列还可以指定 nullable（是否可为空），默认 True——这对后续 join、聚合、空值处理都有影响。\n\n【怎么看 Schema】\n\ndf.printSchema() 打印「字段名 / 类型 / 是否可空」的树状结构；df.schema 拿到 StructType 对象；df.dtypes 拿到 (列名, 类型名) 的列表。\n\n【写下代码后，Spark 内部发生了什么】\n\n当你显式传 schema，Spark 不再抽样推断，而是直接按你给的说明书解析每行数据——遇到类型不符会直接报错（fail-fast），而不是默默存成错误类型。这让错误更早、更清晰地暴露。",
                "examples": [
                    {
                        "title": "显式声明 Schema（推荐）",
                        "code": "from pyspark.sql.types import *\nschema = StructType([\n    StructField(\"order_id\", LongType(), nullable=False),\n    StructField(\"amount\", DoubleType(), nullable=True),\n    StructField(\"city\", StringType(), nullable=True),\n])\ndf = spark.read.schema(schema).csv(\"orders.csv\", header=True)\ndf.printSchema()",
                        "note": "用 schema= 显式声明后，Spark 不抽样、不猜；类型不符直接报错，问题暴露得更早。"
                    },
                    {
                        "title": "查看 Schema 的几种方式",
                        "code": "df.printSchema()      # 树状打印\nprint(df.dtypes)    # [('name','string'),('age','bigint')]\nprint(df.schema['age'].dataType)  # 拿到单个字段类型",
                        "note": "排查「为什么这列不能做数值运算」时，第一件事就是 printSchema 看类型。"
                    },
                    {
                        "title": "类型不匹配会被当场拦下",
                        "code": "bad = StructType([StructField(\"x\", IntegerType())])\n# 若某行 \"abc\" 无法转成整数 → 报错，而不是偷偷存成 null/字符串",
                        "note": "显式 schema 的 fail-fast 特性，能避免「脏数据悄悄污染后续计算」。"
                    }
                ],
                "key_points": [
                    "Schema = 表的说明书：列名 + 数据类型 + 是否可空(nullable)",
                    "显式 StructType 声明 > inferSchema：不抽样、不猜、类型不符直接报错",
                    "常见类型：String / Integer / Long / Double / Boolean / Timestamp / Date",
                    "nullable 默认 True，影响 join、聚合与空值处理",
                    "printSchema() 是排查类型问题的第一命令"
                ],
                "common_mistakes": [
                    {
                        "mistake": "依赖 inferSchema，遇到脏数据被猜错类型",
                        "why": "抽样推断可能把小数列猜成 Long，或把混合列猜成 NullType，后续运算崩溃。",
                        "fix": "生产环境优先显式声明 StructType。"
                    },
                    {
                        "mistake": "以为 LongType 和 IntegerType 没区别",
                        "why": "大整数（如订单号、 时间戳毫秒）用 IntegerType 会溢出；Spark 默认推断长整数为 LongType。",
                        "fix": "涉及大数或时间戳，确认用 LongType；金钱用 DecimalType 避免浮点误差。"
                    },
                    {
                        "mistake": "忽略 nullable，join 时出现意外空值",
                        "why": "字段默认可空，聚合或 join 键出现 null 会导致行被丢弃或产出 null 键。",
                        "fix": "对关键键显式 nullable=False；或先用 dropna / 过滤空值再处理。"
                    }
                ],
                "review": "上一课我们学会了用 spark.read 把 CSV / JSON / Parquet 读成 DataFrame，但为了省事我们用了 inferSchema「猜」类型。\n\n猜，总有出错的时候——尤其是真实数据里总有些「不按套路来」的脏数据。\n\n这一课，我们把「类型」这件事彻底讲清楚：Schema 到底是什么，常见类型有哪些，以及怎么由你亲自拍板，而不是让 Spark 去猜。",
                "problem": "DataFrame 之所以能比 RDD 更快，靠的就是 Spark 知道「每列是什么类型」。可是类型从哪来？自动推断靠谱吗？如果我想要绝对可控、不踩脏数据的坑，该怎么显式告诉 Spark「每一列到底是什么」？",
                "preview": "Schema 这张「说明书」我们已经能自己写了。可写好了表，下一步自然是「看看它长什么样」——不是只看前几行，而是确认结构、抽查字段。\n\nSpark 提供了几个极简的「检视」动作：show、printSchema，以及如何正确引用某一列。这些是日常调试的第一把瑞士军刀。\n\n下一课：检视数据。"
            }
        },
        {
            "title": "检视数据",
            "slug": "l2-inspect",
            "description": "show / printSchema / 列引用等基础检视操作。",
            "objective": "学完本课，你应该能够：用 show / printSchema 查看数据与结构；用三种方式引用列（df.col / df[\"col\"] / col(\"col\")）；并理解 show 默认只显示 20 行这一设计意图。",
            "estimated_minutes": 12,
            "order_index": 3,
            "prerequisites": "",
            "content": {
                "explanation": "【先用人话理解】\n\n「检视」就是「看看这张表到底长什么样」。你刚创建或修改了一个 DataFrame，最自然的冲动就是「让我看看」。Spark 为此准备了几个最直接的小工具：show 看数据、printSchema 看结构、列引用帮你精确定位某一列。\n\n【三个核心动作】\n\n· show(n)：以表格形式打印前 n 行（默认 20）。这是查看数据样貌最快的方式，本身是一个 Action，会触发执行。\n· printSchema()：打印「字段名 / 类型 / 是否可空」的树状结构，也是 Action。\n· 列引用：df.age、df[\"age\"]、col(\"age\") —— 三种等价写法，返回一个 Column 对象，供后续 select / filter 使用。\n\n【为什么 show 默认只看 20 行】\n\n这是刻意设计：防止你一不小心把上亿行全打印出来、刷屏甚至撑爆 Driver。要看更多写 df.show(100)；要全部请先用 count() 确认量级再决定——记住 DataFrame 可能极大。\n\n【列引用的坑】\n\n用 df.age 这种「属性式」写法，当列名含空格或特殊字符、或与 DataFrame 已有方法名冲突时就不行，这时要用 df[\"order amount\"] 或 col(\"order amount\")。三种写法等价，建议保持一致即可。\n\n【写下代码后，Spark 内部发生了什么】\n\nshow / printSchema 作为 Action，会触发前面所有 Transformation 真正执行；show 内部只取下 n 行就收工（不会算全表），所以开销可控。",
                "examples": [
                    {
                        "title": "show 与 printSchema 配合",
                        "code": "df = spark.read.option(\"header\",True).option(\"inferSchema\",True).csv(\"people.csv\")\ndf.printSchema()        # 先看结构（列名 / 类型）\ndf.show(5)              # 再抽样看 5 行数据\ndf.show(50, truncate=False)  # 不截断长字符串",
                        "note": "先结构后数据，是检视 DataFrame 的标准顺序；truncate=False 可看完整长文本。"
                    },
                    {
                        "title": "三种列引用写法",
                        "code": "from pyspark.sql.functions import col\nc1 = df.age          # 属性式（列名不能含空格）\nc2 = df[\"age\"]       # 中括号式（通用）\nc3 = col(\"age\")      # 函数式（最稳妥，常用于表达式）",
                        "note": "三者等价，都是 Column 对象；复杂列名（带空格）只能用后两种。"
                    }
                ],
                "key_points": [
                    "show(n)：表格打印前 n 行（默认 20），是 Action",
                    "printSchema()：打印字段结构树，是 Action",
                    "列引用三种写法：df.col / df[\"col\"] / col(\"col\")，等价",
                    "show 默认 20 行是防刷屏设计，要看全部先 count() 确认量级",
                    "列名含空格或冲突时用 df[\"col\"] 或 col(\"col\")"
                ],
                "common_mistakes": [
                    {
                        "mistake": "用 df.col 访问带空格的列名，报 AttributeError",
                        "why": "Python 属性名不能含空格，df.order amount 是语法错误。",
                        "fix": "改用 df[\"order amount\"] 或 col(\"order amount\")。"
                    },
                    {
                        "mistake": "以为 show() 把全表数据都加载了",
                        "why": "show 只取前 n 行就收工，不会计算全表；所以即使百亿行，show(20) 也很安全。",
                        "fix": "想看全貌先 count()，再决定是否需要 collect（慎用）。"
                    },
                    {
                        "mistake": "直接用 Python len(df) 或下标 df[0]",
                        "why": "DataFrame 不是本地集合，没有这些操作。",
                        "fix": "看行数用 df.count()；看前几行用 df.show() / df.take(n)。"
                    }
                ],
                "review": "上一课我们亲手写好了 Schema，告诉 Spark「每一列是什么」。表造好了，第一反应肯定是「让我看看它」。\n\n可 DataFrame 是分布式的、可能巨大，不能用普通 Python 的方式（len / 下标 / 直接打印）去摸它。Spark 给了几个专门的小工具，既让你看清楚，又不至于把机器搞崩。\n\n这一课，就把这几个「查看」动作一次说清。",
                "problem": "DataFrame 不像本地列表，没法直接 print 或取长度。那我想「瞄一眼数据、确认结构、定位某列」，该用什么安全又高效的动作？为什么 show 默认只给你看 20 行？",
  "preview": "检视工具到手了——show / printSchema / 列引用，足够你随时「看一眼」DataFrame。\n\n现在我们可以正式开始「加工」这张表了。最基础、最常用的两类操作，就是「挑选我关心的列」和「按条件筛选行」。\n\n这正是下一课的主题：select / filter / where。"
            }
        },
        {
            "title": "select / filter / where",
            "slug": "l2-select-filter",
            "description": "筛选列与行的核心变换：select、filter、where、isin、between。",
            "objective": "学完本课，你应该能够：用 select 挑选 / 重命名列、用 filter / where 按条件筛选行；并避开「用 Python 的 and / or / == 而非 Column 运算符」这一最常见陷阱。",
            "estimated_minutes": 15,
            "order_index": 4,
            "prerequisites": "",
            "content": {
                "explanation": "【先用人话理解】\n\nselect 和 filter 是 DataFrame 里「用得最多」的两个动作：\n· select = 「我要看哪些列」（投影）。就像从一张宽表里只抽出你关心的几列。\n· filter / where = 「我要哪些行」（过滤）。就像只保留符合条件的记录。两者功能一样，where 是 filter 的别名，看个人习惯。\n它们都是 Transformation——只记账、不立即执行。\n\n【Column 表达式的陷阱（重点）】\n\nfilter 的条件必须是「Column 表达式」，而不是 Python 普通布尔。在 PySpark 里：\n· 正确：df.filter(df.age > 18) —— 这里 > 被 Column 重载，返回一个 Column。\n· 错误：df.filter(df.age > 18 and df.city == \"BJ\") —— Python 会先算 and，把两个 Column 当布尔判断，直接报错。必须用位运算：df.filter((df.age > 18) & (df.city == \"BJ\"))，且每个条件必须加括号。\n· 错误：用 is 判断相等（df.city is \"BJ\"）—— is 比较对象身份，永远不对；要用 ==。\n\n【常用配套】\n· selectExpr：用 SQL 片段选列，如 df.selectExpr(\"age * 2 as age_x2\")。\n· isin / between：df.filter(df.city.isin(\"BJ\",\"SH\"))；df.filter(df.age.between(18, 60))。\n\n【写下代码后，Spark 内部发生了什么】\n\nselect / filter 在 Driver 记录「要哪些列 / 哪些行」，加入 DAG；等到 Action 时才真正在各分区上执行——Catalyst 还可能把 filter 下推到读取阶段提前过滤（谓词下推），减少后续数据量。",
                "examples": [
                    {
                        "title": "select 挑选与重命名",
                        "code": "df.select(\"name\", \"age\").show()              # 选两列\ndf.select(df.name, (df.age + 1).alias(\"age_next\")).show()  # 计算并重命名\ndf.selectExpr(\"name\", \"age * 2 as age_x2\").show()",
                        "note": "select 返回新 DataFrame；想保留原列名用原名，想改名用 alias 或 selectExpr 里的 as。"
                    },
                    {
                        "title": "filter 多条件是 & 不是 and",
                        "code": "# 正确写法（每个条件单独括号，用位运算符）\nadults_in_bj = df.filter((df.age > 18) & (df.city == \"BJ\"))\n\n# 错误写法：会抛 TypeError\n# df.filter(df.age > 18 and df.city == \"BJ\")",
                        "note": "位运算 & | ~ 对应 与/或/非；Python 的 and/or 不能用在 Column 条件上。"
                    },
                    {
                        "title": "isin 与 between",
                        "code": "df.filter(df.city.isin(\"BJ\", \"SH\")).show()\ndf.filter(df.age.between(18, 60)).show()",
                        "note": "isin 等价于 SQL 的 IN；between 等价于 BETWEEN ... AND ...。"
                    }
                ],
                "key_points": [
                    "select = 投影（挑列）；filter / where = 过滤（挑行），二者等价",
                    "过滤条件必须用 Column 运算符，多条件用 & | ~ 且每个条件单独加括号",
                    "禁止用 Python 的 and / or / is 拼接 Column 条件",
                    "selectExpr 可用 SQL 片段；isin / between 是常用便捷条件",
                    "filter 可被 Catalyst 下推（谓词下推），减少后续数据量"
                ],
                "common_mistakes": [
                    {
                        "mistake": "用 and / or 连接多个 filter 条件",
                        "why": "Python 会先把两个 Column 当布尔求值，抛 \"ValueError: Cannot convert Column to bool\"。",
                        "fix": "用 (cond1) & (cond2) 与 (cond1) | (cond2)，每个条件单独括号。"
                    },
                    {
                        "mistake": "用 is 判断相等：df.city is \"BJ\"",
                        "why": "is 比较对象身份而非值，永远得不到预期结果。",
                        "fix": "用 == 判断值相等；用 isNull() / isNotNull() 判断空值。"
                    },
                    {
                        "mistake": "filter 之后忘了接住返回值",
                        "why": "DataFrame 不可变，filter 返回新 DataFrame，原 df 不变。",
                        "fix": "用 new_df = df.filter(...) 接住结果。"
                    },
                    {
                        "mistake": "以为 select 会修改原表",
                        "why": "所有变换都是惰性且返回新对象，原 DataFrame 不被改动。",
                        "fix": "链式调用或赋值接住：df2 = df.select(...).filter(...)。"
                    }
                ],
                "review": "上一课我们学会了「看」DataFrame——show / printSchema / 列引用。\n\n现在到了真正「动手加工」的第一步。面对一张宽表，你最常做的无非两件事：挑出关心的列、挑出符合条件的行。\n\n这听起来简单，但 PySpark 里有个极易踩的坑：过滤条件不能用普通的 Python 逻辑词。这一课，我们不仅把 select / filter 讲透，还要把这个坑彻底填平。",
                "problem": "怎么从 DataFrame 里「选列」和「选行」？为什么写 filter 条件时，Python 的 and / or / is 会直接报错？正确的 Column 写法究竟长什么样？学会之后，日常 80% 的数据清洗第一步就握在你手里了。",
                "preview": "select / filter 会用了，你能「挑列、挑行」了。\n\n但真实数据往往不能直接用——比如金额要换算币种、要加一列「是否成年」、要把两个字段拼起来。这些都是「根据已有列，生成新列」的需求。\n\n下一课：withColumn 与 Column 表达式。"
            }
        },
        {
            "title": "withColumn 与 Column 表达式",
            "slug": "l2-withcolumn",
            "description": "用 withColumn 生成 / 修改列，掌握 Column 表达式与常用函数。",
            "objective": "学完本课，你应该能够：用 withColumn 新增或修改一列、用 withColumnRenamed 改名、用 pyspark.sql.functions 里的 lit / when / concat / cast 构造列表达式；并知道为什么要用 F 前缀而不是直接裸写。",
            "estimated_minutes": 15,
            "order_index": 5,
            "prerequisites": "",
            "content": {
                "explanation": "【先用人话理解】\n\nwithColumn 就是「往表里加一列，或者改写已有的一列」。你告诉 Spark：「基于已有的列，算出一个新的值，放进一个新列（或覆盖原列）」。它的参数是「新列名」和「一个 Column 表达式」——这个表达式描述「这一列每个单元格怎么算出来」。\n\n【为什么要用 pyspark.sql.functions（习惯上 import 成 F）】\n\n直接用 Python 内置函数（如 abs、round）对 Column 不生效——Column 不是数字。必须用 Spark 提供的函数，才有「不知道里面具体值、但描述怎么算」的延迟计算能力。例如 F.abs(df.amount)、F.round(df.amount, 2)。裸写 Python 函数只对 collect 后的本地数据有效，会破坏分布式。\n\n【常见表达】\n\n· F.lit(常量)：放一个固定值，如 F.lit(0)。\n· F.when(条件, 值).otherwise(默认值)：条件赋值，等价于 SQL 的 CASE WHEN。\n· F.concat / F.concat_ws：拼接字符串。\n· .cast(类型)：类型转换，如 df.age.cast(\"string\")。\n· withColumnRenamed(旧, 新)：改名（不修改内容）。\n\n【一个容易混淆的点】\n\nwithColumn 的第一个参数如果和已有列同名，会「覆盖」该列；想新增就用新名字。返回的是新 DataFrame，原表不变。\n\n【写下代码后，Spark 内部发生了什么】\n\nwithColumn 在 DAG 中加入一个「生成新列」的节点；Catalyst 可能把它和相邻的 map 类操作融合进同一个 Stage，数据流过一次就完成，不落盘。",
                "examples": [
                    {
                        "title": "新增列与覆盖列",
                        "code": "from pyspark.sql import functions as F\n\n# 新增一列：金额打 9 折\ndf2 = df.withColumn(\"amount_discount\", df.amount * 0.9)\n\n# 覆盖已有列：把 age 转成字符串\ndf3 = df.withColumn(\"age\", df.age.cast(\"string\"))",
                        "note": "同名则覆盖，异名则新增；返回新 DataFrame，原 df 不变。"
                    },
                    {
                        "title": "when / otherwise 条件列",
                        "code": "df4 = df.withColumn(\n    \"age_group\",\n    F.when(df.age < 18, \"minor\")\n     .when(df.age < 60, \"adult\")\n     .otherwise(\"senior\"))",
                        "note": "when/otherwise 对应 SQL 的 CASE WHEN；链条顺序即判断顺序，最后一个 otherwise 是兜底层。"
                    },
                    {
                        "title": "lit / concat",
                        "code": "df5 = df.withColumn(\"flag\", F.lit(1))\ndf6 = df.withColumn(\"full_name\", F.concat(df.first, F.lit(\" \"), df.last))",
                        "note": "lit 放常量；concat 拼接多列，concat_ws 可指定分隔符。"
                    }
                ],
                "key_points": [
                    "withColumn(列名, 表达式)：新增或修改（同名覆盖）一列，返回新 DataFrame",
                    "列表达式必须用 pyspark.sql.functions（F）里的函数，不能裸用 Python 内置函数",
                    "F.when/otherwise 实现条件赋值（CASE WHEN）；F.lit 放常量；F.concat 拼接",
                    "cast(\"类型\") 做类型转换；withColumnRenamed 仅改名",
                    "所有操作惰性，Catalyst 可将其与其他 map 融合进同一 Stage"
                ],
                "common_mistakes": [
                    {
                        "mistake": "裸用 Python 函数处理 Column：abs(df.amount)",
                        "why": "Column 不是具体数值，abs 不知道怎么算；而且会破坏分布式执行。",
                        "fix": "用 F.abs(df.amount)；复杂逻辑用 F.udf（必要时）或 pandas_udf。"
                    },
                    {
                        "mistake": "想改列却忘了接住返回值，原表没变化",
                        "why": "DataFrame 不可变，withColumn 返回新对象。",
                        "fix": "df = df.withColumn(...) 或直接链式。"
                    },
                    {
                        "mistake": "when 忘了 otherwise，结果出现 null",
                        "why": "没有兜底层时，不满足任何 when 的行该列就是 null。",
                        "fix": "最后补 .otherwise(默认值)。"
                    },
                    {
                        "mistake": "用 Python 的 if/else 而不是 when",
                        "why": "if/else 在 Driver 端一次性判定，无法逐行按列值分支。",
                        "fix": "逐行分支必须用 F.when(...).otherwise(...)。"
                    }
                ],
                "review": "上一课我们用 select / filter 完成了「挑列、挑行」。\n\n但真实数据常常「不能直接用」：金额需要换算、需要标注「是否成年」、需要把姓和名拼起来。这些都指向同一件事——「根据已有列，生成一个新的列」。\n\n这一课，我们学习 withColumn，以及它背后那套「Column 表达式」语言。",
                "problem": "如何给 DataFrame 增加或修改一列？为什么直接用 Python 的 abs / round / if 对 Column 不灵？正确的 Spark 函数该怎么写、为什么前面总要加 F？",
                "preview": "现在你能挑列、挑行、加新列了。\n\n接下来要处理的是「顺序」与「重复」：按某列排序、去掉重复行、取前 N 条——这些是查询末尾最常见的收尾动作，也是 SQL 里 ORDER BY / DISTINCT / LIMIT 的对应物。\n\n下一课：排序、去重与常用操作。"
            }
        },
        {
            "title": "排序、去重与常用操作",
            "slug": "l2-sort-dedup",
            "description": "orderBy / sort、distinct / dropDuplicates、limit、drop 等收尾操作。",
            "objective": "学完本课，你应该能够：用 orderBy / sort 按单列或多列排序并控制升降序；用 distinct / dropDuplicates 去重；用 limit 取前 N；并区分 distinct 与 dropDuplicates(on=...) 的差异。",
            "estimated_minutes": 12,
            "order_index": 6,
            "prerequisites": "",
            "content": {
                "explanation": "【先用人话理解】\n\n这一课是「收尾三件套」：\n· 排序（orderBy / sort）：按某列把行排个先后——就像 Excel 的排序。\n· 去重（distinct / dropDuplicates）：去掉重复的行或重复的组合。\n· 截断（limit）：只要前 N 行。\n它们通常出现在一条变换链的末尾，在你拿到「最终想要的那些行」之前做最后整理。\n\n【排序细节】\n\n· df.orderBy(\"age\") 默认升序；降序用 F.desc(\"age\") 或 df.age.desc()。\n· 多列：orderBy(\"city\", F.desc(\"age\"))——先按 city 升序，city 相同再按 age 降序。\n· orderBy 与 sort 完全等价。\n\n【去重细节】\n\n· distinct()：整行完全相同才去重。\n· dropDuplicates([\"name\"]) ：只按指定列判断重复（如同一 name 只留一行），其余列取首次出现的值。这是比 distinct 更常用、更可控的写法。\n\n【limit】\n\nlimit(n) 取前 n 行；注意它不是「先全排序再取」那么简单——在有序场景（如 orderBy 后）取前 N 是 TopN 语义。功能上等价于 SQL 的 LIMIT。\n\n【写下代码后，Spark 内部发生了什么】\n\norderBy 通常触发一次 Shuffle（要把相同排序键汇聚到同一分区才能全局有序）——这点会在 Level 5 展开；limit 在很多情况下可以下推、只取所需分区的前 N。",
                "examples": [
                    {
                        "title": "多列排序",
                        "code": "from pyspark.sql import functions as F\ndf.orderBy(\"city\", F.desc(\"age\")).show()   # city 升序，age 降序\ndf.sort(F.col(\"amount\").desc()).show()       # sort 与 orderBy 等价",
                        "note": "升序默认；降序必须用 F.desc() 或 .desc()，不能写字符串 \"desc\"。"
                    },
                    {
                        "title": "distinct 与 dropDuplicates",
                        "code": "df.distinct().show()                       # 整行去重\ndf.dropDuplicates([\"name\"]).show()          # 按 name 去重，保留首次\ndf.dropDuplicates([\"name\", \"city\"]).show()  # 按多列组合去重",
                        "note": "去重前先想清楚「按哪些列算重复」，否则可能误删信息。"
                    },
                    {
                        "title": "limit 取前 N",
                        "code": "df.orderBy(F.desc(\"amount\")).limit(10).show()  # 金额最高的 10 行",
                        "note": "先排序再 limit 即 TopN；limit 本身不会触发全表扫描式排序。"
                    }
                ],
                "key_points": [
                    "orderBy / sort 等价；降序用 F.desc() 或 .desc()，多列依次传入",
                    "distinct() 整行去重；dropDuplicates([\"col\"]) 按指定列去重（更可控）",
                    "limit(n) 取前 N 行；配合 orderBy 即 TopN",
                    "orderBy 通常触发一次 Shuffle（Level 5 展开）",
                    "删除列用 drop(\"col\")；改名用 withColumnRenamed"
                ],
                "common_mistakes": [
                    {
                        "mistake": "用字符串 \"desc\" 指定降序：orderBy(\"age desc\")",
                        "why": "orderBy 的字符串参数只当列名，不会解析 \"desc\" 关键字。",
                        "fix": "用 F.desc(\"age\") 或 df.age.desc()。"
                    },
                    {
                        "mistake": "以为 distinct 只按某几列去重",
                        "why": "distinct() 看的是「整行完全相同」。",
                        "fix": "只想按某些列去重用 dropDuplicates([\"col\"])。"
                    },
                    {
                        "mistake": "用 dropDuplicates 却没想清「保留哪一行」",
                        "why": "保留的是首次出现的行，若业务要「保留最大值的行」需先排序或用窗口函数。",
                        "fix": "明确去重保留规则；必要时配合 orderBy + 窗口函数。"
                    }
                ],
                "review": "上一课我们用 withColumn 生成了新列。\n\n数据加工得差不多了，最后往往需要做点「收尾」：排个序方便看、去掉重复的记录、只取前几条。\n\n这些动作对应 SQL 里的 ORDER BY / DISTINCT / LIMIT，是查询链的常用收尾。这一课一次讲清。",
                "problem": "如何按某列或多列排序（含升降序）？如何去掉完全重复或按某几列重复的行？limit 取前 N 又该怎么用？distinct 和 dropDuplicates 到底差在哪？",
                "preview": "收尾动作也掌握了。可我们一直只是在「描述」数据——挑列、过滤、加列、排序。\n\n但真正数据分析的核心，往往是「分组统计」：每个城市卖了多少、每个用户下了几单、平均值是多少。这正是 groupBy 与聚合要做的事，也是 DataFrame 最有力的武器之一。\n\n下一课：groupBy 与聚合。"
            }
        },
        {
            "title": "groupBy 与聚合",
            "slug": "l2-groupby-agg",
            "description": "分组与聚合：groupBy、agg、count/sum/avg/max/min、多列聚合。",
            "objective": "学完本课，你应该能够：用 groupBy 分组并用 agg / count / sum / avg 等聚合；给聚合结果起别名；对多列做不同聚合；并理解「分组列不能在 agg 里再当普通列」这一约束。",
            "estimated_minutes": 15,
            "order_index": 7,
            "prerequisites": "",
            "content": {
                "explanation": "【先用人话理解】\n\ngroupBy 就是「按某个维度把数据分成几堆」，然后「在每一堆上算一个汇总值」。比如「按城市分组，算每个城市的总销售额」——城市是分组键，总销售额是聚合值。这是数据分析的心脏操作，对应 SQL 的 GROUP BY。\n\n【两种写法】\n\n1) 快捷写法：df.groupBy(\"city\").sum(\"amount\") —— 直接对指定列做某一种聚合。\n2) 通用写法：df.groupBy(\"city\").agg(F.sum(\"amount\").alias(\"total\"), F.avg(\"age\").alias(\"avg_age\")) —— 一次对多列做不同聚合，且能起别名，最常用。\n\n【常用聚合函数（都在 F 下）】\n\ncount / sum / avg / max / min / mean，以及 countDistinct / collect_list（收集成数组）。\n\n【关键约束】\n\ngroupBy 之后，出现在 groupBy 里的列是「分组键」，可以直接出现在结果里；而「非分组列」不能直接出现在 select 里（除非被聚合）——这和 SQL 完全一致。想同时拿「分组键 + 多个聚合」，就用 agg 一起写。\n\n【写下代码后，Spark 内部发生了什么】\n\ngroupBy 通常触发一次 Shuffle（把相同键的行汇聚到同一分区），然后各分区本地预聚合、再跨节点合并——这正是 Level 5 要深挖的「宽依赖 / Shuffle」。现在你只需知道：分组聚合是 Spark 里最常见的 Shuffle 来源之一。",
                "examples": [
                    {
                        "title": "基础分组聚合",
                        "code": "from pyspark.sql import functions as F\ndf.groupBy(\"city\").sum(\"amount\").show()\n\n# 多聚合 + 别名（推荐写法）\n(df.groupBy(\"city\")\n   .agg(F.sum(\"amount\").alias(\"total\"),\n        F.avg(\"age\").alias(\"avg_age\"),\n        F.count(\"*\").alias(\"cnt\"))\n   .show())",
                        "note": "agg 里用 alias 给聚合列起名；count(\"*\") 统计行数，count(\"col\") 统计非 null。"
                    },
                    {
                        "title": "多列分组",
                        "code": "df.groupBy(\"city\", \"product\").agg(F.sum(\"amount\").alias(\"amt\")).show()",
                        "note": "多分组键即为 SQL 的 GROUP BY city, product；结果按组合去重分组。"
                    },
                    {
                        "title": "countDistinct 与 collect_list",
                        "code": "df.groupBy(\"city\").agg(\n    F.countDistinct(\"user_id\").alias(\"uv\"),\n    F.collect_list(\"product\").alias(\"products\")).show(truncate=False)",
                        "note": "countDistinct 算去重人数（UV）；collect_list 把同组元素收集成数组。"
                    }
                ],
                "key_points": [
                    "groupBy(键).agg(...) 是标准写法；count/sum/avg/max/min 均在 F 下",
                    "分组键可直接出现在结果；非分组列必须被聚合，否则报错（同 SQL）",
                    "聚合结果用 alias 起名，便于下游引用",
                    "多分组键 = SQL 的 GROUP BY a, b",
                    "groupBy 通常触发 Shuffle（Level 5 展开）——Spark 最常见的 Shuffle 来源之一"
                ],
                "common_mistakes": [
                    {
                        "mistake": "groupBy 后 select 非分组列（未被聚合）",
                        "why": "一个组里该列可能有多个值，Spark 不知道取哪个。",
                        "fix": "非分组列必须放进 agg（如 F.first(\"col\")）或加入 groupBy。"
                    },
                    {
                        "mistake": "用 sum 对字符串列聚合",
                        "why": "字符串不能相加，直接报错或结果无意义。",
                        "fix": "先确认类型（printSchema）；字符串聚合用 collect_list / concat_ws。"
                    },
                    {
                        "mistake": "混淆 count(\"*\") 与 count(\"col\")",
                        "why": "前者统计行数（含 null 行），后者统计该列非 null 数。",
                        "fix": "要「总人数」用 count(\"*\")；要「有手机号的用户数」用 count(\"phone\")。"
                    }
                ],
                "review": "前面几课我们完成了「挑列、挑行、加列、排序、去重」——这些都是「描述每行」的变换。\n\n但数据分析的灵魂往往是「汇总」：每个城市卖了多少、每个用户下了几单。这要求我们先按某个维度「分类」，再在每类里算一个值。\n\n这就是 groupBy + 聚合。这一课，我们把它彻底拿下。",
                "problem": "如何用 groupBy 分组、用 sum / avg / count 等聚合汇总？为什么 groupBy 之后不能直接 select 非分组列？一次对多列做不同聚合该怎么写？分组聚合背后，Spark 又付出了什么代价？",
                "preview": "至此，DataFrame 的「只读」链路已经相当完整：创建、检视、变换、分组聚合，全部覆盖。\n\n可还有一个绕不开的现实问题：学了这么多「读」，我们还没真正「写」过——怎么把处理好的 DataFrame 保存成文件、或者写进数据库？写的时候有哪些「模式」和坑？\n\n下一课：数据写出。"
            }
        },
        {
            "title": "数据写出",
            "slug": "l2-write-data",
            "description": "write：CSV/Parquet/JSON、写入模式、partitionBy、JDBC 与常见坑。",
            "objective": "学完本课，你应该能够：用 df.write 把 DataFrame 写出为 CSV / Parquet / JSON；理解 mode(overwrite/append/error/ignore) 的差别；用 partitionBy 按列分区落盘；并知道 write 本身是一个 Action（会触发执行）。",
            "estimated_minutes": 15,
            "order_index": 8,
            "prerequisites": "",
            "content": {
                "explanation": "【先用人话理解】\n\n「数据写出」就是把你处理好的 DataFrame，落到硬盘或别的系统里——变成 CSV 文件、Parquet 文件，或者写进数据库。这和我们前面学的「读」正好相反，是真正「交付成果」的一步。\n\n【基本写法】\n\ndf.write.csv(path) / .parquet(path) / .json(path)。链式写法：df.write.mode(\"overwrite\").parquet(path)。\n\n【写入模式 mode（非常重要）】\n\n· \"error\"（默认）：目标已存在则报错——防止误覆盖。\n· \"overwrite\"：覆盖已有输出。\n· \"append\"：追加写入（常用于流式 / 分批）。\n· \"ignore\"：已存在就什么都不做。\n不指定 mode 时默认 error，于是「路径已存在」就直接抛异常——这是新手最常见的写入报错来源。\n\n【partitionBy：按列分区落盘】\n\ndf.write.partitionBy(\"dt\", \"city\").parquet(path) 会按列值建嵌套目录（如 dt=2026-01/city=BJ/）。好处：下游查询可「分区裁剪」只读需要的目录，大幅提升性能。这是数仓建模的标准做法。\n\n【JDBC（点到为止）】\n\ndf.write.jdbc(url, table, mode=\"append\", properties={...}) 可把数据写进 MySQL / PostgreSQL 等关系库；生产里更常见的是先写对象存储（Parquet），再由下游系统消费。\n\n【关键认知：write 是 Action】\n\n和 show / count 一样，write 会触发前面整条链的真正执行——它也常常是 Job 的「终点」。",
                "examples": [
                    {
                        "title": "按模式写出 Parquet（推荐）",
                        "code": "df.write.mode(\"overwrite\").parquet(\"output/result\")  # 列式存储，自带 Schema\n\n# 分区写出\n(df.write.mode(\"overwrite\")\n   .partitionBy(\"dt\", \"city\")\n   .parquet(\"output/by_day_city\"))",
                        "note": "Parquet 是 Spark 默认推荐格式：列式、压缩、自带 Schema；partitionBy 生成 dt=.../city=... 嵌套目录。"
                    },
                    {
                        "title": "写 CSV 的常见写法",
                        "code": "df.write.option(\"header\", True).mode(\"overwrite\").csv(\"output/people\")",
                        "note": "写 CSV 要带上 header=True，否则下游读回时没有表头。"
                    },
                    {
                        "title": "写 JDBC（关系库）",
                        "code": "df.write.jdbc(\n    url=\"jdbc:mysql://host:3306/db\",\n    table=\"result\",\n    mode=\"append\",\n    properties={\"user\": \"u\", \"password\": \"p\"})",
                        "note": "JDBC 写出通常用于把结果同步到业务库；大数据量更推荐先落 Parquet。"
                    }
                ],
                "key_points": [
                    "write 是 Action，会触发前面整条链真正执行",
                    "mode 四种：error(默认)/overwrite/append/ignore——不选则路径存在即报错",
                    "Parquet 是推荐格式：列式、压缩、自带 Schema",
                    "partitionBy 按列建嵌套目录，支撑下游「分区裁剪」提速",
                    "JDBC 可写关系库，但大数据量优先落对象存储/Parquet"
                ],
                "common_mistakes": [
                    {
                        "mistake": "不写 mode，路径已存在直接报错",
                        "why": "write 默认 mode 是 errorIfExists，目标已存在就抛 AnalysisException。",
                        "fix": "明确 mode(\"overwrite\") / mode(\"append\")。"
                    },
                    {
                        "mistake": "写 CSV 忘记 option(\"header\", True)",
                        "why": "默认不写表头，下游读回时列名丢失。",
                        "fix": "写出 CSV 时补 .option(\"header\", True)。"
                    },
                    {
                        "mistake": "以为 write 是 Transformation，等了好久没反应",
                        "why": "write 是 Action，会真正执行；卡住往往是 Shuffle / 数据量大，而不是「没执行」。",
                        "fix": "确信它在跑——看 Spark UI 的 Job / Stage；必要时减小数据量先验证。"
                    },
                    {
                        "mistake": "partitionBy 选了高基数且为空/单调递增的列",
                        "why": "会产生海量小目录或单目录过大，反而拖慢。",
                        "fix": "选低到中基数、有业务意义的列（如日期维度）；避免用唯一 ID 做分区。"
                    }
                ],
                "review": "从「创建 DataFrame」到「select/filter/withColumn/groupBy」，我们已经能把一份原始数据加工成想要的汇总结果。\n\n但结果如果只能活在内存里、程序一停就没了，那就毫无意义。真实工作里，你必须把结果「落盘」——写成文件或写进数据库。\n\n这一课，就来补齐「写」这一半链路。",
                "problem": "如何用 DataFrame 写出 CSV / Parquet / JSON？写入模式 error/overwrite/append/ignore 有什么区别、为什么默认会报错？partitionBy 分区落盘有什么好处？write 本身会不会触发执行？",
                "preview": "至此，DataFrame 的「读 → 加工 → 写」完整闭环已经打通：创建、检视、变换、聚合、写出，一条龙。\n\n我们不妨停下来，用一个小任务把这一章彻底串起来——读一份真实 CSV，清洗、聚合、再写出。这既是复习，也是一次「我能独立写出来」的验证。\n\n下一课：DataFrame 综合练习。"
            }
        },
        {
            "title": "DataFrame 综合练习",
            "slug": "l2-comprehensive",
            "description": "用 DataFrame 走完一次完整链路：读 CSV → 清洗 → 聚合 → 写出。",
            "objective": "学完本课，你应该能够：独立把 Level 2 所学的「创建 / 检视 / select / filter / withColumn / groupBy / write」串成一次完整的 ETL 小任务，并随时说清每一步是 Transformation 还是 Action、是否会触发执行。",
            "estimated_minutes": 20,
            "order_index": 9,
            "prerequisites": "",
            "content": {
                "explanation": "【先人话理解】\n\n这一课给你一个「迷你 ETL」任务，把 Level 2 的全部零件揉进一次实战：读一份销售 CSV → 清洗（过滤脏数据）→ 加工（新增列 / 聚合）→ 写出。它逼着你把「每一步属于哪一类操作」「哪一步才真正触发执行」想清楚，是这一章的收束。\n\n【任务】\n\n输入 sales.csv（region, product, amount, ts），目标：\n1) 读入并确认 Schema；\n2) 过滤掉 amount 非正或缺失的行；\n3) 新增一列 amount_k 表示「千元」；\n4) 按 region 聚合总销售额；\n5) 按金额降序，写出为 Parquet（按 region 分区）。\n\n【把步骤对应到概念】\n\n· spark.read.csv + inferSchema → 创建（Lesson 2/3）\n· filter(amount > 0) → 变换（Lesson 5），用 & 连接条件\n· withColumn(\"amount_k\", amount/1000) → 变换（Lesson 6）\n· groupBy(\"region\").sum(\"amount\") → 聚合（Lesson 8），会触发 Shuffle\n· orderBy(desc) + write.partitionBy → 收尾 + 写出（Lesson 7/9），write 是 Action\n· 整条链前面都是 Transformation，只有 write（Action）才真正执行\n\n【🧪 自测（请先自己写，再对照）】\n\n1) 哪些是 Transformation？——filter / withColumn / groupBy / orderBy 全是，只有 write 是 Action。\n2) 哪一步会触发 Shuffle？—— groupBy 与 orderBy 通常各触发一次。\n3) 为什么先 printSchema 再聚合？——确认 amount 被推断为数值而非字符串，否则 sum 报错。",
                "examples": [
                    {
                        "title": "完整可运行迷你 ETL",
                        "code": "from pyspark.sql import SparkSession\nfrom pyspark.sql import functions as F\n\nspark = SparkSession.builder.master(\"local[*]\").appName(\"etl\").getOrCreate()\n\ndf = (spark.read.option(\"header\", True).option(\"inferSchema\", True).csv(\"sales.csv\"))\ndf.printSchema()   # 先确认 amount 是数值类型\n\nresult = (df.filter((df.amount > 0) & df.amount.isNotNull())\n          .withColumn(\"amount_k\", df.amount / 1000.0)\n          .groupBy(\"region\")\n          .sum(\"amount\").alias(\"total\")\n          .withColumnRenamed(\"sum(amount)\", \"total\"))\n\n(result.orderBy(F.desc(\"total\"))\n       .write.mode(\"overwrite\")\n       .partitionBy(\"region\")\n       .parquet(\"output/region_sales\"))",
                        "note": "整条链只有最后的 write 触发执行；groupBy 的聚合列名默认叫 sum(amount)，用 withColumnRenamed 改个好名字。"
                    },
                    {
                        "title": "安全先看结果（不写盘）",
                        "code": "result.orderBy(F.desc(\"total\")).show(20)",
                        "note": "正式 write 前，先用 show 验证聚合结果是否正确，避免写出错误数据。"
                    }
                ],
                "key_points": [
                    "迷你 ETL 链路：read → filter → withColumn → groupBy → orderBy → write",
                    "filter 多条件用 &，每个条件单独括号",
                    "write 才是 Action，触发前面整条链执行",
                    "groupBy / orderBy 通常触发 Shuffle（Level 5 展开）",
                    "写盘前先用 show 验证，避免写出错误结果"
                ],
                "common_mistakes": [
                    {
                        "mistake": "聚合后列名变成 sum(amount) 却没处理",
                        "why": "默认聚合列名是「sum(amount)」之类，下游难用。",
                        "fix": "用 alias(\"total\") 或在 groupBy 后 withColumnRenamed。"
                    },
                    {
                        "mistake": "filter 条件漏括号，用 and 而非 &",
                        "why": "Column 条件必须用位运算，否则直接报错。",
                        "fix": "(df.amount > 0) & df.amount.isNotNull() 每个条件加括号。"
                    },
                    {
                        "mistake": "写出前不看结果直接 write，写出脏数据",
                        "why": "没有先 show 验证，错误被直接落盘。",
                        "fix": "先用 show(20) 验证聚合与类型，再 write。"
                    }
                ],
                "review": "从「DataFrame 是什么」到「数据写出」，Level 2 的全部零件我们都拿到了：创建、检视、select / filter、withColumn、排序去重、groupBy 聚合、write。\n\n现在，是时候把这些零散的知识点串成一次完整的「动手体验」——读一份真实数据，清洗、聚合、落盘。这一课不是「再做几道题」，而是「恭喜你，把这一章真正收个尾」。",
                "problem": "能不能不靠提示，独立用 DataFrame 走完一次真实 ETL：从 CSV 读入、过滤脏数据、新增一列、按维度聚合、排序并写出？更重要的是，在写的过程中你能随时回答：这一步是 Transformation 还是 Action？哪一步会触发 Shuffle？这正是检验你是否真正串起 Level 2 的标准。",
                "preview": "恭喜你走完了 Level 2——从「DataFrame 是什么」，到「创建 / 检视 / 变换 / 聚合 / 写出」，你已经能用 Spark 完成一次完整的数据处理闭环。\n\n你现在已经能用 DataFrame 写出相当像样的程序了。于是一个很自然、也很关键的追问浮现出来：\n\n「我写的这些代码，Spark 到底是怎么执行的？」\n\n注意——这一次不是重新讲 Driver / Executor，而是进入一个全新的执行模型：执行计划。这正是 Level 3（Spark SQL）之后、Level 4（执行计划）要带你揭开的核心。\n\n去测验里检验一下自己吧。🏁"
            }
        }
    ]
}

def upsert():
    # 1) 合并进 course_seed.json
    with open(SEED, encoding="utf-8") as f:
        data = json.load(f)
    # 幂等：若已存在同 order_index 的 Level 2 则跳过 JSON 插入（避免重复）
    exists = any(lv.get("order_index") == 2 for lv in data["levels"])
    if not exists:
        data["levels"].append(LEVEL2)
        with open(SEED, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print("已写入 course_seed.json（Level 2）")
    else:
        print("course_seed.json 已存在 Level 2，跳过 JSON 写入")

    # 2) upsert 进数据库
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT id,title FROM course_levels WHERE order_index=2")
    row = cur.fetchone()
    if row:
        level_id = row[0]
        print(f"Level 2 已存在于 DB (id={level_id})，仅补充缺失 lesson")
    else:
        cur.execute(
            "INSERT INTO course_levels (title, description, order_index, status) VALUES (?,?,?,?)",
            (LEVEL2["title"], LEVEL2["description"], LEVEL2["order_index"], "active"))
        level_id = cur.lastrowid
        print(f"已插入 Level 2 (id={level_id})")

    inserted = 0
    for ls in LEVEL2["lessons"]:
        cur.execute("SELECT id FROM lessons WHERE slug=?", (ls["slug"],))
        if cur.fetchone():
            continue
        cur.execute(
            """INSERT INTO lessons (level_id, title, slug, description, objective,
               estimated_minutes, order_index, prerequisites, content)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (level_id, ls["title"], ls["slug"], ls.get("description",""), ls.get("objective",""),
             ls.get("estimated_minutes",15), ls["order_index"],              ls.get("prerequisites",""),
             json.dumps(ls["content"], ensure_ascii=False)))
        inserted += 1
    conn.commit()
    conn.close()
    print(f"新增 lesson 数：{inserted}")

if __name__ == "__main__":
    upsert()
