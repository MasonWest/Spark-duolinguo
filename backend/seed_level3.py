# -*- coding: utf-8 -*-
"""一次性脚本：把 Level 3（Spark SQL，9 课）合并进 course_seed.json 与 quiz_seed.json，
并幂等地 upsert 进 spark_quest.db 的 course_levels / lessons / quizzes 表。
不修改 Level 0/1/2 与已有的 lesson_mastery 进度数据。

运行：cd backend && python seed_level3.py
"""
import sqlite3, json, os

BASE = os.path.dirname(os.path.abspath(__file__))
SEED = os.path.join(BASE, "app", "course_seed.json")
QUIZ = os.path.join(BASE, "app", "quiz_seed.json")
DB = os.path.join(BASE, "spark_quest.db")

LEVEL3 = {
    "title": "Level 3：Spark SQL",
    "description": "在 Level 2 的 DataFrame 之上，用 SQL 直接查同一批结构化数据：临时视图、SELECT/WHERE/GROUP BY/JOIN/函数，并与 DataFrame API 共用 Catalyst。为 Level 4 执行计划与 Level 6 Join 铺垫。",
    "order_index": 3,
    "lessons": [
        {
            "title": "Spark SQL 是什么",
            "slug": "l3-what-is-spark-sql",
            "description": "理解 Spark SQL 的定位：与 DataFrame API 共享 Catalyst 的两种方言。",
            "objective": "学完本课，你应该能够：用自己的话解释 Spark SQL 是什么、为什么有了 DataFrame 还要 SQL；说清「SQL 与 API 最终编译成同一套执行计划、性能一致」；并理解 spark.sql() 返回的是惰性 DataFrame，查的「表」本质仍是 DataFrame。",
            "estimated_minutes": 12,
            "order_index": 0,
            "prerequisites": "",
            "content": {
                "explanation": "【先用人话理解】\n\n你已经会用 DataFrame API（select / filter / groupBy）搭管道。但很多数据分析师不写 Python，他们只写 SQL：「SELECT city, sum(amount) FROM sales GROUP BY city」。Spark 的厉害之处在于：它让你用 SQL 也能查同一批数据，而且底层和你的 Python 代码走的是同一套优化器。一句话——同一个引擎，两种点单语言。\n\n【一个直观的心智模型】\n\n把 Spark 想象成一家大工厂，有两个点单窗口：左边窗口你说「中文」（SQL 字符串），右边窗口你说「英文」（DataFrame API）。两个窗口长得不一样，但后厨只有一套——Catalyst 优化器。无论你从哪个窗口下单，厨房都先把订单重新规划一遍（优化），再交给工人（Executor）干。所以「用 SQL」还是「用 API」，对你这种「食材」（DataFrame）来说没区别，区别只是你用哪种语言下单。\n\n⚠️ 比喻的边界（很重要）：\n① SQL 不是另起炉灶的新引擎：它和 DataFrame API 最终都编译成同一套逻辑/物理执行计划（底层还是 RDD 的 Task），性能上没有「谁更快」的说法，差异只在写法。\n② 你用 SQL 查的「表」本质仍是 DataFrame（带 Schema 的货），不是数据库里那种「物理表」——除非你接了 Hive Metastore（本路线不纳入）。没注册成视图的 DataFrame，SQL 根本不认识。\n③ SQL 是黑盒字符串给优化器看：它不像 API 那样能逐步 debug 中间每一步的 DataFrame，排错时你得靠 EXPLAIN（Level 4）和 Spark UI。\n\n【正式的技术定义】\n\nSpark SQL 是 Spark 处理结构化数据（行 + 列 + Schema）的统一模块，提供 SQL 接口与 DataFrame/Dataset API 两种编程抽象，二者共享 Catalyst 优化器与 Tungsten 执行引擎。SQL 通过 SparkSession.sql() 执行，返回的是 DataFrame（惰性）。\n\n【写下代码后，Spark 内部发生了什么】\n\nspark.sql(\"...\") 先把 SQL 文本解析成逻辑计划（Analyzer 补上元数据），交给 Catalyst 做优化（和 DataFrame API 走的是同一个优化器），再切 Task 执行。返回的 DataFrame 和手写 API 返回的，在 Catalyst 眼里是等价的——这是本课最重要的认知。",
                "examples": [
                    {
                        "title": "用 SQL 查 DataFrame（先注册视图）",
                        "code": "df.createOrReplaceTempView(\"sales\")\nspark.sql(\"SELECT city, sum(amount) FROM sales GROUP BY city\").show()",
                        "note": "必须先把 DataFrame 注册成临时视图，否则 SQL 不认识 sales。"
                    },
                    {
                        "title": "同一件事的两种写法对照",
                        "code": "# API 写法\ndf.groupBy(\"city\").sum(\"amount\").show()\n\n# SQL 写法（等价）\nspark.sql(\"SELECT city, sum(amount) FROM sales GROUP BY city\").show()",
                        "note": "两种写法最终编译成相同执行计划，性能一致。"
                    },
                    {
                        "title": "spark.sql 返回的是 DataFrame（惰性）",
                        "code": "result = spark.sql(\"SELECT * FROM sales WHERE amount > 100\")\nprint(type(result))   # DataFrame\nresult.show()         # 这一步才真正执行",
                        "note": "sql() 返回 DataFrame，可以接着 .filter() / .withColumn() 混用，Action 才执行。"
                    }
                ],
                "key_points": [
                    "Spark SQL 提供 SQL 接口；与 DataFrame API 共享 Catalyst 优化器，性能一致",
                    "SQL 不是新引擎，二者最终都编译成同一套执行计划（底层仍是 RDD Task）",
                    "你用 SQL 查的「表」本质是 DataFrame，必须先注册成视图",
                    "spark.sql() 返回 DataFrame（惰性），可和 API 链式混用",
                    "黑盒 SQL 排错要靠 EXPLAIN / Spark UI（Level 4 展开）"
                ],
                "common_mistakes": [
                    {
                        "mistake": "没注册视图就 spark.sql(\"SELECT .. FROM my_df\")。",
                        "why": "SQL 只认「注册过的名字」，DataFrame 变量名不是表名。",
                        "fix": "先 df.createOrReplaceTempView(\"my_df\")。"
                    },
                    {
                        "mistake": "以为「SQL 比 API 慢/快」。",
                        "why": "最终执行计划相同，差异只在写法。",
                        "fix": "选你顺手的写法，性能差异来自写法本身而非接口。"
                    },
                    {
                        "mistake": "把 spark.sql 的结果当「已执行的数据」。",
                        "why": "返回 DataFrame，惰性。",
                        "fix": "要结果用 show / collect，别以为赋完值数据就到位了。"
                    }
                ],
                "review": "在 Level 2 我们用 DataFrame API（select / filter / withColumn / groupBy / write）搭出完整 ETL 管道，已经能用 Spark 完成一次真实的数据处理闭环。\n\n可你可能会问：既然 API 啥都能干，为什么 Spark 还要大张旗鼓地支持 SQL？这一课就来正面回答——Spark SQL 到底多了什么，又和你的 API 代码是什么关系。",
                "problem": "为什么 Spark 既能写代码又能写 SQL，而且查的是同一批数据？SQL 和 API 到底谁更快？想用 SQL 查一个 DataFrame，第一步到底要做什么？",
                "preview": "想用 SQL 查 DataFrame，得先让它「变成 SQL 认识的表」——下集讲临时视图，这是 SQL 能跑起来的前提。"
            }
        },
        {
            "title": "临时视图（Temporary View）",
            "slug": "l3-temp-views",
            "description": "createOrReplaceTempView / global temp view：把 DataFrame 挂成 SQL 能认的「表」。",
            "objective": "学完本课，你应该能够：用 createOrReplaceTempView 把 DataFrame 注册为 session 内临时视图；理解视图不复制数据（零拷贝）、只在 session 有效；并区分它与全局临时视图（global_temp. 前缀）。",
            "estimated_minutes": 12,
            "order_index": 1,
            "prerequisites": "",
            "content": {
                "explanation": "【先用人话理解】\n\nSQL 世界里，「表」是有名字的。但你的数据是 DataFrame（一个变量），SQL 不认变量名。所以你得给它挂个「名字牌」——告诉 Spark：「这张表叫 sales，就是那个 DataFrame」。挂完牌子，你就能写 SELECT * FROM sales。\n\n【一个直观的心智模型】\n\n临时视图就像你在仓库门口挂的一块临时工牌：牌子上写着「这批货叫 orders」。工人（Executor）和前台（Driver）都认这块牌子去取货。关键点：① 工牌不复制货，只是个名字（零拷贝）；② 工牌只在你这次「营业」（SparkSession）期间有效，打烊（session 结束）牌子就摘；③ global temp view 是把牌子挂在大堂公共布告栏，所有 session 都能看。\n\n⚠️ 比喻的边界（很重要）：\n① 注册视图不搬任何数据，只登记「名字 → DataFrame」的映射（惰性、零拷贝）。\n② 视图只在创建它的 SparkSession 生命周期内有效（global 例外）；session 关了，名字失效，再查就报「表不存在」。\n③ 同名视图会覆盖；视图背后仍是 DataFrame，SQL 对它做的操作最终还是 Transformation / Action。\n④ 视图不是数据库的持久表——重启 session 要重新注册。\n\n【正式的技术定义】\n\ncreateOrReplaceTempView(name) 把 DataFrame 注册为当前 session 内的临时视图（同名覆盖）；createOrReplaceGlobalTempView(name) 注册为跨 session 可见的全局临时视图（需通过 global_temp. 前缀访问）。视图不物化数据，仅记录逻辑映射。\n\n【写下代码后，Spark 内部发生了什么】\n\ncreateOrReplaceTempView 只是往 SparkSession 的 catalog（临时视图登记表）里写一条「名字 → 逻辑计划」的记录，不触发任何计算。真正计算发生在你 spark.sql 查询它、并遇到 Action 时。",
                "examples": [
                    {
                        "title": "注册临时视图并查询",
                        "code": "df.createOrReplaceTempView(\"sales\")\nspark.sql(\"SELECT city, count(*) FROM sales GROUP BY city\").show()",
                        "note": "名字在 catalog 里；可重复调用 createOrReplace 覆盖同名。"
                    },
                    {
                        "title": "全局临时视图（跨 session）",
                        "code": "df.createOrReplaceGlobalTempView(\"sales\")\nspark.sql(\"SELECT * FROM global_temp.sales LIMIT 5\").show()",
                        "note": "全局视图必须用 global_temp. 前缀访问；适合在多个 session / 作业间共享。"
                    },
                    {
                        "title": "视图不复制数据",
                        "code": "df.createOrReplaceTempView(\"v\")\n# v 和 df 指向同一份逻辑数据，没有任何拷贝\nspark.sql(\"SELECT * FROM v\").explain()  # 看不到「物化」步骤",
                        "note": "视图是逻辑映射，explain 里不会出现独立的物化节点。"
                    }
                ],
                "key_points": [
                    "createOrReplaceTempView 注册 session 内临时视图（同名覆盖）",
                    "全局临时视图用 createOrReplaceGlobalTempView，访问需 global_temp. 前缀",
                    "视图不物化数据，只是「名字 → DataFrame」的逻辑映射（零拷贝）",
                    "视图仅在当前 session 有效（global 例外），session 结束即失效",
                    "视图背后仍是 DataFrame，SQL 操作最终编译成 Transformation / Action"
                ],
                "common_mistakes": [
                    {
                        "mistake": "session 关了再查视图报「表不存在」。",
                        "why": "临时视图绑定 session 生命周期。",
                        "fix": "在查询前确保 session 未停；或改用 global temp view / 持久表。"
                    },
                    {
                        "mistake": "以为注册视图会复制/落盘数据。",
                        "why": "它只是登记名字。",
                        "fix": "理解零拷贝；需要复用计算结果才用 cache / persist。"
                    },
                    {
                        "mistake": "全局视图没加 global_temp. 前缀。",
                        "why": "全局视图必须显式前缀。",
                        "fix": "查询写 SELECT ... FROM global_temp.name。"
                    }
                ],
                "review": "上一课我们说：用 SQL 查的「表」本质是 DataFrame，但 SQL 只认名字。\n\n那怎么把 DataFrame 变成 SQL 能认的「表」？注册了之后，它会不会复制一份数据、占双倍内存？关掉程序再打开还能查到吗？这一课把「临时视图」一次说清。",
                "problem": "怎么把 DataFrame 变成 SQL 能认的「表」？注册视图会不会复制数据？为什么 session 一关视图就失效？全局临时视图又是什么？",
                "preview": "名字有了，下集就能真正写 SELECT 了——而且你会发现，很多写法和 Level 2 的 select 是「同一道工序的两种菜单」。"
            }
        },
        {
            "title": "SELECT 基础",
            "slug": "l3-select-basics",
            "description": "SELECT 选列、表达式、别名、常量；与 Level 2 select 的对照。",
            "objective": "学完本课，你应该能够：用 SELECT 挑选 / 重命名列、写表达式与常量列；理解它与 Level 2 df.select 是同一道工序的两种写法；并避开「把 Python 变量拼进 SQL 字符串」的坑。",
            "estimated_minutes": 12,
            "order_index": 2,
            "prerequisites": "",
            "content": {
                "explanation": "【先用人话理解】\n\n在 SQL 里，SELECT 就是「我要哪些列、给它们起什么名、要不要加点计算」。比如 SELECT name, age+1 AS age_next FROM t。它和 Level 2 的 df.select(\"name\", (df.age+1).alias(\"age_next\")) 是同一件事，只是一个用 SQL 写、一个用 API 写。\n\n【一个直观的心智模型】\n\n复用 Level 2 的「净水滤网流水线」：SELECT 调整的是流水线的「出水口」——你只关心矿物质和泥沙，就把其他通道关掉，只让这几列液体流出来。SQL 的 SELECT 和 API 的 select，是同一道滤网的两种「操作说明书」（一个用中文写、一个用英文写）。\n\n⚠️ 比喻的边界（很重要）：\n① spark.sql(\"SELECT ...\") 返回的是 DataFrame，惰性——没遇到 Action 不算。\n② SQL 里列名/别名规则：含空格或特殊字符用反引号 `order amount` 包住；别名用 AS（可省略）。\n③ 表达式如 age+1、price*0.9 与 Column 运算符等价，都进 Catalyst 优化——不是「先算好再传进去」。\n④ 别把 Python 变量直接拼进 SQL 字符串：既不安全（注入）也不利计划缓存；要用参数化或 lit / 子查询。\n\n【正式的技术定义】\n\nSELECT 子句指定输出列，可为列名、表达式（col + 运算）、常量（lit）、别名（AS）。spark.sql 解析后返回新 DataFrame；与 df.select(...) 在 Catalyst 中生成等价逻辑计划。\n\n【写下代码后，Spark 内部发生了什么】\n\nsql() 把 SELECT 文本解析成逻辑计划里的 Project 节点，Catalyst 优化后切 Task 执行；返回 DataFrame 可继续链式 .filter() 等，整条链到 Action 才跑。",
                "examples": [
                    {
                        "title": "SELECT 选列 + 表达式 + 别名",
                        "code": "spark.sql(\"\"\"\n  SELECT name, age + 1 AS age_next, 'VIP' AS tag\n  FROM people\n\"\"\").show()",
                        "note": "表达式和常量都行；AS 起别名，字符串常量用单引号。"
                    },
                    {
                        "title": "与 Level 2 API 写法对照",
                        "code": "# SQL\nspark.sql(\"SELECT name, age FROM people\")\n# API（等价）\ndf.select(\"name\", \"age\")",
                        "note": "同一道工序两种菜单；选哪样看你顺手。"
                    },
                    {
                        "title": "反引号包特殊列名",
                        "code": "spark.sql(\"SELECT `order amount`, `user-id` FROM orders\").show()",
                        "note": "列名含空格/连字符必须用反引号；API 用 df[\"order amount\"]。"
                    }
                ],
                "key_points": [
                    "SELECT 指定输出列：列名 / 表达式 / 常量 / 别名(AS)",
                    "spark.sql 返回 DataFrame（惰性），可继续链式",
                    "SQL 与 Level 2 的 select 是同一计划两种写法，性能一致",
                    "特殊列名用反引号 `col` 包住",
                    "别把 Python 变量直接拼进 SQL 字符串（注入/缓存问题）"
                ],
                "common_mistakes": [
                    {
                        "mistake": "把 Python 变量 f-string 拼进 SQL：f\"SELECT * FROM t WHERE id={x}\"。",
                        "why": "注入风险、且每次字符串不同导致计划无法缓存。",
                        "fix": "用参数化 / 子查询，或先在 API 侧 filter。"
                    },
                    {
                        "mistake": "忘了 spark.sql 返回 DataFrame 是惰性的。",
                        "why": "赋完值数据没到位。",
                        "fix": "接 Action（show / collect）才执行。"
                    },
                    {
                        "mistake": "含空格列名没加反引号报错。",
                        "why": "SQL 把空格当分隔。",
                        "fix": "用 `col name`。"
                    }
                ],
                "review": "上一课我们给 DataFrame 挂了「临时视图」这个名字牌，SQL 现在认识它了。\n\n那怎么用 SQL 真正「选列」？SELECT 怎么写表达式、起别名？它和我们 Level 2 学的 select 到底是什么关系？这一课把 SELECT 基础讲透。",
                "problem": "怎么用 SQL 真正「选列」？SELECT 怎么写表达式、起别名？它和我们 Level 2 学的 select 到底是什么关系？为什么不该把 Python 变量直接拼进 SQL？",
                "preview": "选好列之后，下一步自然是「挑行」——WHERE 过滤、「排个序」、「取前几条」，下集讲。"
            }
        },
        {
            "title": "WHERE / ORDER BY / LIMIT",
            "slug": "l3-where-order-limit",
            "description": "SQL 的挑行、排序、截断，与 Level 2 filter/orderBy/limit 对照，含 NULL 三态。",
            "objective": "学完本课，你应该能够：用 WHERE 过滤行、ORDER BY 排序、LIMIT 取前 N；理解它们与 Level 2 的对应；避开 NULL 三态（IS NULL）与「ORDER BY 必 Shuffle」两个关键认知。",
            "estimated_minutes": 12,
            "order_index": 3,
            "prerequisites": "",
            "content": {
                "explanation": "【先用人话理解】\n\nSQL 里挑行用 WHERE，排序用 ORDER BY，取前 N 用 LIMIT。它们一一对应 Level 2 的 filter / orderBy / limit。比如 WHERE age>18 等价于 df.filter(df.age>18)；ORDER BY amount DESC 等价于 df.orderBy(F.desc(\"amount\"))。\n\n【一个直观的心智模型】\n\n复用 Level 2：WHERE 是流水线的「物理隔板」（不合格的行拦下）；ORDER BY 是「全校按身高排队领奖」（全局有序）；LIMIT 是「只放前 N 个进场」。SQL 只是把这三道工序用另一种语言描述了一遍。\n\n⚠️ 比喻的边界（很重要）：\n① SQL 里组合条件用 AND / OR / NOT（不是 Python 的 and/or，因为 SQL 是文本语言，没有 Python 运算符）——但效果和 Level 2 的 & | ~ 一样；别把 Python 逻辑词写进 SQL 字符串。\n② NULL 是「三态」：age = NULL 永远为假，判断空要用 IS NULL / IS NOT NULL；这是新手最常踩的坑。\n③ ORDER BY 全局有序必触发一次 Shuffle（所有人重排），大数据下昂贵——Level 5 展开。\n④ LIMIT 是「取前 N」，不是「均匀抽样」；配合 ORDER BY 才是 TopN。\n\n【正式的技术定义】\n\nWHERE 在分组/聚合前过滤行（行级谓词）；ORDER BY 按列排序（ASC/DESC，多列逗号分隔）；LIMIT 截断结果行数。三者均在 SELECT 之后、Action 之前构成逻辑计划节点，由 Catalyst 优化（WHERE 常下推）。\n\n【写下代码后，Spark 内部发生了什么】\n\nWHERE 被 Catalyst 下推（Predicate Pushdown）到读取端尽早过滤；ORDER BY 触发 Shuffle 做全局排序；LIMIT 可在排序后取前 N 或下推到各分区取局部前 N 再合并。",
                "examples": [
                    {
                        "title": "WHERE 过滤 + AND/OR",
                        "code": "spark.sql(\"\"\"\n  SELECT name, age FROM people\n  WHERE age > 18 AND city = 'BJ'\n\"\"\").show()",
                        "note": "SQL 用 AND/OR/NOT；对应 API 的 & | ~。"
                    },
                    {
                        "title": "NULL 三态：用 IS NULL",
                        "code": "spark.sql(\"SELECT * FROM people WHERE phone IS NULL\").show()\n# 错误：WHERE phone = NULL  -- 永远为假",
                        "note": "判断空必须用 IS NULL / IS NOT NULL；= NULL 是经典坑。"
                    },
                    {
                        "title": "ORDER BY + LIMIT 做 TopN",
                        "code": "spark.sql(\"\"\"\n  SELECT city, sum(amount) AS total\n  FROM sales GROUP BY city\n  ORDER BY total DESC LIMIT 5\n\"\"\").show()",
                        "note": "排序+取前5即 Top5；ORDER BY 触发 Shuffle。"
                    }
                ],
                "key_points": [
                    "WHERE 过滤行（对应 filter）；ORDER BY 排序（对应 orderBy）；LIMIT 取前 N（对应 limit）",
                    "SQL 组合条件用 AND/OR/NOT（不是 Python 的 and/or）",
                    "NULL 三态：判断空用 IS NULL / IS NOT NULL，= NULL 永远为假",
                    "ORDER BY 全局有序必触发 Shuffle（Level 5 展开）",
                    "LIMIT 取前 N 非抽样；配合 ORDER BY 即 TopN"
                ],
                "common_mistakes": [
                    {
                        "mistake": "写 WHERE phone = NULL。",
                        "why": "NULL 不参与 = 比较，结果永远假。",
                        "fix": "用 IS NULL。"
                    },
                    {
                        "mistake": "把 Python 的 and/or 写进 SQL（其实 SQL 里本来就用 AND/OR，但有人误把 DataFrame 的 & 写进 SQL）。",
                        "why": "SQL 文本里只有 AND/OR。",
                        "fix": "SQL 用 AND/OR/NOT；API 用 & | ~。"
                    },
                    {
                        "mistake": "以为 LIMIT 是随机抽样。",
                        "why": "它是「前 N 行」。",
                        "fix": "要抽样用 TABLESAMPLE 或 df.sample()。"
                    }
                ],
                "review": "上一课我们用 SELECT 把「要哪些列」讲清了，而且知道它和 Level 2 的 select 是同一道工序。\n\n那怎么用 SQL 真正「挑行」？ORDER BY 怎么排升降序？为什么 ORDER BY 在大表上很贵？NULL 该怎么判断？这一课一次说清。",
                "problem": "怎么用 SQL 挑行（WHERE）、排序（ORDER BY）、取前几条（LIMIT）？NULL 该怎么判断？为什么 ORDER BY 在大表上很贵、而 LIMIT 不是抽样？",
                "preview": "选列、挑行、排序都会了。可真实分析少不了「分组汇总」——每城市卖多少。而且 SQL 里有个 WHERE 替代不了的新关键字，下集讲 GROUP BY 与 HAVING。"
            }
        },
        {
            "title": "GROUP BY 与 HAVING",
            "slug": "l3-groupby-having",
            "description": "SQL 分组聚合与 HAVING；复用「水果分拣派对」隐喻，对照 Level 2 groupBy。",
            "objective": "学完本课，你应该能够：用 GROUP BY 分组并用聚合函数汇总；理解「非分组列不能直接 SELECT」；并分清 HAVING（分组后过滤）与 WHERE（分组前过滤）的顺序坑。",
            "estimated_minutes": 12,
            "order_index": 4,
            "prerequisites": "",
            "content": {
                "explanation": "【先用人话理解】\n\nGROUP BY 就是「按某个维度把数据分成几堆，在每堆上算一个汇总值」，比如「按城市分组，算每个城市的总销售额」。它对应 Level 2 的 df.groupBy(\"city\").sum(\"amount\")，是数据分析的心脏，也是 SQL 的 GROUP BY。\n\n【一个直观的心智模型】\n\n复用 Level 2 的「水果分拣派对」：每个人抱一箱混杂水果，哨声一响大家按「水果类型」把苹果扔一号桌、橘子扔二号桌（这就是 Shuffle），站定后各桌用秤（sum/avg）算总重量。SQL 的 GROUP BY 喊的就是这道口令，和 API 的 groupBy 是同一场派对。\n\n⚠️ 比喻的边界（很重要）：\n① 聚合后还想过滤（比如「只留总金额>1000 的城市」），必须用 HAVING，不能用 WHERE——WHERE 在分组前过滤、HAVING 在分组后过滤，这是顺序坑。\n② 分组列可直接出现在 SELECT；非分组列不能被 SELECT（除非被聚合），与 Level 2 约束一致。\n③ 同 Level 2：GROUP BY 必触发 Shuffle + Map-side Combine；大表分组是主要成本来源（Level 5）。\n\n【正式的技术定义】\n\nGROUP BY 按一列/多列分组，聚合函数（COUNT/SUM/AVG/MAX/MIN）在每组上计算；HAVING 对分组后的聚合结果再做过滤（WHERE 作用于分组前）。二者生成的逻辑计划节点与 DataFrame API 完全等价。\n\n【写下代码后，Spark 内部发生了什么】\n\nGROUP BY 触发 Shuffle 把同键行汇聚，本地预聚合（Combine）后跨节点合并；HAVING 在聚合结果上过滤，可随聚合一起在节点内完成。",
                "examples": [
                    {
                        "title": "GROUP BY + 聚合",
                        "code": "spark.sql(\"\"\"\n  SELECT city, sum(amount) AS total, count(*) AS cnt\n  FROM sales GROUP BY city\n\"\"\").show()",
                        "note": "分组键 + 聚合函数；count(*) 算行数。"
                    },
                    {
                        "title": "HAVING 过滤聚合结果",
                        "code": "spark.sql(\"\"\"\n  SELECT city, sum(amount) AS total\n  FROM sales GROUP BY city\n  HAVING sum(amount) > 1000\n\"\"\").show()",
                        "note": "HAVING 在分组后过滤；若用 WHERE sum(amount)>1000 会报「聚合不能用于 WHERE」。"
                    },
                    {
                        "title": "多列分组",
                        "code": "spark.sql(\"SELECT city, product, sum(amount) FROM sales GROUP BY city, product\").show()",
                        "note": "GROUP BY 多列 = API 的 groupBy(\"city\",\"product\")。"
                    }
                ],
                "key_points": [
                    "GROUP BY 分组 + 聚合函数（COUNT/SUM/AVG/MAX/MIN）",
                    "分组后过滤用 HAVING，分组前过滤用 WHERE（顺序坑）",
                    "非分组列不能被 SELECT，除非被聚合（同 Level 2 / SQL）",
                    "多列分组 = GROUP BY a, b",
                    "GROUP BY 必触发 Shuffle（Level 5 展开）"
                ],
                "common_mistakes": [
                    {
                        "mistake": "在 WHERE 里用聚合函数：WHERE sum(amount)>1000。",
                        "why": "WHERE 在分组前执行，看不到聚合值。",
                        "fix": "改用 HAVING。"
                    },
                    {
                        "mistake": "SELECT 非分组列（未被聚合）。",
                        "why": "组内该列多值，不知取哪个。",
                        "fix": "放入聚合或 GROUP BY。"
                    },
                    {
                        "mistake": "混淆 GROUP BY 与 ORDER BY 的作用。",
                        "why": "前者分堆汇总，后者排序。",
                        "fix": "想汇总用 GROUP BY，想排序用 ORDER BY（可在其后）。"
                    }
                ],
                "review": "前面我们用 SELECT / WHERE / ORDER BY / LIMIT 完成了「选列、挑行、排序」——都是「描述每行」的操作。\n\n但数据分析的灵魂往往是「汇总」：每个城市卖了多少、每个用户下了几单。这要求我们先按某个维度「分类」，再在每类里算一个值。这就是 GROUP BY + 聚合。这一课，我们把它彻底拿下。",
                "problem": "如何用 SQL 分组汇总（每城市卖多少）？为什么聚合后过滤要用 HAVING 而不是 WHERE？GROUP BY 背后 Spark 又付出什么代价？",
                "preview": "一张表会查了。可真实数据是「多张表」——订单表和用户表要连起来。SQL 怎么把两张表按关键字段拼成一张？下集讲 JOIN（先建立直觉，深入在 Level 6）。"
            }
        },
        {
            "title": "多表关联（JOIN）入门",
            "slug": "l3-joins-intro",
            "description": "INNER JOIN 基础与「连接键」直觉，为 Level 6 铺垫（类型/广播/调优留 L6）。",
            "objective": "学完本课，你应该能够：理解 JOIN 是「按连接键把两表行配对」；写出基本的 INNER JOIN（ON a.key=b.key）；并知道 JOIN 必触发 Shuffle、连接键类型必须一致——深入的各种 JOIN 类型与调优留给 Level 6。",
            "estimated_minutes": 15,
            "order_index": 5,
            "prerequisites": "",
            "content": {
                "explanation": "【先用人话理解】\n\n真实数据很少在一张表里：订单在 orders 表，用户在 users 表，你想「每个用户的订单总额」就得把两表按 user_id 拼起来。JOIN 就是干这个的——按一个「连接键」把两张表的行配对。\n\n【一个直观的心智模型】\n\n想象两张分拣台各抱一摞货（订单摞、用户摞），每摞货上都贴了「user_id」标签。JOIN 就是按 user_id 这个标签，把「同一 user_id 的订单」和「同一 user_id 的用户」并到同一行——像把两个花名册按学号拼成一张总表。本课只讲最基础的 INNER JOIN：两边都有这个键的才留下。\n\n⚠️ 比喻的边界（很重要）：\n① JOIN 必触发 Shuffle：两摞货要按 key 重新分发到同一工人（按 key 重分区），数据在空中飞，代价大。\n② 连接键选错 / 出现重复键，会产生「行数爆炸」（笛卡尔式膨胀）——一个用户有 100 个订单，拼完就多 100 行。这是后续性能与正确性的大坑。\n③ 本课只讲 INNER JOIN 基础语法与「连接键」直觉；LEFT / RIGHT / FULL / CROSS 各种类型、广播 Join、倾斜调优全部留给 Level 6 专门讲，那里才展开。\n\n【正式的技术定义】\n\nJOIN 按连接条件（通常 ON a.key = b.key）把两表的行组合；INNER JOIN 只保留两表都匹配上的行。SQL 通过 spark.sql 执行，返回 DataFrame。连接类型、执行策略（Broadcast / Shuffle）是 Level 6 主题。\n\n【写下代码后，Spark 内部发生了什么】（留白给 Level 6）\n\n本课只需知道：JOIN 通常触发一次 Shuffle（按连接键重分区），把相同 key 的行送到同一节点配对；具体怎么分发、什么时候广播，Level 6 再深挖。",
                "examples": [
                    {
                        "title": "INNER JOIN 基础",
                        "code": "spark.sql(\"\"\"\n  SELECT u.name, o.amount\n  FROM users u\n  JOIN orders o ON u.user_id = o.user_id\n\"\"\").show()",
                        "note": "ON 指定连接键；给表起别名 u/o 让列引用更短。"
                    },
                    {
                        "title": "JOIN 后再聚合",
                        "code": "spark.sql(\"\"\"\n  SELECT u.name, sum(o.amount) AS total\n  FROM users u JOIN orders o ON u.user_id = o.user_id\n  GROUP BY u.name\n\"\"\").show()",
                        "note": "JOIN 之后照常能 GROUP BY；先拼表再汇总很常见。"
                    },
                    {
                        "title": "连接键必须类型一致",
                        "code": "# 若 users.user_id 是字符串、orders.user_id 是整数，JOIN 会匹配不上\nspark.sql(\"SELECT ... FROM users JOIN orders ON users.user_id = orders.user_id\")",
                        "note": "连接键类型不一致会导致「全部不匹配」，先统一类型（cast）。"
                    }
                ],
                "key_points": [
                    "JOIN 按连接键（ON a.key = b.key）把两表行配对",
                    "INNER JOIN 只保留两边都匹配的行（基础类型）",
                    "JOIN 必触发 Shuffle（按 key 重分区），代价大",
                    "连接键类型必须一致，否则匹配不上",
                    "各 JOIN 类型 / 广播 / 倾斜调优留给 Level 6"
                ],
                "common_mistakes": [
                    {
                        "mistake": "忘了 ON 连接条件，写成 JOIN 无 ON。",
                        "why": "变成 CROSS JOIN（笛卡尔积），行数爆炸。",
                        "fix": "一定写 ON a.key=b.key；Level 6 再讲类型。"
                    },
                    {
                        "mistake": "连接键类型不一致导致全不匹配。",
                        "why": "字符串≠整数。",
                        "fix": "先 cast 成一致类型再 JOIN。"
                    },
                    {
                        "mistake": "以为 JOIN 很便宜。",
                        "why": "必 Shuffle，大表 JOIN 是大成本。",
                        "fix": "记住代价；优化手段在 Level 6。"
                    }
                ],
                "review": "上一课我们用 GROUP BY 学会了「单表分组汇总」，SQL 已经能对付一张表的大多数分析。\n\n但真实数据是分散在多张表的——订单、用户、商品各一张。怎么把多张表按关键字段「拼」成一张来分析？JOIN 到底是什么、代价有多大？这一课建立直觉。",
                "problem": "怎么把多张表按关键字段「拼」成一张来分析？JOIN 到底是什么、代价有多大、连接键要注意什么？各种 JOIN 类型又该怎么选？",
                "preview": "JOIN 建立了直觉，但「各种 JOIN 类型怎么选、大表怎么不卡死」是 Level 6 的硬仗。下集我们先把「函数」补齐——SQL 内置函数与 UDF，顺便埋个性能伏笔。"
            }
        },
        {
            "title": "内置函数与 UDF",
            "slug": "l3-functions-and-udf",
            "description": "SQL 内置函数与 UDF 的取舍，埋 Level 7 性能伏笔。",
            "objective": "学完本课，你应该能够：列举常用内置函数（字符串/日期/数学）并知道它们在 F 下；理解 UDF 的用法与「为什么慢」（JVM↔Python 序列化往返、失去 Catalyst 优化）；建立「能不用 UDF 就不用」的原则，为 Level 7 埋线。",
            "estimated_minutes": 15,
            "order_index": 6,
            "prerequisites": "",
            "content": {
                "explanation": "【先用人话理解】\n\nSQL 里算「字符串截取、日期加减、四舍五入」不用自己写循环——Spark 自带一大堆内置函数（upper、substr、datediff、round…），开箱即用。但偶尔你要的逻辑内置没有，就得自己写函数，这叫 UDF（用户自定义函数）。\n\n【一个直观的心智模型】\n\n内置函数像工厂里现成的标准工具——工人（Executor）闭眼会用，而且 Catalyst 还能提前优化（比如把计算下推、代码生成）。UDF 则像你从外面带了个「私人定制工具」：工人不认识它，得先把数据「打包」送到工具那（序列化到 Python/JVM 边界）跑完再送回来，慢，而且 Catalyst 没法优化它。所以能不用 UDF 就不用。\n\n⚠️ 比喻的边界（很重要）：\n① 内置函数走 Catalyst 原生优化（代码生成 / Tungsten），又快又省；优先用它们。\n② UDF 把数据在 JVM↔Python 之间序列化往返，打破流水线、失去 Catalyst 优化——能不用就不用；真要用，优先 pandas UDF（向量化）也比行级 Python UDF 强得多。\n③ 这一课的「UDF 慢」只是埋个伏笔：为什么慢、怎么选、怎么用广播/向量化救场，是 Level 7 性能优化要系统讲的。\n\n【正式的技术定义】\n\nSpark SQL 内置函数位于 pyspark.sql.functions（F），覆盖字符串/日期/数学/聚合/窗口等。UDF 用 F.udf / pandas_udf 注册自定义逻辑；UDF 以行为单位在 Executor 上调 Python，开销高于原生函数。\n\n【写下代码后，Spark 内部发生了什么】\n\n内置函数被 Catalyst 翻译成物理计划的原生算子（Whole-Stage Codegen）；UDF 则在每个匹配行触发一次跨语言调用（序列化/反序列化），成为流水线瓶颈。",
                "examples": [
                    {
                        "title": "常用内置函数",
                        "code": "from pyspark.sql import functions as F\nspark.sql(\"\"\"\n  SELECT upper(name) AS name_up,\n         substr(phone,1,3) AS prefix,\n         round(amount,2) AS amt\n  FROM people\n\"\"\").show()",
                        "note": "内置函数直接写；也可在 API 用 F.upper 等，等价。"
                    },
                    {
                        "title": "UDF 的基本写法",
                        "code": "from pyspark.sql import functions as F\ndef score_category(s):\n    return 'high' if s > 90 else 'low'\nscore_udf = F.udf(score_category)\nspark.sql(\"SELECT name, score FROM stu\").withColumn(\n    \"cat\", score_udf(F.col(\"score\"))).show()",
                        "note": "UDF 把 Python 函数包成列表达式；每行触发一次 Python 调用。"
                    },
                    {
                        "title": "优先内置、避免 UDF",
                        "code": "# 不好：用 UDF 做字符串大写\n# 好：直接用 F.upper / SQL upper()\nspark.sql(\"SELECT upper(name) FROM people\").show()",
                        "note": "内置能做的绝不写 UDF。"
                    }
                ],
                "key_points": [
                    "内置函数覆盖字符串/日期/数学/聚合，走 Catalyst 原生优化（快）",
                    "UDF 自定义逻辑，但 JVM↔Python 序列化往返、失去优化（慢）",
                    "能不用 UDF 就不用；真要用优先 pandas UDF（向量化）",
                    "内置函数与 API 的 F.* 等价（同一套）",
                    "「UDF 为什么慢」是 Level 7 性能优化的伏笔"
                ],
                "common_mistakes": [
                    {
                        "mistake": "用 Python 写个函数就当 UDF 直接用在 SQL。",
                        "why": "SQL 不认普通 Python 函数。",
                        "fix": "用 F.udf / pandas_udf 注册。"
                    },
                    {
                        "mistake": "能用内置偏写 UDF。",
                        "why": "慢且失去优化。",
                        "fix": "先查内置函数表，没有再 UDF。"
                    },
                    {
                        "mistake": "在 UDF 里做重计算且逐行调用。",
                        "why": "行级 Python 调用开销巨大。",
                        "fix": "用 pandas_udf 向量化或改写内置。"
                    }
                ],
                "review": "上一课我们建立了 JOIN 的直觉——按连接键把多表拼起来。\n\n但 SQL 里要做字符串/日期/数学计算，难道要自己写循环？内置函数有哪些？什么时候非得自己写函数（UDF），而 UDF 又为什么「贵」？这一课补齐「函数」。",
                "problem": "SQL 里要做字符串/日期/数学计算，难道要自己写循环？内置函数有哪些？什么时候非得自己写函数（UDF），而 UDF 又为什么「贵」？",
                "preview": "函数和表都会用了。其实除了「把现有 DataFrame 注册成视图」，你还能直接用 SQL 把一份 Parquet/CSV 「当表用」。下集讲 Spark SQL 与表/文件格式（Hive 那条线我们不接）。"
            }
        },
        {
            "title": "Spark SQL 与表 / 文件格式",
            "slug": "l3-tables-and-formats",
            "description": "CREATE TABLE ... USING / LOCATION；明确不接入 Hive Metastore（既定约束）。",
            "objective": "学完本课，你应该能够：用 CREATE TABLE ... USING parquet LOCATION 把文件直接当表查；理解本路线不接入 Hive Metastore（表是 session 内/文件级）；并说清写出（INSERT OVERWRITE/INTO）与 Level 2 write 的对应关系及小文件坑。",
            "estimated_minutes": 12,
            "order_index": 7,
            "prerequisites": "",
            "content": {
                "explanation": "【先用人话理解】\n\n除了把内存里的 DataFrame 注册成视图，你也能「反过来」——直接告诉 Spark：「这份 Parquet/CSV 文件，就是一张表」，然后就能用 SQL 查它，不用先 read 再注册。相当于给仓库里的货直接贴了张标准货架标签。\n\n【一个直观的心智模型】\n\n之前是「先收货（read）再挂牌（createOrReplaceTempView）」；这课是「直接给货架贴标签（CREATE TABLE ... USING parquet / 或 read 后注册）」——殊途同归，都是让 SQL 能按名字找到那批货。区别只是你从「文件」还是从「已读入的 DataFrame」出发。\n\n⚠️ 比喻的边界（很重要）：\n① 本路线明确不接入 Hive Metastore（既有约束）：所以这里的「表」要么是 session 内的临时视图，要么是「文件级」的表（CREATE TABLE 指向路径），不是跨集群永久的 Hive 表。要永久表得接 Hive，本路线不做。\n② 写出的小文件问题：partitionBy 落盘每 Task 一个文件，易产生海量小文件——这是性能坑，接 Level 2 write + Level 7。\n③ SaveMode（overwrite/append/error/ignore）与 Level 2 write 完全一致，SQL 里用 INSERT OVERWRITE / INSERT INTO 对应。\n\n【正式的技术定义】\n\nSpark SQL 可将文件（Parquet/CSV/JSON）注册为表（CREATE TABLE ... USING format LOCATION path，或 DataFrame 注册视图）；读取即按格式解析。Hive 集成（enableHiveSupport）不在本路线范围。写出用 INSERT INTO / INSERT OVERWRITE TABLE。\n\n【写下代码后，Spark 内部发生了什么】\n\nCREATE TABLE ... LOCATION 只是把「路径+格式」记进 catalog，不移动数据；查询时按格式读取，Catalyst 正常优化（谓词下推等）。",
                "examples": [
                    {
                        "title": "直接把 Parquet 当表（CREATE TABLE）",
                        "code": "spark.sql(\"\"\"\n  CREATE TABLE IF NOT EXISTS sales\n  USING parquet\n  LOCATION '/data/sales'\n\"\"\")\nspark.sql(\"SELECT city, sum(amount) FROM sales GROUP BY city\").show()",
                        "note": "不接 Hive 也能用；表指向路径，查询时按需读。"
                    },
                    {
                        "title": "读文件后注册视图（等价路径）",
                        "code": "df = spark.read.parquet(\"/data/sales\")\ndf.createOrReplaceTempView(\"sales\")\nspark.sql(\"SELECT * FROM sales LIMIT 5\").show()",
                        "note": "从 DataFrame 出发的等价做法。"
                    },
                    {
                        "title": "写出：INSERT OVERWRITE",
                        "code": "spark.sql(\"\"\"\n  INSERT OVERWRITE TABLE result\n  SELECT city, sum(amount) FROM sales GROUP BY city\n\"\"\")",
                        "note": "对应 API 的 mode(\"overwrite\").write；错误/追加用 INSERT INTO。"
                    }
                ],
                "key_points": [
                    "可直接把 Parquet/CSV/JSON 注册为表（CREATE TABLE ... USING ... LOCATION）",
                    "本路线不接入 Hive Metastore：表是 session 内 / 文件级，非永久 Hive 表",
                    "读出写出的 SaveMode 与 Level 2 write 一致（INSERT OVERWRITE / INTO）",
                    "小文件问题（partitionBy 每 Task 一文件）是性能坑，接 Level 2 + Level 7",
                    "注册表/视图都只是登记，不移动数据"
                ],
                "common_mistakes": [
                    {
                        "mistake": "以为 CREATE TABLE 会移动/拷贝数据。",
                        "why": "它只登记路径+格式。",
                        "fix": "理解零拷贝，数据仍在原路径。"
                    },
                    {
                        "mistake": "期待「永久表」跨 session 存在（没接 Hive）。",
                        "why": "没 enableHiveSupport。",
                        "fix": "本路线用临时视图或文件级表；不要假设持久。"
                    },
                    {
                        "mistake": "partitionBy 写出产生海量小文件。",
                        "why": "每 Task 一文件。",
                        "fix": "后续合并小文件/调分区数，属 Level 7。"
                    }
                ],
                "review": "上一课我们讲清了内置函数与 UDF——SQL 的计算能力。\n\n除了把已读入的 DataFrame 注册成视图，能不能直接把一份文件「当表」用 SQL 查？Spark SQL 的「表」和数据库的表是一回事吗？写出又怎么写？这一课补齐「表与文件格式」。",
                "problem": "除了把已读入的 DataFrame 注册成视图，能不能直接把一份文件「当表」用 SQL 查？Spark SQL 的「表」和数据库的表是一回事吗？写出又对应 API 的什么？",
                "preview": "所有零件齐了：视图、SELECT/WHERE/GROUP BY/JOIN/函数、文件即表。下集用一次完整分析把它们串起来——读 CSV、注册、多步 SQL、写出。"
            }
        },
        {
            "title": "Spark SQL 综合练习",
            "slug": "l3-comprehensive",
            "description": "用 SQL 走完一次完整分析：读 CSV → 注册 → 多步 SQL → 写出。",
            "objective": "学完本课，你应该能够：独立把 Level 3 所学的「读入 / 注册视图 / WHERE / GROUP BY+HAVING / ORDER BY / 写出」串成一次完整的 SQL 分析任务，并随时说清「spark.sql 返回 DataFrame（惰性）」「哪一步是 Action」「HAVING 与 WHERE 的区别」。",
            "estimated_minutes": 20,
            "order_index": 8,
            "prerequisites": "",
            "content": {
                "explanation": "【先用人话理解】\n\n这一课给你一个「用 SQL 做分析」的迷你任务，把 Level 3 全部零件揉进实战：读 CSV → 注册视图 → 多步 SQL（过滤/聚合/可能 JOIN）→ 写出 Parquet。它逼你把「这条 SQL 在 Catalyst 眼里和等价 DataFrame 代码是同一件事」「哪一步是 Action」想清楚，是这一章的收束。\n\n输入 orders.csv（user_id, city, amount, ts），目标：\n1) 读入并确认 Schema；\n2) 注册为视图 orders；\n3) 过滤 amount>0；\n4) 按 city 聚合总销售额，只留 total>1000（HAVING）；\n5) 按 total 降序，写出 Parquet（按 city 分区）。\n\n【一个直观的心智模型】\n\n把这次分析想成「在仓库里跑一趟拣货流水线」：读 CSV 是「收货上架」，注册视图是「给这批货挂个工牌名字」，WHERE 是「流水线入口的筛子」，GROUP BY+HAVING 是「按城市分拣并只留大单」，ORDER BY 是「按金额重新排队」，最后的写出是「装车发货」——只有装车这一步（Action）货才真的离开仓库，前面全是「计划这张单怎么跑」。\n\n⚠️ 比喻的边界（很重要）：\n\n① 这里的「写出 Parquet」是落盘 Action，和 Level 2 的 df.write 等价；别以为 SQL 的 INSERT OVERWRITE 不算 Action——它照样触发一次完整作业。\n② 自测题里的「HAVING 与 WHERE 区别」是高频考点：WHERE 在分组前过滤单行，HAVING 在分组后过滤聚合结果，二者位置不能互换。\n③ spark.sql 返回的始终是惰性 DataFrame，哪怕你写的是「SELECT ...」，没接 Action（show / 写出）就不会真正算。\n\n【正式的技术定义】\n\n一次完整的 Spark SQL 分析 = read（创建 DataFrame）→ createOrReplaceTempView（注册 session 内视图）→ 一系列 SELECT（WHERE / GROUP BY / HAVING / ORDER BY，均为 Transformation）→ 写出（INSERT OVERWRITE TABLE / write，为 Action）。所有 SELECT 节点在 Catalyst 中被编译为逻辑计划，直到 Action 出现才物化执行。\n\n【写下代码后，Spark 内部发生了什么】\n\n整条 SQL 被 Catalyst 编译成逻辑计划（Project / Filter / Aggregate / Sort / Write），除了最后的 Write（Action）会真正执行，前面都是惰性节点；GROUP BY 与 ORDER BY 各触发一次 Shuffle。由于 SQL 与 DataFrame API 共享 Catalyst，这条 SQL 和等价 API 代码的物理执行计划是一致的。",
                "examples": [
                    {
                        "title": "完整可运行分析",
                        "code": "df = spark.read.option(\"header\",True).option(\"inferSchema\",True).csv(\"orders.csv\")\ndf.createOrReplaceTempView(\"orders\")\n\n# 先看结果\nspark.sql(\"\"\"\n  SELECT city, sum(amount) AS total\n  FROM orders\n  WHERE amount > 0\n  GROUP BY city\n  HAVING sum(amount) > 1000\n  ORDER BY total DESC\n\"\"\").show()\n\n# 验证无误后写出\nspark.sql(\"\"\"\n  INSERT OVERWRITE TABLE result\n  SELECT city, sum(amount) AS total\n  FROM orders WHERE amount > 0\n  GROUP BY city HAVING sum(amount) > 1000\n\"\"\")",
                        "note": "先 show 验证再写出；spark.sql 返回 DataFrame，写出才是 Action。"
                    },
                    {
                        "title": "SQL 与 API 混合也没问题",
                        "code": "result = spark.sql(\"SELECT city, sum(amount) AS total FROM orders GROUP BY city\")\nresult.filter(result.total > 1000).orderBy(result.total.desc()).show()",
                        "note": "sql() 返回 DataFrame，可继续接 API 的 filter / orderBy。"
                    }
                ],
                "key_points": [
                    "迷你分析链路：read → 注册视图 → WHERE → GROUP BY+HAVING → ORDER BY → 写出",
                    "spark.sql 返回 DataFrame（惰性），写出才是 Action",
                    "SQL 与 API 可混用，Catalyst 统一优化",
                    "写盘前先用 show 验证",
                    "HAVING 分组后过滤 vs WHERE 分组前过滤"
                ],
                "common_mistakes": [
                    {
                        "mistake": "忘了注册视图就 SELECT FROM orders。",
                        "why": "SQL 只认注册名。",
                        "fix": "先 createOrReplaceTempView。"
                    },
                    {
                        "mistake": "聚合后过滤写在 WHERE。",
                        "why": "报错。",
                        "fix": "用 HAVING。"
                    },
                    {
                        "mistake": "写出前不验证直接落盘。",
                        "why": "脏数据落盘。",
                        "fix": "先 show。"
                    }
                ],
                "review": "从「Spark SQL 是什么」到「视图、SELECT/WHERE/GROUP BY/JOIN/函数、文件即表」，Level 3 的零件都齐了。\n\n现在，是时候把这些零散的知识点串成一次完整的「动手体验」——读一份真实数据，注册、过滤聚合、写出。这一课不是「再做几道题」，而是「恭喜你，把这一章真正收个尾」。",
                "problem": "能不能不靠提示，独立用 SQL 走完一次真实分析：读 CSV、注册、过滤聚合、排序写出？更重要的是，在写的过程中你能随时回答：spark.sql 返回什么、哪步是 Action、HAVING 和 WHERE 差在哪？这正是检验你是否真正串起 Level 3 的标准。",
                "preview": "恭喜你走完了 Level 3——你现在能用 SQL 或 API 查同一批数据了。但一个更深的问题浮现：「我写的这些，Spark 到底怎么执行、怎么优化？」 那是 Level 4（执行计划）的主场。去测验检验自己吧。🏁"
            }
        }
    ]
}

LEVEL3_QUIZZES = [
    {"lesson_slug": "l3-what-is-spark-sql", "questions": [
        {"type": "single_choice", "prompt": "Spark SQL 最准确的定位是？", "options": ["一个新的独立计算引擎", "Spark 处理结构化数据的统一模块，提供 SQL 与 DataFrame API", "一种只支持 SQL 的数据库", "一个 Python 数据分析库"], "correct_index": 1, "explanation": "Spark SQL 是 Spark 处理结构化数据的统一模块，SQL 与 DataFrame API 共享 Catalyst 优化器，不是新引擎。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "spark.sql(\"SELECT ...\") 返回什么？", "options": ["一个执行后的结果表", "一个 DataFrame（惰性）", "一个 Python list", "一个 JDBC 连接"], "correct_index": 1, "explanation": "spark.sql 返回惰性 DataFrame，可继续链式 .filter() 等，遇到 Action 才执行。", "dimension": "mechanism"},
        {"type": "single_choice", "prompt": "为什么 Spark 同时提供 SQL 和 DataFrame API？", "options": ["它们底层是两套不同引擎，性能不同", "让分析师用 SQL、工程师用 API，且共享同一优化器", "SQL 更快", "API 更快"], "correct_index": 1, "explanation": "二者共享 Catalyst 优化器，只是两种写法，目的是适配不同使用者。", "dimension": "why"},
        {"type": "single_choice", "prompt": "关于 Spark SQL 与 DataFrame API 的关系，正确的是？", "options": ["SQL 编译成的执行计划和 API 等价", "SQL 比 API 快一倍", "API 不能做聚合", "二者无法混用"], "correct_index": 0, "explanation": "二者最终编译成相同逻辑/物理计划，性能一致。", "dimension": "comparison"},
        {"type": "single_choice", "prompt": "当你调用 spark.sql，内部首先发生什么？", "options": ["立刻把数据算完返回", "解析成逻辑计划交给 Catalyst 优化", "把 DataFrame 物化成表", "启动一个 MapReduce 作业"], "correct_index": 1, "explanation": "sql() 先把 SQL 文本解析成逻辑计划，再交 Catalyst 优化，不立即计算。", "dimension": "mechanism"},
        {"type": "single_choice", "prompt": "想用 SQL 查询一个叫 df 的 DataFrame，第一步该？", "options": ["直接 spark.sql(\"SELECT * FROM df\")", "先 df.createOrReplaceTempView(\"df\") 再查", "把 df 转成 pandas", "用 df.toTable()"], "correct_index": 1, "explanation": "SQL 只认注册过的名字，必须先注册成视图。", "dimension": "apply"},
        {"type": "single_choice", "prompt": "直接 spark.sql(\"SELECT * FROM my_df\") 报 Table or view not found，原因是？", "options": ["DataFrame 没有注册成视图", "SQL 语法错", "Spark 没启动", "列不存在"], "correct_index": 0, "explanation": "SQL 只认在 catalog 中注册过的名字，未注册的 DataFrame 变量名不是表名。", "dimension": "debug"},
        {"type": "single_choice", "prompt": "Catalyst 在 Spark SQL 中的作用是？", "options": ["一个存储格式", "Spark 的优化器，SQL 与 API 共用", "一种网络协议", "一种 UDF 框架"], "correct_index": 1, "explanation": "Catalyst 是 Spark 的优化器，SQL 与 DataFrame API 都经由它优化。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "关于「SQL 比 API 慢」的说法，正确的是？", "options": ["一定更慢", "一定更快", "二者最终执行计划相同，性能差异来自写法本身", "无法比较"], "correct_index": 2, "explanation": "执行计划相同，性能差异只来自具体写法，而非接口选择。", "dimension": "comparison"},
        {"type": "single_choice", "prompt": "如何把 spark.sql 的结果继续用 API 加工？", "options": ["结果不是 DataFrame 不能用 API", "结果是 DataFrame，可直接接 .filter() 等", "必须先 collect", "必须再注册一次"], "correct_index": 1, "explanation": "spark.sql 返回 DataFrame，自然可以接着用 API 链式处理。", "dimension": "apply"}
    ]},
    {"lesson_slug": "l3-temp-views", "questions": [
        {"type": "single_choice", "prompt": "createOrReplaceTempView 做了什么？", "options": ["把 DataFrame 物化成表落盘", "在 session 内注册一个名字指向该 DataFrame（零拷贝）", "复制一份数据", "启动一个 Job"], "correct_index": 1, "explanation": "它只是往 catalog 写一条「名字→DataFrame」的映射，不移动数据。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "让 SQL 能查 df，正确写法是？", "options": ["df.toTable(\"t\")", "df.createOrReplaceTempView(\"t\")", "spark.register(df)", "spark.sql(\"CREATE t FROM df\")"], "correct_index": 1, "explanation": "createOrReplaceTempView 把 DataFrame 注册为临时视图。", "dimension": "apply"},
        {"type": "single_choice", "prompt": "为什么临时视图「不复制数据」很重要？", "options": ["避免双倍内存与拷贝开销", "因为它更快", "因为 SQL 要求", "没意义"], "correct_index": 0, "explanation": "视图只是逻辑映射，零拷贝避免内存与 IO 浪费。", "dimension": "why"},
        {"type": "single_choice", "prompt": "注册视图后，真正计算发生在？", "options": ["createOrReplaceTempView 时", "你 spark.sql 查询它并遇到 Action 时", "session 关闭时", "注册时预计算"], "correct_index": 1, "explanation": "注册只是登记名字；查询遇到 Action 才真正执行。", "dimension": "mechanism"},
        {"type": "single_choice", "prompt": "临时视图 vs 全局临时视图，正确的是？", "options": ["二者完全一样", "全局视图需 global_temp. 前缀且跨 session 可见", "临时视图跨 session 可见", "全局视图不能跨 session"], "correct_index": 1, "explanation": "全局临时视图用 global_temp. 前缀访问，且跨 session 可见。", "dimension": "comparison"},
        {"type": "single_choice", "prompt": "session 关闭后再查之前注册的视图报「表不存在」，原因？", "options": ["视图只在创建它的 session 有效", "数据被删了", "SQL 错", "视图名冲突"], "correct_index": 0, "explanation": "临时视图绑定 session 生命周期，session 关闭即失效。", "dimension": "debug"},
        {"type": "single_choice", "prompt": "全局临时视图查询时前缀是？", "options": ["temp.", "global_temp.", "public.", "session."], "correct_index": 1, "explanation": "全局临时视图必须用 global_temp. 前缀访问。", "dimension": "apply"},
        {"type": "single_choice", "prompt": "临时视图本质是？", "options": ["数据库里的物理表", "catalog 中「名字→DataFrame」的逻辑映射", "一份拷贝", "一个 UDF"], "correct_index": 1, "explanation": "视图是逻辑映射，不是物理表、不物化数据。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "关于视图与底层数据，正确的是？", "options": ["视图修改会影响原 DataFrame 吗——不会，视图只是映射", "视图会物化数据", "视图就是表", "视图不可查询"], "correct_index": 0, "explanation": "视图只是映射，不持有数据，也不改变底层 DataFrame。", "dimension": "comparison"},
        {"type": "single_choice", "prompt": "同名再调用 createOrReplaceTempView 会？", "options": ["报错", "覆盖同名视图", "创建两个", "忽略"], "correct_index": 1, "explanation": "createOrReplace 语义就是同名覆盖。", "dimension": "debug"}
    ]},
    {"lesson_slug": "l3-select-basics", "questions": [
        {"type": "single_choice", "prompt": "SQL 中 SELECT 的作用是？", "options": ["过滤行", "指定输出列（投影）", "排序", "分组"], "correct_index": 1, "explanation": "SELECT 指定输出列，对应 DataFrame 的 select（投影）。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "选出 name 列并重命名 age→age_next，正确？", "options": ["SELECT name, age AS age_next", "SELECT name, age=age_next", "SELECT name, rename age age_next", "SELECT name, age->age_next"], "correct_index": 0, "explanation": "SQL 用 AS 起别名；age AS age_next 是标准写法。", "dimension": "apply"},
        {"type": "single_choice", "prompt": "spark.sql(\"SELECT ...\") 返回的是？", "options": ["执行结果", "惰性 DataFrame", "list", "表"], "correct_index": 1, "explanation": "spark.sql 返回惰性 DataFrame，需 Action 才执行。", "dimension": "mechanism"},
        {"type": "single_choice", "prompt": "SELECT name, age 与 DataFrame API df.select(\"name\",\"age\") 的关系？", "options": ["完全不同", "Catalyst 中等价", "API 更快", "SQL 更快"], "correct_index": 1, "explanation": "两者在 Catalyst 中生成等价逻辑计划，性能一致。", "dimension": "comparison"},
        {"type": "single_choice", "prompt": "为什么不建议把 Python 变量直接拼进 SQL 字符串？", "options": ["写法麻烦", "有注入风险且计划无法缓存", "会报错", "不支持"], "correct_index": 1, "explanation": "拼接既带来注入风险，又让每次字符串不同、计划无法复用缓存。", "dimension": "why"},
        {"type": "single_choice", "prompt": "列名含空格 `order amount` 在 SQL 中报错，修复？", "options": ["去掉空格", "用反引号 `order amount`", "加引号", "改列名"], "correct_index": 1, "explanation": "含空格/特殊字符的列名必须用反引号包裹。", "dimension": "debug"},
        {"type": "single_choice", "prompt": "给每行加常量列 tag='VIP'，正确？", "options": ["SELECT name, 'VIP' AS tag", "SELECT name, VIP", "SELECT name, \"VIP\"", "SELECT name, const VIP"], "correct_index": 0, "explanation": "字符串常量用单引号，AS 起别名。", "dimension": "apply"},
        {"type": "single_choice", "prompt": "SQL 里字符串常量用什么包裹？", "options": ["双引号", "单引号", "反引号", "不加"], "correct_index": 1, "explanation": "SQL 字符串常量用单引号；双引号在多数方言里用于标识符。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "关于 SQL SELECT 与 Level 2 df.select，正确的是？", "options": ["一个会触发执行一个不会", "都惰性，都返回 DataFrame，等价", "select 不能起别名", "SQL 不能写表达式"], "correct_index": 1, "explanation": "两者都惰性、都返回 DataFrame、在 Catalyst 中等价。", "dimension": "comparison"},
        {"type": "single_choice", "prompt": "调用 spark.sql 后变量里「没有数据」，原因？", "options": ["SQL 报错了", "spark.sql 惰性，需 Action 才执行", "DataFrame 为空", "视图错"], "correct_index": 1, "explanation": "spark.sql 仅构造惰性 DataFrame，数据在 Action 时才算。", "dimension": "debug"}
    ]},
    {"lesson_slug": "l3-where-order-limit", "questions": [
        {"type": "single_choice", "prompt": "SQL 中挑行用？", "options": ["SELECT", "WHERE", "ORDER BY", "LIMIT"], "correct_index": 1, "explanation": "WHERE 过滤行，对应 DataFrame 的 filter。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "过滤 age>18 且 city='BJ'，正确？", "options": ["WHERE age>18 AND city='BJ'", "WHERE age>18 & city='BJ'", "WHERE age>18 && city='BJ'", "FILTER"], "correct_index": 0, "explanation": "SQL 用 AND/OR/NOT 组合条件，对应 API 的 & | ~。", "dimension": "apply"},
        {"type": "single_choice", "prompt": "为什么 ORDER BY 在大表上昂贵？", "options": ["它要全局有序，必触发 Shuffle", "它慢因为语法", "它复制数据", "它不优化"], "correct_index": 0, "explanation": "全局有序需要按排序键重分区，必触发一次 Shuffle。", "dimension": "why"},
        {"type": "single_choice", "prompt": "WHERE 条件通常如何被优化？", "options": ["被忽略", "被 Catalyst 下推到读取端尽早过滤", "在最后执行", "在写入时"], "correct_index": 1, "explanation": "Catalyst 常做谓词下推，让过滤尽早发生、减少后续数据量。", "dimension": "mechanism"},
        {"type": "single_choice", "prompt": "WHERE phone = NULL 查不到空值行，原因？", "options": ["列不存在", "NULL 不参与 = 比较，永远假，要用 IS NULL", "语法错", "索引问题"], "correct_index": 1, "explanation": "NULL 是未知值，= NULL 永远为假，判断空必须用 IS NULL。", "dimension": "debug"},
        {"type": "single_choice", "prompt": "取金额最高的 5 个城市，正确？", "options": ["ORDER BY total DESC LIMIT 5", "LIMIT 5 ORDER BY total", "TOP 5", "SELECT MAX(5)"], "correct_index": 0, "explanation": "先排序再 LIMIT 即 TopN；ORDER BY 触发 Shuffle。", "dimension": "apply"},
        {"type": "single_choice", "prompt": "SQL 的 AND/OR 与 Level 2 API 的 & | ~ 的关系？", "options": ["完全无关", "语义一样，只是 SQL 文本用 AND/OR，API 用 & | ~", "一个快一个慢", "API 不支持"], "correct_index": 1, "explanation": "语义等价，只是语言不同；效果都是组合条件。", "dimension": "comparison"},
        {"type": "single_choice", "prompt": "判断空值正确的写法是？", "options": ["= NULL", "IS NULL", "== NULL", "equals NULL"], "correct_index": 1, "explanation": "SQL 用 IS NULL / IS NOT NULL 判断空值。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "LIMIT 5 返回结果「感觉是随机的」，原因？", "options": ["LIMIT 是随机抽样", "LIMIT 取前 5 行，未排序则顺序不定", "数据错", "bug"], "correct_index": 1, "explanation": "LIMIT 取前 N 行；未配合 ORDER BY 时顺序不保证，并非抽样。", "dimension": "debug"},
        {"type": "single_choice", "prompt": "ORDER BY 与 Level 2 的 orderBy 关系？", "options": ["完全不同", "Catalyst 中等价，ORDER BY 触发 Shuffle", "orderBy 更快", "SQL 不能排序"], "correct_index": 1, "explanation": "二者等价，ORDER BY 通常触发一次 Shuffle（Level 5 展开）。", "dimension": "comparison"}
    ]},
    {"lesson_slug": "l3-groupby-having", "questions": [
        {"type": "single_choice", "prompt": "GROUP BY 的作用是？", "options": ["过滤行", "按维度分组并对每组聚合", "排序", "投影"], "correct_index": 1, "explanation": "GROUP BY 按维度分组，再用聚合函数汇总每组。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "按 city 算总额，正确？", "options": ["SELECT city, sum(amount) FROM sales GROUP BY city", "SELECT sum(amount) FROM sales", "SELECT city, amount FROM sales GROUP BY city", "GROUP BY city sum(amount)"], "correct_index": 0, "explanation": "分组键出现在 SELECT，聚合函数算汇总值。", "dimension": "apply"},
        {"type": "single_choice", "prompt": "为什么聚合后过滤要用 HAVING 而非 WHERE？", "options": ["HAVING 更快", "WHERE 在分组前执行看不到聚合值", "语法要求", "没原因"], "correct_index": 1, "explanation": "WHERE 在分组前执行，看不到聚合结果；HAVING 在分组后。", "dimension": "why"},
        {"type": "single_choice", "prompt": "WHERE sum(amount)>1000 报错，修复？", "options": ["改成 HAVING sum(amount)>1000", "改成 FILTER", "删掉", "用 WHERE amount>1000"], "correct_index": 0, "explanation": "聚合函数不能用于 WHERE，必须放 HAVING。", "dimension": "debug"},
        {"type": "single_choice", "prompt": "GROUP BY 通常触发？", "options": ["无代价", "一次 Shuffle（按 key 汇聚）+ 本地预聚合", "一次排序", "一次写入"], "correct_index": 1, "explanation": "分组需按 key 重分区并汇聚，必触发 Shuffle，且常有 Map-side Combine。", "dimension": "mechanism"},
        {"type": "single_choice", "prompt": "GROUP BY city, product 与 API 的对应？", "options": ["groupBy(\"city\").groupBy(\"product\")", "groupBy(\"city\",\"product\")", "groupBy(\"city\"+\"product\")", "无法对应"], "correct_index": 1, "explanation": "多列分组在 API 里是 groupBy(\"city\",\"product\")。", "dimension": "comparison"},
        {"type": "single_choice", "prompt": "非分组列出现在 SELECT 但未聚合会？", "options": ["自动取第一个", "报错", "返回 null", "忽略"], "correct_index": 1, "explanation": "组内该列有多个值，Spark 不知道取哪个，直接报错（同 SQL）。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "只留总金额>1000 的城市，正确？", "options": ["WHERE sum(amount)>1000", "HAVING sum(amount)>1000", "GROUP BY city HAVING sum(amount)>1000", "FILTER"], "correct_index": 2, "explanation": "先 GROUP BY 再 HAVING 对聚合结果过滤。", "dimension": "apply"},
        {"type": "single_choice", "prompt": "SELECT city, amount FROM sales GROUP BY city 报错，原因？", "options": ["amount 未聚合也未被分组", "city 错", "语法错", "没数据"], "correct_index": 0, "explanation": "amount 既不在 GROUP BY 也未被聚合，违反约束。", "dimension": "debug"},
        {"type": "single_choice", "prompt": "SQL GROUP BY 与 Level 2 df.groupBy 关系？", "options": ["不同引擎", "Catalyst 中等价", "API 不能聚合", "SQL 不能多列分组"], "correct_index": 1, "explanation": "二者生成等价逻辑计划。", "dimension": "comparison"}
    ]},
    {"lesson_slug": "l3-joins-intro", "questions": [
        {"type": "single_choice", "prompt": "JOIN 的作用是？", "options": ["过滤", "按连接键把两表行配对", "排序", "分组"], "correct_index": 1, "explanation": "JOIN 按连接条件把两表的行组合（配对）。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "按 user_id 内连接 users 与 orders，正确？", "options": ["JOIN orders ON users.user_id=orders.user_id", "JOIN orders WHERE user_id", "JOIN orders USING user_id WITHOUT ON", "CROSS"], "correct_index": 0, "explanation": "INNER JOIN 用 ON 指定连接键。", "dimension": "apply"},
        {"type": "single_choice", "prompt": "为什么 JOIN 通常代价大？", "options": ["它要触发 Shuffle 按 key 重分区", "它复制表", "它慢因为语法", "没原因"], "correct_index": 0, "explanation": "JOIN 需按连接键重分区，必触发 Shuffle，代价大。", "dimension": "why"},
        {"type": "single_choice", "prompt": "INNER JOIN 保留的是？", "options": ["左表全部", "右表全部", "两表都匹配上的行", "两表所有行（含不匹配）"], "correct_index": 2, "explanation": "INNER JOIN 只保留两边都能匹配上的行。", "dimension": "mechanism"},
        {"type": "single_choice", "prompt": "JOIN 后行数远超预期（爆炸），可能原因？", "options": ["连接键有重复导致笛卡尔式膨胀", "数据少", "SQL 错", "索引"], "correct_index": 0, "explanation": "连接键重复会产生多对多膨胀，是常见性能/正确性问题。", "dimension": "debug"},
        {"type": "single_choice", "prompt": "INNER JOIN 与后续 Level 6 的关系？", "options": ["本课只讲 INNER 基础，类型/广播/调优在 L6", "已全部讲完", "INNER 最慢", "无关"], "correct_index": 0, "explanation": "本课只建立直觉；各种 JOIN 类型与调优在 Level 6 展开。", "dimension": "comparison"},
        {"type": "single_choice", "prompt": "连接键类型不一致会导致？", "options": ["自动转换", "匹配不上（全空）", "报错", "忽略"], "correct_index": 1, "explanation": "字符串≠整数，类型不一致会导致全部不匹配。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "JOIN 之后继续聚合，正确？", "options": ["不行", "SELECT u.name, sum(o.amount) FROM users u JOIN orders o ON ... GROUP BY u.name", "必须分开", "用 HAVING"], "correct_index": 1, "explanation": "JOIN 后可正常 GROUP BY 汇总。", "dimension": "apply"},
        {"type": "single_choice", "prompt": "忘了 ON 直接 JOIN 两表，结果？", "options": ["报错", "变成 CROSS JOIN（笛卡尔积）行数爆炸", "正常", "空"], "correct_index": 1, "explanation": "无连接条件会变成 CROSS JOIN，行数 = 两表行数乘积。", "dimension": "debug"},
        {"type": "single_choice", "prompt": "JOIN 与 Level 2 单表操作关系？", "options": ["JOIN 是多表，必 Shuffle，L6 深讲", "JOIN 免费", "JOIN 只在 API", "无关"], "correct_index": 0, "explanation": "JOIN 是多表操作，必触发 Shuffle，深入在 Level 6。", "dimension": "comparison"}
    ]},
    {"lesson_slug": "l3-functions-and-udf", "questions": [
        {"type": "single_choice", "prompt": "Spark SQL 内置函数位于？", "options": ["pandas", "pyspark.sql.functions（F）", "os", "math"], "correct_index": 1, "explanation": "内置函数都在 pyspark.sql.functions 下（F 前缀）。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "为什么优先用内置函数而非 UDF？", "options": ["内置走 Catalyst 原生优化更快", "内置更简单", "UDF 不支持", "没原因"], "correct_index": 0, "explanation": "内置函数被 Catalyst 编译成原生算子，快且可优化。", "dimension": "why"},
        {"type": "single_choice", "prompt": "UDF 为什么慢？", "options": ["它要 JVM↔Python 序列化往返且失去 Catalyst 优化", "它语法复杂", "它不支持聚合", "它复制数据"], "correct_index": 0, "explanation": "UDF 每行触发一次跨语言调用并序列化，且绕过 Catalyst 优化。", "dimension": "mechanism"},
        {"type": "single_choice", "prompt": "把 Python 函数 score_category 变成可用列表达式，正确？", "options": ["直接用在 SQL", "F.udf(score_category) 注册", "def 即可", "score_category()"], "correct_index": 1, "explanation": "需用 F.udf 把 Python 函数注册成 UDF。", "dimension": "apply"},
        {"type": "single_choice", "prompt": "在 SQL 里直接调用普通 Python 函数报错，原因？", "options": ["SQL 不认普通 Python 函数，需 F.udf 注册", "函数错", "列错", "语法"], "correct_index": 0, "explanation": "SQL 文本里不能直接引用 Python 函数，必须经过 F.udf 注册。", "dimension": "debug"},
        {"type": "single_choice", "prompt": "行级 Python UDF vs pandas UDF，正确的是？", "options": ["一样", "pandas UDF 向量化更快，优先", "行级更快", "都不能用"], "correct_index": 1, "explanation": "pandas UDF 向量化执行，比逐行 Python UDF 高效得多。", "dimension": "comparison"},
        {"type": "single_choice", "prompt": "关于 UDF 的「慢」，本课态度是？", "options": ["UDF 不能用", "能不用就不用，埋伏笔给 Level 7", "UDF 最快", "无所谓"], "correct_index": 1, "explanation": "本课确立「能不用 UDF 就不用」的原则，深入优化留 Level 7。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "字符串大写，正确做法？", "options": ["写 UDF", "直接用内置 upper() 或 F.upper", "用 Python upper", "用循环"], "correct_index": 1, "explanation": "内置能做的绝不写 UDF。", "dimension": "apply"},
        {"type": "single_choice", "prompt": "内置函数 upper 与 API F.upper 关系？", "options": ["不同", "同一套，Catalyst 等价", "API 更快", "SQL 不支持"], "correct_index": 1, "explanation": "二者是同一套函数的两种调用方式。", "dimension": "comparison"},
        {"type": "single_choice", "prompt": "UDF 在 Executor 上性能差，排查方向？", "options": ["看是否行级 Python 调用过多，考虑 pandas_udf", "重装 Spark", "加内存", "忽略"], "correct_index": 0, "explanation": "行级 Python 调用是瓶颈，优先改 pandas_udf 或内置。", "dimension": "debug"}
    ]},
    {"lesson_slug": "l3-tables-and-formats", "questions": [
        {"type": "single_choice", "prompt": "不接 Hive 时，CREATE TABLE ... USING parquet LOCATION 做了什么？", "options": ["移动数据", "把「路径+格式」登记进 catalog，不移动数据", "复制数据", "启动 Job"], "correct_index": 1, "explanation": "它只登记元数据，数据仍在原路径，按需读取。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "把 Parquet 路径直接当表查，正确？", "options": ["CREATE TABLE t USING parquet LOCATION '/data/sales' 然后 SELECT", "必须先用 pandas 读", "不支持", "用 LOAD"], "correct_index": 0, "explanation": "CREATE TABLE ... LOCATION 即可把文件注册成可查的表。", "dimension": "apply"},
        {"type": "single_choice", "prompt": "本路线明确不接入什么？", "options": ["Parquet", "Hive Metastore（永久表）", "CSV", "JSON"], "correct_index": 1, "explanation": "既定约束明确不接 Hive Metastore，表非永久 Hive 表。", "dimension": "why"},
        {"type": "single_choice", "prompt": "这里的「表」与数据库永久表区别？", "options": ["一样", "本路线表是 session 内或文件级，非永久 Hive 表", "更快", "不能查"], "correct_index": 1, "explanation": "未接 Hive 时表是临时/文件级，不跨 session 持久。", "dimension": "comparison"},
        {"type": "single_choice", "prompt": "CREATE TABLE ... LOCATION 查询时？", "options": ["立刻读全表", "按需按格式读取，Catalyst 正常优化", "复制", "报错"], "correct_index": 1, "explanation": "查询时按格式读取，Catalyst 照常优化（含谓词下推）。", "dimension": "mechanism"},
        {"type": "single_choice", "prompt": "对应 API mode(\"overwrite\").write 的 SQL 写出是？", "options": ["INSERT OVERWRITE TABLE", "SAVE TABLE", "UPDATE", "EXPORT"], "correct_index": 0, "explanation": "SQL 用 INSERT OVERWRITE TABLE 对应 overwrite 模式。", "dimension": "apply"},
        {"type": "single_choice", "prompt": "写出产生海量小文件，原因？", "options": ["partitionBy 每 Task 一文件", "数据少", "SQL 错", "列多"], "correct_index": 0, "explanation": "partitionBy 落盘每 Task 生成一个文件，易产生小文件（Level 7 坑）。", "dimension": "debug"},
        {"type": "single_choice", "prompt": "SaveMode 与 Level 2 write 的关系？", "options": ["完全不同", "一致（overwrite/append/error/ignore），SQL 用 INSERT OVERWRITE/INTO", "只 API 有", "SQL 没有"], "correct_index": 1, "explanation": "SQL 的 INSERT OVERWRITE/INTO 对应 API 的 overwrite/append。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "注册视图 vs CREATE TABLE ... LOCATION，正确的是？", "options": ["都只是登记，不移动数据", "后者移动数据", "前者更快", "不能混用"], "correct_index": 0, "explanation": "两者都只登记逻辑映射，不移动/复制数据。", "dimension": "comparison"},
        {"type": "single_choice", "prompt": "期望「永久表」跨 session 存在却失败，原因？", "options": ["没接 Hive（enableHiveSupport）", "数据丢了", "SQL 错", "权限"], "correct_index": 0, "explanation": "本路线不接 Hive，表非持久，跨 session 需重新注册。", "dimension": "debug"}
    ]},
    {"lesson_slug": "l3-comprehensive", "questions": [
        {"type": "single_choice", "prompt": "本综合练习链路的第一步通常是？", "options": ["直接写 SQL", "读 CSV 并确认 Schema", "注册 Hive", "直接写出"], "correct_index": 1, "explanation": "先读入并 printSchema 确认类型，是标准第一步。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "读 CSV 后让 SQL 能查，正确？", "options": ["直接 SELECT", "先 createOrReplaceTempView", "转 pandas", "toTable"], "correct_index": 1, "explanation": "必须先注册成视图，SQL 才能按名字查。", "dimension": "apply"},
        {"type": "single_choice", "prompt": "为什么写出前先用 show 验证？", "options": ["避免写出脏数据", "更快", "必须", "语法"], "correct_index": 0, "explanation": "先验证聚合与类型，避免错误落盘。", "dimension": "why"},
        {"type": "single_choice", "prompt": "综合练习中哪一步是 Action（真正执行）？", "options": ["注册视图", "最后的写出（INSERT OVERWRITE / write）", "spark.sql 返回时", "读 CSV 时"], "correct_index": 1, "explanation": "只有最后的写出（Write）是 Action，触发前面整条链执行。", "dimension": "mechanism"},
        {"type": "single_choice", "prompt": "聚合后过滤写在 WHERE 报错，修复？", "options": ["HAVING", "FILTER", "删", "改 SELECT"], "correct_index": 0, "explanation": "聚合后过滤必须用 HAVING。", "dimension": "debug"},
        {"type": "single_choice", "prompt": "spark.sql 返回结果与 API 链式加工，正确的是？", "options": ["不能混用", "结果是 DataFrame，可继续接 API", "必须重新注册", "不同引擎"], "correct_index": 1, "explanation": "spark.sql 返回 DataFrame，可自然接 API 链式处理。", "dimension": "comparison"},
        {"type": "single_choice", "prompt": "按 city 聚合且只留 total>1000，正确？", "options": ["WHERE sum>1000", "GROUP BY city HAVING sum(amount)>1000", "GROUP BY city WHERE", "FILTER"], "correct_index": 1, "explanation": "先分组再 HAVING 过滤聚合结果。", "dimension": "apply"},
        {"type": "single_choice", "prompt": "spark.sql(...) 返回的是？", "options": ["结果表", "惰性 DataFrame", "list", "连接"], "correct_index": 1, "explanation": "spark.sql 返回惰性 DataFrame。", "dimension": "concept"},
        {"type": "single_choice", "prompt": "Level 3 与 Level 2 的关系？", "options": ["无关", "L3 用 SQL 操作 L2 的 DataFrame，共享 Catalyst", "L3 替代 L2", "L3 更慢"], "correct_index": 1, "explanation": "L3 是在 L2 的 DataFrame 之上用 SQL 这层方言，共享同一优化器。", "dimension": "comparison"},
        {"type": "single_choice", "prompt": "写出 Parquet 按 city 分区，SQL 侧对应？", "options": ["分区在 CREATE TABLE 时 PARTITIONED BY 定义，写出用 INSERT OVERWRITE TABLE", "SQL 不支持分区", "用 LIMIT 分区", "partitionBy 只在 pandas 用"], "correct_index": 0, "explanation": "分区由目标表定义（建表时 PARTITIONED BY），写出用 INSERT OVERWRITE。", "dimension": "apply"}
    ]}
]


def upsert():
    # 1) 合并进 course_seed.json
    with open(SEED, encoding="utf-8") as f:
        data = json.load(f)
    exists = any(lv.get("order_index") == 3 for lv in data["levels"])
    if not exists:
        data["levels"].append(LEVEL3)
        with open(SEED, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print("已写入 course_seed.json（Level 3）")
    else:
        print("course_seed.json 已存在 Level 3，跳过 JSON 写入")

    # 2) 合并进 quiz_seed.json
    with open(QUIZ, encoding="utf-8") as f:
        qdata = json.load(f)
    qentries = qdata.setdefault("quizzes", [])
    existing = {e["lesson_slug"] for e in qentries}
    added_q = 0
    for entry in LEVEL3_QUIZZES:
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
        print("quiz_seed.json 已包含 Level 3 题库，跳过")

    # 3) upsert 进数据库
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT id,title FROM course_levels WHERE order_index=3")
    row = cur.fetchone()
    if row:
        level_id = row[0]
        print(f"Level 3 已存在于 DB (id={level_id})，仅补充缺失 lesson")
    else:
        cur.execute(
            "INSERT INTO course_levels (title, description, order_index, status) VALUES (?,?,?,?)",
            (LEVEL3["title"], LEVEL3["description"], LEVEL3["order_index"], "active"))
        level_id = cur.lastrowid
        print(f"已插入 Level 3 (id={level_id})")

    inserted_lessons = 0
    for ls in LEVEL3["lessons"]:
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
    for entry in LEVEL3_QUIZZES:
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
