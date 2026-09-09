"""Level 4 「上一课回顾 / 本课要解决的问题 / 下一课伏笔」文案重写 2026-09-09

背景：这三段（content.review / problem / preview）写得太像目录摘要——
L4 现在每段 60~110 字，而 Level 0 / 1 同字段是 review 140~280、problem 90~150、
preview 170~380 字。用户要求对齐 Level 0/1 的调性。

Level 0/1 的写法特征（本次照抄）：
1. review：先承接「我们已经知道了 X」→ 一个转折 → 抛出本课要解决的悬念；分段留白
2. problem：连续反问 + 结尾一句「理解了 X 你才能…」点明价值
3. preview：先总结本课收获 → 抛一个「很自然的追问」制造悬念 → 固定收尾「下一课：XXX」
   （Level 末课不含该行，改为收尾 + 🏁）
4. 全程第二人称「你」、口语化、允许共情与反问

比喻只复用《心智模型与比喻边界案例库》已登记道具，不新造：
导航路线单 / 概念图 vs 施工图 / 施工排程单 / 车间布局图 / 总工等价省工 /
焊成一体化机器 / 空中飞货 / 出货指令。

技术口径与 2026-09-09 修复后的课文保持一致（*(N) 是编号、broadcast join 例外、
formatted 需 3.0+、AQE 版本提示、UDF 依赖顺序等）。

用法：python rewrite_level4_narrative_20260909.py [--apply]   # 默认 dry-run
"""

import json
import shutil
import sqlite3
import sys

DB = "spark_quest.db"
LEVEL_ORDER_INDEX = 4

# (lesson_id, 标题关键字, review, problem, preview)
DATA = [
    (
        31,
        "为什么该看执行计划",
        "从 Level 0 到 Level 3，你已经能写出「跑得通、结果还对」的 Spark 程序了：RDD、"
        "Transformation、Action、DataFrame API、常用的聚合和连接，你都用过。\n\n"
        "但有个挺尴尬的事实：写了这么多代码，你其实一次都没真正「看见」过 Spark 内部是怎么算的。\n\n"
        "你知道有个叫 Catalyst 的「优化大脑」在背后替你改计划（谓词下推、列裁剪），"
        "可它到底改成了什么样？为什么看起来一模一样的两段聚合，别人跑 30 秒、你跑 5 分钟？\n\n"
        "这一课，我们先把灯打开。",
        "为什么「代码能跑出正确结果」和「代码跑得快」完全是两件事？当你怀疑一段聚合特别慢的时候，"
        "第一件该做的事是什么——凭感觉改代码，还是先去找证据？更重要的是：Spark 内部那份"
        "「打算怎么算」的方案，到底藏在哪儿、要怎么看出来？",
        "现在我们达成了一个共识：执行计划就是 Spark 出发前算好的那张「路线单」。"
        "遇到性能问题，第一件事是把它调出来看，而不是拍脑袋改代码。\n\n"
        "可等你真把 explain() 打印出来，多半会愣住：这一大坨缩进文本，一会儿叫 Logical、"
        "一会儿叫 Physical，中间还夹着 Analyzed、Optimized——它们到底是同一张图的四个名字，"
        "还是四张不同的图？\n\n"
        "为什么非得分这么多层？每一层各自管什么？\n\n"
        "下一课：逻辑计划 vs 物理计划。",
    ),
    (
        32,
        "逻辑计划 vs 物理计划",
        "上一课我们立了个规矩：遇到性能问题，先看执行计划，别急着改代码。\n\n"
        "可第一次把计划打印出来时，最扎眼的往往不是某个算子看不懂，而是——它为什么要分成好几段？"
        "Parsed、Analyzed、Optimized、Physical 四段堆在一起，看起来像同一张图被印了四遍。\n\n"
        "你可能还撞见过一件很气人的事：表名明明写错了，它却不在你敲回车的那一刻报错，"
        "非得等你运行、甚至等你 explain 才炸出来。\n\n"
        "这两件事，其实指向同一个答案。",
        "为什么执行计划非要分「逻辑」和「物理」两层？Parsed / Analyzed / Optimized / Physical "
        "这四段各自干了什么？为什么「表不存在」这种看着写代码时就该发现的错误，"
        "非要拖到 Analyzed 才报？",
        "现在我们手里有了四段结构：逻辑计划是「想做什么」，物理计划是「怎么用 Spark 算子做」，"
        "中间夹着 Analyzed（校验）和 Optimized（等价改写）两道工序。\n\n"
        "于是问题变得很实际：这四段不会自动摊在你面前，得你自己「调」出来。\n\n"
        "而 explain() 有好几种调法——默认只给你一截、有的能给你完整四段、"
        "还有一种缩进排得漂漂亮亮的树状版。它们分别怎么用？还有个更要紧的问题："
        "既然它把计划都打印了，会不会顺手把你 2TB 的数据也真算一遍？\n\n"
        "下一课：explain() 怎么用。",
    ),
    (
        33,
        "explain() 怎么用",
        "上一课我们拆开了四段结构，也接受了「逻辑是想做什么、物理是怎么做」这个设定。\n\n"
        "但那四段当时只是讲给你听的，你还没亲手调出来过。\n\n"
        "好消息是，Spark 把「看计划」做成了一个随手可得的动作：不用等作业跑完，"
        "不用盯着进度条等几分钟，一行代码就能把方案摊在你面前。\n\n"
        "坏消息是，这一行代码有好几种写法，输出的信息量差得很远。",
        "explain() 默认给你什么？想看完整的四段该用哪个档位？想要那种缩进整齐、"
        "一眼能看出先后关系的树状版，又要怎么调？还有个关键问题：既然它把计划都打印出来了，"
        "它会不会顺手把你的数据也真算一遍？",
        "现在你已经能把计划调出来了，而且知道 explain() 只是「偷看图纸」——它不会真的开工，"
        "你不必担心它把你那张 2TB 的表跑一遍。\n\n"
        "可当你真的盯着那一坨文本，新的问题马上来了：Scan、Filter、Project、Aggregate、Exchange "
        "这些名字，哪个是读数据、哪个是洗数据、哪个是在花钱？\n\n"
        "尤其是那个 Exchange——老手一看到它就皱眉，它到底意味着什么？\n\n"
        "下一课：怎么读执行计划文本。",
    ),
    (
        34,
        "怎么读执行计划文本",
        "上一课我们学会了几个档位，能把整张施工单摊在桌上。\n\n"
        "可第一次读的人几乎都卡在同一个地方：这些节点名单看都认识——Scan、Filter、Project——"
        "连起来却不知道数据是怎么流的；更别提那些 `*(1)` `*(2)` 的星号，"
        "和括号里标着的「行数：xxx」，看着像答案，其实全是猜的。\n\n"
        "这一课，我们一个一个认。",
        "Scan / Filter / Project / Aggregate / Exchange 分别代表什么动作？为什么老手说"
        "「看到 Exchange 就要警惕」——它背后到底发生了什么、贵在哪？那些带星号的 `*(N)` "
        "又是什么意思（提前提醒：它**不是**「融合了 N 个算子」，这个误解非常普遍）？"
        "还有计划里那些行数和字节数，能信吗？",
        "现在我们能认节点了：Scan 进货、Filter 筛、Project 挑列、Aggregate 聚、"
        "而 Exchange 就是那次「货在空中飞」的 Shuffle——看到它，基本就等于看到钱在飞。\n\n"
        "不过你大概也察觉到了一件事：Optimized 这一段，好像总比你写代码时想的要「聪明」。"
        "你明明是聚合之后才过滤的，它却好像把过滤提前了；你明明读了一整张宽表，"
        "它却只读了你真正要的那几列。\n\n"
        "这些「自作主张」的改写，是谁做的？一共做了哪几件？\n\n"
        "下一课：Catalyst 优化规则。",
    ),
    (
        35,
        "Catalyst 优化规则",
        "前面几课我们一直在读 Optimized 这一段，也隐约发现它和你的写法不太一样："
        "顺序被换过、列被裁过、常量被提前算掉了。\n\n"
        "干这些事的，就是 Catalyst——Spark 的「总工程师」。它不动你的结果，只动你的流程。\n\n"
        "但「优化」这个词特别容易被人误会成玄学：它到底能改哪些、不能改哪些？"
        "为什么有人兴冲冲地写了个 UDF 指望它帮忙优化，结果反而更慢？",
        "Catalyst 在 Optimized 段到底做了哪些「等价省工」的改写——谓词下推、列裁剪、常量折叠、"
        "null 传播，各自省在哪？为什么这些改写能保证结果不变（真的一直能保证吗）？"
        "以及最实际的一个问题：为什么包在 UDF 里的过滤条件，往往推不下去？",
        "现在我们知道了：在你写代码和 Spark 真正执行之间，Catalyst 会插进去一层「等价改写」——"
        "能提前过滤的提前、用不上的列不读、能先算的常量先算。\n\n"
        "可到这里为止，省的全是「少干活」。还有一类更快，不是少干，而是**换一种干法**："
        "把好几个相邻的工位焊成一台连轴转的机器，连中间的交接都省了。\n\n"
        "这种「焊起来」的加速，就藏在你已经见过的那些 `*(N)` 里。它到底怎么做到？"
        "为什么一遇到 Shuffle 就焊不下去了？\n\n"
        "下一课：WholeStageCodegen 与 Tungsten。",
    ),
    (
        36,
        "WholeStageCodegen 与 Tungsten",
        "上一课我们看 Catalyst 怎么「少干活」：提前过滤、裁掉不用的列、常量先算掉。\n\n"
        "但 Spark 的快，不只来自少干活，还有一个更狠的手段——**换一种干法**。\n\n"
        "你早就注意到计划里那些 `*(1)` `*(2)` 的星号了吧？前面我们一直说「先别管」，"
        "现在该揭晓了：它标记的是 Spark 把一整段算子流水线生成到同一份代码里、"
        "编译成一台连轴转的机器。\n\n"
        "顺带一句提醒：这个数字的含义，几乎每个人都猜错过。",
        "计划里的 `*(N)` 到底是什么编号？（提示：它**不是**「融合了 N 个算子」——"
        "这是个极其普遍的误解）为什么相邻的算子能被生成到同一段代码里，"
        "而一遇到 Shuffle 就断？断掉以后 Spark 又退回成什么样在执行？"
        "还有，Tungsten 和 WholeStageCodegen 到底是什么关系？",
        "现在我们知道了：WholeStageCodegen 会把一段能连续 codegen 的流水线焊成一台机器，"
        "而 Exchange（Shuffle）就是那把必然落下的铡刀——焊到这儿必须断，断开处就是 Stage 的边界。\n\n"
        "于是问题自然往前一步：为什么偏偏是 Shuffle 必须断开？为什么有些算子天生能和邻居"
        "待在同一个 Stage 里，有些却非得跨 Stage 不可？\n\n"
        "答案藏在一个更底层的概念里：依赖的类型。\n\n"
        "下一课：窄依赖 vs 宽依赖。",
    ),
    (
        37,
        "窄依赖 vs 宽依赖",
        "上一课我们看到，WholeStageCodegen 焊好的流水线一碰到 Exchange 就被切断，"
        "切出来的每一段，正好就是一个 Stage。\n\n"
        "可为什么偏偏在这里切？总得有个更根本的理由，而不是「Spark 就是这么写的」。\n\n"
        "这个理由就是依赖类型：有的算子，每个分区只靠自己那份数据就能算完；"
        "有的算子，必须先把所有分区里同 key 的货凑到一起才能开工。"
        "前者在车间内部就能解决，后者只能把货抛到空中、运去别人的车间。",
        "窄依赖和宽依赖到底差在哪？为什么宽依赖天然就是 Stage 的「断点」？"
        "这两种依赖在失败恢复时的代价差多少？map / filter / groupBy / join / orderBy 里，"
        "哪些是窄、哪些是宽——又有没有例外？",
        "现在我们手里有了判断 Stage 边界的尺子：宽依赖处必切一刀，"
        "因为那里必须等所有同 key 的货都到齐。\n\n"
        "那把视角往上抬一层：你点下运行之后，Spark 究竟是怎么把这件事组织起来的？"
        "你听过的 Job、Stage、Task 这三个词，到底谁是老大、谁包着谁？"
        "为什么大家都说 Task 数等于分区数，那 Stage 数又该怎么数？\n\n"
        "这一课，把三层模型一次讲清。\n\n"
        "下一课：Job / Stage / Task 层级。",
    ),
    (
        38,
        "Job / Stage / Task 层级",
        "上一课我们拿到了「宽依赖 = Stage 断点」这把尺子。\n\n"
        "可你迟早会在 Spark UI 上撞见另外两个词：Job 和 Task。它们和 Stage 到底是什么关系？"
        "为什么简简单单一次 show()，也能在 UI 上留下一串记录？\n\n"
        "更现实的问题是：当别人说「这个作业卡在 Stage 2 的第 37 个 Task」，"
        "你得立刻反应过来他在说哪一层。",
        "Job / Stage / Task 三层到底怎么对应？为什么通常一次 Action 就是一个 Job"
        "（什么时候不是）？Stage 为什么按宽依赖切、Task 又为什么按分区切？"
        "这三层里，谁和谁必须排队、谁和谁可以同时开工？",
        "现在三层模型齐了：Action 触发 Job，宽依赖把 Job 切成 Stage，"
        "每个 Stage 再按分区切成一堆并行跑的 Task。你已经能从 UI 上的任何一个数字，"
        "反推出它属于哪一层。\n\n"
        "但「看得懂」和「真的会看」之间，还差一次不看答案的独立读图。\n\n"
        "给你一段真实代码，你能自己把它的计划读出来、数出 Stage、认出 Shuffle、"
        "指出至少一处优化吗？\n\n"
        "下一课：综合练习。",
    ),
    (
        39,
        "综合练习",
        "Level 4 的零件，到这里全齐了：\n\n"
        "· 为什么该看执行计划——它是诊断性能的第一视角；\n"
        "· 逻辑计划 vs 物理计划——四段各管什么；\n"
        "· explain() 怎么用——几档输出、惰性窥视；\n"
        "· 怎么读执行计划文本——认节点、认 Exchange、读对 `*(N)`；\n"
        "· Catalyst 优化规则——下推 / 裁剪 / 折叠的等价省工；\n"
        "· WholeStageCodegen 与 Tungsten——把流水线焊成一台机器；\n"
        "· 窄依赖 vs 宽依赖——Stage 断点的根源；\n"
        "· Job / Stage / Task——三层模型。\n\n"
        "这些现在都还是「别人讲给你听的」。这一课，把它们变成你自己能独立读出来的东西。",
        "能不能不靠任何提示，独立给一段真实代码读出它的 explain() 输出——数出 Stage、"
        "认出 Shuffle、指出至少一处 Catalyst 优化？更重要的是，你能否用自己的话说清"
        "「它打算怎么算、哪里最花钱」？这正是检验你是否真正串起 Level 4 的标准。",
        "恭喜你走完 Level 4——你现在能「看见」Spark 内部怎么算、在哪儿优化、在哪儿花钱，"
        "不再是对着一个黑盒瞎猜。\n\n"
        "但一个更实际的问题马上浮上来：既然你已经能看出「这里有一次 Shuffle」，"
        "那能不能让它少一次？能不能让并行度更合适、让拖后腿的那几个 Task 不再倾斜？\n\n"
        "看得出问题是第一步，**动手把它改快**是另一件事。\n\n"
        "那是 Level 5（分区 / Shuffle）的主场。去测验检验自己吧。🏁",
    ),
]


def main(apply: bool):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute(
        "select id, title, content from lessons "
        "where level_id = (select id from course_levels where order_index = ?) "
        "order by order_index",
        (LEVEL_ORDER_INDEX,),
    )
    rows = cur.fetchall()
    if len(rows) != 9:
        print(f"[ABORT] Level 4 课程数 = {len(rows)}，期望 9")
        return 1
    by_id = {r[0]: r for r in rows}

    for lid, kw, _, _, _ in DATA:
        if lid not in by_id:
            print(f"[ABORT] lesson id {lid} 不在 Level 4")
            return 1
        if kw not in by_id[lid][1]:
            print(f"[ABORT] lesson {lid} 标题「{by_id[lid][1]}」不含「{kw}」")
            return 1

    for lid, kw, review, problem, preview in DATA:
        content = json.loads(by_id[lid][2])
        for key in ("review", "problem", "preview"):
            if key not in content:
                print(f"[ABORT] lesson {lid} content 缺字段 {key}")
                return 1
        content["review"] = review
        content["problem"] = problem
        content["preview"] = preview
        print(
            f"[{lid}] {by_id[lid][1]}: review {len(review)}字 / "
            f"problem {len(problem)}字 / preview {len(preview)}字"
        )
        if apply:
            cur.execute(
                "update lessons set content=? where id=?",
                (json.dumps(content, ensure_ascii=False), lid),
            )

    if apply:
        conn.commit()
        print("\n已写入真库。")
    else:
        print("\ndry-run，未写入。加 --apply 执行。")
    conn.close()
    return 0


if __name__ == "__main__":
    if "--apply" in sys.argv:
        shutil.copy(DB, DB + ".bak_before_narrative_20260909")
        print("已备份:", DB + ".bak_before_narrative_20260909")
    sys.exit(main("--apply" in sys.argv))
