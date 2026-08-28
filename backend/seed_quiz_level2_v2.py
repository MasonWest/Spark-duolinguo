# -*- coding: utf-8 -*-
# 重写 Level 2 的 50 题干扰项 + 打散正确项位置（幂等）。
# 保留题干 / 正确答案 / 解析；仅替换 options 与 correct_index。
import sqlite3, json, os

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, 'spark_quest.db')
SEED = os.path.join(BASE, 'app', 'quiz_seed.json')

# 每个问题的 3 个新干扰项（按底层 quizzes 的读取顺序，i=0..49）。
# 普通题：干扰项 = 听起来合理的典型误区；"下列说法错误的是"题：干扰项 = 真命题。
NEW_DISTRACTORS = [
    # Q1 l2-what-is-dataframe
    ["Spark 在 Driver 端维护、可随时原地修改的本地二维表",
     "按行切分但不记录列名与类型的纯分布式集合",
     "RDD 之上仅为了代码简洁而存在的语法糖层"],
    # Q2
    ["为了在单机也能像 pandas 那样直接原地修改数据",
     "因为列式存储强制要求数据必须带 Schema 才能读取，否则连文件都无法被成功打开",
     "为了让 Driver 能够串行、逐行地处理全部记录"],
    # Q3
    ["会先在 Driver 端把所有数据物化到内存，再等待后续操作",
     "会立刻扫描全表推断类型，确保每一行的类型都被正确解析",
     "会立即分配 Task 并开始读取，只是暂不把结果返回给用户"],
    # Q4
    ["对几百行数据做简单求和，只追求代码最短、不关心执行效率",
     "对图片、音频等非结构化文件做特征提取与预处理",
     "需要自己手写每台机器的循环逻辑来逐条处理记录"],
    # Q5 (错误说法题 -> 干扰项须为真)
    ["DataFrame 的查询会先经 Catalyst 优化再翻译成 RDD 执行",
     "DataFrame 通过 Schema 让你以列名而非下标访问数据",
     "DataFrame 与 RDD 共用分区、血缘与 Task 这一套执行机制"],
    # Q6 l2-create-dataframe
    ["已经被 Spark 全部读入 Driver 内存的本地 pandas.DataFrame",
     "一个记录文件位置、尚未解析内容的文件句柄",
     "一个已经物化、可直接索引的 RDD[Row]"],
    # Q7
    ["指示 Spark 跳过空行以加快读取速度",
     "告诉 Spark 该文件使用哪种字符编码",
     "要求 Spark 在读取前先验一遍 Schema 是否匹配，不匹配的文件会被直接丢弃"],
    # Q8
    ["spark.read.csv 调用的一瞬间，数据就已全部读取并进入内存",
     "程序启动后由 Driver 自动、无条件地先把全表读一遍",
     "只在 Driver 端由单个进程顺序读取并解析，不经过集群"],
    # Q9
    ["pd.DataFrame(rows)（得到的是单机 pandas 对象）",
     "sc.parallelize(rows)（得到的是 RDD 而非 DataFrame）",
     "spark.read.csv('rows')（把 rows 当成文件路径去读）"],
    # Q10 (错误说法 -> 真)
    ["不加 inferSchema 时，所有列默认会被当成 StringType",
     "加 inferSchema 会抽样推断类型，但仍可能因样本偏差猜错",
     "生产环境推荐用 schema=StructType 显式声明类型更可靠"],
    # Q11 l2-schema-types
    ["描述数据应当写入哪个输出目录与文件格式",
     "描述集群中 Executor 的数量与内存配置",
     "描述 Spark 会把这份数据切成多少个分区"],
    # Q12
    ["因为 inferSchema 在 Spark 中尚未被实现，无法使用",
     "因为显式声明能把数据压缩得更小、更省内存",
     "因为 inferSchema 一定把所有数字都猜成字符串类型"],
    # Q13
    ["自动把该值替换为 null，以保持程序继续运行不中断",
     "自动把该值转成字符串以尽量保留原始信息",
     "静默跳过这一行，仅记录一条警告日志后继续"],
    # Q14
    ["DoubleType（二进制浮点，存在舍入误差）",
     "IntegerType（只能存整数，无法表示小数）",
     "StringType（虽精确但无法进行数值运算）"],
    # Q15 (错误说法 -> 真)
    ["字段默认 nullable=True，即默认允许出现空值",
     "nullable 会影响 join 与聚合时 null 值的处理逻辑",
     "可以对关键的外键列显式设置 nullable=False"],
    # Q16 l2-inspect
    ["分页打印整张表的全部行，无论规模多大",
     "仅打印列名与数据类型组成的 Schema 结构",
     "返回一个新的 DataFrame 供后续继续链式调用"],
    # Q17
    ["因为 Spark 引擎存在限制，单次最多只能取出 20 行",
     "因为 DataFrame 在内存中本来就只缓存了约 20 行",
     "因为超过 20 行后剩余数据会被 Spark 自动丢弃"],
    # Q18
    ["会立刻触发一次 Action，把数据读取到 Driver",
     "只能用于数值类型列，对字符串列无效",
     "会直接修改原 DataFrame 的列结构并写回"],
    # Q19
    ["用 df.show() 看几行数值，肉眼判断像不像数字",
     "用 df.count() 统计行数，从行数推断类型",
     "用 df.collect() 把所有数据拉回本地再逐个判断，这是最稳妥也最常用的做法"],
    # Q20 (错误说法 -> 真)
    ["show() 是 Action，会真正触发一次作业执行",
     "列名含空格时应使用 df['order amount'] 或 col('order amount')",
     "printSchema() 用于查看字段名与数据类型的结构"],
    # Q21 l2-select-filter
    ["select 用来挑行，filter 用来挑列",
     "两者功能完全一样，都是用来挑行的",
     "两者都会就地修改原 DataFrame，而非返回新表"],
    # Q22
    ["因为 & / | 的执行速度比 and / or 更快，应优先使用",
     "因为 filter 本身不支持多个条件组合，必须拆成多个 filter",
     "因为 and / or 不是 Spark 提供的合法运算符，语法上不允许"],
    # Q23
    ["它是 Action，调用时会立即触发整条计算链执行",
     "其中的 & 可以直接替换为 Python 的 and，二者完全等价",
     "它会在 Driver 端一次性把全表数据过滤完再分发"],
    # Q24
    ["df.filter(df.age.between(18,60) and df.city.isin('BJ','SH'))",
     "df.filter(df.age>=18 & df.age<=60 & df.city=='SH')",
     "df.filter(df.age.between(18,60)).filter(df.city=='BJ' or df.city=='SH')"],
    # Q25 (错误说法 -> 真)
    ["filter 返回新 DataFrame，不会改变原表",
     "多条件必须用 (c1) & (c2) 的形式且每个条件单独加括号",
     "filter 与 where 在功能上完全等价"],
    # Q26 l2-withcolumn
    ["直接修改传入的 DataFrame，使其列被原地更新",
     "从 DataFrame 中删除指定的那一列",
     "删除满足某个条件的若干行"],
    # Q27
    ["因为 Python 内置函数运行速度更慢，会成为性能瓶颈",
     "因为 Spark 完全不支持在 Python 中调用任何函数",
     "因为 Python 内置函数只能作用于字符串类型的列，对数值无效"],
    # Q28
    ["复制已有的某一列的数据到新列中",
     "触发整条 Transformation 链立即执行",
     "为 DataFrame 的每一行生成一个自增的行号"],
    # Q29
    ["df.withColumn('tag', if df.age>=18 then 'adult' else 'minor')",
     "df.filter(df.age>=18).withColumn('tag', F.lit('adult'))",
     "df.select('adult' if df.age>=18 else 'minor')"],
    # Q30 (错误说法 -> 真)
    ["同名会覆盖该列，异名则新增一列",
     "返回的是新 DataFrame，原表不会被改动",
     "when 漏写 otherwise 会让不满足条件的行该列为 null"],
    # Q31 l2-sort-dedup
    ["两者完全一样，都是按整行去重",
     "dropDuplicates 按整行去重，distinct 按指定列去重",
     "两者都只能在分组之后使用才有意义"],
    # Q32
    ["因为要先打印排序结果，所以必须经过网络",
     "因为要重新统计每个分区的行数",
     "因为要先把数据全部读入 Driver 的内存里再排序，这样才能保证顺序绝对正确"],
    # Q33
    ["先取前 10 行，再在这 10 行内部排序",
     "随机取出 10 行，不保证任何顺序",
     "只取金额最大的那一行，并返回它的 10 个字段"],
    # Q34
    ["df.distinct()（要求整行都相同才算重复）",
     "df.drop('city')（这是删除列，不是去重）",
     "df.orderBy('city').limit(1)（只取一行，非按城市去重）"],
    # Q35 (错误说法 -> 真)
    ["降序要用 F.desc('age') 或 df.age.desc() 来表达",
     "orderBy 与 sort 在功能上完全等价",
     "多列排序时依次传入多个排序表达式即可"],
    # Q36 l2-groupby-agg
    ["先对全表直接求 amount 的总和，忽略分组",
     "按行号自动分组，每组恰好一行",
     "对每个 city 分别求平均值而非求和"],
    # Q37
    ["因为要把聚合结果打印出来展示给用户",
     "因为要按聚合列再做一次排序",
     "因为要先把数据源重新从头读取一遍"],
    # Q38
    ["能，Spark 会自动从重复值里任取一个，不需要显式指定",
     "只能 select 分组键，其它列一律不允许出现在 select 中，哪怕它们并不需要被聚合",
     "只有数值类型的非分组列才能直接使用，字符列不行"],
    # Q39
    ["df.groupBy('city').sum('amount')（只能得到单一聚合）",
     "先 df.groupBy('city').count()，再单独做一遍 sum",
     "df.select('city', F.sum('amount'))（缺少 groupBy 会报错）"],
    # Q40 (错误说法 -> 真)
    ["聚合出的列建议用 alias 起名，便于下游引用",
     "多分组键等价于 SQL 的 GROUP BY a, b",
     "count('*') 统计行数（含 null 行），count('col') 只统计该列非 null 数"],
    # Q41 l2-write-data
    ["一个 Transformation，只把写配置登记进执行计划",
     "一个只读的检查操作，不会真正触发作业执行",
     "一种特殊的聚合操作，只统计将要写出的行数"],
    # Q42
    ["默认会把已有输出直接覆盖掉",
     "默认以追加方式写入，不会清空旧数据，因此重复运行也会越来越安全",
     "默认会忽略本次写入，什么都不会发生"],
    # Q43
    ["把所有数据合并写入单个大文件，方便后续整体读取",
     "按随机生成的名字拆成多个互不相关的文件",
     "仅在内存中生效，便于调试，并不会真正落盘"],
    # Q44
    ["把所有数据写进单个 CSV 大文件，最直观也最简单",
     "使用 mode('append') 不断追加到原目录，避免覆盖旧数据，同时也最利于下游读取",
     "完全不使用分区，让输出目录保持扁平、不分层"],
    # Q45 (错误说法 -> 真)
    ["Parquet 是推荐的写出格式：列式、压缩、自带 Schema",
     "写 CSV 通常需要 option('header', True) 才能保留表头",
     "partitionBy 选高基数或唯一 ID 列会产生海量小目录"],
    # Q46 l2-comprehensive
    ["这六个步骤全部都是 Action，会逐个立即执行",
     "只有 read 是 Action，其余步骤都不是",
     "只有 groupBy 是 Transformation，其它都是 Action"],
    # Q47
    ["能显著加快最终写出的速度",
     "能自动减少需要写出的数据量",
     "能避免触发任何 Shuffle 操作"],
    # Q48
    ["自动命名为 'total'，可直接引用",
     "与原列名 'amount' 完全相同，不会冲突",
     "自动命名为分组键 'region'，不会重复"],
    # Q49
    ["df.amount > 0 and df.amount.isNotNull()",
     "df.amount > 0 or df.amount == None",
     "df.filter(amount > 0)（未使用 Column 写法）"],
    # Q50 (错误说法 -> 真)
    ["filter 多条件必须用 & 且每个条件单独加括号",
     "groupBy / orderBy 通常各会触发一次 Shuffle",
     "write 才是真正触发整条链执行的那个 Action"],
]

def main():
    c = sqlite3.connect(DB)
    rows = c.execute(
        "SELECT q.id, l.slug, q.prompt, q.options, q.correct_index, q.explanation "
        "FROM quizzes q JOIN lessons l ON q.lesson_id=l.id "
        "WHERE l.level_id=3 ORDER BY l.order_index, q.id"
    ).fetchall()
    assert len(rows) == 50, "Level 2 应有 50 题，实际 %d" % len(rows)
    assert len(NEW_DISTRACTORS) == 50

    seed_data = json.load(open(SEED, encoding='utf-8'))
    seed_by_slug = {}  # slug -> list of question dicts (引用)
    for entry in seed_data.get('quizzes', []):
        seed_by_slug.setdefault(entry['lesson_slug'], []).extend(entry['questions'])
    seed_pointer = {}  # slug -> index

    updated = 0
    for idx, (qid, slug, prompt, opts_json, cc, exp) in enumerate(rows):
        old_opts = json.loads(opts_json)
        correct = old_opts[cc]  # 保留原正确答案文本（与解析一致）
        distractors = NEW_DISTRACTORS[idx]
        assert len(distractors) == 3

        p = idx % 4  # 打散正确项位置：A/B/C/D 轮流，各约 12-13 次
        new_opts = list(distractors)
        new_opts.insert(p, correct)
        assert len(new_opts) == 4 and new_opts[p] == correct

        c.execute("UPDATE quizzes SET options=?, correct_index=? WHERE id=?",
                  (json.dumps(new_opts, ensure_ascii=False), p, qid))

        # 同步种子 JSON（按 slug + prompt 定位）
        qs_list = seed_by_slug.get(slug, [])
        ptr = seed_pointer.get(slug, 0)
        # 找到 prompt 匹配且尚未处理的
        target = None
        for k in range(ptr, len(qs_list)):
            if qs_list[k]['prompt'] == prompt:
                target = k
                break
        if target is None:
            # 退而求其次：按顺序取下一个未匹配的
            target = ptr
        seed_pointer[slug] = target + 1
        qobj = qs_list[target]
        qobj['options'] = new_opts
        qobj['correct_index'] = p
        updated += 1

    c.commit()
    json.dump(seed_data, open(SEED, 'w', encoding='utf-8'),
              ensure_ascii=False, indent=2)

    # 校验
    dist = {}
    for (ci,) in c.execute(
        "SELECT q.correct_index FROM quizzes q JOIN lessons l ON q.lesson_id=l.id "
        "WHERE l.level_id=3"):
        dist[ci] = dist.get(ci, 0) + 1
    print("已更新 %d 题。correct_index 分布(0=A,1=B,2=C,3=D): %s"
          % (updated, dict(sorted(dist.items()))))

if __name__ == '__main__':
    main()
