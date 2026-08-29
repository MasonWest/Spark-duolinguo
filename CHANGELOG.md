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
