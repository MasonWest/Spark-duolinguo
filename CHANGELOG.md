# Changelog — Spark Quest

> 本文件回答：**系统是怎么一步步变成现在这样的？**
> 当前事实以同目录 `CURRENT_STATE.md` 为准；本文件只记录演进历史。
>
> 规则：每完成一个阶段，追加一个 `## YYYY-MM-DD` 段落，分 `Added / Changed / Fixed / Architecture` 小节。
> 后续增量更新只追加新条目，不要改写历史条目。

---

## 2026-08-28 — V1.0 基线（当前版本起点）

本条目汇总自项目启动至 2026-08-28 的全部累计演进，作为第一份正式基线。
后续每次完成一个阶段，单独追加新日期条目即可。

### Added
- **项目骨架**：React 18 + Vite 5 + TypeScript 前端；FastAPI + Uvicorn + SQLAlchemy + SQLite 后端；端口 6001（前端）/ 9000（后端）
- **Phase 1 课程地图**：`course_levels` / `lessons` 表 + `/map` 页面
- **Phase 2 Dashboard / 今日任务**：`/api/dashboard` + 推荐首课 + 进度条
- **Phase 3 Lesson 学习页**：`/lesson/:id`；七要素 `content`（explanation / examples / key_points / common_mistakes / review / problem / preview）
- **Phase 4 Lesson Mastery Quiz**：`quizzes` 表 + `lesson_mastery` 表；每课随机抽 5 题；掌握标准 ≥80% → `mastered`
- **Phase 5 统一派生学习状态**：`locked / available / mastered / needs_review` 由 `services.py` 统一计算，Dashboard / Map / Lesson 三处一致
- **Phase 6.1 Quiz Bank 扩充**：每课 10 题（共 210 题），`quizzes.dimension` 开放维度标签，`_sample_quiz_questions` 优先维度多样抽 5 题
- **Phase 6.2 Level 2 题库**：Level 2（DataFrame 核心，10 课）每课补齐至 10 题
- **课程内容**：Level 0（5 课）+ Level 1（6 课）+ Level 2（10 课）共 21 课，含【心智模型】+ ⚠️ 比喻边界
- **Lesson Notes**：`lesson_notes` 表 + `GET/POST/DELETE /api/lessons/{id}/notes`，append-only，前端 Lesson 页接入（草稿/保存/删除/时间显示）

### Changed
- 课程解锁规则：仅第一关第一课 `available`，其余前驱 `mastered` 才 `available`（Phase 5 前均为占位 `locked`）
- Mastery 状态改为纯派生（不再硬编码于 Lesson 行）
- 抽题逻辑：固定 4 题 → 题库 10 题随机抽 5 题、优先维度多样
- 概念解释排版增强：`RichText` 组件支持小节标题（`【】`）/ 行内 `code` / `**加粗**` / `⚠️` 警示块 / 有序·无序列表

### Fixed
- `RichText` 中 `·` 列举在「单换行混排」场景下的渲染修复（2026-08-28）
- 历史 bug：LessonOut 缺 `order_index`（地图 NaN）、`index.css` 颜色覆盖、后端 `attempts None+1`、uvicorn 陈旧字节码等（详见 `CURRENT_STATE.md` 关键约定与坑位）

### Architecture
- **学习状态模型冻结**：Dashboard / Course Map / Lesson 共用 `services.py` 派生逻辑，杜绝三套状态互不一致
- **不新增 learning state、不新增 progress 字段、不新增冗余表**；能派生的状态绝不存储
- 单用户本地应用：无登录鉴权、无用户系统
- 明确不引入：Alembic / Redis / Docker / AI
- 课程内容数据化：文本存于 `lessons.content`（JSON 文本列），React 端零硬编码课程文本

---

## 2026-08-28 — Level 3：Spark SQL（V1.0 基线之后增量）

V1.0 基线建立后，按用户确认的新路线图落地 Level 3（9 课），设计上严格不抢跑 L4–L7。

### Added
- **Level 3：Spark SQL**（9 课，order_index=3）：`l3-what-is-spark-sql` / `l3-temp-views` / `l3-select-basics` / `l3-where-order-limit` / `l3-groupby-having` / `l3-joins-intro` / `l3-functions-and-udf` / `l3-tables-and-formats` / `l3-comprehensive`
- 每课 10 题，共 90 题，全 `single_choice` + 开放 `dimension`（concept/why/mechanism/apply/comparison/debug）+ `explanation`
- 每课 explanation 含 v1.0 五固定小节（【先用人话理解】/【一个直观的心智模型】/⚠️ 比喻的边界（很重要）：/【正式的技术定义】/【写下代码后，Spark 内部发生了什么】）
- 课程总量升至 30 课（L0 5 + L1 6 + L2 10 + L3 9），题库 300 题

### Changed
- 课程结构：新增 Level 3 节点；JOIN 仅做轻量 INNER 入门，深类型/broadcast/调优显式留给 Level 6；UDF 点出"慢"作为 Level 7 伏笔；明确不接 Hive Metastore
- 种子机制：`seed_level3.py` 将 JSON 合并与 DB upsert 合二为一（此前 Level 2 用 `seed_level2.py` + `expand_quizzes_to_10.py` 分体），仍保持幂等且不动 L0–L2 与 lesson_mastery 进度

### Fixed
- l3-comprehensive 的 explanation 原本缺 3 个 v1.0 固定小节（含"先人话理解"笔误），已补回五小节并同步 DB / JSON / 源脚本
- 心智模型案例库 slug 不一致：`l2-sort-dedup-limit` / `l2-inspect-data` 校正为种子实际 slug `l2-sort-dedup` / `l2-inspect`

### Architecture
- 延续"不抢跑"原则：SQL 与 DataFrame API 共享同一 Catalyst 优化大脑，每课尽量与 Level 2 等价操作配对，避免重复造概念
- 复用 v1.0 道具表（Catalyst=同一套优化大脑；临时视图=仓库门口临时工牌），新隐喻登记入案例库

---

## 2026-08-28 — Level 4：执行计划（V1.0 基线之后增量）

V1.0 基线 + Level 3 之后，按设计稿 `Spark_Quest_Level4_执行计划_设计.md` 落地 Level 4（9 课），只教「怎么看懂 Spark 怎么算」，不抢跑 L5–L7 调优。

### Added
- **Level 4：执行计划**（9 课，order_index=4）：`l4-why-explain` / `l4-logical-vs-physical` / `l4-explain-api` / `l4-read-plan` / `l4-catalyst-rules` / `l4-wholestage-codegen` / `l4-dependency-narrow-wide` / `l4-job-stage-task` / `l4-comprehensive`
- 每课 10 题，共 90 题，全 `single_choice` + 开放 `dimension`（concept/why/mechanism/apply/comparison + 部分 debug）+ `explanation`
- 每课 explanation 含 v1.0 五固定小节（【先用人话理解】/【一个直观的心智模型】/⚠️ 比喻的边界（很重要）：/【正式的技术定义】/【写下代码后，Spark 内部发生了什么】）
- 课程总量升至 39 课（L0 5 + L1 6 + L2 10 + L3 9 + L4 9），题库 390 题
- 新脚本 `backend/seed_level4.py`（一次性幂等 upsert，JSON 合并 + DB upsert 一体，沿用 `seed_level3.py` 模式）

### Changed
- 课程结构：新增 Level 4 节点；红线不展开 Shuffle/分区调优（L5）、JOIN 策略（L6）、Tungsten 内存细节（L7）；综合练习只验收「读得懂」，不要求调优
- 案例库：全局道具表补 4 行（设计师概念图 vs 施工图 / Stage / WholeStageCodegen / Job→Stage→Task），新增「## 5. Spark 执行计划（Level 4）」章节，原使用约定/待升级章节顺延为 ## 6 / ## 7

### Fixed
- 落库前修正了两处 Quiz JSON 结构笔误（options 内误植 correct_index/explanation），已通过语法 + 数据合规校验（每课 10 题、七要素、五小节、correct_index∈[0,3]、dimension 覆盖五类）

### Architecture
- 延续「不抢跑」原则：复用 Catalyst=优化大脑、Shuffle=空中飞货、Driver=前台、Executor=工人 等已登记道具，避免重造概念
- 复用 v1.0 道具表，Level 4 新隐喻（概念图/施工图、Stage、WholeStageCodegen、Job→Stage→Task）登记入案例库

---

## 2026-08-28 — Level 5：分区与 Shuffle（V1.0 基线之后增量）

V1.0 基线 + Level 3 + Level 4 之后，按设计稿 `Spark_Quest_Level5_执行计划_设计.md` 落地 Level 5（9 课），只教「数据怎么被切分、又在什么情况下被搬来搬去（Shuffle）及其代价」，不抢跑 L6–L7 调优。

### Added
- **Level 5：分区与 Shuffle**（9 课，order_index=5）：`l5-what-is-partition` / `l5-partition-count-parallelism` / `l5-what-is-shuffle` / `l5-shuffle-cost` / `l5-narrow-wide-partition` / `l5-shuffle-trigger-operators` / `l5-reducebykey-vs-groupbykey` / `l5-repartition-coalesce` / `l5-comprehensive`
- 每课 10 题，共 90 题，全 `single_choice` + 开放 `dimension`（concept/why/mechanism/apply/comparison）+ `explanation`
- 每课 explanation 含 v1.0 五固定小节（【先用人话理解】/【一个直观的心智模型】/⚠️ 比喻的边界（很重要）：/【正式的技术定义】/【写下代码后，Spark 内部发生了什么】；综合练习亦含五小节）
- 课程总量升至 48 课（L0 5 + L1 6 + L2 10 + L3 9 + L4 9 + L5 9），题库 480 题
- 新脚本 `backend/seed_level5.py`（一次性幂等 upsert，JSON 合并 + DB upsert 一体，沿用 `seed_level4.py` 模式）

### Changed
- 课程结构：新增 Level 5 节点；红线不展开 JOIN 策略深类型（L6）、Tungsten 内存细节（L7）、具体调优参数/最优分区数（L7）；综合练习只验收「读得懂」，不要求调优
- 案例库：全局道具表补 5 行（托盘/货盘、工人数量上限=托盘数、装箱→装车→卸货分拣、车间本地先捆小包再空运、推倒重排 vs 就地并拢），新增「## 6. Spark 分区与 Shuffle（Level 5）」章节，原使用约定/待升级章节顺延为 ## 7 / ## 8

### Fixed
- 收尾核验按 `Spark_Quest_新增Level_收尾核验踩坑.md` §5 参数化脚本（ORDER_INDEX=5, PREFIX="l5-"）跑通：连真库 `backend/spark_quest.db`（非 `app/sparkquest.db`）、`quizzes` 用 `lesson_id` 关联、聚合结构、`content` 用实现态七键——全绿；lesson_mastery 进度未动（18）

### Architecture
- 延续「不抢跑」原则：复用 Catalyst=优化大脑、Shuffle=空中飞货、Driver=前台、Executor=工人、Stage=不跨车间工序段、Job→Stage→Task 等已登记道具；把 L4 窄/宽依赖定义延展到分区物化层面
- 复用 v1.0 道具表，Level 5 新隐喻（托盘/货盘、装箱→装车→卸货分拣、本地先捆包再空运、推倒重排 vs 就地并拢）登记入案例库

---

## 2026-08-29 — Level 6：JOIN 深类型与 Broadcast（V1.0 基线之后增量）

按设计稿 `Spark_Quest_Level6_执行计划_设计.md` 落地 Level 6（9 课），把 L3「JOIN 必 Shuffle、深类型留 L6」、L4 的 `BroadcastHashJoin`/`SortMergeJoin` 计划标记、L5「Shuffle 代价 / 空中飞货」全部延展到 JOIN 策略层面。

### Added
- **Level 6：JOIN 深类型与 Broadcast**（9 课，order_index=6）：`l6-what-is-join` / `l6-join-strategies-overview` / `l6-broadcast-hash-join` / `l6-sort-merge-join` / `l6-shuffle-hash-join` / `l6-how-spark-chooses` / `l6-broadcast-hint-and-control` / `l6-join-data-skew` / `l6-comprehensive`
- 每课 10 题，共 90 题，全 `single_choice` + `dimension` 五类（concept/why/mechanism/apply/comparison）各 2 题 + `explanation`；`correct_index` 在四个选项位上均匀打散（避免学员按位置猜答案）
- 每课 explanation 含 v1.0 五固定小节（含综合练习课 `l6-comprehensive`），examples 三件套、common_mistakes 三件套齐全
- 课程总量升至 57 课（L0 5 + L1 6 + L2 10 + L3 9 + L4 9 + L5 9 + L6 9），题库 570 题
- 新脚本 `backend/seed_level6.py`（复制 `seed_level5.py` 模式，一次性幂等 upsert）

### Changed
- 课程结构：新增 Level 6 节点；`CURRENT_STATE.md` 总体状态表 Phase 8 行改为「Level 2/3/4/5/6 已落地；Level 7 规划中」，数据量 6→7 levels / 48→57 lessons / 480→570 quizzes
- 案例库：全局道具表补 5 行（小册子复印 N 份=BHJ、两本按 key 排序的电话簿逐页对照=SMJ、抽屉柜流式查=SHJ、Catalyst 看两桌人数决定拼法=策略自动选择、某把椅子挤满 90% 的人=数据倾斜），新增「## 7. Spark JOIN 深类型（Level 6）」章节，原使用约定/待升级章节顺延为 ## 8 / ## 9

### RedLines（未抢跑 L7）
- 不展开 Tungsten 内存管理 / 堆外 / 编码字节级细节
- 不展开 shuffle 分区数最优值与深调优参数；广播阈值只讲概念（不给数值与调优）
- skew 只到「识别 + 原理级应对」（salting 加盐 / 隔离大 key / BHJ 绕过），不写 `skewJoin` 类开关
- 不重复 L3 INNER 语法、L4 explain 读法、L5 Shuffle 定义与代价

### Fixed
- 收尾核验按 `Spark_Quest_新增Level_收尾核验踩坑.md` §5 参数化脚本（ORDER_INDEX=6, PREFIX="l6-"）跑通：连真库 `backend/spark_quest.db`、`quizzes` 用 `lesson_id` 关联、`quiz_seed.json` 聚合结构、`content` 用实现态七键——全绿；`lesson_mastery` 总数未变（18）、新 Level 引用 = 0；L0–L5 课数未变
- 落库前备份 `spark_quest.db` / `course_seed.json` / `quiz_seed.json`（`*.bak_before_l6`）

### Architecture
- 延续「不抢跑」原则：复用 Catalyst=优化大脑、Shuffle=空中飞货、Driver=前台、Executor=工人、JOIN=两拨货按 key 拼桌、托盘=分区、Stage=不跨车间工序段等已登记道具
- 心智模型严格复用案例库已登记道具，L6 新增 5 个隐喻全部登记入案例库

---

## 2026-08-29 — Level 7：性能调优（V1.0 基线之后增量 · Phase 8 课程主线收官）

按设计稿 `Spark_Quest_Level7_执行计划_设计.md` 落地 Level 7（9 课），把 L3 埋下的 UDF 慢、L4 的 Tungsten/WholeStageCodegen 内存细节、L5 的 shuffle 分区数与 spill、L6 的广播阈值与 skew 深调优全部收口到一套调优方法论。**至此 Phase 8 课程主线（Level 0–7）全部完成。**

### Added
- **Level 7：性能调优**（9 课，order_index=7）：`l7-what-is-tuning` / `l7-tungsten-encoding` / `l7-executor-memory` / `l7-shuffle-partitions` / `l7-broadcast-threshold` / `l7-aqe` / `l7-skew-tuning` / `l7-read-less-data` / `l7-comprehensive`
- 每课 10 题，共 90 题，全 `single_choice` + `dimension` 五类（concept/why/mechanism/apply/comparison）各 2 题 + `explanation`；`correct_index` 在四个选项位上均匀打散
- 每课 explanation 含 v1.0 五固定小节（含综合练习课 `l7-comprehensive`），examples 三件套、common_mistakes 三件套齐全
- 课程总量升至 66 课（L0 5 + L1 6 + L2 10 + L3 9 + L4 9 + L5 9 + L6 9 + L7 9），题库 660 题
- 新脚本 `backend/seed_level7.py`（复制 `seed_level6.py` 模式，一次性幂等 upsert）

### Changed
- 课程结构：新增 Level 7 节点；`CURRENT_STATE.md` 总体状态表 Phase 8 行改为「Level 2/3/4/5/6/7 已全部落地——课程主线完成」，数据量 7→8 levels / 57→66 lessons / 570→660 quizzes
- 案例库：全局道具表补 7 行（木桶/最慢工序、真空压缩袋、货车车厢四格、车道数与车流、秤的刻度、会实时改路的导航、交警堵点分流），新增「## 8. 性能调优（Level 7）」章节，原使用约定/待升级章节顺延为 ## 9 / ## 10

### RedLines（不越界）
- 不讲集群资源调度层（YARN/K8s 队列、动态资源分配），不展开 GC 调优
- 不给万能最优参数值：所有旋钮只给「起点思路 + 取舍 + 实测收敛」
- 不重复 L4 explain 读法、L5 Shuffle 定义与代价、L6 JOIN 策略框架
- 不引入外部监控体系（只讲 Spark UI 与 explain）

### Fixed
- 收尾核验按 `Spark_Quest_新增Level_收尾核验踩坑.md` §5 参数化脚本（ORDER_INDEX=7, PREFIX="l7-"）跑通：连真库 `backend/spark_quest.db`、`quizzes` 用 `lesson_id` 关联、`quiz_seed.json` 聚合结构、`content` 用实现态七键——全绿；`lesson_mastery` 总数未变（18）、新 Level 引用 = 0；L0–L6 课数未变（5/6/10/9/9/9/9）
- 题库首版答案位置又一次全挤在 B（同 L6 首版），已按「base 序列 + 课序偏移」重排为每课 2/3/2/3 分布
- 程序化改写 quiz 块时再次出现括号问题（`questions": [[` 重复开括号），已修正并 `py_compile` 复验——**该坑已第二次出现，见项目记忆**
- 落库前备份 `spark_quest.db` / `course_seed.json` / `quiz_seed.json`（`*.bak_before_l7`）

### Architecture
- 延续「不抢跑 / 不越界」原则：L7 只收口前面各 Level 明确留下的伏笔，不引入集群运维与 JVM 调优话题
- 心智模型严格复用案例库已有道具，L7 新增 7 个隐喻全部登记入案例库

---

## 2026-08-29 — Phase 6b：Lesson 级间隔复习闭环（V1.0 基线之后增量）

在 Phase 6.1/6.2 建成题库与维度标签之后，落地真正的间隔复习。范围由用户明确划定并严格执行，未做任何扩大。

### Added
- **复习调度内核**（`services.py`）：`REVIEW_INTERVALS_DAYS = [1, 3, 7, 14, 30, 60, 120]`、`REVIEW_FAIL_INTERVAL_DAYS = 3`、`REVIEW_QUESTION_COUNT = 5`；`is_due_for_review / due_lesson_ids / due_reviews / init_review_schedule / advance_review_schedule / defer_review_schedule`
- **三个接口**（`routers/review.py`）：`GET /api/review/due`、`GET /api/review/{lesson_id}`（抽 5 题、不泄露答案）、`POST /api/review/{lesson_id}/submit`（5/5 判过 + 重新调度）
- **复习页** `/review/:id`（`ReviewPage.tsx` + CSS）：第 n/5 题进度、5/5 闸门、通过态显示「下次复习 N 天后」、失败态提供「重新阅读本课」与「直接再挑战一次」
- **Dashboard「🔁 今日复习」区块**（Home.tsx）：列出到期课程 + Level + 逾期天数
- **课程地图「待复习」角标**（MapPage.tsx）：mastered 课到期时显示 🔁，图例同步补项
- **学习页复习入口**（LessonPage.tsx）：mastered 课加「间隔复习（5 题）」；`?from=review` 时顶部显示「先重读一遍，再挑战复习」提示条 + 「再次复习」
- **验收脚本** `backend/_p6b_e2e_check.py`：37 项端到端断言，跑在 DB 临时副本上，不污染真库
- **弱维度优先抽题**：复用 Phase 6.1 的 `_sample_quiz_questions`，新增可选 `priority_dims`（上一轮答错题目所属 dimension 优先访问），仅排序偏好，不建权重模型

### Changed
- `lesson_mastery` 扩展 5 列：`first_mastered_at / srs_stage / next_review_at / last_review_at / review_count`（幂等迁移 + 存量回填 18 条）
- `GET /api/dashboard` 新增 `reviews_due`；`GET /api/levels` 的 lesson 新增 `due_for_review`（纯视觉提示，非第 5 种状态）
- `submit_quiz` 在「首次转 mastered」时写入 `first_mastered_at` 等复习锚点（后续重测不再移动锚点）
- 共用样式 `.btn-ghost` 由 `QuizPage.css` 上提到 `index.css`（现 Quiz / Lesson / Review 三处使用）

### Fixed
- 无 bug 修复（本阶段为纯新增）。已规避的坑：`srs_stage` 不可由 `next_review_at` 反推（失败与「通过 stage0」的间隔都是 3 天，会撞车），必须独立存储；`first_mastered_at` 与 `last_quiz_at` 语义分离，不混用

### Architecture
- **不新增任何表**：复习调度信息全部落在既有 `lesson_mastery`；原规划的 `review_items` 表不建，`review_attempts` 历史日志不做
- **不新增第 5 种学习状态**：`locked / available / needs_review / mastered` 四状态体系原封不动，复习是 `mastered` 之上的附加调度信息；`due_for_review` 只是布尔提示
- **失败不降级**：复习失败只插入一次 3 天后的短期巩固，`srs_stage` 保持不变
- **「立即重做」与「下一次调度」解耦**：失败后 `next_review_at` 推到 3 天后，但取题接口只看是否 mastered，用户读完本课可立即再挑战
- **复习不污染学习态**：`/api/review/.../submit` 绝不改动 `status / score / attempts / last_quiz_at`，5 题复习得分不覆盖 10 题学习测验得分
- 明确不做：SM-2 / Anki 式 SRS、个性化遗忘曲线拟合、单题级 SRS、每 dimension 独立进度、复杂统计、连错智能教学、AI 动态出题

---

## 2026-08-29 — 题库质量修复：Level 0/1 干扰项重构 + 答案位置洗牌

用户复习 Level 0 时发现「所有题目答案都是 A，且最长的选项就是答案」。经全库诊断确认属实，且为系统性缺陷。**本轮按用户指定范围，只修复 Level 0 / Level 1（110 题），其余关卡未触碰。**

### Added
- 无新增功能

### Changed
- **干扰项重写**：Level 0/1 共 330 个干扰项全部重写。旧干扰项是随手编的短废话（如 `q62` 的「因为 Python 太慢 / 硬盘太大 / 网络太快」），新干扰项针对每道题的真实常见误解撰写，且长度与正确项相当
- **答案位置洗牌**：对 110 题做确定性置换，`A/B/C/D` 分布由 `A=75 / B=29 / C=4 / D=2` 变为 `A=28 / B=28 / C=27 / D=27`
- **seed 与 DB 同步更新**：`backend/app/quiz_seed.json` 与 `spark_quest.db` 同时改写，避免下次 re-seed 把缺陷带回来（已校验两者完全一致）

### Fixed
- **位置偏置**：Level 0/1 答案落在 A 的比例由 **74%** 降至 **25.5%**
- **「最长即答案」**：正确项是唯一最长选项的比例由 **92%** 降至 **30.0%**；同时反向指标「正确项唯一最短」控制在 **10.9%**，避免形成新的可预测规律
- 修复前已验证 0/110 题的解析引用选项字母或位置（此前全库扫描到的 9 条「第 N 个」全是误报：CSV 第一行、排查第一步、第一视角），故洗牌不会让任何解析失效
- `weak_points` 存的是 `question_id` 而非选项下标，洗牌不污染 P6b 任何已有复习数据

### Architecture
- **只改内容，不改逻辑**：四状态体系、复习调度、判分阈值（学习 80% / 复习 5/5）均未改动
- **严格限定范围**：Level 2–7 的 550 题保持原样（其 A 占比 48.7%、最长即答案 88.4% 的旧特征被保留，作为「未修复关卡」的对照基线）
- 回归验证：110 题按 DB 正确答案提交全部通过；抽样 15 题提交错误答案均不被判满分；P6b 复习闭环（取题 / 5-5 通过 / 4-5 失败 / 失败后立即可重做）全部复测通过
- 改动前自动备份：`spark_quest.db.*.bak_before_l01_fix`、`app/quiz_seed.json.*.bak_before_l01_fix`（已被 `.gitignore` 排除，不入库）

---

## 2026-09-04 — 修复：答题页与结果页题目顺序不一致

### Fixed
- **结果页顺序错位**（用户报障）：`POST /api/lessons/{id}/quiz/submit` 遍历的是**按 `order_index` 排序的全库题目**，而 `GET /api/lessons/{id}/quiz` 返回的是**随机抽样并打乱顺序**的 5 题。前端结果页直接按后端 `results` 顺序渲染，导致「做题时看到的第 3 题」与「结果页列出的第 3 题」不是同一题。
  - 修复：改为按 `payload.answers`（= 前端呈现顺序）遍历构造 `results`，结果列表与呈现顺序严格一致。
- **间隔复习同源缺陷**：`POST /api/review/{id}/submit` 存在完全相同的遍历顺序问题，一并修复。
- **重复 `question_id` 未收敛**：重复提交同一题时 `total` 按提交条数计、但 `results` 去重渲染，分数与题数不符。现统一在计数前折叠重复（`last wins`）。
- **空提交除零**：`answers: []` 时 `correct / total` 触发 `ZeroDivisionError` → 500。现返回 422 `Empty submission: no answers provided`。

### Architecture
- 判分语义不变：仍以 `selected_index == correct_index` 为准，阈值不变（学习 ≥80%、复习 5/5），`weak_points` 仍存 `question_id`
- 复习提交的数量校验改为在**去重后**执行：`[A,A,B,C,D]` 现返回 422「需提交 5 道不同的题，本次收到 4 道」，避免 4 题作答被按 5 题计分而误判失败
- 只改后端两个路由（`app/routers/quizzes.py`、`app/routers/review.py`），前端 `QuizPage.tsx` / `ReviewPage.tsx` 无需改动（其提交顺序本就与呈现顺序一致）
- 回归验证：乱序提交 → 结果顺序 == 提交顺序；重复 id → `total` 收敛为 5；空提交 / 非法 id → 422；Quiz 与 Review 两链路抽题顺序与结果顺序逐一比对一致
- 验证过程产生的脏数据已还原：`lesson_id=1` 的 `lesson_mastery` 整行回滚至测试前快照（score 100、attempts 2、SRS 排期不变），全库 `mastery` 24 行、无非 `mastered` 残留
- 改动前自动备份：`spark_quest.db.bak_before_quizfix`

---

## 2026-09-07 — v1.1 Product Experience Polish：Course Map 重做

### Added
- **Course Map 全新视觉**：从「课程长列表」改为**区域化垂直旅程地图**（region-based vertical journey），单条蜿蜒路径 + 节点沿路径排布，可垂直滚动
- **5 态节点 + 6 态视觉**：
  - `mastered` 实心绿 + 白勾；`due_for_review` 在 mastered 之上叠加紫色外环（不新增状态，纯装饰）
  - `needs_review` 琥珀实心 + 白色叹号
  - `available`（全图唯一焦点）放大 1.32 倍 + 蓝色呼吸光环 + 浮动「开始」气泡
  - `locked` 灰虚线圈 + 锁图标，标题仍可见（预告前方）
- **完成感三层叠加**：
  1. 节点层（实心 + 勾）
  2. **路径层**（核心载体）：已掌握节点之间的道路从灰虚线变亮实线 ——「走过的路被点亮」
  3. 区域层（整区通关 → 绿色 + 插旗 + 已通关印章）
- **三档时间叙事**（`regionTone()` 纯函数派生 from `Level.status`）：
  - `past`（已通关）— `saturate(.65) brightness(1.06) contrast(.92)` + `scale(.985)`，徽章「已通关 · N/N」+ 旗帜
  - `present`（进行中）— 全饱和 + 蓝色描边 + 高光阴影，徽章「进行中 · N/N」
  - `future`（未解锁）— 节点 z-index 高于 ::after 蒙层，徽章「未解锁 · N 课」+ 锁
- **顶部区域导航胶囊**：8 个胶囊，当前高亮（蓝色），已通关用绿字，未解锁灰；点击跳转并展开 —— 直接回答 UX Audit Q1「我现在在哪里」
- **地图/列表视图切换**（无障碍兜底）：右上角 toggle，状态持久化到 `localStorage: sq_map_view`，列表视图为同一份数据的语义化 `<ol>` 呈现
- **首次进入自动滚动**到焦点节点（`scrollIntoView`），用户不用自己找「学到哪了」
- **氛围层**：`MapBackdrop.tsx`（纯装饰）— sticky 远景山 + 渐变天空 + 漂浮云，`z-index: 0`，**不接收任何 props，不知道课程/状态/进度的存在**。删掉它整个结构仍可读。

### Changed
- `pages/MapPage.tsx` **完全重写**：取数 / 折叠状态 / 自动定位 / 视图切换 / 区域导航 / 列表视图
- `pages/MapPage.css` **删除**（174 行旧样式全部废弃，CSS 现统一在 `components/map/map.css`）
- `types.ts`：`Level.status` 由 `string` 收窄为联合类型 `LevelStatus = 'completed' | 'in_progress' | 'available' | 'locked'`（仅前端类型收窄，后端 schema 未动）
- 地图页副标题由「Spark 学习路线：从环境搭建到 RDD 基础」改为数据驱动的「N 个区域 · M 课 · 已完成 K 课」

### Fixed
- **`currentLessonId` 抢占焦点 bug**：旧代码把 `needs_review` 也算进 current 焦点，导致琥珀节点被错误地套上 current 蓝色大圆 + 光环（needs_review 不该抢「下一步」的视觉焦点）。改为**只 `available` 才是 current**，needs_review 单独显示
- **节点标题重叠**：L1 RDD 基础（6 课）的 stepY=86 导致 5/6 课两行标题与下一节点 orb 重叠。改为 `stepY=96`，所有 9 课区域都安全

### Architecture
- **`components/map/mapLayout.ts` 纯函数布局算法**（v1.1 硬约束兑现点）：
  - `layoutRegion(count, opts)` 输入只有课程数，输出 `MapNode[]`，加课自动延长、零硬编码
  - 水平偏移用**预设偏移表循环** `[0, 58, 78, 58, 0, -58, -78, -58]`（不是 `sin()`，确定性、可单测）
  - `regionHeight(count)`、`segmentPath(a, b)`（S 曲线三次贝塞尔）、`regionTone(level)` 全部纯函数
  - **零新增依赖**（不引动画库/UI 库），仅用 CSS `@keyframes` + `prefers-reduced-motion` 关闭
- **新增文件清单**：
  - `components/map/mapLayout.ts`（纯函数）
  - `components/map/LessonNode.tsx`（5 态节点）
  - `components/map/LessonPath.tsx`（SVG 分段道路）
  - `components/map/JourneyRegion.tsx`（Level 区域）
  - `components/map/RegionNav.tsx`（顶部导航）
  - `components/map/MapBackdrop.tsx`（氛围层）
  - `components/map/map.css`（统一样式）
- **约束兑现：禁用全部氛围层与滤镜后结构 100% 可读**（已脚本验证）

### 验收
- `tsc -b && vite build` 零错误
- DOM 节点数 === 66（全展开地图视图）；列表 `<li>` 数 === 66
- 真实数据下 5 态全部出现（mastered:30 / locked:35 / current:1 / due:12；临时插入 needs_review 验证琥珀节点后还原）
- `mapLayout(11)` 返回 11 个坐标（数据驱动断言：`layoutRegion` 数量 === 输入）
- 375px 窄屏无横向溢出（节点最左 108 / 最右 298，视口 0..375）
- 31 个 `<a.lesson-node>`（可点）+ 35 个 `<div.lesson-node>`（locked 不可点）= 66
- 实机截图见 `E:\MMMason\Spark_dlg\ux_audit\v11-*.png`

---

## 2026-09-07 — v1.1.1 Product Experience Polish（地图交互修复 + 复习入口合并）

v1.1 Course Map 重做上线后，用户实机走查反馈三处地图交互问题，并发现已掌握课底部复习入口存在产品语义重复。均属 v1.1 范围内的打磨，不引入新功能、不碰后端。

### Fixed（地图交互，Round A）
- **展开/收起任意 Level 不再自动滚动到焦点节点**：`pages/MapPage.tsx` 原 `useEffect` 依赖 `expanded`，每次 toggle 都触发 `scrollIntoView`；改为 `useRef` 守卫，仅首次进入地图时滚动一次，切列表↔地图不重滚。
- **Level 介绍在收起/展开都能看全**：
  - 收起态 `components/map/map.css` 的 `.region-summary` 去掉 `-webkit-line-clamp:2` 截断，长介绍完整显示；
  - 展开态路径上方新增 `.region-intro` 浅蓝左边框卡片，长介绍不再丢失。
- **`due_for_review` 渲染确认**：设计为「绿勾 + 紫色外环」（`map.css` `.is-due .node-orb::before`），非黄色问号；用户确认紫环已存在，未改动。

### Changed（复习入口合并，Round B）
- 经代码核查确认：`复习测验`（`/lesson/{id}/quiz`）与 `间隔复习`（`/review/{id}`）出题逻辑完全相同——同一 `quizzes` 10 题库、同一采样函数 `_sample_quiz_questions(questions, n=5)`、同 n=5；review 仅多「上次错题维度优先」弱偏好（`priority_dims`，读 `weak_points`），非逐题遗忘曲线。
- **合并已掌握课底部入口**：`pages/LessonPage.tsx` mastered 分支删「复习测验」链接，仅留「下一课」（btn-primary）+「间隔复习（5 题）」（btn-ghost → `/review/{id}`）；available/needs_review 分支不变。
- **复习结果页显示本次得分**：`pages/ReviewPage.tsx` 结果 banner 加「本次复习得分 X%」+「仅本次反馈，不写回本课掌握得分」提示；后端 `submit_review` 本就不改 `score/attempts`，与约定一致，无需改。

### 验收
- `tsc -b && vite build` 零错误
- 地图：展开区 2 个 `.region-intro`、收起区 6 个 `.region-summary`；toggle 时 scrollY 0→0→0（不跳）
- 复习：已掌握课 CTA 仅剩「下一课 / 间隔复习（5 题）」；结果页 `🎉 复习通过 | 5/5 · 本次复习得分 100% | 不写回提示`

### 备注（教训已记入项目记忆）
- 本轮验证脚本跑完整 5/5 复习时真实推进了 lesson 1 的 SRS（违反「写库前先快照」约定，无真快照，已用 Python 还原为估算值）；核查全库仅 lesson 1 被碰且已还原，其余 29 行完好。单用户本地库影响可忽略，但规矩不能破。

---

## 2026-09-07 — Phase 9.1：🔥 Streak 连续学习

Phase 8 课程主线（Level 0–7）与 Phase 6b 复习闭环建成后，游戏化第一阶段落地 Streak。产品意义上的第三阶段：**Content（把学习内容系统化）→ Learning/Retention Loop（把学习过程闭环）→ Streak（把学习行为持续化）**。

### Added
- **新表 `study_days`**（一天一行，`UNIQUE(user_id, study_date)`）：`user_id / study_date / activity_count / lessons_done / reviews_done / first_at / last_at`
  - `user_id` 为未来用户系统预留，当前恒为 `DEFAULT_USER_ID = "local"`（无鉴权单用户本地应用）
  - 必须建表的原因：`lesson_mastery.last_quiz_at` 是每课**最后一次**提交时间，重做旧课会让更早的学习日从记录中消失，历史会回溯性损坏
- **Streak 内核**（`services.py`）：`LOCAL_UTC_OFFSET_HOURS` / `local_now()` / `local_today()` / `record_activity()` / `compute_streak()` → 返回 `StreakInfo(current, longest, studied_today, last_study_date)`
- **存量回填** `migrate.backfill_study_days()`：从 `last_quiz_at / last_review_at` 折算本地日期，`INSERT OR IGNORE` 幂等写入 9 天（08-24 / 08-26 / 08-27 / 08-28 / 08-31 / 09-02 / 09-03 / 09-04 / 09-07）
- **前端 `components/StreakBadge.tsx` + `.css`**：三态 `active / at-risk / broken`，状态由纯函数 `streakVariant(days, studiedToday)` 派生
- **验收脚本**：`backend/_p91_e2e_check.py`（28 项，跑临时库）、`backend/_p91_smoke.py`（真 API 冒烟，快照 + 还原）

### Changed
- `GET /api/dashboard`：`streak_days` 由硬编码 `0` 改为真值，并新增 `studied_today` / `longest_streak` / `last_study_date`
- `POST /api/lessons/{id}/quiz/submit` 与 `POST /api/review/{id}/submit`：成功后记一次有效学习行为
- `Home.tsx` hero 新增 `.hero-metrics` 容器（进度环 + Streak 同层），窄屏整组右对齐换行；「最长连续 N 天 · 最近日期」进「进度摘要」次要区
- `types.ts`：`Dashboard` 补 3 个 streak 字段

### Fixed
- **时区切天错误（预防性修复）**：全库存 UTC，若按 UTC 日期切天，UTC+8 用户的"一天"会是本地 08:00→次日 08:00，早上 7 点学完记到"昨天"。改为按 `LOCAL_UTC_OFFSET_HOURS` 折算本地日历日

### Architecture
- **Streak 永不持久化**：任何表都没有 `current_streak` / `longest_streak` 列，一律读时计算，无法与活动日志失同步，规则变更无需迁移
- **同事务埋点**（用户明确要求）：`record_activity()` 只 `flush()` 不 `commit()`，在两个提交接口的 `db.commit()` 之前调用——判分/调度写入与学习日记入同事务，成功同成功、失败同回滚
- **常量通用化**：偏移量命名为 `LOCAL_UTC_OFFSET_HOURS` 而非 Streak 专属，作为全应用业务时区
- **中断语义（Duolingo 式）**：不是"没学立刻清零"，而是"过完一整天没学才断"；今天没学但昨天学了 → streak 保持 N（At Risk），最后学习 ≤ 前天 → 归零（Broken）；`longest` 断链不回退
- **有效学习行为口径**：Quiz 提交 ✅ / Review 提交 ✅（过不过都算，空提交已被既有 422 拦截）；Lesson 阅读 ❌ / Note ❌ / 打开 Dashboard ❌
- **零新增依赖**：不用 `zoneinfo`（Windows 缺 tzdb，需额外装 `tzdata`），不用动画库；火焰呼吸仅 CSS `@keyframes` + `prefers-reduced-motion` 关闭

### RedLines（未抢跑）
- 不做 Streak Freeze（断连保护卡）/ 补签 / Badge 成就 / 每日目标 XP / 学习日历热力图 / 定时与后台任务 / 前端倒计时
- 不做多用户鉴权（`user_id` 只预留列位，不建 user 表）

### 验收
- `_p91_e2e_check.py` 28 项全绿：空库 / 同日幂等 / 连续三天 / 宽限日不断链 / 隔整天断链 / 断链后重来 / 时区边界（UTC 09-06 23:30 → 本地 09-07）/ 未知 kind 报错 / flush 未 commit 不落库 / 真库只读核对
- API 冒烟：提交 lesson 33 测验（score 40 失败）后 `study_days` 09-07 `activity_count` 4→5、`lessons_done` 2→3，证明**失败提交同样计入有效学习日**
- 冒烟前后快照 + 还原并复核：`lesson_mastery=32`、`lesson 33 mastery=0`、`study_days=9`、`09-07=(4,2,2)`、`lessons=66 / quizzes=660` 全部未变（备份 `spark_quest.db.bak_before_streak`）
- `tsc -b && vite build` 零错误

---

## 2026-09-08 — Phase 9.2：🏅 Badge 成就系统

Phase 9.1 Streak 之后，游戏化第二阶段落地 Badge。产品意义：**Content → Learning/Retention Loop → Badge（成就可视化、给正反馈）**。严格按设计稿落地，未扩大范围（无 XP/金币/排行榜/商店/社交/多用户）。

### Added
- **3 张表**：`badge_definitions`（目录，20 枚：`code` 唯一 + `is_secret` 单字段 + `image` 为 `/badges/*.webp` 相对路径）、`user_badges`（`UNIQUE(user_id, badge_id)`，insert-only，幂等基石）、`user_stats`（终身事件计数器：quiz_correct / quiz_submitted / reviews_passed / reviews_submitted / debug_correct）
- **解锁引擎 `badge_service.py`**：`BADGE_RULES` 字典（20 枚全量重算）+ `evaluate_badges()`（读时求值，新解锁 `ON CONFLICT(user_id, badge_id) DO NOTHING`）+ `increment_user_stats()`（同事务加性累加，永不递减）+ `build_context()` 一次聚合
- **20 枚徽章**：8 旅程 `LEVEL_0–7`（由 `course_levels` 自动派生，非硬编码数量）+ 12 特别（QUIZ_100/500/1000、STREAK_7/30/100、REVIEW_50、BUG_HUNTER、BLITZ、LATE_NIGHT、WANMEI、QUANJING）；`LEVEL_NAMES` 手工映射 0–7 中文名
- **种子 `seed_badges.py`**：`ON CONFLICT(code) DO UPDATE` 保留 `id`（规避 `REPLACE` 重排 rowid 破坏 `user_badges.badge_id` 外键）
- **背填 `migrate.backfill_badges()`**：`user_stats` 仅当行不存在时写一次（绝不覆盖线上累加），再 `evaluate_badges` 解锁一切可派生徽章；挂 `init_db` 课程种子之后（LEVEL 定义依赖 `course_levels`）
- **前端**：`pages/BadgesPage.tsx`（`/badges` 路由，按 tier 分两组网格，未解锁灰度、SECRET 未解锁显示「神秘徽章 / ?」）、`Home.tsx`「最近解锁」条 + 页脚入口、`components/BadgeUnlockToast.tsx`（提交后右下角轻量浮动提示，5.2s 自动消失，解锁的 SECRET 正常显示）
- **验收脚本**：`backend/_p92_smoke.py`、`backend/_p92_e2e_check.py`（7 项，均快照 + 还原）

### Changed
- `POST /api/lessons/{id}/quiz/submit` 与 `POST /api/review/{id}/submit`：`record_activity` 之后、`db.commit()` 之前调用 `increment_user_stats` → `evaluate_badges`（同事务；`autoflush=False` 靠两者内部 `flush()` 让刚写状态对引擎可见）；响应新增 `new_badges`
- `GET /api/badges`（新增）：20 枚目录 + 解锁态，SECRET 未解锁时 `name/description/image` 置空
- `GET /api/dashboard`：新增 `recent_badges`（最近 6 枚，解锁的 SECRET 正常显示）
- `QuizPage` 提交带 `started_at`（`new Date().toISOString()`）供 BLITZ；`types.ts` 补 `Badge` / `new_badges` / `recent_badges` / `started_at`

### Fixed
- **BLITZ 时区 bug**：`_parse_started_at` 曾把客户端 UTC 时间戳转成本地时区，与 `datetime.utcnow()`（UTC）对比导致 UTC+8 机器上时长变负、BLITZ 永不触发 → 改为统一转 UTC 朴素时间戳
- `badge_service.evaluate_badges` 误把 `select(UserBadge.badge_id)` 的标量结果当实体取 `.badge_id` → 改为 `set(scalars(...))`
- `is_late_night` 仅在 `event_kind` 非空时判定，背填/只读路径不会因运行时间误判深夜徽章

### 决策与修正（用户拍板）
- Bug 猎手阈值 50→**20**（全库仅 43 道 debug 题，且前 4 Level 已掌握，50 永远够不到）
- 背填 `user_stats` 精度：quiz_submitted=SUM(attempts)=68、reviews_passed=SUM(review_count)=42 为**准确值**；quiz_correct=SUM(correct_count)=160 为**下界**（lesson_mastery 只存每课最近一次）；debug_correct 无历史起点 0
- SECRET 仅单字段 `is_secret`（去掉多余的隐藏开关）；计数器语义跟随既有 submit/attempt；背填按字段区分精度

### Architecture
- **不新增任何学习状态列**：20 枚徽章全由既有表 + `user_stats` 派生
- **幂等**：`user_badges` 唯一约束 + `ON CONFLICT DO NOTHING`；背填 `user_stats` 用 INSERT OR IGNORE 仅写基线一次
- **零新增依赖**：前端纯 CSS 动画，不引动画库；二进制 webp 由 Vite 静态托管
- **背填恰为 6 枚**：LEVEL_0–3（已全掌握）+ QUIZ_100（160≥100）+ WANMEI（34 课全部 100%）；REVIEW_50(42<50) / STREAK_7(最长 3) / QUIZ_500(160<500) / 事件型（无真实事件）均不解锁，符合预期

### RedLines（未抢跑）
- 不做 XP / 金币 / 排行榜 / 商店 / 社交分享 / 每日目标 / 学习日历热力图 / 多用户鉴权 / 后台定时任务 / 前端倒计时

### 验收
- `_p92_e2e_check.py` 7 项全绿：目录形状 20=8+12、SECRET 置空、背填恰 6 枚、背填幂等、BLITZ 快交触发/慢交抑制、BUG_HUNTER/LATE_NIGHT 保持锁定
- 真实 `uvicorn --port 9000` 启动：`/api/health` ok、`/api/badges` 20 枚（6 解锁）、`/api/dashboard` 含 `recent_badges=6`，路由全部挂载正常
- `tsc -b` 与 `vite build` 零错误

---

## 2026-09-08 — Phase 10.1：🧠 薄弱题 / Weak Questions（事实层 + 单题重练）

Phase 9.2 Badge 之后，把核心学习闭环补完整：**学习 → 测试 → 犯错 → 记录 → 再做 → 修复 → 再验证**。此前 Quiz/Review 每次提交的逐题结果（含解析）只回传前端即丢弃，`weak_points` 仅存每课"最近一次"错题 id（覆盖写）；"马马虎虎看一眼解析就过去"的题从此无据可查。本阶段以**专项架构审计**（2026-09-08）定性为 Level B（基础数据够、缺一个很小的事实记录）后实施。设计稿 `Spark_Quest_Phase10_薄弱题_执行计划_设计.md` 经用户验收通过（含 4 点修订）。

### Added
- **事实层 `quiz_answer_log`（append-only）**：`user_id(哨兵) / lesson_id / question_id / source('quiz'|'review'|'practice') / selected_index / correct_index(事件快照) / is_correct / submitted_at`；复合索引 `ix_quiz_answer_log_user_question_time(user_id, question_id, submitted_at)` 替代 3 个单列索引（事实表典型访问路径：一个用户 → 某道题 → 全部历史 → 按时间排序）；**零状态列**（无 wrong_count/status/mastery/is_fixed）
- **写入点**：Quiz submit（source='quiz'）与 Review submit（source='review'）在 `db.commit()` 前同事务逐题追加；新端点 Practice（source='practice'）独立事务追加
- **`routers/weak_questions.py`（3 端点）**：`GET /api/weak-questions`（跨来源派生：wrong_count=COUNT / last_wrong_at=MAX / last_attempt_correct=最近一行，过滤 wrong_count≥1，排序 wrong_count DESC + last_wrong_at DESC）、`GET /api/weak-questions/{id}`（题面**不含 correct_index**）、`POST /api/weak-questions/{id}/practice`（服务端判分 + 返回对错/解析）
- **前端 `/wrong-questions`（最小版）**：`WeakQuestionsPage.tsx`（总数 + 卡片列表：题干/维度·L{n}/错误 N 次·相对时间/「最近一次已做对」标签；「重新练习」弹单题面板 → 独立作答 → 对错高亮 + 解析 → 可重试，**无强制勾选**）+ `Home.tsx` 页脚「🧠 薄弱题 →」入口 + 路由/类型
- **验收脚本**：`backend/_p101_smoke.py`（23 项，快照 → 测 → 还原）

### Changed
- `lesson_mastery.weak_points` 语义保留不动（继续作为 Review 维度提示）；Review 调度、5/5 门槛、Quiz 判分全部不变
- `schemas.py` 新增 `WeakQuestionOut / WeakQuestionDetailOut / WeakQuestionPracticeIn / WeakQuestionPracticeOut`

### 决策与修正（用户验收拍板，4 点）
- **复合索引替代 3 单列索引**：结构设计问题，不是性能优化；`lesson_id` 不单建索引
- **`correct_index` 保留**：是"作答事件当时正确答案的快照"，非状态非聚合——题库日后修订，历史仍准确回答"当时如何判定"
- **Practice 绝不触碰 mastery/SRS/streak/badge stats**（来源 × 副作用矩阵写死）：一次重练就是一条新事实，不能因"答对了"偷偷影响学习状态
- **"薄弱"定义写死**：= "历史上至少出现过一次错误作答"，不代表当前未掌握；`wrong_count=2` 且 `last_attempt_correct=true` 仍在列表是设计语义
- **跨来源统一聚合**：Quiz ❌ + Review ❌ + Practice ✅ → `{wrong_count:2, last_attempt_correct:true}`，`source` 只是事件标签

### Architecture
- **不叫 `wrong_questions`**：命名会诱导塞入 status/mastery/wrong_count/is_fixed，最终造出第二套 Mastery；"事实存库、状态派生"原则的正面落地
- **不做历史 backfill**：Phase 10.1 前的逐题尝试已丢弃不可恢复，强行回填=制造伪历史；日志自实施日起累积，越用越有价值
- **不强制阅读解析**：真正的"懂了没"靠之后重新独立遇到并作答，不是勾选"我看过了"

### RedLines（未抢跑）
- 无错题状态表 / 无错题 Mastery / 无"已修复"状态机 / 无强制阅读解析 / 不重建 Review / 不引入新 SRS / 不一次做全 UX（筛选/归档/薄弱度升级留 Phase 10.2+）

### 验收
- `_p101_smoke.py` 23/23 全绿：quiz 错→入列(wrong_count=1)、practice 错→2、review 错→3（跨来源合并）、practice 对→count 不变+last_attempt_correct=true、practice 对 study_days(行数+行内容)/user_badges/user_stats/lesson_mastery 零污染、log 表无状态列
- 真实 `uvicorn --port 9000`：health ok、新表由 init_db 自动创建、干净库 `/api/weak-questions` 返回 `[]`、不存在题 404
- `tsc -b` 与 `vite build` 零错误；测后 DB 从快照还原（quiz_answer_log=0 行就绪，用户进度零触碰）

---

## 2026-09-09 — Level 4（执行计划）全面技术修复

起因：学员学到 L4-6「WholeStageCodegen 与 Tungsten」时发现 `*(N)` 概念错误。据此先出《Spark Quest Level 4 技术审查报告（2026-09-09）》（四维：技术事实准确性 / 示例真实性 / 概念边界 / 版本敏感性），结论 **P0 1 项、P1 6 项、P2 6 项、P3 5 项**，随后按报告逐项落地。审查对象：Level 4 全部 9 课（lesson id 31–39）+ 90 道 quiz，数据以 `backend/spark_quest.db` 真库为准。

### Fixed — P0：`*(N)` 语义完全说反
- 课文与题库原写「`*(N)` = WholeStageCodegen 融合的算子数」，**实为 codegen stage 编号（codegenStageId）**
- 证据 SPARK-23032（Fix 2.3.0）官方输出：`*(1)` 下有 2 个算子、`*(3)` 下只有 1 个；Exchange 之后编号继续 `(4)(5)(6)`、**不归零**
- 正确读法：数「带相同 N 的行数」= 该 stage 的算子数；数「不同 N 的个数」= 这条查询有几个 codegen stage
- 涉及 L4-4 / L4-6 / L4-9 课文 + **q379 / q397 / q403 / q404 / q433 —— 5 道题原本在考错误答案**

### Fixed — P1（6 项）
- `explain(mode="formatted")` 版本：2.3+ → **3.0+**（SPARK-27395；勿与 SPARK-23032 混为一谈）
- **join 非必然宽依赖**：shuffle-based join（SortMergeJoin / ShuffleHashJoin）才需要 Exchange；**Broadcast Join 不 Shuffle、不切 Stage**（与 Level 6 教学对齐，消除跨 Level 自相矛盾）
- **groupBy 非必然 Shuffle**：上游已按该 key 分区时 `EnsureRequirements` 判定满足，不插 Exchange
- L4-8 `repartition(200)` 示例漏算一次 Shuffle：repartition 自身即 Exchange，实为 **2 个 Shuffle 边界 / 3 个 Stage**
- **Action ≠ 恰好一个 Job**：`show()` 底层是 `take(21)` 逐轮扩大，可能触发多个 Job
- **Job 内 Stage 非必然串行**：有依赖的等父 Stage，无依赖的可并行提交

### Fixed — P2（6 项）
- 3 处 `df.select('city').filter(df.amount>0)` 会抛 AnalysisException → 改为 `select('city','amount')` 或 filter 前置
- **UDF 下推失效的因果讲反了**：不是「优化器看不懂 UDF」，而是含 UDF 的过滤条件依赖 UDF 输出值、顺序上无法前移；且**列裁剪照常发生**，只是 UDF 依赖的列必须保留
- 等价改写补非确定性表达式边界：`rand()` / `current_timestamp()` / `monotonically_increasing_id()`
- 宽依赖容错：「重算整个上游重排」是 RDD 论文（2012）的叙述 → 改为「Shuffle 输出丢失时可能需重新执行相关上游 map task」
- 「Stage 数 = Shuffle 数 + 1」降格为**单条线性链**的快速估算，多分支 DAG 不套用
- 列裁剪：Parquet/ORC 可跳过整列数据；**csv 等行式文本通常仍需读取并解析整行**

### Added — P3（版本敏感性）
- L4-3 补 Spark 3.0+ 五档 explain 模式（simple / extended / codegen / cost / formatted），并说明 `mode="codegen"` 可直接看生成的 Java 代码
- **AQE 版本提示**：Spark 3.2+ 默认开启，`explain()` 只给初始计划（常显示 `AdaptiveSparkPlan isFinalPlan=false`、整棵树看不到 `*(N)`）；教学演示需 `spark.conf.set("spark.sql.adaptive.enabled","false")`，最终计划结合 Spark UI 看
- FileScan parquet 在 Spark 3.x 常不带 `*`（向量化读取后 codegen 从 ColumnarToRow 开始），不代表没优化
- 版本注：WholeStageCodegen 2.0 引入 / `*(N)` 编号 2.3 引入 / formatted 3.0 引入 / AQE 3.2 默认开启
- **Tungsten 重新定义**：紧凑二进制内存表示 + cache-aware 算法与数据结构 + 代码生成；**WholeStageCodegen 属于其中「代码生成」一支，是包含关系而非并列两层**

### Changed
- 措辞统一：「生成一个手写 Java 方法」→「生成 Java 代码并编译执行」；「回退到解释执行」→「回退为逐算子 iterator（Volcano 式）执行，Spark 没有解释器」
- **答案位置重排**：L4 90 题 correct_index 原为 A38/B45/C6/D1（学员凭位置即可猜中约 70%）→ **A22/B24/C22/D22**。只动**无 `quiz_answer_log` 作答记录**的题（38 题）；15 道已作答题 + q427（选项为 0/1/2/3 天然序列）冻结不动
- **`lessons.objective` 补修**：该字段是独立列（前端渲染为「🎯 学完后，你应该能回答」），不在 content JSON 内，首轮修复漏扫 → 9 条中 8 条重写；`description` 同源 2 处一并修
- **三段引导文案重写**（review / problem / preview）：原每段仅 60~110 字、读起来像目录摘要 → 对齐 Level 0/1 调性重写为 review 160~313 字 / problem 98~170 字 / preview 193~249 字（承接已知 → 转折悬念 → 固定「下一课：XXX」）

### Architecture
- 不改表结构、不新增持久化状态；全部改动落在现有 lessons / quizzes 行内
- `app/course_seed.json` / `app/quiz_seed.json` 已用真库回写（否则删库重建会把错误内容重新种回）；`seed_level4.py` 加「已过期、勿执行」警告
- 《心智模型与比喻边界案例库》§5 Level 4 九条目 + L2/L3 四处同源口径一并更正 —— **该文档是写新课时参考的源头，也是本次 Level 4 出错的根因**

### RedLines（未抢跑）
- 不改 Level 4 课程结构与课时数；不顺手重构 UI / DB；不修改用户学习进度（`lesson_mastery` / `study_days` / `user_stats`）

### 遗留技术债（用户决定暂不修）
- **L2 / L3 课文与题库仍是旧口径**（orderBy 必 Shuffle / 聚合必 Shuffle / JOIN 必 Shuffle），与已更正的设计文档存在**已知的不一致**；当前收益低，登记为技术债
- L4 lesson 31 因 5 道冻结题中有 4 道固定在 B，该课答案分布只能做到 A2/B4/C2/D2

### 验收
- 真库核实：Level 4 仍 9 课 / 90 题 / 每课 10 题 / 无重复题干 / 无 orphan quiz
- 关键词扫描剩 11 处命中，逐条人工确认均为合法文本（纠错句、否定句、以及干扰项里故意保留的旧说法）
- 答案重排正确性：与重排前备份逐题比对 —— 正确答案**文本** 0 改动、选项集合 0 异常、已作答题位置 0 移动
- 脚本（均支持 dry-run 与自动备份）：`backend/fix_level4_20260909.py`、`fix_level4_20260909_round2.py`、`fix_level4_objective_20260909.py`、`rebalance_l4_answers_20260909.py`、`rewrite_level4_narrative_20260909.py`、`sync_seed_from_db_20260909.py`、`preview_level4_narrative.py`
- 文档：`spark_quest/docs/Spark_Quest_Level4_技术审查报告_20260909.md`、`Spark_Quest_Level4_修复报告_20260909.md`（含附录 A 重排 / B objective 补修 / C 文案重写 / D 比喻库更正）

---

## 模板（后续阶段直接复制此结构，改日期与内容）

## YYYY-MM-DD — <阶段标题>

### Added
-

### Changed
-

### Fixed
-

### Architecture
-
