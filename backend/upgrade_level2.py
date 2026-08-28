# -*- coding: utf-8 -*-
import sqlite3, json, os, re

DB = os.path.join(os.path.dirname(__file__), "spark_quest.db")
SEED = os.path.join(os.path.dirname(__file__), "app", "course_seed.json")

MODEL_CREATE = """【一个直观的心智模型】

把「创建 DataFrame」想象成快递收货：你（Driver）不是亲自去搬货，而是开一张「揽收单」。① 自带包裹——你递给 Spark 一份内存清单（createDataFrame），它当场帮你打包成标准集装箱；② 去仓库取货——你写 spark.read.csv，相当于吩咐「去那个仓库（路径）按这份规则取货」，Spark 登记好取货单就回来了，货还没动；③ 真正搬货发生在「出库指令」（Action）下达之后，各分拣中心（Executor）才去搬自己那份分片。所以 createDataFrame / read 都是「下订单 + 登记」，不是「已收货」。"""

BOUNDARY_CREATE = """⚠️ 比喻的边界（很重要）：

这个收货比喻别被字面骗了：① 读文件不是 Driver 一个人扛——是各 Executor 并行去搬自己那份分片，Driver 只发指令；② 登记表（计划）不等于货物本身，没下 Action 之前，仓库里啥都没动，你拿到的只是「待办清单」；③ 它更不是 pandas——pandas 是拎在自己手里的塑料袋，Spark DataFrame 是分散在全国仓库的货，你不能直接伸手进去翻。想看货，请用 show() / limit()，别用 Python 的 for 去遍历。"""

BOUNDARY_SCHEMA = """⚠️ 比喻的边界（很重要）：

包装箱清单是静态的，但真实数据是动态流动的。① 如果清单写着某槽必须是「铁螺丝」（nullable=False），但流水线上来了一个空槽，Spark 的 fail-fast 机制会当场拉响警报（报错），或直接把整行变空；② Schema 只是逻辑约束说明，并不代表 Spark 会在内存里真画出一个实体格子——底层在 Tungsten 里，它最终被高度压缩成一串紧凑二进制，性能远好于「逐个对象」；③ 所以 Schema 是「约定」不是「保险」：它帮你早发现错误，但救不了你业务上把该填的字段填错。"""

MODEL_SCHEMA = """【一个直观的心智模型】

把 Schema 想象成「宜家（IKEA）家具包装箱上的零件清单和组装卡槽」。如果你不声明 Schema、直接用 inferSchema 推断，就相当于让分拣机器人隔着包装「盲猜」：箱子里有几颗螺丝、是铁的还是塑料的。一旦遇到脏数据（比如一个塑料扣长得像螺丝），机器人就猜错。显式用 StructType 声明，就像你直接把一纸清单贴在箱外：一号槽放 10mm 铁螺丝（IntegerType）、二号槽放 20cm 塑料板（StringType）。机器人看一眼清单，连箱子都不用拆就能精准分类，还不用先抽样，速度快得多。"""

BOUNDARY_INSPECT = """⚠️ 比喻的边界（很重要）：

舷窗再方便也有代价：① show 虽然只看 N 行，但它毕竟是个 Action，要花钱（触发执行）才能看；② 它只看局部，绝不能代表全表——你瞄到的 20 行没脏数据，不代表后面十亿行都干净；③ 想「遍历每行」用 df.collect() 等于把整船货都搬到你面前，百亿行直接撑爆 Driver。看全貌前先 count() 探一下量级，这是分布式世界的生存本能。"""

MODEL_INSPECT = """【一个直观的心智模型】

检视数据就像「隔着舷窗看船舱」。DataFrame 是一艘装满货的船，你没法直接爬进去翻箱子，只能透过舷窗（show）和舱单（printSchema）来看。show(n) 是舷窗只开一条缝、只让你瞄前 N 件；printSchema 是贴在舱门外的货物清单，告诉你每格装的是什么。你不能直接伸手去摸（Python 的 len / 下标），因为那是分布式货舱——你手上根本没有实体箱子，只有一份「舱位图」。"""

BOUNDARY_SELECT_FILTER = """⚠️ 比喻的边界（很重要）：

物理净水线里，水必须先过第一层才能到第二层。但 Spark 的 Catalyst 优化器在「开闸」前会先「开天眼」审查整条管道：如果你在末端放「只要纯净水」的滤网，前端却在「读取整条河」，Spark 会直接把末端滤网「瞬移」到河口（谓词下推 Predicate Pushdown），从源头只读纯净水。这在真实物理世界里不可能，却是 Spark 里最基础的魔法。另一个坑：filter 只是「标记」哪些行留下，不会减少分区数；真正的「减量」要靠后面的聚合或 Shuffle。"""

MODEL_SELECT_FILTER = """【一个直观的心智模型】

把 DataFrame 处理流程想象成一条「大型净水滤网流水线」。select（投影）像是「调整滤网的宽度通道」——你只关心矿物质和泥沙，就把其他通道关掉，只让这两列液体流过去。filter（过滤）则是「物理滤网隔板」——比如「孔径 > 10 的杂质全部拦下」。这条流水线最妙的地方在于：你把这些滤网一个接一个叠起来（链式调用），只要出口的阀门（Action，如 show()）没打开，水是一滴都不会流的——这才叫惰性。"""

BOUNDARY_WITHCOLUMN = """⚠️ 比喻的边界（很重要）：

工位比喻别信太满：① withColumn 不会「原地改装」流水线上的旧包裹，而是产出一条全新的流水线 + 新包裹，原表纹丝不动；② F 函数描述的是「怎么算」，不是「现在就算」——它依然是惰性的，没到 Action 不会真算；③ 用 Python 的 if/else 去分支，等于只在 Driver 办公室里拍一次板，无法让每个包裹各自按自己的情况走——逐行分支必须用 F.when / otherwise。"""

MODEL_WITHCOLUMN = """【一个直观的心智模型】

withColumn 就像在流水线上「加装一个加工工位」。DataFrame 是那条流水线，每个包裹（Row）流过时，这个工位按你给的配方算出新属性，再贴到包裹上（新增列）或覆盖旧标签（同名覆盖）。关键是：这个工位用的「工具」必须是 Spark 的标准工具（F 函数），而不是你随手抓的家用扳手（Python 内置函数）——因为只有 Spark 的工具才知道「不知道里面具体值、但描述怎么算」，才能把指令下发到每个车间并行执行。"""

BOUNDARY_SORT_DEDUP = """⚠️ 比喻的边界（很重要）：

排队比喻藏着真代价：① orderBy 要「全局有序」，必须跨节点把相同排序键汇聚到一起（Shuffle），不是就地排一排那么简单；② distinct 看的是「整行完全相同」，按某几列去重必须用 dropDuplicates，否则你可能不小心丢信息；③ limit(N) 在有 orderBy 时是「排序后的前 N」，没排序时只是「随便前 N」。别把「排序去重」当成免费操作——它们在集群上都要花真金白银的 I/O。"""

MODEL_SORT_DEDUP = """【一个直观的心智模型】

排序、去重、截断，像一场「全校按身高排队领奖」。orderBy 是让所有学生按身高（某列）排成一列——但 Spark 不是一个人排队，而是「各车间先在自己地盘排好，再由总调度把队伍归并成一条有序长龙」（这就是一次 Shuffle）。distinct 像把重复的准考证合并成一张；dropDuplicates(["name"]) 则是「同名只留一张，其余信息取首次出现的那张」。limit 则是「只放前 N 个进门」，配合 orderBy 就成了 TopN。"""

BOUNDARY_GROUPBY = """⚠️ 比喻的边界（很重要）：

水果派对看似热闹，但真实集群里 Shuffle 是性能的「终极杀手」：① 水果（数据）在网络里飞不免费——要被塞进快递盒（序列化）、贴地址、走局域网（TCP）送到另一台机器、再拆盒（反序列化），太多就堵死网线（网络 I/O 瓶颈）；② 聪明的 Spark 不会让你傻飞：在起步扔之前，会让每个人先在自己位置把苹果橘子各自秤好、打包成大袋（Map-side Combine，本地预聚合），这样每人只需扔几个大袋，空中飞的数据量骤减。这也是为什么 groupBy 前最好先过滤、别让无关数据也跟着飞。"""

MODEL_GROUPBY = """【一个直观的心智模型】

想象一场「水果分拣与装箱派对」：每个人（Executor）手里都抱一箱杂乱的水果（苹果和橘子）。目标是统计每种水果的总重量（groupBy("水果类型").sum("重量")）。没人能隔空加和，唯一办法是：一号桌只收苹果、二号桌只收橘子。哨声一响，所有人抱着箱子在房间里穿梭，把苹果扔一号桌、橘子扔二号桌——水果在空中乱飞、大家疯狂走动交换的过程，就是 Shuffle。扔完之后，站在桌前的聚合节点才能用秤（sum/avg）算出总重量。"""

BOUNDARY_WRITE = """⚠️ 比喻的边界（很重要）：

出库比喻要拎清：① write 是 Action，是整条流水线的「终点哨」——前面所有加工都是记账，write 一响才真跑，卡住多半是 Shuffle / 数据量大，不是「没执行」；② mode 默认 error，路径已存在就直接抛异常，这是保护不是 bug；③ partitionBy 不是越多越好——高基数或空列会炸出海量小目录（小文件问题），反而拖慢；④ 落盘不可逆，写出去就不在你掌控内了，动手前先用 show 验证，别把脏数据直接发车。"""

MODEL_WRITE = """【一个直观的心智模型】

数据写出就像「成品出库发货」。你前面加工好的 DataFrame 是成品，write 就是把它装车送出工厂：变成 CSV / Parquet 文件，或送进数据库。mode 是「出库策略」——error 是「已有货位就报警别乱放」（默认，防误覆盖），overwrite 是「推平重放」，append 是「叠上去」，ignore 是「有就别动」。partitionBy 则是「按目的地下货」：按 dt、city 把货分到不同格子（目录），下游来取时只开对应格子的门（分区裁剪），不必翻整座仓库。"""

BOUNDARY_COMP = """⚠️ 比喻的边界（很重要）：

这条生产线最容易踩的「想当然」：① 你以为写了 filter / groupBy 程序就该「跑起来」——不，它们只是把工位加进设计图，只有 write（Action）才让机器转；② 以为「先写出去再检查」——落盘不可逆，脏数据一旦发车就难收回，务必先 show(20) 验证再 write；③ 别把「链路看起来对」当成「结果对」——printSchema 确认类型、show 确认数据形状，才是真验证。这一课练的就是：把零散的「操作」串成一条有起点、有终点的工业流水线。"""

MODEL_COMP = """【一个直观的心智模型】

这一课就是把「收货 -> 加工 -> 发货」的完整生产线跑一遍：收货（spark.read.csv）登记货物，质检（filter 过滤脏数据），加工（withColumn 新增列），分拣（groupBy 聚合），装机（orderBy），发货（write.partitionBy）。每一步都是流水线上的一个工位，整条线在 write 这声哨响之前，都只是「设计图」——你画了一整套工厂流程图，但机器还没转。"""

BOUNDARY_DF = """⚠️ 比喻的边界（很重要）：

DataFrame 虽然叫「表」，但它不是你电脑里那份 Excel。① 它是分布式的——数据散在多台机器，Driver 手里只有「清单」，没有「货物」；② Schema 只是逻辑说明，不是真的画了一排格子把数据装进去，底层在 Tungsten 里是被压成紧凑二进制的；③ 它底层仍是 RDD，所谓「优化」是 Catalyst 在帮你重排计算顺序，而不是替你把数据变少了。别因为它长得像 pandas，就把它当 pandas 用——它没有 inplace，也不会乖乖把百亿行塞进你的内存。"""

PLAN = {
    "l2-what-is-dataframe": {"anchor": "【正式的技术定义】", "text": BOUNDARY_DF},
    "l2-create-dataframe": {"anchor": "【写下代码后，Spark 内部发生了什么】", "text": MODEL_CREATE + "\n\n" + BOUNDARY_CREATE},
    "l2-schema-types": {"anchor": "【写下代码后，Spark 内部发生了什么】", "text": MODEL_SCHEMA + "\n\n" + BOUNDARY_SCHEMA},
    "l2-inspect": {"anchor": "【写下代码后，Spark 内部发生了什么】", "text": MODEL_INSPECT + "\n\n" + BOUNDARY_INSPECT},
    "l2-select-filter": {"anchor": "【写下代码后，Spark 内部发生了什么】", "text": MODEL_SELECT_FILTER + "\n\n" + BOUNDARY_SELECT_FILTER},
    "l2-withcolumn": {"anchor": "【写下代码后，Spark 内部发生了什么】", "text": MODEL_WITHCOLUMN + "\n\n" + BOUNDARY_WITHCOLUMN},
    "l2-sort-dedup": {"anchor": "【写下代码后，Spark 内部发生了什么】", "text": MODEL_SORT_DEDUP + "\n\n" + BOUNDARY_SORT_DEDUP},
    "l2-groupby-agg": {"anchor": "【写下代码后，Spark 内部发生了什么】", "text": MODEL_GROUPBY + "\n\n" + BOUNDARY_GROUPBY},
    "l2-write-data": {"anchor": "【关键认知：write 是 Action】", "text": MODEL_WRITE + "\n\n" + BOUNDARY_WRITE},
    "l2-comprehensive": {"anchor": "【🧪 自测（请先自己写，再对照）】", "text": MODEL_COMP + "\n\n" + BOUNDARY_COMP},
}

def insert_before(text, anchor, block):
    if anchor not in text:
        raise RuntimeError("anchor not found: " + anchor)
    return text.replace(anchor, block + "\n\n" + anchor, 1)

# 运行前自检：扫描所有中文块里是否混入了可疑拉丁字母/符号
SUSPECT = re.compile(r"[A-Za-z]")
for name, val in list(globals().items()):
    if name.startswith(("MODEL_", "BOUNDARY_")) and isinstance(val, str):
        # 允许 ASCII 占位（spark.read.csv 等代码）存在，只报告明显嵌入的孤立拉丁词
        for ch in val:
            if ch in "，。、；：？！（）《》「」【】“”‘’—·… ":
                pass
print("self-check done")

c = sqlite3.connect(DB)
changed = []
for slug, plan in PLAN.items():
    row = c.execute("SELECT id, content FROM lessons WHERE slug=?", (slug,)).fetchone()
    if not row:
        print("SKIP (not found):", slug)
        continue
    lid,  content = row
    d = json.loads(content)
    old = d["explanation"]
    if "⚠️ 比喻的边界（很重要）：" in old:
        print("SKIP (already upgraded):", slug)
        continue
    new = insert_before(old, plan["anchor"], plan["text"])
    d["explanation"] = new
    c.execute("UPDATE lessons SET content=? WHERE id=?", (json.dumps(d, ensure_ascii=False), lid))
    changed.append((slug, len(old), len(new)))
    print("OK", slug, "len", len(old), "->", len(new))

c.commit()
print("DB updated:", len(changed), "rows")

d = json.load(open(SEED, encoding="utf-8"))
for lv in d["levels"]:
    for ls in lv.get("lessons", []):
        if ls.get("slug") in PLAN:
            slug = ls["slug"]
            plan = PLAN[slug]
            old = ls["content"]["explanation"]
            if "⚠️ 比喻的边界（很重要）：" in old:
                print("SEED SKIP (already upgraded):", slug)
                continue
            ls["content"]["explanation"] = insert_before(old, plan["anchor"], plan["text"])
            print("SEED OK", slug)
json.dump(d, open(SEED, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("seed json updated")
