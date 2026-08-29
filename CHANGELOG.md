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
