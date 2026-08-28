# -*- coding: utf-8 -*-
"""一次性脚本：为 Level 2（DataFrame 核心）的 10 个 lesson 各生成 5 道高质量单选题，
并幂等地合并进 quiz_seed.json 与 spark_quest.db 的 quizzes 表。

每课 5 题，按用户定义的 5 类目的编排：
  1) 概念理解题  2) 为什么存在题  3) 运行机制题  4) 场景应用题  5) 易错辨析题
题型统一为 single_choice；第 5 题「易错辨析」问「下列说法错误的是」，correct_index 指向错误项。
"""
import sqlite3, json, os

BASE = os.path.dirname(os.path.abspath(__file__))
SEED = os.path.join(BASE, "app", "quiz_seed.json")
DB = os.path.join(BASE, "spark_quest.db")

NEW_QUIZZES = [
    {
        "lesson_slug": "l2-what-is-dataframe",
        "questions": [
            {
                "type": "single_choice",
                "prompt": "DataFrame 最准确的定义是？",
                "options": [
                    "以命名列组织的分布式数据集（带 Schema 的表）",
                    "单机内存中的二维表，和 pandas.DataFrame 完全一样",
                    "一种分布式文件系统",
                    "Spark 用来存元数据的数据库"
                ],
                "correct_index": 0,
                "explanation": "DataFrame 是「以命名列组织的分布式数据集」：底层按分区分布式存放，同时带有 Schema（列名+类型）。它不是单机 pandas，也不是文件系统或元数据数据库。"
            },
            {
                "type": "single_choice",
                "prompt": "Spark 为什么要在 RDD 之上再提供 DataFrame 这一层？",
                "options": [
                    "为了在保留分布式能力的同时，让 Catalyst 能看懂结构并自动优化",
                    "因为 RDD 写起来太长，DataFrame 只是语法糖",
                    "因为 DataFrame 比 RDD 运行更快，和 Schema 无关",
                    "因为 RDD 已经被官方废弃"
                ],
                "correct_index": 0,
                "explanation": "DataFrame 在 RDD 之上加了 Schema（列名+类型），让 Catalyst 优化器能像 SQL 引擎一样做谓词下推、列裁剪、join 重排，这正是它比裸 RDD 快的根本原因。"
            },
            {
                "type": "single_choice",
                "prompt": "写下 spark.createDataFrame(rows, schema) 后，下列说法正确的是？",
                "options": [
                    "只是登记数据与结构，并未真正计算；show() 之类的 Action 出现后才执行",
                    "立即把全部数据载入 Driver 内存",
                    "立即创建一张物理表并写入磁盘",
                    "立即把每一行都计算一遍"
                ],
                "correct_index": 0,
                "explanation": "createDataFrame 只是「登记」数据与结构；和所有 Transformation 一样惰性，真正读取/计算要等 show / count 等 Action 触发。"
            },
            {
                "type": "single_choice",
                "prompt": "下列哪类任务最符合「优先用 DataFrame」的场景？",
                "options": [
                    "对 TB 级结构化数据做分组聚合，并希望 Spark 自动优化",
                    "本地几十行数据做一次性计算（更适合 pandas）",
                    "需要逐字节控制序列化的非结构化数据（更适合 RDD）",
                    "单纯打印一段文字"
                ],
                "correct_index": 0,
                "explanation": "DataFrame 的价值在「数据大到单机工具处理不动、且需自动优化」时最明显；小数据用 pandas 更简单，非结构化/底层控制才用 RDD。"
            },
            {
                "type": "single_choice",
                "prompt": "以下关于 DataFrame 与 RDD 的关系，说法错误的是？",
                "options": [
                    "DataFrame 和 RDD 是两种互相独立、可以互相替代的抽象",
                    "DataFrame 底层仍用 RDD 那套分区、血缘、Task 机制运行",
                    "DataFrame 比 RDD 多了一份 Schema（列名 + 类型）",
                    "DataFrame 是声明式 API，你写「要什么」，Spark 决定「怎么算」"
                ],
                "correct_index": 0,
                "explanation": "DataFrame 与 RDD 不是并列替代关系：DataFrame 底层执行模型就是 RDD，它是「上层声明式 API」而非独立替代物。"
            }
        ]
    },
    {
        "lesson_slug": "l2-create-dataframe",
        "questions": [
            {
                "type": "single_choice",
                "prompt": "spark.read.csv(path) 返回的对象是？",
                "options": [
                    "一个 DataFrame，但此时尚未真正读取数据（惰性）",
                    "已经把文件全部读进内存的 pandas.DataFrame",
                    "一个 RDD",
                    "一个文件句柄对象"
                ],
                "correct_index": 0,
                "explanation": "spark.read.csv 返回的是 Spark DataFrame，且是惰性的——只是登记读取计划，数据并未真正读入。"
            },
            {
                "type": "single_choice",
                "prompt": "读 CSV 时通常要加 .option('header', True)，主要是为了？",
                "options": [
                    "让 Spark 把第一行当作表头（列名），否则表头会变成数据",
                    "提升文件读取速度",
                    "对文件进行压缩",
                    "避免读取时报错"
                ],
                "correct_index": 0,
                "explanation": "不加 header，CSV 第一行会被当成普通数据，出现名为「name」的奇怪取值；加 header 才把首行当列名。"
            },
            {
                "type": "single_choice",
                "prompt": "读 CSV 后调用 show(10)，数据真正被读取发生在？",
                "options": [
                    "show() 这个 Action 触发时，各 Executor 读取自己负责的分片并解析",
                    "spark.read.csv 调用时已全部读入内存",
                    "程序启动时就自动读取",
                    "只在 Driver 端由单个进程读取"
                ],
                "correct_index": 0,
                "explanation": "read 是惰性的，只记账；show 作为 Action 触发时，Driver 把任务分发给各 Executor，由 Executor 读取各自分片并解析。"
            },
            {
                "type": "single_choice",
                "prompt": "要把一个 Python 列表 [('Alice',34),('Bob',28)] 变成分布式 DataFrame，应使用？",
                "options": [
                    "spark.createDataFrame(rows, ['name','age'])",
                    "pd.DataFrame(rows)",
                    "sc.parallelize(rows)（仅得到 RDD，不是 DataFrame）",
                    "spark.read.csv('rows')"
                ],
                "correct_index": 0,
                "explanation": "createDataFrame 把内存集合 + 列名/StructType 变成 DataFrame；pd.DataFrame 是单机对象，parallelize 得到的是 RDD。"
            },
            {
                "type": "single_choice",
                "prompt": "关于 CSV 读取后的数据类型，下列说法错误的是？",
                "options": [
                    "即使不加 inferSchema，Spark 也会自动把所有列准确识别为正确的类型",
                    "不加 inferSchema 时，所有列默认被当成 StringType",
                    "加 inferSchema 会抽样推断类型，但仍可能猜错",
                    "推荐用 schema=StructType 显式声明类型更可靠"
                ],
                "correct_index": 0,
                "explanation": "不加 inferSchema 时 Spark 不会「准确识别」，而是把所有列默认当成 StringType；正确做法是显式声明或开启 inferSchema。"
            }
        ]
    },
    {
        "lesson_slug": "l2-schema-types",
        "questions": [
            {
                "type": "single_choice",
                "prompt": "Schema（StructType）的主要作用是什么？",
                "options": [
                    "描述每一列的名称、数据类型以及是否可空",
                    "描述数据存放在哪个文件路径",
                    "描述集群的资源配置",
                    "描述 Spark 的执行计划"
                ],
                "correct_index": 0,
                "explanation": "Schema 是「表的说明书」：列名 + 数据类型 + 是否可空（nullable），它让 Spark 知道能对该列做什么运算、能否优化。"
            },
            {
                "type": "single_choice",
                "prompt": "生产环境为何更推荐显式 StructType 声明 Schema，而非 inferSchema？",
                "options": [
                    "避免抽样推断出错、类型不符当场报错（fail-fast），且不抽样更快",
                    "因为 inferSchema 在 Spark 中不被支持",
                    "因为显式声明能减少内存占用",
                    "因为 inferSchema 一定会把数字猜成字符串"
                ],
                "correct_index": 0,
                "explanation": "inferSchema 靠抽样猜测，可能因样本偏差猜错且更慢；显式 StructType 不抽样、不猜，类型不符直接报错，问题暴露得更早。"
            },
            {
                "type": "single_choice",
                "prompt": "显式声明 Schema 后读取数据，遇到「字符串无法转成 IntegerType」的行会怎样？",
                "options": [
                    "直接报错（fail-fast），而不是悄悄存成 null 或错误类型",
                    "自动把该值转成 null",
                    "自动把该值转成字符串",
                    "跳过这一行继续读"
                ],
                "correct_index": 0,
                "explanation": "显式 schema 的 fail-fast 特性能在解析阶段就拦下脏数据，避免「脏数据悄悄污染后续计算」。"
            },
            {
                "type": "single_choice",
                "prompt": "金额字段需要避免浮点误差、保持精确，应该使用哪种类型？",
                "options": [
                    "DecimalType",
                    "DoubleType",
                    "IntegerType",
                    "StringType"
                ],
                "correct_index": 0,
                "explanation": "金钱等需要精确十进制计算的场景应用 DecimalType，避免 DoubleType 的二进制浮点误差；大整数用 LongType。"
            },
            {
                "type": "single_choice",
                "prompt": "关于字段的 nullable，下列说法错误的是？",
                "options": [
                    "字段默认 nullable=False，因此 DataFrame 中不可能出现空值",
                    "字段默认 nullable=True",
                    "nullable 会影响 join 与聚合时 null 的处理",
                    "可对关键键显式设 nullable=False"
                ],
                "correct_index": 0,
                "explanation": "Spark 字段 nullable 默认是 True（可空），不是 False；忽略这一点可能导致 join / 聚合时意外出现 null。"
            }
        ]
    },
    {
        "lesson_slug": "l2-inspect",
        "questions": [
            {
                "type": "single_choice",
                "prompt": "df.show(20) 的作用是？",
                "options": [
                    "以表格形式打印前 20 行（默认数量）并触发执行",
                    "打印整张表的所有行",
                    "打印列名与类型的 Schema 结构",
                    "返回一个新的 DataFrame"
                ],
                "correct_index": 0,
                "explanation": "show(n) 以表格打印前 n 行（默认 20），本身是 Action 会触发执行；printSchema 才看结构。"
            },
            {
                "type": "single_choice",
                "prompt": "show() 默认只展示 20 行，这样设计是为了？",
                "options": [
                    "防止刷屏，也避免把可能极巨大的表全量拉回 Driver",
                    "因为 DataFrame 最多只有 20 行",
                    "因为 Spark 性能限制最多只能读 20 行",
                    "因为 20 行之后数据会丢失"
                ],
                "correct_index": 0,
                "explanation": "刻意设计：防止一不小心把上亿行全打印出来刷屏甚至撑爆 Driver；要看更多先 count 评估量级。"
            },
            {
                "type": "single_choice",
                "prompt": "用 df.age 这种「属性式」引用列的局限是？",
                "options": [
                    "当列名含空格或与 DataFrame 已有方法名冲突时无法使用",
                    "会立即触发数据计算",
                    "只能用于数值类型的列",
                    "会修改原 DataFrame 的结构"
                ],
                "correct_index": 0,
                "explanation": "属性式写法对含空格的列名（如 df.order amount）或重名方法无效，此时要用 df['col'] 或 col('col')。"
            },
            {
                "type": "single_choice",
                "prompt": "想确认某列到底是 string 还是 bigint，应该？",
                "options": [
                    "用 df.printSchema() 或 df.dtypes 查看类型",
                    "用 df.show() 看数值长得像不像数字",
                    "用 df.count() 统计行数",
                    "用 df.collect() 把所有数据拉回来猜"
                ],
                "correct_index": 0,
                "explanation": "printSchema / dtypes 直接给出每列类型，是排查「为什么不能做数值运算」的第一动作。"
            },
            {
                "type": "single_choice",
                "prompt": "以下关于检视操作的错误说法是？",
                "options": [
                    "可以用 Python 的 len(df) 直接获取 DataFrame 的行数",
                    "show() 是 Action，会触发执行",
                    "列名含空格时应使用 df['order amount'] 或 col('order amount')",
                    "printSchema() 用于查看字段结构"
                ],
                "correct_index": 0,
                "explanation": "DataFrame 不是本地集合，没有 len(df)；看行数用 df.count()，看前几行用 show / take。"
            }
        ]
    },
    {
        "lesson_slug": "l2-select-filter",
        "questions": [
            {
                "type": "single_choice",
                "prompt": "select 与 filter 分别用于？",
                "options": [
                    "select 用来挑列（投影），filter 用来挑行（过滤）",
                    "select 用来挑行，filter 用来挑列",
                    "两者完全一样都是挑行",
                    "两者都会修改原 DataFrame"
                ],
                "correct_index": 0,
                "explanation": "select = 投影（选列），filter / where = 过滤（选行），二者功能等价；两者都返回新 DataFrame，不修改原表。"
            },
            {
                "type": "single_choice",
                "prompt": "为什么 filter 的多条件必须用 & / | 而非 Python 的 and / or？",
                "options": [
                    "因为条件必须是 Column 表达式，and/or 会先把 Column 当布尔求值而报错",
                    "因为 and/or 运算速度更慢",
                    "因为 filter 不支持多条件组合",
                    "因为 & / | 是 Spark 的语法糖，and 不支持"
                ],
                "correct_index": 0,
                "explanation": "Python 的 and/or 会先把两个 Column 当布尔判断，抛 ValueError；必须用位运算 & | ~ 且每个条件单独加括号。"
            },
            {
                "type": "single_choice",
                "prompt": "对于 df.filter((df.age>18) & (df.city=='BJ'))，下列说法正确的是？",
                "options": [
                    "它是 Transformation，只记账不立即执行；Catalyst 还可能把过滤下推到读取阶段",
                    "它是 Action，会立即触发计算",
                    "其中的 & 可以替换为 Python 的 and",
                    "它会在 Driver 端一次性过滤所有数据"
                ],
                "correct_index": 0,
                "explanation": "filter 是 Transformation，不立即执行；而且 Catalyst 常把 filter 下推（谓词下推）到读取阶段提前过滤，减少后续数据量。"
            },
            {
                "type": "single_choice",
                "prompt": "想保留「年龄 18–60 且城市为北京或上海」的行，应写成？",
                "options": [
                    "df.filter((df.age.between(18,60)) & (df.city.isin('BJ','SH')))",
                    "df.filter(df.age.between(18,60) and df.city.isin('BJ','SH'))",
                    "df.filter(df.age>=18 & df.age<=60 & df.city=='SH')",
                    "df.filter(df.age.between(18,60)).filter(df.city=='BJ' or df.city=='SH')"
                ],
                "correct_index": 0,
                "explanation": "多条件必须用 Column 运算符：区间用 between，集合用 isin，组合用 & 且每个条件加括号；Python 的 and/or 会报错。"
            },
            {
                "type": "single_choice",
                "prompt":
                    "以下关于 filter 的错误说法是？",
                "options": [
                    "用 df.city is 'BJ' 可以正确判断相等",
                    "filter 返回新 DataFrame，原表不变",
                    "多条件要用 (c1) & (c2) 且每个条件加括号",
                    "filter 与 where 功能等价"
                ],
                "correct_index": 0,
                "explanation": "is 比较对象身份而非值，永远得不到预期结果；判断相等用 ==，判断空值用 isNull()/isNotNull()。"
            }
        ]
    },
    {
        "lesson_slug": "l2-withcolumn",
        "questions": [
            {
                "type": "single_choice",
                "prompt": "withColumn(name, expr) 的作用是？",
                "options": [
                    "新增（或同名则覆盖）一列，返回一个新的 DataFrame",
                    "直接修改传入 DataFrame 的列（原地修改）",
                    "删除指定的列",
                    "删除符合条件的行"
                ],
                "correct_index": 0,
                "explanation": "withColumn 第一个参数若与已有列同名则覆盖，否则新增；返回新 DataFrame，原表不变。"
            },
            {
                "type": "single_choice",
                "prompt": "对 Column 做运算时，必须用 F.abs / F.round 等 Spark 函数，而不能用 Python 内置 abs / round，是因为？",
                "options": [
                    "Column 不是具体数值，只有 Spark 函数才能描述「怎么算」并保持分布式执行",
                    "因为 Python 内置函数运行更慢",
                    "因为 Spark 不支持 Python 函数",
                    "因为 Python 内置函数只能用字符串列"
                ],
                "correct_index": 0,
                "explanation": "Column 是「延迟计算的占位」，不是具体数值；裸用 Python 函数无法表达「逐行怎么算」，且会破坏分布式执行。"
            },
            {
                "type": "single_choice",
                "prompt": "df.withColumn('flag', F.lit(1)) 中 F.lit(1) 的作用是？",
                "options": [
                    "放一个固定常量值作为新列的每个单元格",
                    "从已有的某一列复制数据",
                    "触发整条链立即执行",
                    "为 DataFrame 创建行号索引"
                ],
                "correct_index": 0,
                "explanation": "F.lit(常量) 生成一个「每一行都相同」的常量列；它不会触发执行。"
            },
            {
                "type": "single_choice",
                "prompt": "想新增一列「是否成年」：age>=18 为 'adult'，否则 'minor'，应？",
                "options": [
                    "df.withColumn('tag', F.when(df.age>=18, 'adult').otherwise('minor'))",
                    "df.withColumn('tag', if df.age>=18 then 'adult' else 'minor')（Python if/else）",
                    "df.filter(df.age>=18).withColumn('tag','adult')",
                    "df.select('adult' if df.age>=int(18) else 'minor')"
                ],
                "correct_index": 0,
                "explanation": "逐行分支必须用 F.when(...).otherwise(...)（对应 SQL 的 CASE WHEN）；Python 的 if/else 在 Driver 端一次性判定，无法逐行分支。"
            },
            {
                "type": "single_choice",
                "prompt": "以下关于 withColumn 的错误说法是？",
                "options": [
                    "withColumn 会修改传入的 DataFrame 原对象",
                    "同名会覆盖该列，异名则新增",
                    "返回的是新 DataFrame，原表不变",
                    "when 忘记 otherwise 会导致不满足条件的行该列为 null"
                ],
                "correct_index": 0,
                "explanation": "DataFrame 不可变，withColumn 返回新对象；原 DataFrame 不会被改动，必须用变量接住返回值或链式调用。"
            }
        ]
    },
    {
        "lesson_slug": "l2-sort-dedup",
        "questions": [
            {
                "type": "single_choice",
                "prompt": "distinct() 与 dropDuplicates(['name']) 的区别是？",
                "options": [
                    "distinct 按「整行完全相同」去重；dropDuplicates 按指定的列组合去重",
                    "两者完全相同，都是按整行去重",
                    "dropDuplicates 按整行去重，distinct 按指定列",
                    "两者都只能保留最后一个出现的行"
                ],
                "correct_index": 0,
                "explanation": "distinct 看整行是否完全相同；dropDuplicates(['col']) 只按指定列判断重复，更可控，是日常更常用的写法。"
            },
            {
                "type": "single_choice",
                "prompt": "为什么 orderBy 通常需要触发一次 Shuffle？",
                "options": [
                    "需要把相同排序键的数据汇聚到同一分区，才能完成全局有序",
                    "因为要执行打印操作",
                    "因为要统计行数",
                    "因为要重新读取数据"
                ],
                "correct_index": 0,
                "explanation": "全局有序要求相同排序键的数据在同一处分区处理，因此需要一次 Shuffle（Level 5 会展开）。"
            },
            {
                "type": "single_choice",
                "prompt": "df.orderBy(F.desc('amount')).limit(10) 表达的语义是？",
                "options": [
                    "先按金额降序排序，再取排序后的前 10 行（TopN）",
                    "先取前 10 行，再在这 10 行内排序",
                    "随机取 10 行",
                    "只取金额最大的那一行的 10 个字段"
                ],
                "correct_index": 0,
                "explanation": "limit 一般配合 orderBy 实现 TopN：先全局排序，再取前 N；并不是先取再排。"
            },
            {
                "type": "single_choice",
                "prompt": "想按城市去重，只保留每个城市首次出现的那一行，应？",
                "options": [
                    "df.dropDuplicates(['city'])",
                    "df.distinct()",
                    "df.drop('city')",
                    "df.orderBy('city').limit(1)"
                ],
                "correct_index": 0,
                "explanation": "dropDuplicates(['city']) 按 city 判断重复，保留首次出现的行；distinct 要整行相同才算重复。"
            },
            {
                "type": "single_choice",
                "prompt": "以下关于排序的错误说法是？",
                "options": [
                    "orderBy('age desc') 可以在字符串参数里直接写 'desc' 指定降序",
                    "降序要用 F.desc('age') 或 df.age.desc()",
                    "orderBy 与 sort 完全等价",
                    "多列排序依次传入多个排序表达式"
                ],
                "correct_index": 0,
                "explanation": "orderBy 的字符串参数只当列名，不会解析 'desc' 关键字；降序要用 F.desc() 或 .desc()。"
            }
        ]
    },
    {
        "lesson_slug": "l2-groupby-agg",
        "questions": [
            {
                "type": "single_choice",
                "prompt": "df.groupBy('city').agg(F.sum('amount')) 表达的是？",
                "options": [
                    "按 city 分组，并对每个组的 amount 求和",
                    "对所有行直接求 amount 总和",
                    "按行号分组",
                    "对每个 city 求平均"
                ],
                "correct_index": 0,
                "explanation": "groupBy 指定分组键，agg 指定聚合方式；sum 对每个组内的 amount 求和，而非对全表。"
            },
            {
                "type": "single_choice",
                "prompt": "groupBy 操作通常会触发 Shuffle，原因是？",
                "options": [
                    "需要把相同分组键的行汇聚到同一节点，才能在该组上聚合",
                    "因为要把结果打印出来",
                    "因为要按列排序",
                    "因为要重新读取数据"
                ],
                "correct_index": 0,
                "explanation": "分组聚合需要把相同 key 的行汇聚到同一分区，这就是一次 Shuffle——Spark 最常见的 Shuffle 来源之一。"
            },
            {
                "type": "single_choice",
                "prompt": "groupBy 之后，非分组列能否直接在 select 中使用？",
                "options": [
                    "不能，非分组列必须被聚合（如 F.first）或加入 groupBy，否则报错",
                    "能直接使用，Spark 会自动选择其中一个值",
                    "只能 select 分组键，其他列都不允许出现",
                    "只有数值列可以直接使用"
                ],
                "correct_index": 0,
                "explanation": "一个组里非分组列可能有多个值，Spark 不知道取哪个；这和 SQL 的 GROUP BY 约束完全一致。"
            },
            {
                "type": "single_choice",
                "prompt": "想统计每个城市的订单数与总销售额，应？",
                "options": [
                    "df.groupBy('city').agg(F.count('*').alias('cnt'), F.sum('amount').alias('total'))",
                    "df.groupBy('city').sum('amount')（只能得到一个聚合）",
                    "df.groupBy('city').count() 后再单独 sum",
                    "df.select('city', F.sum('amount'))"
                ],
                "correct_index": 0,
                "explanation": "agg 可一次对多列做不同聚合并用 alias 起名；count('*') 统计行数，sum 统计销售额。"
            },
            {
                "type": "single_choice",
                "prompt": "以下关于聚合的错误说法是？",
                "options": [
                    "count('*') 和 count('col') 的结果永远相同",
                    "聚合结果建议用 alias 起名，便于下游引用",
                    "多分组键等价于 SQL 的 GROUP BY a, b",
                    "count('*') 统计行数（含 null 行），count('col') 统计该列非 null 数"
                ],
                "correct_index": 0,
                "explanation": "count('*') 统计总行数（含 null 行），count('col') 只统计该列非 null 数，二者通常不同。"
            }
        ]
    },
    {
        "lesson_slug": "l2-write-data",
        "questions": [
            {
                "type": "single_choice",
                "prompt": "df.write 属于？",
                "options": [
                    "一个 Action，会触发前面整条 Transformation 链真正执行",
                    "一个 Transformation，只把写配置登记到计划",
                    "一个只读操作，不影响执行",
                    "一个聚合操作"
                ],
                "correct_index": 0,
                "explanation": "write 和 show / count 一样是 Action，会触发前面所有 Transformation 真正执行，常作为 Job 的终点。"
            },
            {
                "type": "single_choice",
                "prompt": "write 的默认写入模式是 errorIfExists（mode 默认），这意味着？",
                "options": [
                    "目标路径已存在时直接抛异常，防止误覆盖",
                    "默认会覆盖已有输出",
                    "默认会追加写入",
                    "默认会忽略写入（什么都不做）"
                ],
                "correct_index": 0,
                "explanation": "默认 mode 是 errorIfExists，路径已存在就抛 AnalysisException——这是新手最常见的写入报错来源；需显式 overwrite/append。"
            },
            {
                "type": "single_choice",
                "prompt": "df.write.partitionBy('dt','city').parquet(path) 会产生？",
                "options": [
                    "按列值建立嵌套目录（如 dt=.../city=...），支撑下游分区裁剪",
                    "一个单一的大文件",
                    "随机命名的多个文件",
                    "只在内存中生效，不落盘"
                ],
                "correct_index": 0,
                "explanation": "partitionBy 按列值生成嵌套目录，下游查询可只扫描需要的目录（分区裁剪），大幅提升性能。"
            },
            {
                "type": "single_choice",
                "prompt": "想减少小文件、并让下游按日期查询更快，写出时应？",
                "options": [
                    "用 partitionBy 按有意义的低/中基数列分区，并使用 Parquet",
                    "把所有数据写进单个 CSV 文件",
                    "使用 mode('append') 不断追加",
                    "不使用任何分区"
                ],
                "correct_index": 0,
                "explanation": "Parquet 列式压缩 + 按有意义的维度分区，既减少小文件又利于分区裁剪；避免用高基数/唯一 ID 列分区。"
            },
            {
                "type": "single_choice",
                "prompt": "以下关于写出的错误说法是？",
                "options": [
                    "write 是 Transformation，写完不会触发执行",
                    "Parquet 是推荐的写出格式：列式、压缩、自带 Schema",
                    "写 CSV 通常需要 option('header', True) 才能保留表头",
                    "partitionBy 选高基数或唯一 ID 列会产生海量小目录"
                ],
                "correct_index": 0,
                "explanation": "write 是 Action，会真正执行；卡住往往是因为 Shuffle / 数据量大，而不是「没执行」。"
            }
        ]
    },
    {
        "lesson_slug": "l2-comprehensive",
        "questions": [
            {
                "type": "single_choice",
                "prompt": "在「读 CSV → filter → withColumn → groupBy → orderBy → write」链路中，哪些是 Transformation？",
                "options": [
                    "filter / withColumn / groupBy / orderBy 都是 Transformation，只有 write 是 Action",
                    "这六个步骤全部是 Action",
                    "只有 read 是 Action，其余都不是",
                    "只有 groupBy 是 Transformation"
                ],
                "correct_index": 0,
                "explanation": "read / filter / withColumn / groupBy / orderBy 都是惰性 Transformation，只有 write（或 show/count）这类 Action 才触发执行。"
            },
            {
                "type": "single_choice",
                "prompt": "在正式 write 之前，先用 show(20) 验证聚合结果的好处是？",
                "options": [
                    "避免把计算错误的聚合结果直接落盘",
                    "能显著提升写出的速度",
                    "能减少需要写出的数据量",
                    "能避免触发 Shuffle"
                ],
                "correct_index": 0,
                "explanation": "先 show 验证聚合与类型正确，再 write，可避免把错误数据直接写进文件。"
            },
            {
                "type": "single_choice",
                "prompt": "groupBy('region').sum('amount') 得到的聚合列，默认列名是？",
                "options": [
                    "类似 'sum(amount)'，通常需要用 alias 改名",
                    "自动叫 'total'",
                    "与原列名 'amount' 相同",
                    "自动叫 'region'"
                ],
                "correct_index": 0,
                "explanation": "默认聚合列名形如 'sum(amount)'，难以下游引用，建议用 agg(F.sum('amount').alias('total')) 改名。"
            },
            {
                "type": "single_choice",
                "prompt": "在 ETL 中过滤「amount 非正或为空」的行，条件应写成？",
                "options": [
                    "(df.amount > 0) & df.amount.isNotNull()",
                    "df.amount > 0 and df.amount.isNotNull()",
                    "df.amount > 0 or df.amount == None",
                    "df.filter(amount > 0)"
                ],
                "correct_index": 0,
                "explanation": "多条件用 & 且每个条件单独加括号；判断空值用 isNotNull()，不能用 Python 的 None 直接比较。"
            },
            {
                "type": "single_choice",
                "prompt": "以下关于这个迷你 ETL 链路的错误说法是？",
                "options": [
                    "整条链路只有最后的 Action 才触发执行，所以 read 也会立即执行",
                    "filter 多条件必须用 & 且每个条件单独加括号",
                    "groupBy / orderBy 通常各触发一次 Shuffle",
                    "write 才是真正触发整条链执行的 Action"
                ],
                "correct_index": 0,
                "explanation": "惰性指「只有 Action 才触发」，并不意味着 read 是 Action——read 是 Transformation，只是记账，只有 write/show/count 才是触发点。"
            }
        ]
    }
]

def upsert():
    # 1) 合并进 quiz_seed.json（按 lesson_slug 幂等）
    with open(SEED, encoding="utf-8") as f:
        data = json.load(f)
    existing_slugs = {e.get("lesson_slug") for e in data.get("quizzes", [])}
    added = 0
    for entry in NEW_QUIZZES:
        if entry["lesson_slug"] in existing_slugs:
            print("已存在，跳过 JSON：", entry["lesson_slug"])
            continue
        data["quizzes"].append(entry)
        existing_slugs.add(entry["lesson_slug"])
        added += 1
    if added:
        with open(SEED, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"quiz_seed.json 新增 {added} 个 lesson 的题库")
    else:
        print("quiz_seed.json 已包含所有 Level 2 题库，跳过 JSON 写入")

    # 2) upsert 进 DB（按 lesson_id 幂等：已有题目的课跳过）
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    lessons = {r[1]: r[0] for r in cur.execute("SELECT id, slug FROM lessons")}
    inserted = 0
    for entry in NEW_QUIZZES:
        lesson_id = lessons.get(entry["lesson_slug"])
        if lesson_id is None:
            print("DB 中无此 lesson，跳过：", entry["lesson_slug"])
            continue
        if cur.execute("SELECT 1 FROM quizzes WHERE lesson_id=?", (lesson_id,)).fetchone():
            print("DB 已有该课题目，跳过：", entry["lesson_slug"])
            continue
        for i, q in enumerate(entry["questions"]):
            cur.execute(
                """INSERT INTO quizzes (lesson_id, type, prompt, options, correct_index, explanation, order_index)
                   VALUES (?,?,?,?,?,?,?)""",
                (lesson_id, q["type"], q["prompt"],
                 json.dumps(q["options"], ensure_ascii=False),
                 q["correct_index"], q["explanation"], i))
            inserted += 1
    conn.commit()
    conn.close()
    print(f"DB 新增题目数：{inserted}")

if __name__ == "__main__":
    upsert()
