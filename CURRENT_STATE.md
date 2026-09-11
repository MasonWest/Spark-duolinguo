# Spark Quest — 当前项目状态

> 最后更新：2026-09-11（Level 7 技术审查与修复 + Level 5/6/7 三段文案重写完成；与 `CHANGELOG.md` 同步）
> 代码目录：`E:\MMMason\Spark_dlg\spark-quest-app\`
> 代码仓库：`https://github.com/MasonWest/Spark-duolinguo`（分支 `main`）
> 文档目录（通常只读）：`E:\MMMason\Spark_dlg\spark_quest\`

## 总体状态

| Phase | 内容 | 状态 |
|-------|------|------|
| 0 | 项目骨架（前后端通信 + SQLite 连接） | 🟢 已完成并验收 |
| 1 | 课程地图（course_levels / lessons + /map 页面） | 🟢 已完成并验收（v1.1 已重做：长列表 → 区域化垂直旅程） |
| 2 | Dashboard / 今日任务（/api/dashboard + 推荐首课） | 🟢 已完成并验收 |
| 3 | Lesson 学习页面（/api/lessons/{id} + /lesson/:id，七要素 + 数据化） | 🟢 已完成并验收 |
| 4 | Lesson Mastery Quiz + 最小进度 + 解锁 | 🟢 已完成 |
| 5 | 完整 Progress Dashboard 动态化 + 状态系统 | 🟢 已完成 |
| 6a | Quiz Bank 扩充（每课扩至 10 题 + 多样性抽题；L0/L1/L2 全完成） | 🟢 已完成（Phase 6.1 + 6.2） |
| 6b | Review / Spaced Repetition（Lesson 级间隔复习闭环） | 🟢 已完成并验收（37 项端到端全过） |
| 7 | Parking Lot 防止思绪发散 | 🔒 规划中 |
| 8 | 完整 Spark 课程（Level 2/3/4/5/6/7 **已全部落地**：DataFrame 核心 / Spark SQL / 执行计划 / 分区与 Shuffle / JOIN 深类型与 Broadcast / 性能调优）——课程主线完成 | 🟢 已完成（待验收） |
| 9 | 游戏化 UI / Streak / Badge | 🟢 **9.1 Streak 已完成并验收**；🟡 **9.2 Badge 成就已完成（待验收）** |
| 10 | ~~AI Tutor~~ → **10.1 薄弱题 / Weak Questions**（`quiz_answer_log` 事实层 + 派生薄弱题列表 + 单题重练） | 🟡 **10.1 已完成（待验收）**；10.2+ / AI Tutor 规划中 |
| Notes | Lesson 学习笔记（lesson_notes 表 + 笔记 API + 前端接入） | 🟢 已完成（V1.0 基线） |
| **技术修复** | **Level 4（执行计划）全面技术修复（2026-09-09）**：P0 `*(N)` 语义 + P1×6 / P2×6 / P3×5；9 课课文 + 27 道题 + objective + 答案位置重排 + 三段文案重写 + 比喻库口径更正 | 🟢 **已完成并验收并推送**（遗留 L2/L3 旧口径已登记为技术债，暂不修） |
| **技术修复** | **Level 5（分区与 Shuffle）+ Level 6（JOIN 与 Broadcast）技术审查与修复（2026-09-10）**：4 项明确错误（`repartition` 是 round-robin 非 hash 重分布 / `sortWithinPartitions` 不 Shuffle / q481 旧容错口径 / BroadcastExchange 也是 Exchange）+ 绝对化清理 + 15 处版本事实；17 课课文 + 26 道题 + 比喻库 §6/§7 十七条更正 | 🟢 **已完成并推送**（L7 待审；L2/L3 旧口径技术债未修） |
| **文案修缮** | **Level 5 / 6 / 7 三段引导文案重写（2026-09-11）**（上一课回顾 / 本课要解决的问题 / 下一课伏笔）：27 课 × 3 段全部按 Level 0/1 调性重写，篇幅约翻 2~3 倍；比喻沿用已登记道具，技术口径与已修复课文对齐 | 🟢 **已完成并落库**（未 commit、未 push） |
| **技术修复** | **Level 7（性能调优）技术审查与修复（2026-09-11）**：无 P0；P1×3（乱码 2 处 / **AQE 3.2+ 默认开启的事实缺失** / 绝对化「几个数量级」）+ P2×4 精度 + P3×3 版本事实；8 课课文 + 5 题解析 + 比喻库 §8 五条目更正 | 🟢 **已完成**（L0/L1 未审；L2/L3 技术债仍在） |
| **v1.1** | **Course Map 重做（区域化垂直旅程 / 三档时间叙事 / 5 态节点 / 列表兜底）** | **🟢 已完成并验收** |

**当前进度：Phase 9.1 Streak 已完成并验收；Phase 9.2 Badge 已实现完毕（待验收）；Phase 10.1 薄弱题 / Weak Questions 已实现完毕（`quiz_answer_log` 事实层 + 跨来源派生薄弱题 + `/wrong-questions` 重练页，待验收）。**

**下一个可做方向**：Phase 7 Parking Lot 防发散 / Phase 10.2（薄弱度启发式升级：连续做对才移出列表）/ Level 8「真实 ETL 毕业项目」（见 CHANGELOG 2026-08-29 结论：不再线性扩 Spark 内核，不引入 Flink）。

## 运行端口（已统一）

| 服务 | 端口 | 说明 |
|------|------|------|
| 前端（Vite） | 6001 | 安全端口（6000 被 Chromium 列为 `ERR_UNSAFE_PORT`，禁用） |
| 后端（Uvicorn） | 9000 | 9000 不在 Chromium 不安全端口列表 |
| SQLite | 文件 `backend/spark_quest.db` | 无端口，本地文件 |

- 前端经 Vite dev proxy 访问 `/api/*` → `http://localhost:9000`
- 后端 CORS 允许 `http://localhost:6001`
- Vite 已设 `host: true`，`localhost` 与 `127.0.0.1` 均可访问
- 验收时核对：6001/9000 均在监听

## 技术栈

| 层 | 技术 | 版本 |
|----|------|------|
| 前端 | React + Vite + TypeScript | React 18.3 / Vite 5.4 / TS ~5.6 |
| 路由 | react-router-dom | 7.18.2 |
| 后端 | FastAPI + Uvicorn | FastAPI 0.141.1 / Uvicorn 0.52.4 |
| ORM | SQLAlchemy | 2.0.52 |
| 数据库 | SQLite | 本地文件 |
| Python | 3.13.14（venv 隔离在 `backend/.venv`） | 不升级 |
| Node | 22.22.2 / npm 10.9.7 | — |

## 启动命令

```bash
# 终端 1：后端（9000）
cd E:\MMMason\Spark_dlg\spark-quest-app\backend
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 9000 --reload

# 终端 2：前端（6001）
cd E:\MMMason\Spark_dlg\spark-quest-app\frontend
npm run dev
```

访问：<http://localhost:6001>

> ⚠️ 停止前端 `npm run dev` 后，`TaskStop` 只杀 npm 外壳，node 子进程会残留并占住端口，必须 `taskkill /PID <node子进程> /F` 释放。

## 数据库结构

共四张表：Phase 1 引入 `course_levels` / `lessons`；**Phase 4 新增 `quizzes` 与 `lesson_mastery`**（不再用原规划的 `user_progress` 表，改为单课一对一的 `lesson_mastery`，详见下方"关键约定"）。Phase 0 不建表，Phase 2/3 未改 schema——结构化课程内容以 JSON 文本形式存于既有 `lessons.content` 列。

```text
course_levels (id, title, description, order_index, status)
     │ 1:N
lessons (id, level_id FK→course_levels.id, title, slug, description,
        objective, estimated_minutes, order_index, prerequisites, content)
     │ 1:N
quizzes (id, lesson_id FK→lessons.id, type, prompt, options[JSON],
        correct_index, explanation, order_index)
     │ 1:1
lesson_mastery (id, lesson_id FK→lessons.id UNIQUE, status, score,
        correct_count, total_count, attempts, last_quiz_at, weak_points[JSON],
        # ↓ Phase 6b 新增：间隔复习调度（不新增表）
        first_mastered_at, srs_stage, next_review_at, last_review_at,
        review_count)
     │ 1:N
lesson_notes (id, lesson_id FK→lessons.id ON DELETE CASCADE, content,
        created_at)   # V1.0 基线新增：append-only 学习笔记
study_days (id, user_id, study_date, activity_count, lessons_done,
        reviews_done, first_at, last_at)   # ↓ Phase 9.1 新增：Streak 数据源
        UNIQUE(user_id, study_date)
```

### 表字段

**course_levels**
| 列 | 类型 |
|----|------|
| id | INTEGER (PK) |
| title | VARCHAR |
| description | TEXT |
| order_index | INTEGER |
| status | VARCHAR |

**lessons**
| 列 | 类型 |
|----|------|
| id | INTEGER (PK) |
| level_id | INTEGER (FK → course_levels.id) |
| title | VARCHAR |
| slug | VARCHAR (unique) |
| description | TEXT |
| objective | TEXT |
| estimated_minutes | INTEGER |
| order_index | INTEGER |
| prerequisites | TEXT |
| content | TEXT（Phase 3 填充，目前为空占位） |

**quizzes**（Phase 4 引入；`options` 为 JSON 列表字符串，`correct_index` 为正确选项下标）
| 列 | 类型 |
|----|------|
| id | INTEGER (PK) |
| lesson_id | INTEGER (FK → lessons.id) |
| type | VARCHAR（`single_choice` / `true_false` / `application`，三者统一按 `selected_index == correct_index` 判分） |
| prompt | TEXT |
| options | TEXT（JSON list[str]） |
| correct_index | INTEGER |
| explanation | TEXT |
| order_index | INTEGER |
| dimension | TEXT（Phase 6.1 新增；认知维度标签，开放词表如 concept/why/mechanism/apply/comparison/debug，可空） |

**lesson_mastery**（Phase 4 引入；每课一行；`weak_points` 为 JSON 列表字符串，存"最近一次提交答错的 question_id"）
| 列 | 类型 |
|----|------|
| id | INTEGER (PK) |
| lesson_id | INTEGER (FK → lessons.id, **UNIQUE**，每课仅一行) |
| status | VARCHAR（`mastered` / `needs_review`，首次达 ≥80% 后锁定为 `mastered`，Phase 4 内不降级） |
| score | INTEGER（最近一次提交得分，0–100） |
| correct_count | INTEGER |
| total_count | INTEGER |
| attempts | INTEGER（该课 Quiz 累计提交次数） |
| last_quiz_at | DATETIME (nullable) |
| weak_points | TEXT（JSON list[int]，最近一次答错的 question_id 列表） |
| first_mastered_at | DATETIME (nullable)（**Phase 6b 新增**：首次掌握时间，SRS 锚点；语义 ≠ last_quiz_at） |
| srs_stage | INTEGER default 0（**Phase 6b 新增**：阶梯档位，索引 `REVIEW_INTERVALS_DAYS`；权威调度状态，不可由 next_review_at 反推） |
| next_review_at | DATETIME (nullable)（**Phase 6b 新增**：下次复习到期时间） |
| last_review_at | DATETIME (nullable)（**Phase 6b 新增**：上次复习时间，独立于 last_quiz_at） |
| review_count | INTEGER default 0（**Phase 6b 新增**：累计通过复习次数，纯统计，不参与调度） |

**lesson_notes**（V1.0 基线新增；每课可有多条笔记，新建即追加、不覆盖历史）
| 列 | 类型 |
|----|------|
| id | INTEGER (PK) |
| lesson_id | INTEGER (FK → lessons.id, ON DELETE CASCADE, 有索引) |
| content | TEXT |
| created_at | DATETIME (默认 datetime.now) |

**study_days**（Phase 9.1 新增；Streak 的唯一数据源，一天一行）
| 列 | 类型 |
|----|------|
| id | INTEGER (PK) |
| user_id | VARCHAR (有索引；当前单用户恒为 `"local"`，见 `models.DEFAULT_USER_ID`) |
| study_date | VARCHAR，**本地**日历日 `"YYYY-MM-DD"`（按 `LOCAL_UTC_OFFSET_HOURS` 折算，非 UTC 日期） |
| activity_count | INTEGER default 0（当天有效学习动作总数） |
| lessons_done | INTEGER default 0（学习测验提交次数） |
| reviews_done | INTEGER default 0（间隔复习提交次数） |
| first_at | DATETIME (nullable, UTC) |
| last_at | DATETIME (nullable, UTC) |

> 唯一键 `UNIQUE(user_id, study_date)`。全表**没有** `current_streak` / `longest_streak` 之类的持久化字段——Streak 一律读时计算。

### 种子数据

- 课程：`backend/app/course_seed.json`，首次启动且表为空时自动播种（不重复插入）。
  Phase 3 起还会在启动时按 slug 幂等回填 `lessons.content`（仅当原 content 为空时覆盖，已编辑内容不会被回写覆盖）。
- 题库：**Phase 4 新增 `backend/app/quiz_seed.json`**，首次启动且 `quizzes` 表为空时按 `lesson_slug` 幂等播种。Phase 6.1/6.2 已将全部 21 课每课扩至 10 题（共 210 题）：Level 0/1（11 课）在原 44 题基础上补 66 题，Level 2（10 课）在原 50 题基础上补 50 题；均为 `single_choice`，每题带 `dimension` 标签（开放词表：概念理解 / 为什么 / 运行机制 / 场景应用 / 对比辨析 / 排错等，不强求固定类别）。已存在题目的课跳过，不重复插入。

- **Level 0：环境与 Spark 初识**（5 课）
  1. Spark 是什么 · 2. Spark 解决什么问题 · 3. Driver / Executor · 4. SparkSession · 5. 第一个 PySpark 程序
- **Level 1：RDD 基础**（6 课）
  1. RDD 是什么 · 2. Transformation · 3. Action · 4. Lazy Evaluation · 5. RDD 为什么逐渐被 DataFrame 替代 · 6. RDD 小练习
- **Level 2：DataFrame 核心**（10 课，2026-08-27 新增，见下方 Phase 8 记录）
  1. DataFrame 是什么 · 2. 创建 DataFrame · 3. Schema 与数据类型 · 4. 检视数据 · 5. select/filter/where · 6. withColumn 与 Column 表达式 · 7. 排序/去重/常用操作 · 8. groupBy 与聚合 · 9. 数据写出 · 10. DataFrame 综合练习
- **Level 3：Spark SQL**（9 课，2026-08-28 新增，见下方 Level 3 实现记录）
  1. Spark SQL 是什么 · 2. 临时视图（Temporary View）· 3. SELECT 基础 · 4. WHERE / ORDER BY / LIMIT · 5. GROUP BY 与 HAVING · 6. 多表关联（JOIN）入门 · 7. 内置函数与 UDF · 8. Spark SQL 与表 / 文件格式 · 9. Spark SQL 综合练习
- **Level 4：执行计划**（9 课，2026-08-28 新增，见下方 Level 4 实现记录）
  1. 为什么该看执行计划 · 2. 逻辑计划 vs 物理计划 · 3. explain() 怎么用 · 4. 怎么读执行计划文本 · 5. Catalyst 优化规则 · 6. WholeStageCodegen 与 Tungsten · 7. 窄依赖 vs 宽依赖 · 8. Job / Stage / Task 层级 · 9. 综合练习
- **Level 5：分区与 Shuffle**（9 课，2026-08-28 新增，见下方 Level 5 实现记录）
  1. 分区是什么 · 2. 分区数与并行度 · 3. Shuffle 是什么 · 4. Shuffle 为什么贵 · 5. 窄/宽依赖在分区层面的含义 · 6. 哪些操作会触发 Shuffle · 7. reduceByKey vs groupByKey · 8. repartition vs coalesce · 9. 综合练习
- **Level 6：JOIN 深类型与 Broadcast**（9 课，2026-08-29 新增，见下方 Level 6 实现记录）
  1. JOIN 是什么（为什么比单表聚合更重）· 2. JOIN 策略全景 · 3. Broadcast Hash Join（小表广播）· 4. Sort-Merge Join（大表×大表默认）· 5. Shuffle Hash Join 与兜底策略 · 6. Spark 怎么选 JOIN 策略 · 7. 主动控制：broadcast() 提示与避坑 · 8. JOIN 中的数据倾斜（Skew）· 9. 综合练习
- **Level 7：性能调优**（9 课，2026-08-29 新增，见下方 Level 7 实现记录）——**Phase 8 课程主线最后一关**
  1. 性能调优是什么（度量驱动的闭环）· 2. Tungsten 与编码字节级 · 3. Executor 内存模型与 OOM 根因 · 4. Shuffle 分区数怎么定 · 5. 广播阈值调优 · 6. AQE：让 Spark 在运行时自我修正 · 7. 数据倾斜实战处理 · 8. 最优先的调优：少读、少传、少算 · 9. 综合练习（诊断清单与优先级）

每课 `content` 字段结构（Phase 3 引入，JSON 文本）：
```json
{
  "explanation": "...",                       // 概念解释（多段，\\n\\n 分段）
  "examples": [                               // 示例
    {"title": "...", "code": "...", "note": "..."}
  ],
  "key_points": ["..."],                      // 必记知识
  "common_mistakes": [                        // 常见错误
    {"mistake": "...", "why": "...", "fix": "..."}
  ]
}
```
> 注意：Level 2 课程 content 已升级为 **七要素**（在原有 explanation / examples / key_points / common_mistakes 基础上新增 `review` / `problem` / `preview`，与前端学习页契合）。

title / objective / estimated_minutes 仍为独立列；课程文本**不硬编码在 React 组件**。

当前数据量：`course_levels = 8`，`lessons = 66`，`quizzes = 660`，`lesson_mastery = 34`（用户真实进度，改代码时别碰），`study_days = 10`（Phase 9.1 由 mastery 时间戳回填，属下界估计）；Phase 9.2 新增 `badge_definitions = 20`（8 旅程 + 12 特别，种子幂等 upsert）、`user_badges = 6`（背填解锁：LEVEL_0–3 / QUIZ_100 / WANMEI，详见下方实现记录）、`user_stats = 1`（背填基线：quiz_correct=160 / quiz_submitted=68 / reviews_passed=42，均为下界估计）；Phase 10.1 新增 `quiz_answer_log = 0`（逐题作答事实层，append-only，自实施日起累积——历史不可回填，这是有意接受的事实缺口）；全部 lesson.content 已回填（Level 2 新增 10 课、Level 3 新增 9 课、Level 4 新增 9 课、Level 5 新增 9 课、Level 6 新增 9 课、Level 7 新增 9 课）。

> ✅ 全部 66 课均已补齐 Quiz 题库（每课 10 题，共 660 题）；Level 2/3/4/5/6/7 课程测试接口正常返回题目，且抽题已按维度多样性生效。

### 尚未引入的表（按文档规划，随对应 Phase 引入）

- `review_items`（Phase 6）
- `parking_lot`（Phase 7）
- ~~`study_sessions`（后续）~~ → **Phase 9.1 已引入，落地为 `study_days`（日粒度一行，而非逐次事件）**

> Phase 4 已落地 `quizzes` 与 `lesson_mastery`（替代原规划的 `user_progress`）；Phase 9.1 已落地 `study_days`。

## API 列表

| 端点 | 说明 | 引入 Phase |
|------|------|-----------|
| `GET /api/health` | app / status / database 状态 | 0 |
| `GET /api/dashboard` | 总进度(已完成数/total)、当前 Level、今日推荐 Lesson、`streak_days`；**Phase 9.1 起**新增 `studied_today` / `longest_streak` / `last_study_date`（全部读时计算） | 2（Phase 4 改"已完成"语义为 mastered；9.1 填充真 streak） |
| `GET /api/levels` | 全部 Level，含嵌套 lessons 与**真实派生状态** | 1（Phase 4 状态改为派生） |
| `GET /api/levels/{level_id}/lessons` | 单个 Level 的 lesson 列表 | 1 |
| `GET /api/lessons/{lesson_id}` | 单课详情：基础信息 + 解析后的 content + 下一课指针 + 派生 status/mastery_score；404 on missing | 3 |
| `GET /api/lessons/{lesson_id}/quiz` | 取该课 Quiz（**不返回 correct_index / explanation**）；每课题库 10 题（Phase 6.1 起），**随机抽取 5 题且优先维度多样**（无硬约束）；lesson 为 `locked` 时返回 **403** | 4（抽题逻辑 Phase 6.1 升级） |
| `POST /api/lessons/{lesson_id}/quiz/submit` | 提交答案，服务端确定性判分 → 返回 score / passed / status / 每题结果 / 是否解锁下一课；**仅对本次呈现的 5 题判分**（total=提交题数）；未知 question_id → 422，无题 → 400，locked → 403 | 4（判分逻辑 Phase 6.1 升级） |
| `GET /api/lessons/{lesson_id}/notes` | 列出该课全部笔记，按 `created_at` 倒序（最新在前） | V1.0 基线（Notes） |
| `POST /api/lessons/{lesson_id}/notes` | 新建一条笔记（append-only，绝不覆盖历史）；body `{content}`；返回新建笔记 | V1.0 基线（Notes） |
| `DELETE /api/lessons/{lesson_id}/notes/{note_id}` | 删除单条笔记（仅当该笔记确属该 lesson 时才删，否则拒绝）；成功 204 | V1.0 基线（Notes） |
| `GET /api/review/due` | **Phase 6b**：到期的复习列表（mastered 且 `next_review_at <= now`），按课程顺序；含 `overdue_days` | 6b |
| `GET /api/review/{lesson_id}` | **Phase 6b**：取一轮复习（该课题库抽 5 题，不泄露答案；弱维度优先 + 维度多样性）；只要 `mastered` 即可取题（含失败后立即重试）；非 mastered → 403 | 6b |
| `POST /api/review/{lesson_id}/submit` | **Phase 6b**：批改并重新调度。**5/5 才算通过**（4/5 判失败）；通过 → stage+1 且间隔按阶梯延长；失败 → stage 不变、`next_review_at = now+3d`、写 `weak_points`；提交题数 ≠5 → 422；**不改动 status / score / attempts / last_quiz_at** | 6b |
| `GET /api/weak-questions` | **Phase 10.1**：从 `quiz_answer_log` **跨来源（quiz+review+practice）派生**薄弱题列表：`wrong_count` / `last_wrong_at` / `last_attempt_at` / `last_attempt_correct` 全部读时计算，不持久化；过滤 `wrong_count>=1`；排序 wrong_count DESC, last_wrong_at DESC | 10.1 |
| `GET /api/weak-questions/{question_id}` | **Phase 10.1**：单题题面（id/type/prompt/options/dimension），**不含 correct_index**（答案不泄露）；404 on missing | 10.1 |
| `POST /api/weak-questions/{question_id}/practice` | **Phase 10.1**：单题重练。服务端按 `quizzes.correct_index` 判分，追加一行 `quiz_answer_log(source='practice')`（独立事务）；**绝不触碰** mastery / SRS / streak / badge / user_stats | 10.1 |

> Phase 6b 的 `/api/dashboard` 新增 `reviews_due`（与 `/api/review/due` 同源同序）；`/api/levels` 的 lesson 新增 `due_for_review`（布尔，纯视觉提示，**不是第 5 种状态**）。

### 真实状态逻辑（Phase 4 起，由 `lesson_mastery` 派生，替换原占位规则）

`Lesson` 不再存状态，状态由后端按如下规则实时计算（见 `services.py`）：

- `mastered` 🟢：该课 `lesson_mastery.status == "mastered"`（首次达 ≥80% 后锁定，Phase 4 内 re-quiz <80% **不降级**）
- `needs_review` 🟡：该课已提交但最近一次 <80%
- `available` 🔵：未尝试过，且（是课程首课 **或** 前驱课已 `mastered`）
- `locked` 🔒：前驱课未 `mastered`

> 因 `mastered` 粘性且解锁判定只看前驱是否 mastered，**已解锁资格在 Phase 4 内永久保留**（re-quiz 失败不会重新锁住后续课）。

### Quiz 提交与掌握判定（Phase 4）

- 三类题型统一判分：`selected_index == correct_index` 即正确（无 AI / 无自由文本评分）
- 掌握标准：`score = round(correct/total*100)`，`score >= 80` → `passed` + `mastered`；`<80` → `needs_review`
- `attempts` 每次提交 +1（用 `(existing.attempts or 0) + 1`，规避新建行时 SQLAlchemy 默认未生效导致 `None+1` 报错）
- `weak_points` = 最近一次提交答错的 `question_id` 列表（**非长期薄弱点模型**，Phase 6 再做 Review/Spaced Repetition）
- 不建 `quiz_attempts` 历史表（累计次数用 `attempts` 字段表达，历史明细留待 Phase 6）

### Dashboard 推荐规则（Phase 4 更新）

- `completed` = 状态为 `mastered` 的课数（不再是固定 0）
- 今日课程 = 课程顺序中**第一个尚未 mastered** 的课（无论是 `available` 还是 `needs_review`），保证失败后仪表盘仍指向"下一步该做的课"而非空白
- `streak_days` 曾固定为 0；**Phase 9.1 起由 `study_days` 读时计算**（见下方 Phase 9.1 实现记录）

## 前端页面

| 路由 | 内容 | 引入 Phase |
|------|------|-----------|
| `/` | Dashboard：总进度条 + 当前阶段 + 🎯今日任务卡 + 课程地图入口 | 2 |
| `/map` | 课程地图：Level → Lesson 层级 + locked/available/mastered/needs_review 状态图标 | 1（Phase 4 状态词更新） |
| `/lesson/:id` | 学习页面：标题 / 预计时间 / 学习目标 / 概念解释 / 示例 / 必记知识 / 常见错误 / 下一课；按状态显示「开始测验 / 复习测验 / 已掌握」入口 | 3（Phase 4 接 Quiz 入口） |
| `/lesson/:id/quiz` | **Phase 4 新增**：测验页——拉取题目 → 单选作答 → 提交 → 显示得分 / 每题解释 / 通过则提示解锁下一课、未通过提示复习 | 4 |
| `/review/:id` | **Phase 6b 新增**：间隔复习页——5 题（第 n/5 题进度）→ 5/5 显示「🎉 复习通过 + 下次复习 N 天后」；<5/5 显示「还需巩固」→「重新阅读本课」（跳 `/lesson/:id?from=review`）或「直接再挑战一次」 | 6b |
| `/lesson/:id?from=review` | **Phase 6b 新增**：学习页在复习失败入口下显示「先重读一遍，再挑战复习」提示条 + 「再次复习」按钮 | 6b |
| `/wrong-questions` | **Phase 10.1 新增**：薄弱题页——顶部薄弱题总数 + 卡片列表（题干 / `维度 · L{n}` / 错误 N 次 · 最近一次相对时间 / 「最近一次已做对」标签）；点「重新练习」弹单题面板 → 独立作答 → 对错 + 解析（不强制勾选）→ 可重试；提交即写入 `quiz_answer_log(source='practice')` | 10.1 |

## 目录结构

```text
spark-quest-app/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI 入口 + 路由注册 + lifespan
│   │   ├── database.py        # engine / Base / init_db（建表 + 课程/题库幂等种子 + content 回填）
│   │   ├── models.py          # ORM：CourseLevel、Lesson、QuizQuestion、LessonMastery
│   │   ├── schemas.py         # Pydantic 响应模型（含 Phase 4 Quiz*/QuizResult*、LessonOut 增 status/mastery_score）
│   │   ├── services.py        # 共享逻辑：ordered_lessons / compute_lesson_status / mastery_score / lesson_status_map（真实派生）
│   │   ├── course_seed.json   # 种子数据（含 66 课的结构化 content：L0-L7）
│   │   ├── quiz_seed.json     # 题库种子（66 课 × 10 题 = 660 题，按 lesson_slug；Phase 6.1/6.2 + Level 3/4/5/6/7 扩充）
│   │   └── routers/
│   │       ├── courses.py     # /api/levels、/api/levels/{id}/lessons
│   │       ├── dashboard.py   # /api/dashboard（Phase 4：completed=mastered 数，今日课=首个未 mastered）
│   │       ├── lessons.py     # /api/lessons/{id}（Phase 3，返回派生 status/mastery_score）
│   │       ├── quizzes.py     # Phase 4：/api/lessons/{id}/quiz、/api/lessons/{id}/quiz/submit（P6b：首次掌握时写入复习锚点）
│   │       ├── review.py      # Phase 6b：/api/review/due、/api/review/{id}、/api/review/{id}/submit
│   │       └── migrate.py     # 幂等迁移（P6.1 dimension；P6b lesson_mastery 五列 + 存量回填；P9.1 study_days 回填）
│   ├── _p6b_e2e_check.py      # Phase 6b 端到端验收脚本（跑在 DB 临时副本上，不污染真库）
│   ├── _p91_e2e_check.py      # Phase 9.1 Streak 端到端验收脚本（28 项，跑临时库；真库只读）
│   ├── _p91_smoke.py          # Phase 9.1 API 冒烟（真提交 → 快照 → 还原）
│   ├── .venv/
│   ├── requirements.txt
│   └── spark_quest.db
├── frontend/
│   ├── src/
│   │   ├── main.tsx           # 路由（/、/map、/lesson/:id、/lesson/:id/quiz）
│   │   ├── index.css          # 全局样式
│   │   ├── types.ts           # API 类型（LessonStatus = locked/available/mastered/needs_review；Quiz* 类型）
│   │   └── components/
│   │       ├── ui/                    # Badge / Icon / ProgressRing
│   │       ├── RichText.tsx + .css    # 零依赖富文本渲染
│   │       ├── map/                   # v1.1 课程地图（mapLayout.ts 纯函数 + 5 个组件 + map.css）
│   │       └── StreakBadge.tsx + .css # Phase 9.1：🔥 三态（active / at-risk / broken）
│   │   └── pages/
│   │       ├── Home.tsx + Home.css       # Dashboard
│   │       ├── MapPage.tsx + MapPage.css # 课程地图（Phase 4 状态词/图例更新）
│   │       ├── LessonPage.tsx + LessonPage.css # 学习页面（Phase 4 接 Quiz 入口，按状态显示）
│   │       ├── QuizPage.tsx + QuizPage.css # Phase 4 新增：测验页（P6b 复习页复用其题目卡片样式）
│   │       └── ReviewPage.tsx + ReviewPage.css # Phase 6b 新增：间隔复习页
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts         # 端口 6001，proxy /api → 9000
├── README.md
├── CURRENT_STATE.md           # 本文件
└── .gitignore
```

## 关键约定与坑位

- **端口 6000 不可用**：Chromium 内核浏览器（Chrome/Edge）把 6000 列为 `ERR_UNSAFE_PORT`（X11 保留），访问会显示"网页似乎有问题或已永久移动"。前端统一用 **6001**。Chromium 不安全端口黑名单含 1,7,9,…,6000,6667,…,10080 等。
- **npm 缓存目录沙箱限制**：`npm install` 默认缓存 `AppData` 会被沙箱拦截（EPERM）。用 `--cache <项目内目录>` 规避，如 `npm install --cache .npm-cache`。
- **`rm` 用相对路径**：绝对路径会被 safe-delete 钩子错误拼接导致失败，`cd` 后用相对路径 `rm`。
- **tsc -b EPERM**：写 `tsconfig.tsbuildinfo` 报 EPERM 时，删除旧 tsbuildinfo 重跑。
- **停前端**：`TaskStop` 只杀 npm 外壳，node 子进程残留占端口，需 `taskkill /PID <pid> /F`。
- **后端进程不止一个**：用 `uvicorn --reload` 时会派生 reloader + server 两个子进程，停止时必须用 `Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'uvicorn.*9000' }` 找全所有 python 进程并一并 Stop-Process，仅杀 reloader 会留下孤儿 server 进程占住端口（Phase 3 调试时踩到）。
- **`vite build` 清 dist 失败**：safe-delete 钩子对 `dist/` 报 trash 错误，预先 `rm -rf dist` 再 build 即可。
- **不引入**（按文档明确的非目标）：Alembic / Redis / Docker / AI / 用户系统 / 登录鉴权。
- **每阶段最小可运行**：业务表随对应 Phase 引入，不提前实现后续功能。
- **课程内容数据化**（Phase 3）：所有课程文本存于 `lessons.content`（JSON 文本列），React 端零硬编码课程文本——通过 `/api/lessons/{id}` 拉取后渲染。
- **Phase 3 顺带修的两个历史 bug**：
  1. `LessonOut` 缺 `order_index` 字段（Phase 1 遗留，地图显示 `NaN`）— 已补齐
  2. `index.css` 的 `.card a { color: #2563eb }` 覆盖了 `.btn-primary` 的 `color: #fff`（Phase 2 遗留，首页「开始学习」文字不可见）— 改用 `.card a:not(.btn-primary)`

- **Phase 4 顺带修复/踩坑**：
  1. **`existing.attempts + 1` 报 `TypeError: NoneType + int`**：SQLAlchemy 的 `mapped_column(default=0)` 是 Python 端默认值，**仅在 INSERT（flush）时生效**，新建对象在提交前 `attempts` 属性为 `None`。改为 `(existing.attempts or 0) + 1`（对新建行与已有 NULL 行都安全）。同理任何"读取自身再 +1"的计数字段都要防御 `None`。
  2. **uvicorn `--reload` + `.pyc` 陈旧导致改了代码却不生效**：编辑 `.py` 后 WatchFiles 触发 Reload，但若旧 worker 仍在处理在途请求，或 `__pycache__` 的 `.pyc` 因 mtime 精度被复用，会命中旧代码（现象：traceback 行号指向新注释行、行为不变）。排查时直接 `rm -rf app/__pycache__` 并以**不带 `--reload`** 方式重启，可彻底排除陈旧字节码；日常开发用 `--reload` 即可。
  3. **调试端口被孤儿 uvicorn 占用**：多次启停会在 9000 留下 reloader + server 多个孤儿进程（含 `--reload` 派生的 `multiprocessing.spawn` 子进程），`Get-NetTCPConnection -LocalPort 9000` 看到的 `OwningProcess` 可能是子进程而非你在 `Stop-Process` 的父 PID。`$pid` 在 PowerShell 中是只读常量，遍历进程时务必用别的变量名（如 `$id`）。停服要kill净所有 `app.main` 相关 python 进程再重启，否则 curl 会命中旧版本（如 quiz 接口 404）。

## 浏览器自动化能力（已就绪，用于 UI 验证）

- `agent-browser`（全局 CLI，v0.27.0）已安装，Chromium 位于 `C:\Users\Administrator\.agent-browser`
- 用法：`agent-browser open <url>` → `agent-browser screenshot --full <path>` → `agent-browser close`

## Phase 4 实现记录（已完成，待用户验收）

**目标**：在每课 `/lesson/:id` 之后接 Mastery Quiz，并打通「测验 → 最小进度 → 解锁下一课」的最小可运行闭环。

**已落地**：
- 新增 `quizzes` 表 + `quiz_seed.json`（44 题，11 课 × 4 题，三类题型：单选/判断/应用）
- 新增 `lesson_mastery` 表（每课一行，替代原规划的 `user_progress`；字段见上方"数据库结构"）
- `GET /api/lessons/{id}/quiz`（不泄露答案）+ `POST /api/lessons/{id}/quiz/submit`（服务端确定性判分）
- 掌握标准 ≥80% → `mastered`，<80% → `needs_review`
- **粘性 mastered**（Phase 4 内不降级、不重新锁后续课）
- 解锁逻辑：首课默认 `available`，其余课前驱 `mastered` 才 `available`
- 真实派生状态 `locked / available / mastered / needs_review`，替换原占位逻辑
- 前端：`/lesson/:id/quiz` 测验页；`/map` 与 `/lesson/:id` 按真实状态显示
- Dashboard：`completed` = mastered 数；今日课 = 首个未 mastered 课
- `weak_points` = 最近一次提交答错的 question_id 列表（Phase 6 再做长期薄弱点/复习）

**自测结果（端到端，8 项全过）**：
1. `GET /api/health` 正常
2. `GET /api/lessons/1/quiz` 返回题目且**不含** correct_index/explanation
3. `GET /api/lessons/2/quiz`（locked）→ 403
4. lesson 1 全对提交 → `mastered` + `unlocked_next=true` + lesson 2 变 `available`
5. lesson 1 再测全错 → `passed=false` 但 `status` 仍 `mastered`（粘性），lesson 2 不回退为 locked
6. lesson 2 首测全错 → `needs_review` + `unlocked_next=false`，lesson 3 仍 locked（403）
7. Dashboard 今日课正确指向首个未 mastered 课
8. 前端 `tsc -b` 通过；Vite proxy `/api` → 9000 正常

> 说明：本机浏览器自动化（agent-browser）在当前沙箱冷启动卡死，未做可视化截图验证；后端逻辑与前后端联通已由上述 API/代理/类型检查覆盖。

## Phase 8 实现记录 —— Level 2：DataFrame 核心（2026-08-27，部分落地）

**范围（用户确认）**：按用户新路线图，本次只落地 **Level 2：DataFrame 核心（10 课）**；数据读写（CSV/Parquet/JSON/JDBC/partitionBy）并入 Level 2；Hive 不纳入；Level 3（Spark SQL）及之后暂不动。

**已落地**：
- 新增 `course_levels` 行：Level 2（order_index=2，id=3，status=active）
- 新增 10 课（slug 前缀 `l2-*`），内容沿用七要素 content（explanation / examples / key_points / common_mistakes / review / problem / preview）
  1. `l2-what-is-dataframe` DataFrame 是什么
  2. `l2-create-dataframe` 创建 DataFrame（集合 / CSV / JSON / Parquet）
  3. `l2-schema-types` Schema 与数据类型
  4. `l2-inspect` 检视数据（show / printSchema / 列引用）
  5. `l2-select-filter` select / filter / where
  6. `l2-withcolumn` withColumn 与 Column 表达式
  7. `l2-sort-dedup` 排序、去重与常用操作
  8. `l2-groupby-agg` groupBy 与聚合
  9. `l2-write-data` 数据写出
  10. `l2-comprehensive` DataFrame 综合练习（迷你 ETL）
- 同步更新 `backend/app/course_seed.json`（幂等：若已存在 Level 2 则跳过 JSON 写入）；数据库 upsert 按 slug 跳过已存在课程，**未触碰 Level 0/1 与 lesson_mastery 进度**
- 校验：10 课 content 七要素齐全、JSON 合法；lessons 总数 21（原 11 + 新增 10）；Level 0/1 课程数仍为 11

**2026-08-27 二次升级（用户评估后）**：针对「Level 2 缺少 Level 1 灵魂」的评估报告，为 Level 2 全部 10 课补足 Level 1 标志性模块——每课新增【一个直观的心智模型】（鲜活实体隐喻，如宜家包装箱清单、净水滤网流水线、水果分拣派对、成品出库发货）与「⚠️ 比喻的边界（很重要）：」（防生搬硬套的硬核警示）。第 1 课原有心智模型、本次补边界；其余 9 课两者皆补；并就 peer-programmer 口吻做了整体润色。插入点位于「写下代码后 / 关键认知 / 自测」之前，对齐 Level 1「人话理解 → 心智模型 → 比喻边界 → 正式定义 → 机制」的节奏。

- 校验（二次升级）：每课 explanation 恰好含 1 个【一个直观的心智模型】与 1 个「⚠️ 比喻的边界（很重要）：」，无重复插入；JSON 合法；Level 0/1 不受影响。同步写入 `backend/app/course_seed.json`。

**脚本**：`backend/seed_level2.py`（一次性幂等 upsert）；`backend/upgrade_level2.py`（二次升级：心智模型 + 比喻边界，幂等可重跑）——均已保留在项目内。

**课程编写规范（2026-08-27 新增）**：在 `spark_quest/docs/` 沉淀三件套——
- `Spark_Quest_课程编写规范.md`（主规范：教学理念 / 七要素结构 / 概念解释规范 / 示例 / 前后连接 / Quiz / AI 自检清单 + 心智模型·比喻边界·文风·落库章节）
- `Spark_Quest_Lesson_模板与范例.md`（可直接填充的 content JSON 骨架 + 填写范例 + 常见错误对照）
- `Spark_Quest_心智模型与比喻边界案例库.md`（按概念归类的已落地隐喻/边界与跨课一致性道具表）
- 规范把「每课必配【一个直观的心智模型】+ ⚠️ 比喻的边界（很重要）：」确立为 v1.0 标准；Level 0/1 早期课除 `l1-what-is-rdd` 外仍缺显式边界，列为待升级项。

**未解决 / 后续**：
- ✅ Level 2 的 10 课 Quiz 已补齐（见 `seed_quiz_level2.py`；50 题，5 类题型），测验接口对 Level 2 现已正常返回题目。
- ✅ Level 3（Spark SQL，9 课）已于 2026-08-28 落地（见下方「Level 3 实现记录」）；Level 4（执行计划，9 课）已于 2026-08-28 落地（见下方「Level 4 实现记录」）；✅ Level 5（Partition/Shuffle）、Level 6（JOIN 深类型与 Broadcast）、Level 7（性能调优）已全部落地（L6/L7 均于 2026-08-29 完成，见下方对应实现记录）——Phase 8 课程主线完成。

## Level 3 实现记录 —— Spark SQL（2026-08-28）

**范围（用户确认）**：在 Level 2（DataFrame 核心）之后落地 **Level 3：Spark SQL（9 课）**。设计原则严格"不抢跑 L4–L7"——SQL 与 DataFrame API 共享同一套 Catalyst 优化大脑；每课尽量与 Level 2 的等价 DataFrame 操作配对；JOIN 只做轻量 INNER 入门（深类型 / broadcast / 调优留给 Level 6）；UDF 点出"为什么慢"作为 Level 7 伏笔；明确不接入 Hive Metastore（沿用既有约束）。

**已落地**：
- 新增 `course_levels` 行：Level 3（order_index=3，id=4，status=active）
- 新增 9 课（slug 前缀 `l3-*`），内容沿用七要素 content（explanation / examples / key_points / common_mistakes / review / problem / preview），且每课 explanation 含 v1.0 规定的 5 个固定小节（【先用人话理解】/【一个直观的心智模型】/⚠️ 比喻的边界（很重要）：/【正式的技术定义】/【写下代码后，Spark 内部发生了什么】）
  1. `l3-what-is-spark-sql` Spark SQL 是什么
  2. `l3-temp-views` 临时视图（Temporary View）
  3. `l3-select-basics` SELECT 基础
  4. `l3-where-order-limit` WHERE / ORDER BY / LIMIT
  5. `l3-groupby-having` GROUP BY 与 HAVING
  6. `l3-joins-intro` 多表关联（JOIN）入门（仅 INNER，深类型留 L6）
  7. `l3-functions-and-udf` 内置函数与 UDF（点出 UDF 慢 → L7 伏笔）
  8. `l3-tables-and-formats` Spark SQL 与表 / 文件格式（CREATE TABLE ... USING ... LOCATION；不接 Hive）
  9. `l3-comprehensive` Spark SQL 综合练习（读 CSV → 注册 → 多步 SQL → 写出）
- 每课 10 题，共 90 题，`single_choice`、`dimension` 开放词表（concept/why/mechanism/apply/comparison/debug），全部带 `explanation`；题库随 `quiz_seed.json` 与运行库同步写入。
- 跨课一致性：复用 v1.0 道具表（Catalyst = 同一套优化大脑；临时视图 = 仓库门口临时工牌），并在「心智模型与比喻边界案例库」登记 Level 3 的新隐喻。
- 同步更新 `backend/app/course_seed.json`（幂等：若已存在 Level 3 则跳过 JSON 写入）与 `backend/app/quiz_seed.json`（按 lesson_slug 追加，已存在则跳过）；数据库 upsert 按 slug 跳过已存在课程/题库，**未触碰 Level 0/1/2 与 lesson_mastery 进度**。

**脚本**：`backend/seed_level3.py`（一次性幂等 upsert；JSON 合并 + DB upsert 一体，并顺带处理题库，覆盖 seed_level2 与 expand_quizzes 的分体模式）。

**校验**：
- DB：levels=4、lessons=30、quizzes=300、lesson_mastery=17（进度未动）。
- 9 个 L3 课每课 `quizzes` = 10，`correct_index` ∈ [0,3]；全部 L3 课 content 七要素齐全、explanation 五小节齐全；JSON 合法。
- 前端 `npm run build`（`tsc -b` + vite）通过：**tsc -b 类型检查通过**；vite 产出因 safe-delete 钩子拦截 `dist/` 清理而需在临时配置下构建（环境限制，非代码问题，已用临时 outDir 验证可正常产出 index.html + assets）。

**未做 / 后续**：
- ✅ Level 4（执行计划，9 课）已于 2026-08-28 落地（见下方「Level 4 实现记录」）；✅ Level 5（Partition/Shuffle）、Level 6（JOIN 深类型与 Broadcast）、Level 7（性能调优）已落地（L6/L7 均于 2026-08-29，见下方「Level 6 / Level 7 实现记录」）——Phase 8 课程主线完成。
- 案例库 slug 一致性：原 `Spark_Quest_心智模型与比喻边界案例库.md` 中 `l2-sort-dedup-limit` / `l2-inspect-data` 与种子实际 slug `l2-sort-dedup` / `l2-inspect` 不符，本次一并校正。

## Level 4 实现记录 —— 执行计划（2026-08-28）

**范围（用户确认）**：在 Level 3（Spark SQL）之后落地 **Level 4：执行计划（9 课）**。设计上严格"不抢跑 L5–L7"——只教"怎么看懂 Spark 怎么算"，不展开 Shuffle/分区调优（L5）、JOIN 策略（L6）、Tungsten 内存细节（L7）；复用 Catalyst=优化大脑、Shuffle=空中飞货、Driver=前台、Executor=工人 等已登记道具。

**已落地**：
- 新增 `course_levels` 行：Level 4（order_index=4，id=5，status=active）
- 新增 9 课（slug 前缀 `l4-*`），内容沿用七要素 content（explanation / examples / key_points / common_mistakes / review / problem / preview），且每课 explanation 含 v1.0 规定的 5 个固定小节（【先用人话理解】/【一个直观的心智模型】/⚠️ 比喻的边界（很重要）：/【正式的技术定义】/【写下代码后，Spark 内部发生了什么】）
  1. `l4-why-explain` 为什么该看执行计划
  2. `l4-logical-vs-physical` 逻辑计划 vs 物理计划（四段 Parsed→Analyzed→Optimized→Physical）
  3. `l4-explain-api` explain() 怎么用（默认 / True / formatted 三档）
  4. `l4-read-plan` 怎么读执行计划文本（Scan/Filter/Project/Aggregate/Exchange）
  5. `l4-catalyst-rules` Catalyst 优化规则（谓词下推/列裁剪/常量折叠/null 传播）
  6. `l4-wholestage-codegen` WholeStageCodegen 与 Tungsten（*(N) 融合标记）
  7. `l4-dependency-narrow-wide` 窄依赖 vs 宽依赖（Stage 边界根源）
  8. `l4-job-stage-task` Job / Stage / Task 层级模型
  9. `l4-comprehensive` 综合练习（独立读图：找 Exchange → 数 Stage → 找优化点）
- 每课 10 题，共 90 题，`single_choice`、`dimension` 覆盖 concept/why/mechanism/apply/comparison 五类（+ 部分 debug），全部带 `explanation`；题库随 `quiz_seed.json` 与运行库同步写入。
- 跨课一致性：复用 v1.0 道具表，并在「心智模型与比喻边界案例库」登记 Level 4 的新隐喻（设计师概念图 vs 施工图、Stage、WholeStageCodegen、Job→Stage→Task）。
- 同步更新 `backend/app/course_seed.json`（幂等：若已存在 Level 4 则跳过 JSON 写入）与 `backend/app/quiz_seed.json`（按 lesson_slug 追加，已存在则跳过）；数据库 upsert 按 slug 跳过已存在课程/题库，**未触碰 Level 0/1/2/3 与 lesson_mastery 进度**。

**脚本**：`backend/seed_level4.py`（一次性幂等 upsert；JSON 合并 + DB upsert 一体，沿用 `seed_level3.py` 模式）。

**校验**：
- DB：levels=5、lessons=39、quizzes=390、lesson_mastery=18（进度未动）。
- 9 个 L4 课每课 `quizzes` = 10，`correct_index` ∈ [0,3]，dimension 无 NULL；全部 L4 课 content 七要素齐全、explanation 五小节齐全；JSON 合法。
- 前端 `npm run build`（`tsc -b` + vite）未改前端，无需重跑；课程文本数据化经 `/api/lessons/{id}` 渲染，与既有 L0–L3 一致。

**未做 / 后续**：
- ✅ Level 5（Partition/Shuffle）已于 2026-08-28 落地；✅ Level 6（JOIN 深类型与 Broadcast）与 Level 7（性能调优）均已于 2026-08-29 落地（见下方「Level 6 / Level 7 实现记录」）——Phase 8 课程主线完成。
- Level 4 综合练习只验收"读得懂"，不要求调优（呼应设计稿红线）。

## Level 5 实现记录 —— 分区与 Shuffle（2026-08-28）

**范围（用户确认）**：在 Level 4（执行计划）之后落地 **Level 5：分区与 Shuffle（9 课）**。设计上严格"不抢跑 L6–L7"——只教"数据怎么被切分（分区）、又在什么情况下被搬来搬去（Shuffle）及其代价"，不展开 JOIN 策略深类型（L6）、Tungsten 内存细节（L7）、具体调优参数/最优分区数（L7）；复用 Catalyst=优化大脑、Shuffle=空中飞货、Driver=前台、Executor=工人、Stage=不跨车间工序段、Job→Stage→Task 等已登记道具，并把 L4 的窄/宽依赖定义延展到分区物化层面。

**已落地**：
- 新增 `course_levels` 行：Level 5（order_index=5，id=6，status=active）
- 新增 9 课（slug 前缀 `l5-*`），内容沿用七要素 content（explanation / examples / key_points / common_mistakes / review / problem / preview），且每课 explanation 含 v1.0 规定的 5 个固定小节（【先用人话理解】/【一个直观的心智模型】/⚠️ 比喻的边界（很重要）：/【正式的技术定义】/【写下代码后，Spark 内部发生了什么】；综合练习 l5-comprehensive 亦含五小节，未踩 L3 早期"comprehensive 缺小节"的坑）
  1. `l5-what-is-partition` 分区是什么
  2. `l5-partition-count-parallelism` 分区数与并行度
  3. `l5-what-is-shuffle` Shuffle 是什么
  4. `l5-shuffle-cost` Shuffle 为什么贵
  5. `l5-narrow-wide-partition` 窄/宽依赖在分区层面的含义
  6. `l5-shuffle-trigger-operators` 哪些操作会触发 Shuffle
  7. `l5-reducebykey-vs-groupbykey` reduceByKey vs groupByKey
  8. `l5-repartition-coalesce` repartition vs coalesce
  9. `l5-comprehensive` 综合练习（独立读图：找 Shuffle → 数 Stage → 估并行度 → 指 reduceByKey 优化点）
- 每课 10 题，共 90 题，`single_choice`、`dimension` 覆盖 concept/why/mechanism/apply/comparison 五类（无 NULL），全部带 `explanation`；题库随 `quiz_seed.json` 与运行库同步写入。
- 跨课一致性：复用 v1.0 道具表，并在「心智模型与比喻边界案例库」登记 Level 5 的新隐喻（托盘/货盘、工人数量上限=托盘数、装箱→装车→卸货分拣、车间本地先捆小包再空运、推倒重排 vs 就地并拢）；案例库原 §6/§7 顺延为 §7/§8，新增 L5 章节为 §6。
- 同步更新 `backend/app/course_seed.json`（幂等：若已存在 Level 5 则跳过 JSON 写入）与 `backend/app/quiz_seed.json`（按 lesson_slug 追加，已存在则跳过）；数据库 upsert 按 slug 跳过已存在课程/题库，**未触碰 Level 0/1/2/3/4 与 lesson_mastery 进度**。

**脚本**：`backend/seed_level5.py`（一次性幂等 upsert；JSON 合并 + DB upsert 一体，沿用 `seed_level4.py` 模式）。

**校验**：
- DB：levels=6、lessons=48、quizzes=480、lesson_mastery=18（进度未动）。
- 9 个 L5 课每课 `quizzes` = 10，`correct_index` ∈ [0,3]，dimension 五类全覆盖、无 NULL；全部 L5 课 content 七要素齐全、explanation 五小节齐全；JSON 合法。
- 收尾核验按「Spark_Quest_新增Level_收尾核验踩坑.md §5」参数化脚本（`ORDER_INDEX=5, PREFIX="l5-"`）跑通：连真库 `backend/spark_quest.db`（非 `app/sparkquest.db`）、`quizzes` 用 `lesson_id` 关联、聚合结构、`content` 用实现态七键——全绿。

**未做 / 后续**：
- ✅ Level 6 与 Level 7 均已落地（见下方「Level 6 / Level 7 实现记录」）——Phase 8 课程主线（Level 0–7）至此全部完成。
- Level 5 综合练习只验收"看得懂分区与 Shuffle、能识别触发点"，不要求给出调优参数或最优分区数（呼应设计稿红线）。

## Level 6 实现记录 —— JOIN 深类型与 Broadcast（2026-08-29）

**范围（依据 `spark_quest/docs/Spark_Quest_Level6_执行计划_设计.md`）**：在 Level 5（分区与 Shuffle）之后落地 **Level 6：JOIN 深类型与 Broadcast（9 课）**。把 L3 埋下的「JOIN 必 Shuffle、深类型留 L6」、L4 埋下的 `BroadcastHashJoin`/`SortMergeJoin` 计划标记、L5 埋下的「Shuffle 代价 / 空中飞货」全部延展到 JOIN 策略层面。

**红线（未抢跑 L7）**：不展开 Tungsten 内存/堆外/编码字节级；不展开 shuffle 分区数最优值与深调优参数；广播阈值只讲「存在这把尺子」的概念（不给数值）；skew 只到「识别 + 原理级应对」（salting / 隔离大 key / BHJ 绕过），不写 `skewJoin` 类开关；不重复 L3 INNER 语法、L4 explain 读法、L5 Shuffle 定义与代价。

**已落地**：
- 新增 `course_levels` 行：Level 6（order_index=6，id=7，status=active）
- 新增 9 课（slug 前缀 `l6-*`），content 七要素齐全（explanation / examples / key_points / common_mistakes / review / problem / preview），每课 explanation 含 5 个固定小节（含 `l6-comprehensive`）：
  1. `l6-what-is-join` JOIN 是什么（为什么比单表聚合更重）
  2. `l6-join-strategies-overview` JOIN 策略全景（Spark 怎么拼）
  3. `l6-broadcast-hash-join` Broadcast Hash Join（小表广播）
  4. `l6-sort-merge-join` Sort-Merge Join（大表×大表默认）
  5. `l6-shuffle-hash-join` Shuffle Hash Join 与兜底策略
  6. `l6-how-spark-chooses` Spark 怎么选 JOIN 策略（基于代价）
  7. `l6-broadcast-hint-and-control` 主动控制：broadcast() 提示与避坑
  8. `l6-join-data-skew` JOIN 中的数据倾斜（Skew）
  9. `l6-comprehensive` 综合练习（诊断五步：判大小 → 看计划 → 数 Exchange → 给/不给 hint → 查倾斜）
- 每课 10 题，共 90 题，`single_choice`、`dimension` 五类各 2 题（concept/why/mechanism/apply/comparison），全部带 `explanation`；`correct_index` ∈ [0,3] 且**每课四个位置均被打散**（避免学员按位置猜答案）。
- 跨课一致性：复用已登记道具（Catalyst=优化大脑、Shuffle=空中飞货、Driver=前台、Executor=工人、JOIN=两拨货按 key 拼桌、托盘=分区、Stage=不跨车间工序段），并在案例库登记 Level 6 的 5 个新隐喻（小册子复印 N 份=BHJ、两本按 key 排序的电话簿逐页对照=SMJ、抽屉柜流式查=SHJ、Catalyst 看两桌人数决定拼法=策略自动选择、某把椅子挤满 90% 的人=数据倾斜）；案例库原 §7/§8 顺延为 §8/§9，新增 L6 章节为 §7。
- 同步更新 `backend/app/course_seed.json`（幂等）与 `backend/app/quiz_seed.json`（按 lesson_slug 追加）；数据库 upsert 按 slug 跳过已存在课程/题库，**未触碰 Level 0–5 与 lesson_mastery 进度**。

**脚本**：`backend/seed_level6.py`（复制 `seed_level5.py` 模式，一次性幂等 upsert）。落库前已备份 `spark_quest.db.bak_before_l6` / `course_seed.json.bak_before_l6` / `quiz_seed.json.bak_before_l6`。

**校验**：
- 运行前 DB：levels=6、lessons=48、quizzes=480、lesson_mastery=18
- 运行后 DB：levels=7、lessons=57、quizzes=570、lesson_mastery=18（进度未动）
- L0–L5 课数不变（5/6/10/9/9/9）；9 个 L6 课每课 `quizzes` = 10，选项无重复、4 选项、`correct_index` 合法、dimension 五类全覆盖；全部 L6 课 content 七要素齐全、explanation 五小节齐全；JSON 合法无乱码。
- 收尾核验按「Spark_Quest_新增Level_收尾核验踩坑.md §5」参数化脚本（`ORDER_INDEX=6, PREFIX="l6-"`）跑通：连真库 `backend/spark_quest.db`、`quizzes` 用 `lesson_id` 关联（无 `lesson_slug` 列）、`quiz_seed.json` 聚合结构、`content` 用实现态七键——全绿；新 Level 在 `lesson_mastery` 引用 = 0。

**未做 / 后续**：
- ✅ Level 7（性能调优）已落地（见下方 Level 7 实现记录）——**Phase 8 课程主线（Level 0–7）至此全部完成**。
- Level 6 综合练习只验收「看得懂 JOIN 策略与触发点、能选策略、能给 hint」，不要求手调参数。

## Level 7 实现记录 —— 性能调优（2026-08-29）

**范围（依据 `spark_quest/docs/Spark_Quest_Level7_执行计划_设计.md`）**：在 Level 6（JOIN 深类型与 Broadcast）之后落地 **Level 7：性能调优（9 课）**，是 Phase 8 课程主线的最后一关。把 L3 埋下的 UDF 慢、L4 埋下的 Tungsten/WholeStageCodegen 内存细节、L5 埋下的 shuffle 分区数与 spill、L6 埋下的广播阈值与 skew 深调优**全部收口到一套调优方法论**。

**红线（不越界）**：不讲集群资源调度层（YARN/K8s 队列、动态资源分配）；不展开 GC 调优；不给万能最优参数值（只给起点思路与取舍）；不重复 L4 explain 读法、L5 Shuffle 定义与代价、L6 JOIN 策略框架；不引入外部监控体系。

**已落地**：
- 新增 `course_levels` 行：Level 7（order_index=7，id=8，status=active）
- 新增 9 课（slug 前缀 `l7-*`），content 七要素齐全（explanation / examples / key_points / common_mistakes / review / problem / preview），每课 explanation 含 5 个固定小节（含 `l7-comprehensive`）：
  1. `l7-what-is-tuning` 性能调优是什么（度量驱动的闭环）
  2. `l7-tungsten-encoding` Tungsten 与编码字节级
  3. `l7-executor-memory` Executor 内存模型与 OOM 根因
  4. `l7-shuffle-partitions` Shuffle 分区数怎么定
  5. `l7-broadcast-threshold` 广播阈值调优
  6. `l7-aqe` AQE：让 Spark 在运行时自我修正
  7. `l7-skew-tuning` 数据倾斜实战处理
  8. `l7-read-less-data` 最优先的调优：少读、少传、少算
  9. `l7-comprehensive` 综合练习（诊断清单与优先级）
- 每课 10 题，共 90 题，`single_choice`、`dimension` 五类各 2 题（concept/why/mechanism/apply/comparison），全部带 `explanation`；`correct_index` ∈ [0,3] 且**每课四个位置均被打散**（沿用 L6 的做法，写完后重排并复核）。
- 跨课一致性：复用已登记道具（Catalyst=优化大脑、Shuffle=空中飞货、Executor=工人、分区=托盘、BHJ=小册子、skew=挤满人的椅子、UDF=临时外聘手艺人、谓词下推=滤网瞬移），并在案例库登记 Level 7 的 7 个新隐喻（木桶/最慢工序、真空压缩袋、货车车厢四格、车道数与车流、秤的刻度、会实时改路的导航、交警堵点分流）；案例库原 §8/§9 顺延为 §9/§10，新增 L7 章节为 §8。
- 同步更新 `backend/app/course_seed.json`（幂等）与 `backend/app/quiz_seed.json`（按 lesson_slug 追加）；数据库 upsert 按 slug 跳过已存在课程/题库，**未触碰 Level 0–6 与 lesson_mastery 进度**。

**脚本**：`backend/seed_level7.py`（复制 `seed_level6.py` 模式，一次性幂等 upsert）。落库前已备份 `spark_quest.db.bak_before_l7` / `course_seed.json.bak_before_l7` / `quiz_seed.json.bak_before_l7`。

**校验**：
- 运行前 DB：levels=7、lessons=57、quizzes=570、lesson_mastery=18
- 运行后 DB：levels=8、lessons=66、quizzes=660、lesson_mastery=18（进度未动）
- L0–L6 课数不变（5/6/10/9/9/9/9）；9 个 L7 课每课 `quizzes` = 10，选项无重复、4 选项、`correct_index` 合法、dimension 五类全覆盖；全部 L7 课 content 七要素齐全、explanation 五小节齐全；JSON 合法无乱码。
- 收尾核验按「Spark_Quest_新增Level_收尾核验踩坑.md §5」参数化脚本（`ORDER_INDEX=7, PREFIX="l7-"`）跑通：连真库 `backend/spark_quest.db`、`quizzes` 用 `lesson_id` 关联、`quiz_seed.json` 聚合结构、`content` 用实现态七键——全绿；新 Level 在 `lesson_mastery` 引用 = 0。
- API 冒烟：`/api/levels` 返回 8 个 Level（末位为 Level 7：性能调优），L7 九课均可通过 `/api/lessons/{id}` 取到完整七要素与五小节；L7 课程 `status=locked` 是既有解锁规则（前置未 mastered），非缺陷。

**未做 / 后续**：
- Phase 8 课程主线已全部完成（Level 0–7）。后续可选方向：Level 0/1 早期课按 v1.0 补「⚠️ 比喻的边界」小节（案例库 §10 已标注）；Phase 6b 间隔重复已完成；Phase 9.1 Streak 已完成（待验收），Badge 未启动；Phase 7 Parking Lot、Phase 10 AI Tutor 仍规划中。
- Level 7 综合练习只验证「会诊断、知道优先级、能给方向」，不要求背参数值。

## Phase 5 实现记录 —— 完整 Progress Dashboard 动态化 + 状态系统（已完成并验收）

**目标**：把 Phase 4 的"最小派生状态"升级为完整状态机，并让 Dashboard 真正动态呈现。

**已落地**：
- 完整进度状态系统（在 Phase 4 的 `locked / available / mastered / needs_review` 派生状态基础上，打通 Dashboard 的动态呈现：总进度、今日任务、课程地图均按真实状态实时渲染）
- 前端 Dashboard / 课程地图 / 学习页三处状态联动一致，不再依赖占位规则
- 通过回归测试（Phase 4 既有 8 项端到端自测 + Dashboard 动态化验证）

**本阶段明确不做（留给后续）**：
- 复习调度 / Spaced Repetition（Phase 6）
- 停车场（Phase 7）
- AI 出题（Phase 10）

## Phase 6.1 实现记录 —— Quiz Bank & Assessment Quality Upgrade（2026-08-27，L0/L1 完成）

**目标**：把每课题库从 4/5 题扩到 10 题，并让每次测验从题库**随机抽取 5 题、优先维度多样**（无硬约束）。这是后续 Review / Spaced Repetition 的基础设施，本身不引入新状态机。

**设计原则（与用户确认）**：
- **维度标签开放**：`quizzes` 新增 `dimension` 列（可空，开放词表 `concept / why / mechanism / apply / comparison / debug`，不固定枚举）。
- **不强制五维全覆盖**：每课 10 题只需"自然覆盖、有一定多样性"，比例按课程性质定；像「Spark 安装环境」可偏 `concept+apply+debug`，不必硬塞 `why/mechanism` 产生垃圾题。
- **抽题无硬约束**：优先从不同维度各取 1 题（维度越分散越好），不足 5 维则从剩余题随机补足；绝不因规则把课绑死。
- **范围先小后大**：本期只做 **Level 0（5 课）+ Level 1（6 课）= 11 课**，验证抽题体验 / 分数分布 / difficulty / 重复感后再扩 Level 2+。质量 > 数量。

**已落地**：
- `backend/app/models.py`：`QuizQuestion` 增加 `dimension: Optional[str]`（可空）。
- `backend/app/migrate.py`（新增）：`migrate.run_migrations()` 用 `ALTER TABLE quizzes ADD COLUMN dimension TEXT`（PRAGMA 检测、幂等），并在 `database.init_db` 中调用，启动即对新库/旧库都生效。独立运行：`cd backend && python -m app.migrate`。
- `backend/expand_quizzes_to_10.py`（新增，幂等）：
  - 更新 `app/quiz_seed.json`：11 课各 4→10 题（保留原 4 题原文，补 6 道新题，全部打 `dimension`）；仅当 `<10` 时追加。
  - 更新运行库：回填 44 道老题的 `dimension`；按 prompt 去重插入 66 道新题（L0/L1 每课 +6）。
- `backend/app/routers/quizzes.py`：
  - `_sample_quiz_questions()`：10 抽 5，按 `dimension` 分组、各维取 1、随机补足、洗牌；无硬约束。
  - `submit_quiz`：改为**仅对本次呈现的 5 题判分**（`total = len(payload.answers)`），`weak_points` 只记这 5 题中答错的；阈值 80% 不变（5 题需 ≥4 对）。
- 前端：`types.ts` 的 `QuizQuestion` 增加 `dimension?`；`QuizPage` 题头显示维度徽标（中文标签），便于人工评估质量/重复感。

**数据现状**：
- 全部 21 课每课 `quizzes` 行数 = 10（共 210 题：L0/L1 = 44 老题 + 66 新题 = 110；L2 = 50 老题 + 50 新题 = 100）。
- 抽题验证：某 L0 课 200 次抽样，抽中 5 题的「不同维度数」分布为 `{5: 200}`（本课维度充足时自然全分散）；L2 课（10 题、`dimension` 已打标）同样走多样性抽样，不再退化为"抽全部 5 题"。
- `submit` 验证：全对 → score=100/passed/master；全错 → score=0/needs_review，且仅基于 5 题。

**未做 / 后续**：
- 真正的 `review_items` / Spaced Repetition（原 Phase 6 主体，现为 Phase 6b）仍规划中；Phase 6.1/6.2 的 `dimension` 标签与随机抽题为其预留了能力。
- 停车场（Phase 7）、Badge 成就（Phase 9.2）、AI Tutor（Phase 10）仍按原规划；**Streak（Phase 9.1）已完成待验收**。

## Phase 6.2 实现记录 —— Level 2 Quiz Bank 扩至 10 题（2026-08-27，L2 完成）

**目标**：把 Level 2 的 10 课每课从 5 题扩到 10 题（每课 +5 新题 = 共 +50），按与 Phase 6.1 完全相同的标准：开放维度词表、不强制五维、质量优先、保留原题只补差额。复用 `expand_quizzes_to_10.py` 的同一套幂等机制（仅补 10 个 `l2-*` slug、`EXISTING_DIM` 归类、50 道新题到 `NEW_QUESTIONS`）。

**明确不做（本期仍留给后续）**：
- `review_items` / Spaced Repetition 调度（Phase 6b 主体）——首页的「复习测验 / 需复习」仅为 `needs_review` 状态驱动的整份重测，并非复习系统。
- 停车场（Phase 7）
- 游戏化 UI / Badge 成就（Phase 9.2）——**Streak（9.1）已完成，见下方实现记录**
- AI Tutor（Phase 10）

**已落地**：
- `backend/expand_quizzes_to_10.py`（扩展，幂等）：
  - 新增 `L2_SLUGS`（10 个 `l2-*`）+ `ALL_SLUGS = L0L1_SLUGS + L2_SLUGS`；两个处理函数改遍历 `ALL_SLUGS`。
  - `EXISTING_DIM` 新增 10 课各 5 道老题的维度归类（开放词表，自然多样，不硬凑五维）。
  - `NEW_QUESTIONS` 新增 10 课各 5 道新题（共 50），`single_choice`、4 选项含合理干扰项、`explanation` 1–3 句、维度自然多样。
- 执行结果：`quiz_seed.json` 中 10 课各 5→10 题（保留原 5 题原文并补 `dimension`，追加 5 道新题）；运行库回填 50 道老题 `dimension` + 按 prompt 去重插入 50 道新题。`lesson_mastery` 进度与解锁逻辑未触碰。

**验证**：
- DB：10 个 L2 课每课 `quizzes` = 10，`dimension` 无 NULL（全部回填+新题带标）。
- 抽样：某 L2 课（池含全部 6 维度）300 次抽样，抽中 5 题的维度组合分散覆盖全部 6 维（`apply / comparison / concept / debug / mechanism / why` 的多种 5 组合），无 `correct_index` 泄露。
- 前端 `npm run build`（`tsc -b` + vite）通过（前端无改动，仅确认完整性）。
- `submit_quiz` 仍只判本次呈现的 5 题（阈值 80% 不变）。

**数据现状（全部）**：21 课 × 10 题 = 210 题；L0/L1 = 110（44+66），L2 = 100（50+50）。

## Phase 6b 实现记录 —— Lesson 级间隔复习闭环（2026-08-29，已完成并端到端验收）

**目标**：学完 Lesson → 到期 → 做 5 题 → 全对通过 → 延长下一次复习间隔；答错 → 回看本 Lesson → 再做 5 题 → 直到通过。让用户每天打开系统就能明确知道「今天哪些 Lesson 需要复习，复习完下次什么时候复习」。

**硬约束（用户明确划定，已严格遵守）**：
- **不新增任何表**——复习调度信息全部落在既有 `lesson_mastery` 上（原规划的 `review_items` 表不建）
- **不新增 `review_attempts` 历史日志**
- **不新增第 5 种学习状态**——`locked / available / needs_review / mastered` 四状态体系原封不动；复习是 `mastered` 之上的附加调度信息
- **不做 SM-2 / Anki 式 SRS / 个性化遗忘曲线拟合**，只用固定可解释的间隔阶梯
- **复习单位是 Lesson**，不做单题级 SRS、不做每 dimension 独立进度

**调度规则（`services.py`）**：
```
REVIEW_INTERVALS_DAYS = [1, 3, 7, 14, 30, 60, 120]     # srs_stage 索引这张表
REVIEW_FAIL_INTERVAL_DAYS = 3
REVIEW_QUESTION_COUNT = 5
```
- 首次掌握（学习测验第一次转 `mastered`）→ `first_mastered_at = now`、`srs_stage = 0`、`next_review_at = now + 1d`
- 复习通过（5/5）→ `srs_stage + 1`（封顶 6）、`review_count + 1`、`next_review_at = now + INTERVALS[stage]`
- 复习失败（<5/5）→ **`srs_stage` 保持不变**、`next_review_at = now + 3d`（只插入一次短期巩固，不是降级）
- 到达 120 天后封顶，不再无限增长
- `srs_stage` 是权威调度状态，**不可由 `next_review_at` 反推**（失败与「通过 stage0」的间隔都是 3 天，会撞车）；`review_count` 只做统计，不参与调度

**关键设计点：失败后的「立即重做」与「下一次调度」是两个概念。** 失败会把 `next_review_at` 推到 3 天后，但 `GET /api/review/{id}` **只看是否 mastered**，不看是否到期——因此用户读完本课可以立刻再挑战，不受 `next_review_at` 阻挡。

**数据模型变更（最小）**：`lesson_mastery` 新增 5 列 `first_mastered_at / srs_stage / next_review_at / last_review_at / review_count`。`first_mastered_at` 与 `last_quiz_at` 语义分离（前者＝首次掌握，后者＝最近一次测验），不混用。
**存量回填**（`migrate.py::backfill_mastered_review_schedule`）：对 `status='mastered' AND next_review_at IS NULL AND last_quiz_at IS NOT NULL` 的历史行，令 `first_mastered_at = last_quiz_at`、`srs_stage = 0`、`next_review_at = last_quiz_at + 1d`。**代码注释已明确声明**：历史数据没有真实首次掌握时间，`last_quiz_at` 只是**近似锚点**；此后新掌握的 Lesson 用真实 `first_mastered_at`。本次执行回填了 **18 条**存量 mastered 记录。

**改动文件清单（15 个）**：

后端
1. `models.py` — `LessonMastery` 增 5 列 + 类注释说明「review ≠ 新状态」「stage 权威、count 仅统计」
2. `migrate.py` — `add_lesson_mastery_review_columns()`（PRAGMA 检测 + ALTER，幂等）+ 上述回填函数，挂进 `run_migrations()`（`init_db` 已自动调用）
3. `services.py` — 新增 `REVIEW_INTERVALS_DAYS` 等常量 + `is_due_for_review / due_lesson_ids / due_reviews / init_review_schedule / advance_review_schedule / defer_review_schedule`
4. `routers/review.py`（新增）— `/api/review/due`、`/api/review/{id}`、`/api/review/{id}/submit`
5. `routers/quizzes.py` — `submit_quiz` 在「首次转 mastered」分支写入复习锚点（+5 行）；`_sample_quiz_questions` 增加可选 `priority_dims`（弱维度优先，仅排序偏好，非权重模型）
6. `routers/dashboard.py` — `DashboardOut.reviews_due`
7. `routers/courses.py` — `_to_lesson_out` 增加 `due_for_review`
8. `schemas.py` — `ReviewDueItem / ReviewFetchOut / ReviewSubmitIn / ReviewResultOut`；`LessonOut.due_for_review`、`DashboardOut.reviews_due`
9. `main.py` — 注册 review router

前端
10. `types.ts` — `ReviewDue / ReviewFetch / ReviewSubmit / ReviewResult`；`Lesson.due_for_review`、`Dashboard.reviews_due`
11. `main.tsx` — 新增 `/review/:id` 路由
12. `Home.tsx` + `Home.css`/`index.css` — Dashboard「🔁 今日复习」区块（显示 Level 与逾期天数）
13. `MapPage.tsx` — mastered 课加「待复习」角标 + 图例补 🔁
14. `LessonPage.tsx` — mastered 课加「间隔复习（5 题）」入口；`?from=review` 时顶部显示重读提示条 + 「再次复习」按钮
15. `ReviewPage.tsx` + `ReviewPage.css`（新增）— 5 题答题、第 n/5 进度、5/5 闸门、失败态「重新阅读本课 / 直接再挑战一次」

**抽题策略**：复用 Phase 6.1 的 `_sample_quiz_questions`，先按 `dimension` 分组各取 1 题（保证维度覆盖），不足 5 题再随机补足；上一轮答错题目所属 dimension 排在**优先访问顺序**（简单排序偏好，不建权重模型）。每课固定 10 题，抽 5 题永远可行。

**验收（`backend/_p6b_e2e_check.py`，DB 临时副本上运行，不污染真库；37 项全过）**：
1. 新掌握 → `first_mastered_at` 已记录、`next_review_at = +1 天`、`stage=0 / count=0`
2. 到期 → `review/due` 与 Dashboard `reviews_due` 均出现（显示逾期 2 天）
3. `GET /api/review/{id}` → 5 题、不含 `correct_index`、维度分散（`comparison/debug/apply/concept/mechanism`）
4. 5/5 → 通过，`stage 0→1`，间隔 3 天；`review_count=1` 不参与调度
5. 连续通过验证整条阶梯 `1→3→7→14→30→60→120` 全部正确，到 120 天后封顶
6. 4/5 → 判失败；`srs_stage` 不变；`next_review_at = +3 天`；错题 id 写入 `weak_points`；**score / attempts / last_quiz_at / status 四个学习态字段零改动**
7. 失败后（`next_review_at` 已在 3 天后）仍能立即再次取题挑战（HTTP 200）
8. 未到期（+1 天）不出现在今日复习；`reviews_due` 与 `review/due` 完全一致
9. 存量 18 条 mastered 已回填并可正常进入复习（回填锚点＝`last_quiz_at`，近似值）
10. 状态词表仍只有 4 个、复习全程零状态变化、Level 状态词表不变、Map `due_for_review` 只出现在 mastered 课上、Dashboard 进度口径不变、非 mastered 课复习被 403、提交题数 ≠5 被 422

**未做 / 明确不属于 Phase 6b**：SM-2 / Anki 式 SRS、个性化遗忘曲线拟合、单题级 SRS、每 dimension 独立进度、`review_attempts` 历史日志、复杂统计分析、连错智能教学、AI 动态出题。

**遗留 / 观察项**：
- 存量 18 课的首次复习锚点是近似的（= `last_quiz_at`），因此它们几乎全部一次性变为「已逾期」。这是历史数据兼容的必然结果，用户可选择先清一遍再进入正常节奏。
- `.venv` 内新增了 `httpx2`（Starlette TestClient 依赖，仅供验收脚本使用），不影响运行时依赖。

## 概念解释排版增强（2026-08-27）

**问题**：每课概念解释（及上一课回顾 / 本课问题 / 下一课伏笔）正文带有轻量排版标记——`【小节标题】`、行内反引号代码（`` `code` ``）、`**加粗**`、`⚠️ 比喻的边界` 警示、`① ② ③` 与 `·` 列举——但 `LessonPage` 仅按空行切段后原样塞进 `<p>`，导致标题无层级、代码带字面反引号、整段像一堵无排版文字墙。

**方案**：新增零依赖的 `frontend/src/components/RichText.tsx` + `RichText.css`，不引入 Markdown 库、不改动数据库/种子文本。渲染规则：
- 按 `/\n\n+/` 切段；每段若以 `【...】` 开头（或段内粘连的 `【...】` 标题，只要该 `【】` 后接换行/另一 `【`/段尾即视为小节标题）→ 渲染为 `<h4 class="rich-subhead">`。
- 行内解析：`` `code` `` → `<code class="inline-code">`；`**bold**` → `<strong>`。
- `⚠️` 开头段 → 警示块（`.rich-warning`，标题 + 后续非结构段作为正文）。
- `① ② ③`（≥2 个）整段 → `<ol class="rich-list">`；整段以 `· ` 分句（每段都 `·` 开头）→ `<ul class="rich-list rich-list-ul">`。
- 行内 `【...】`（如「Spark 是一个【分布式统一计算引擎】」后接句号）→ 保留为普通文本，不当标题。
- 兼容两种作者习惯：小节之间用空行分隔、或 `【标题】` 与正文粘连未空行分隔（递归 `parseBlock` 处理）。

**已落地**：`LessonPage.tsx` 的 `explanation / review / problem / preview` 四处改用 `<RichText text={...} />`；`examples / key_points / common_mistakes` 已是结构化列表/代码块，未动。

**验证**：`npm run build`（`tsc -b` + vite）通过；以 `react-dom/server` 对样例（含标题/code/有序列表/项目符号/警示/加粗）做静态渲染，输出 HTML 含 `rich-subhead` / `inline-code`（无字面反引号）/ `ol`·`ul` / `rich-warning` / `strong`，符合预期；对全部 21 课四字段跑解析模拟，共解析出 115 个子标题、25 个有序列表、13 个警示块，无异常。

## 概念解释排版增强（续：· 列举修复，2026-08-28）

**问题**：上一轮修复后，标题/代码/警示已正常，但 `l2-select-filter` 等课的正文仍是一坨。根因：这些课的 `·` 列举项是用**单个换行 `\n` 分隔、且与正文混排**（如「先用人话理解…：\n· select=…\n· filter=…\n它们都是 Transformation…」），而非上一轮 `·` 规则假设的「用 `；` 分句且每段都以 `·` 开头」→ 该规则永不命中，整段退化为一个 `<p>`。

**方案（仅前端，不动数据库/种子）**：改 `RichText.renderBlock` 的 `·` 列举识别为**按行识别**——段落按 `\n` 拆行，标记以 `· ` 开头的行；当某段出现 ≥2 个 `· ` 行即视为列举：列表前的普通行 → 一个 `<p>`，连续的 `· ` 行 → `<ul class="rich-list rich-list-ul">`（每项走行内解析），列表后的普通行 → 再一个 `<p>`；<2 个 `· ` 行的段落保持单 `<p>`，避免误伤。 `renderBlock` 返回类型由单 `ReactNode` 改为 `ReactNode[]`（可能含多元素），调用处已用数组收集，结构不变。 `① ② ③` 圆点逻辑仍优先。

**验证**：`npm run build` 通过；以 `react-dom/server` 对「l2-select-filter 风格」样例静态渲染，确认输出 `<h4 class="rich-subhead">` + 多个 `<p>` + 多个 `<ul><li>`（行内 `code` 正常、无字面反引号），不再是一整段；对全部 21 课四字段（84 个文本块）跑 SSR 渲染，0 异常、生成 27 个 `<ul>` 列表、115 个子标题，且无字面 `· ` 泄漏到 HTML。种子实际无反引号（0 处），故 `inline-code` 在语料中为休眠态，但样例已证明可用。

## Lesson Notes 实现记录 —— 学习笔记（V1.0 基线，2026-08-28）

**目标**：允许学习者在 Lesson 学习过程中记录个人理解、疑问、易错点、联想与工作经验连接。定位为"学习过程中产生的个人学习痕迹"，而非复杂编辑系统。

**已落地**：
- `backend/app/models.py`：新增 `LessonNote`（表 `lesson_notes`），字段 `id / lesson_id(FK→lessons.id, ON DELETE CASCADE, 有索引) / content / created_at(默认 datetime.now)`。单用户本地应用，无 `user_id`。
- `backend/app/routers/lessons.py`：在 `lessons` 路由内新增三条端点（详见上方"API 列表"）：
  - `GET /api/lessons/{lesson_id}/notes` → 倒序返回该课全部笔记
  - `POST /api/lessons/{lesson_id}/notes` → 新建一条（`NoteCreate{content}`，append-only，绝不覆盖历史）
  - `DELETE /api/lessons/{lesson_id}/notes/{note_id}` → 仅当笔记确属该 lesson 时删除，否则拒绝；成功 204
- `backend/app/schemas.py`：新增 `LessonNoteOut` / `NoteCreate`。
- 前端 `frontend/src/pages/LessonPage.tsx` + `LessonPage.css`：接入笔记卡（`note-card`），含草稿输入、保存（`POST`）、列表渲染（倒序、`formatNoteTime` 显示时间）、删除（`DELETE`）；`frontend/src/types.ts` 新增 `LessonNote` 接口。
- 建表由 `Base.metadata.create_all` 覆盖（`init_db` 启动时自动创建 `lesson_notes`），无需单独 migration。

**设计要点**：
- **append-only**：每条保存新建一行，历史永不覆盖；删除为硬删（单用户本地，无回收站需求）。
- 不引入 `user_id`（单用户）；不新增 learning state / progress 字段；与既有派生状态体系无耦合。
- 笔记不参与 Mastery / 解锁逻辑，纯个人记录。

**验证**：前端 `npm run build`（`tsc -b` + vite）通过；`LessonPage` 笔记卡渲染逻辑与端点调用完整（草稿态禁用保存、删除即时从列表移除）。浏览器可视化验证受沙箱限制未做截图，但类型检查与端点契约已覆盖。

---

## v1.1 实现记录 — Course Map 重做（2026-09-07）

### 范围
- 仅重做 `pages/MapPage.tsx` 与新增 `components/map/*`
- 不动后端 / `LessonStatus` 四态模型 / API
- 不碰 Dashboard / Lesson / Quiz / Review / Notes

### 新增文件
- `components/map/mapLayout.ts` — 纯函数布局算法（`layoutRegion / regionHeight / segmentPath / regionTone`），零依赖
- `components/map/LessonNode.tsx` — 5 态节点（mastered/needs / /available/locked + due 紫环叠加）
- `components/map/LessonPath.tsx` — SVG 分段道路，一段一课，mastered 点亮该段
- `components/map/JourneyRegion.tsx` — 一个 Level 一个区域，header 含徽章 + 折叠按钮
- `components/map/RegionNav.tsx` — 顶部 8 个区域导航胶囊，点击跳转并展开
- `components/map/MapBackdrop.tsx` — sticky 氛围层（远山/云 + CSS 渐渐），零信息载荷
- `components/map/map.css` — 统一样式（含三档、5 态、响应式、reduced-motion）

### 改写 / 删除
- 改写：`pages/MapPage.tsx`（取数 / 折叠状态 / 自动定位 / 视图切换）
- 删除：`pages/MapPage.css`（174 行旧样式全部废弃）
- 类型收窄：`types.ts` 中 `Level.status: string` → `LevelStatus` 联合类型

### 三档时间叙事（`regionTone()` 派生自 `Level.status`）
| 档位 | 触发 | 增强层 | 信息兜底徽章 |
|------|------|--------|--------------|
| past | `completed` | `saturate(.65) brightness(1.06) contrast(.92) scale(.985)` | 「已通关 · N/N」+ 旗帜 |
| present | `in_progress` / `available` | 无滤镜 + 蓝色描边 + 高光阴影 | 「进行中 · N/N」 |
| future | `locked` | `::after` 白色蒙层 42%，节点 `z-index` 高于蒙层 | 「未解锁 · N 课」+ 锁 |

蒙层浓度 42%（用户底线 30-50%，按实机节点文字清晰度取中位）。past 沉淀保守（saturate(.65)），按用户「先保持不加重」原则。

### 验收
- `tsc -b && vite build` 零错误
- 全展开地图 66 节点 / 列表视图 66 `<li>`
- 5 态齐全（临时插入 needs_review 后还原）
- 禁用氛围层 + 滤镜 + 蒙层后 8 个区域徽章仍清晰
- `mapLayout(11)` 返回 11 坐标（加课无需改码）
- 31 个 `<a>` + 35 个 `<div>`（locked 不可点）
- 375px 窄屏无横向溢出

### 实机截图
- `E:\MMMason\Spark_dlg\ux_audit\v11-01-initial.png` — 1280 宽首屏（默认展开 L4+L5）
- `v11-03-current-focus.png` — 自动定位到当前节点
- `v11-past-closeup.png` — past 沉淀特写（L1 RDD 基础）
- `v11-present-closeup.png` — present 高亮 + current 节点特写（L4 执行计划）
- `v11-future-closeup.png` — future 朦胧特写（L6 JOIN）
- `v11-needs_review-closeup.png` — 琥珀节点验证
- `v11-04-no-ambience.png` — 禁用氛围层后整体可读
- `v11-05-list-view.png` — 列表视图（无障碍兜底）
- `v11-06-narrow-375.png` — 窄屏 375px 无溢出

### 顺手修的两个 bug
1. `currentLessonId` 旧逻辑把 `needs_review` 也算进 current，导致琥珀节点被错套 current 样式 → 改为只 `available` 是 current
2. `stepY=86` 时 L1 RDD 6 课的 5/6 节点标题与下一节点 orb 重叠 → 改为 96

---

## v1.1.1 实现记录 — 地图交互修复 + 复习入口合并（2026-09-07）

v1.1 Course Map 重做上线后的两轮打磨，不引入新功能、不碰后端、不新增文件。

### Round A — 地图交互三处修复
- 展开/收起任意 Level 不再自动滚动：`MapPage.tsx` 的 `useEffect` 改为 `useRef` 守卫（仅首次进入地图滚动一次，切列表↔地图不重滚）。
- 长介绍显示：`.region-summary` 去 `-webkit-line-clamp:2` 截断（收起态完整显示）；展开态路径上方加 `.region-intro` 卡片（长介绍不丢失）。
- `due_for_review` 维持「绿勾 + 紫色外环」设计（`map.css` `.is-due .node-orb::before`），未改动（用户确认紫环已存在）。

### Round B — 复习入口合并
- 代码核查：`/lesson/{id}/quiz`（复习测验）与 `/review/{id}`（间隔复习）同库、同 `_sample_quiz_questions(questions, n=5)`、同 n=5；review 仅多弱维度优先偏好（`priority_dims`，读 `weak_points`），非逐题遗忘曲线。
- `LessonPage.tsx` mastered 分支删「复习测验」入口，仅留「下一课」（btn-primary）+「间隔复习（5 题）」（btn-ghost → `/review/{id}`）；available/needs_review 分支不变。
- `ReviewPage.tsx` 结果页显示「本次复习得分 X%」并注明不写回 `lesson_mastery.score`；后端 `submit_review` 本就不碰 `score/attempts`，与约定一致，无需改。

### 验收
- `tsc -b && vite build` 零错误；地图 toggle 不跳滚动、长介绍收起/展开均完整；已掌握课 CTA 仅「下一课 / 间隔复习（5 题）」，结果页显示本次得分且不写回掌握分。

### 教训（已记入项目记忆）
- 写库接口冒烟前必须 `cp spark_quest.db` 快照。本轮验证完整复习推进了 lesson 1 的 SRS 且无真快照，已用 Python 还原为估算值（status/score/attempts 完好，仅下次复习排期可能早几天）。单用户本地库影响可忽略，但规矩不能破。

---

## Phase 9.1 实现记录 —— 🔥 Streak 连续学习（2026-09-07，已完成，待验收）

### 有效学习日定义

| 行为 | 是否计入 |
|------|---------|
| Quiz 提交（学习测验，过不过都算） | ✅ |
| Review 提交（间隔复习，过不过都算） | ✅ |
| Lesson 阅读 | ❌ |
| Note 写笔记 | ❌ |
| 打开 Dashboard | ❌ |

空提交已被既有 422 拦截，因此不存在"刷空提交刷天数"的漏洞。

### 数据模型

新增 `study_days`（一天一行，UNIQUE(user_id, study_date)）。

**为什么必须建表、不能从 `lesson_mastery` 派生**：`last_quiz_at` 是**每课最后一次**提交时间。9/1 学过第 3 课、9/5 又重做一次，9/1 就从记录里消失——历史会**回溯性损坏**，streak 越用越短。

`user_id` 为未来用户系统预留，当前恒为 `DEFAULT_USER_ID = "local"`（无鉴权、无 user 表，与项目单用户定位一致）。

### 时区（关键决策）

全库时间戳是 UTC，但"一天"必须是**本地**日历日。若按 UTC 日期切天，UTC+8 用户的"一天"会变成 本地 08:00 → 次日 08:00，早上 7 点学完会被记到"昨天"。

- 常量 `services.LOCAL_UTC_OFFSET_HOURS = 8` —— 按用户要求**不命名为 Streak 专属**，它是全应用业务时区
- 不用 `zoneinfo`：Windows 无系统 tzdb，`ZoneInfo("Asia/Shanghai")` 会抛 `ZoneInfoNotFoundError`，需额外装 `tzdata`
- `study_date` 直接存本地日期字符串，一次折算、后续零换算
- `first_at` / `last_at` 仍按既有约定存 UTC

### 核心 API（`app/services.py`）

| 函数 | 职责 |
|------|------|
| `local_now(now)` | UTC → 本地墙钟（naive，**仅取日期/展示，禁止写库**） |
| `local_today(now)` | 返回 `"YYYY-MM-DD"` |
| `record_activity(db, kind, now, user_id)` | `kind ∈ {quiz, review}`；flush 不 commit，与调用方业务写入**同事务** |
| `compute_streak(db, now, user_id)` | 返回 `StreakInfo(current, longest, studied_today, last_study_date)`，**纯读** |

### 连续天数计算

```
today = local_today()
if   today   ∈ days:  从 today   往前数
elif today-1 ∈ days:  从 today-1 往前数   ← 今天还没到晚上，streak 仍存活
else:                 current = 0         ← 昨天也没学 → 已断
longest = 全表最长连续段
```

### Streak 中断逻辑（Duolingo 语义）

**不是"没学就立刻清零"**，而是"过完一整天都没学才断"：
- 今天已学 → `current` 含今天，徽章 Active
- 今天没学、昨天学了 → `current` 保持 N 不变，`studied_today=false`，徽章 At Risk（「今天还没学」）
- 昨天也没学（最后学习 ≤ 前天） → `current=0`，徽章 Broken（「重新开始」）
- `longest` 是历史最高值，**断链不回退**

### 事务约定（用户明确要求）

`record_activity()` 在 `quizzes.py::submit_quiz` 与 `review.py::submit_review` 中，**在各自 `db.commit()` 之前调用**，只 `flush()`。因此：
- 判分/调度写入与学习日记入**同事务**，成功同成功、失败同回滚
- 不存在"mastery 写了但 streak 没记"或反之的割裂状态

### 存量回填

`migrate.backfill_study_days()`：从 `lesson_mastery.last_quiz_at / last_review_at` 折算本地日期，`INSERT OR IGNORE` 幂等写入，已回填 **9 天**：

`2026-08-24 / 08-26 / 08-27 / 08-28 / 08-31 / 09-02 / 09-03 / 09-04 / 09-07`

当前真值：`current=1`、`longest=3`、`studied_today=true`、`last=2026-09-07`。

⚠️ **这是下界不是真相**：只能恢复"每课最后一次提交"落在哪天，早期重复刷同一课的日子已不可考。已在函数 docstring 中写明。

### 前端

- `components/StreakBadge.tsx` + `.css`：三态 `active / at-risk / broken`，状态由纯函数 `streakVariant(days, studiedToday)` 派生（与后端同源规则）
- 色板走组件级 CSS 变量（`--streak-bg/border/fg`），三态各覆盖一次，不写死散落颜色
- `Home.tsx` hero 新增 `.hero-metrics` 容器（进度环 + Streak 同一视觉层级），窄屏整组右对齐换行，不散开
- 「最长连续 N 天 · 最近 YYYY-MM-DD」放在次要区「进度摘要」，**不占 hero 焦点**
- 火焰呼吸用 CSS `@keyframes` + `prefers-reduced-motion` 关闭，**零新增依赖、无动画库、无倒计时、无后台任务**

### 验收

- `backend/_p91_e2e_check.py`：**28 项全绿**（空库 / 同日幂等 / 连续三天 / 宽限日不断链 / 隔整天断链 / 断链后重来 / 时区边界 UTC 23:30→本地次日 / 未知 kind 报错 / flush 未 commit 不落库 / 真库只读核对）
- `backend/_p91_smoke.py`：真实 API 冒烟——提交 lesson 33 测验（score 40 失败）后 `study_days` 09-07 由 `activity_count=4` 增至 `5`、`lessons_done` 2→3，验证**失败提交同样计入有效学习日**且埋点生效
- **冒烟前后快照 + 还原**：`study_days` 全表与 `lesson_mastery(33)` 已还原，复核 `lesson_mastery=32 行`、`lesson 33 mastery=0`、`study_days=9 行`、`09-07=(4,2,2)`、`lessons=66 / quizzes=660` 均未变
- `tsc -b && vite build` 零错误

### 明确不做

Streak Freeze（断连保护卡）· 补签 · Badge 成就 · 每日目标 XP · 学习日历热力图 · 定时/后台任务 · 前端倒计时 · 多用户鉴权。

---

## Phase 9.2 实现记录 —— 🏅 Badge 成就系统（2026-09-08，已完成，待验收）

> 游戏化第二阶段。产品意义：**Content（把学习内容系统化）→ Learning/Retention Loop（把学习过程闭环）→ Badge（把成就可视化、给正反馈）**。
> 严格按用户确认的设计稿落地，**未扩大 Phase 9.2 范围**：无 XP / 金币 / 排行榜 / 商店 / 社交 / 多用户。

### 数据模型（3 张表，职责分离）

| 表 | 职责 | 关键约束 |
| --- | --- | --- |
| `badge_definitions` | 徽章目录（事实） | `code` 唯一；`is_secret` 单字段控制「解锁前隐藏」；`image` 是 `/badges/*.webp` 相对路径（Vite 静态托管，二进制不进 SQLite） |
| `user_badges` | 每用户解锁记录（insert-only） | `UNIQUE(user_id, badge_id)` —— 幂等基石；解锁后绝不更新 |
| `user_stats` | 终身事件计数器（事实） | 一行/用户；`total_quiz_correct / total_quiz_submitted / total_reviews_passed / total_reviews_submitted / total_debug_correct` |

- **不新增任何「学习状态」列**到 `lesson_mastery` / `course_levels`——20 枚徽章全部由既有表 + `user_stats` 派生。
- `user_id` 沿用 `DEFAULT_USER_ID = "local"`（单用户本地应用，无 auth 无 user 表）。

### 解锁引擎（`backend/app/badge_service.py`）

- `BADGE_RULES`：`code -> rule_fn(BadgeContext) -> bool` 字典，20 枚全量重算（用户明确认可「20 个全量检查完全 OK」）。
- `evaluate_badges(...)`：**读时**对每条 badge 规则求值，新解锁的通过 `INSERT ... ON CONFLICT(user_id, badge_id) DO NOTHING` 写入 `user_badges`——天然幂等。返回本次**新解锁**列表。
- `increment_user_stats(...)`：在同事务内加性累加 `user_stats`（与既有 `attempts` / `review_count` 语义一致：一次接受提交 = +1，不去重）。**永不递减**。
- `build_context(...)`：一次性聚合所有求值所需事实（stats / 已掌握数 / 全部课程 / 完美通关 / 最长连续 / Level 维度 / 事件派生）。
- `started_at` 解析 `_parse_started_at`：**统一转成 UTC 朴素时间戳**（与 `datetime.utcnow()` 同帧）。⚠️ 曾误转成本地时区，导致 UTC+8 机器上 BLITZ 时长变负、永不触发——已修。
- `is_late_night` 仅在 `event_kind` 非空（真有提交事件）时判定，背填/只读路径不会误判。

### 20 枚徽章

- **8 旅程（LEVEL_0–7）**：由 `course_levels` 自动派生（非硬编码数量），每 Level 全课掌握即解锁。`LEVEL_NAMES` 手工映射 0–7 中文名。
- **12 特别**：QUIZ_100/500/1000（累计答对）、STREAK_7/30/100（历史最长连续）、REVIEW_50（累计复习通过）、BUG_HUNTER（debug 维度累计答对 ≥20，原为 50，因全库仅 43 道 debug 题且前 4 Level 已掌握、永远够不到 → 改为 20）、BLITZ（5/5 且 ≤60s）、LATE_NIGHT / BUG_HUNTER 为 **SECRET**（解锁前 `name/description/image` 在 API 中置空，仅暴露 `?`）。
- 背填（存量解锁）：**LEVEL_0–3 + QUIZ_100 + WANMEI** = 6 枚（其余因数据未达标不解锁，符合预期）。

### 种子 + 背填（幂等、不改既有 Mastery/Progress/Quiz 数据）

- `seed_badges(db)`：`ON CONFLICT(code) DO UPDATE` 保留 `id`，以免破坏 `user_badges.badge_id` 外键（曾用 `REPLACE` 会重排 rowid → 外键悬空，已规避）。
- `backfill_badges()`：`user_stats` 仅当行不存在时写入一次（INSERT OR IGNORE，绝不覆盖线上累加），再由 `evaluate_badges` 解锁一切可派生徽章。SECRET 与事件型（BLITZ/LATE_NIGHT）在背填时不解锁（无真实事件归因）。**挂在 `init_db` 课程种子之后**（LEVEL 定义依赖 `course_levels`）。

### 挂载点（与提交同事务）

- `routers/quizzes.py::submit_quiz`：`record_activity` 之后、`db.commit()` 之前调用 `increment_user_stats(quiz_correct=..., quiz_submitted=True, debug_correct=...)` → `evaluate_badges(event_kind="quiz", started_at=payload.started_at, ...)`。
- `routers/review.py::submit_review`：同上（`review_passed/review_submitted` + `debug_correct`）。
- ⚠️ Session 用 `autoflush=False`，靠 `record_activity` / `increment_user_stats` 内部显式 `flush()` 让刚写入的 mastery / study_day / counter 对 `evaluate_badges` 的查询可见。
- 响应 `QuizResultOut` / `ReviewResultOut` 新增 `new_badges` 供前端弹 toast。

### API

- `GET /api/badges`：20 枚完整目录 + 每用户解锁态；SECRET 未解锁时 `name/description/image` 置空（`is_secret` + `code` 仍暴露）。
- `GET /api/dashboard`：新增 `recent_badges`（最近 6 枚，解密锁定的 SECRET 正常展示）。

### 前端（React + Vite，零新增依赖）

- `pages/BadgesPage.tsx` + `.css`：`/badges` 路由，按 `tier` 分「旅程徽章 / 特别成就」两组网格；未解锁灰度、SECRET 未解锁显示「神秘徽章 / ?」斜纹占位。
- `Home.tsx`：次要区「最近解锁」徽章条 + 页脚「🏅 最近解锁 →」入口。
- `components/BadgeUnlockToast.tsx` + `.css`：提交后 `new_badges.length>0` 时右下角轻量浮动提示（5.2s 自动消失，纯展示不阻塞），解锁的 SECRET 在此正常显示。
- `QuizPage` / `ReviewPage`：提交带上 `started_at`（启动即记 `new Date().toISOString()`）供 BLITZ；结果页渲染 toast。
- `types.ts`：新增 `Badge` 接口 + `QuizResult.new_badges` / `ReviewResult.new_badges` / `Dashboard.recent_badges` / `QuizSubmit.started_at`。

### 验证

- `backend/_p92_smoke.py` + `backend/_p92_e2e_check.py`：7 项端到端全过（目录形状 20=8+12、SECRET 置空、背填恰为 6 枚、背填幂等、BLITZ 快交触发/慢交抑制、BUG_HUNTER/LATE_NIGHT 保持锁定），均**快照→还原**不污染真库。
- 真实 `uvicorn app.main:app --port 9000` 启动：`/api/health` ok、`/api/badges` 20 枚（6 解锁）、`/api/dashboard` 含 `recent_badges=6`，路由全部挂载正常。
- `tsc -b` 与 `vite build` 零错误。

### 明确不做

XP / 金币 / 排行榜 / 商店 / 社交分享 / 每日目标 / 学习日历热力图 / 多用户鉴权 / 后台定时任务 / 前端倒计时。SECRET 仅「解锁前隐藏」，解锁后无特殊处理。

---

## Phase 10.1 实现记录 —— 🧠 薄弱题 / Weak Questions（2026-09-08，已完成，待验收）

> 学习闭环补全：学习 → 测试 → **犯错 → 记录 → 再做 → 修复 → 再验证**。产品意义：第一次错了"马马虎虎看过去"的题，之后会被系统重新摆到你面前，**独立重做**才是真正检验"懂了没有"。
> 设计稿：`spark_quest/docs/Spark_Quest_Phase10_薄弱题_执行计划_设计.md`（2026-09-08 用户验收通过，含 4 点修订）。**未扩大范围**：无错题状态表 / 无错题 Mastery / 无"已修复"状态机 / 无强制阅读解析 / 不重建 Review / 不引入新 SRS。

### 核心架构决策（验收写死）

- **`quiz_answer_log` = 事实层，不是状态层**：只记"某时刻、某用户、对某题、选了什么、对错与否"。不叫 `wrong_questions`——那个名字会诱导塞入 `status/mastery/wrong_count/is_fixed`，最终造出第二套 Mastery。
- **一切派生**：错几次=COUNT / 最近错=MAX / 是否后来做对=查其后是否有 correct / 哪些进列表=过滤+排序。全部读时计算，零持久化状态。
- **"薄弱"定义**：= "历史上至少出现过一次错误作答"，**不代表当前未掌握**。`wrong_count=2` 且 `last_attempt_correct=true` 仍留在列表（曾暴露薄弱点、最近一次已答对）——这是设计语义，不是 Bug。
- **跨来源统一聚合**：`source` 只是事件标签（quiz/review/practice），同一题三来源记录合并统计，不是三套体系。
- **不做历史 backfill**：Phase 10.1 之前的逐题尝试已丢弃、不可恢复；强行回填=制造伪历史。日志从实施日起累积，越用越有价值。

### 数据模型（1 张表）

`quiz_answer_log`（append-only）：`id / user_id(哨兵) / lesson_id / question_id / source / selected_index / correct_index(事件快照) / is_correct / submitted_at`。
- **复合索引** `ix_quiz_answer_log_user_question_time (user_id, question_id, submitted_at)` 替代 3 个单列索引（事实表典型访问路径：一个用户 → 某道题 → 全部历史 → 按时间排序；`lesson_id` 不单建索引）。
- `correct_index` 是**事件快照**：题库日后修订正确答案，历史记录仍准确回答"当时系统如何判定"。
- 无任何 `wrong_*` / `status` / `mastery` / `is_fixed` 列（冒烟断言过）。

### 写入点（来源 × 副作用矩阵，逐格核对）

| 来源 | 写 answer log | 改 mastery | 改 SRS | 改 streak | 改 badge stats |
|---|---|---|---|---|---|
| Quiz | ✅（同事务） | ✅ | ❌ | ✅ | ✅ |
| Review | ✅（同事务） | 仅 reschedule | ✅ | ✅ | ✅ |
| Practice | ✅（独立事务） | ❌ | ❌ | ❌ | ❌ |

Practice 端点**绝不调用** `record_activity / increment_user_stats / evaluate_badges`——一次重练就是一条新事实，仅此而已。

### API（3 个端点，`routers/weak_questions.py`）

- `GET /api/weak-questions`：跨来源派生列表（wrong_count / last_wrong_at / last_attempt_correct 计算标签），join 出 `lesson_title / level_order / dimension / prompt`
- `GET /api/weak-questions/{id}`：单题题面，**不含 correct_index**（答案不泄露）
- `POST /api/weak-questions/{id}/practice`：服务端判分 + 追加 practice 事实 + 返回对错/correct_index/explanation

### 前端（`/wrong-questions` 最小版）

- `WeakQuestionsPage.tsx`：薄弱题总数 + 卡片列表（题干两行截断 / `维度 · L{n}` / 错误 N 次 · 相对时间 / 「最近一次已做对」绿标）→「重新练习」弹单题面板（选项作答 → 对错高亮 + 解析块 → 可重试/返回），**无强制勾选**
- `Home.tsx` 页脚新增「🧠 薄弱题 →」入口；`main.tsx` 路由 `/wrong-questions`；`types.ts` 新增 3 个接口

### 验证（快照 → 测 → 还原，`_p101_smoke.py` 23/23 全过）

1. Quiz 错 1 题 → 列表出现、wrong_count=1；单题端点无 correct_index
2. Practice 错 → wrong_count=2；Review 错 → wrong_count=3（**跨来源合并**）
3. Practice 对 → wrong_count 保持 3、`last_attempt_correct=true`、仍在列表
4. Practice 不污染：study_days 行数+行内容 / user_badges / user_stats / lesson_mastery 全部零变化（对照矩阵逐格断言）
5. `quiz_answer_log` 无任何状态列；真 uvicorn 实测 health ok、新表自动创建、干净库返回 `[]`、不存在题 404
6. `tsc -b` + `vite build` 零错误；测后 DB 从快照还原（quiz_answer_log=0 行就绪，用户进度零触碰）

### 明确不做（Phase 10.2+ 候选）

筛选/分类/归档、"连续做对 N 次才移出列表"的薄弱度升级、与 Review 的来源切换联动、错题 SRS、强制阅读解析。

---

## Level 4 技术修复记录 —— 执行计划（2026-09-09，已完成并验收）

起因：学员学到 L4-6「WholeStageCodegen 与 Tungsten」时发现 `*(N)` 概念错误。据此先出审查报告（四维：技术事实准确性 / 示例真实性 / 概念边界 / 版本敏感性），再按报告逐项落地。详见同目录 `CHANGELOG.md` 的 2026-09-09 条目。

### 核心事实（本项目口径以此为准）

| 项 | 正确口径 |
|---|---|
| `*(N)` | N 是 **codegen stage 编号**（codegenStageId），**不是**融合算子数。数「同编号行数」= 该 stage 算子数，数「不同编号个数」= codegen stage 数；Exchange 后编号**继续递增、不归零** |
| `explain(mode="formatted")` | **Spark 3.0+**（SPARK-27395）；`*(N)` 编号 2.3 起（SPARK-23032）；WholeStageCodegen 2.0 起；**AQE 3.2.0 起默认开启** |
| join | shuffle-based join（SMJ / SHJ）需 Exchange；**Broadcast Join 不 Shuffle、不切 Stage**（与 Level 6 一致） |
| groupBy | 通常需要 Exchange；**上游已按该 key 分区时可省** |
| Action → Job | 通常 1:1；`take` / `show` 可能触发多个 Job |
| Stage 执行 | 有依赖串行、**无依赖可并行**；Stage 数 = Shuffle 边界 + 1 **只对单条线性链成立** |
| UDF 下推 | 过滤条件依赖 UDF 输出值、顺序上不能前移（**不是「优化器看不懂」**）；列裁剪照常，UDF 依赖列保留 |
| Tungsten | 紧凑二进制内存表示 + cache-aware 算法 + **代码生成**；WholeStageCodegen 是其中一支（**包含关系**） |
| 回退执行 | 逐算子 iterator（Volcano 式）—— **Spark 没有「解释器」**，不要说「回退到解释执行」 |

### 改动范围

- **9 课课文**：L4-6 整字段重写（改用真实可信的 explain 示例）；其余按点修补
- **27 道 quiz**（题干 / 选项 / 正确答案 / 解析四要素同步）：含 5 道原本在考错误答案的 `*(N)` 题
- **`lessons.objective` 8 条 + `description` 2 条**（objective 是独立列，不在 content JSON 里，首轮漏扫）
- **答案位置重排**：A38/B45/C6/D1 → A22/B24/C22/D22；只动无 `quiz_answer_log` 记录的 38 题
- **三段引导文案**（review / problem / preview）按 Level 0/1 调性重写
- **《心智模型与比喻边界案例库》**：§5 Level 4 九条目 + L2/L3 四处同源口径更正

### 技术债（已知、暂不修）

- **L2 / L3 课文与题库仍是旧口径**（orderBy 必 Shuffle / 聚合必 Shuffle / JOIN 必 Shuffle），与已更正的设计文档不一致。收益低，暂挂
- L4 lesson 31 答案分布 A2/B4/C2/D2（5 道冻结题有 4 道固定在 B），无法进一步优化

### 防回退

- `app/course_seed.json` / `app/quiz_seed.json` 已用真库回写；`seed_level4.py` 已标注「已过期、勿执行」
- 修复脚本全部支持 dry-run 与自动备份，位于 `backend/`：
  `fix_level4_20260909.py` / `fix_level4_20260909_round2.py` / `fix_level4_objective_20260909.py` /
  `rebalance_l4_answers_20260909.py` / `rewrite_level4_narrative_20260909.py` / `sync_seed_from_db_20260909.py` / `preview_level4_narrative.py`

---

## Level 5 / Level 6 技术审查与修复记录 —— 分区与 Shuffle / JOIN 与 Broadcast（2026-09-10，已完成并推送）

Level 4 修复完成后，对同为「执行与优化」主线的 Level 5（分区与 Shuffle，lesson id 40–48）与 Level 6（JOIN 与 Broadcast，lesson id 49–57）做同口径审查，过程中发现问题顺手修掉。详见 `CHANGELOG.md` 的 2026-09-10 条目。

### 结论

**L5 问题明显重于 L6**。L6 的 BHJ / SMJ / SHJ 原理写得扎实，主要缺口是未提 AQE 会在运行时改写计划；L5 有多处与 L4 已更正口径**直接冲突**。

### 核心事实（本项目口径以此为准）

| 项 | 正确口径 |
|---|---|
| `repartition(n)` | **round-robin 轮询打散，不是 hash 重分布**，同 key 不保证同分区；只有 `repartition(n, col)` 才按列哈希 |
| `sortWithinPartitions` | 只在各分区内部排序，**不 Shuffle**（旧版误列进 Shuffle 触发清单） |
| BroadcastExchange | **名字里就带 Exchange**——广播路径是「1 个 BroadcastExchange + 大表侧无普通 Exchange」，不是「0 个 Exchange」 |
| 免 Shuffle 路径 | **两条**：一侧足够小可广播（BHJ），或两侧已按同一 join key 分好区 |
| 宽依赖 | 通常需 Shuffle（上游已按该 key 分区时可省）；**Broadcast Join 不属于宽依赖** |
| 容错 | Shuffle 输出丢失时可能需**重新执行相关上游 map task**；「整体重算上游」是 RDD 论文（2012）的叙述 |
| combine 条件 | **可结合**（associative）是必要条件；可交换通常同时成立但非必要 |
| 磁盘 spill | 通常比内存慢 **1~2 个数量级**（不是「几个数量级」） |

### 版本事实（本次新增，均核对官方文档）

| 项 | 事实 |
|---|---|
| `spark.sql.adaptive.skewJoin.enabled` | 默认 **true**（Spark 3.0+）→ AQE 自动拆倾斜分区，**3.x 上手工加盐往往不是第一步** |
| AQE 运行时改写 | 3.2+ 可把 SMJ 改成 BHJ → 「策略只在规划期决策一次」不成立，实际是「规划期一次 + 运行期若干次」 |
| `spark.sql.crossJoin.enabled` | 3.0 起默认 **true**（2.4 及更早对隐式笛卡尔积直接抛异常） |
| `spark.sql.join.preferSortMergeJoin` | 3.x 默认 true → SHJ 相对少见 |
| `spark.sql.autoBroadcastJoinThreshold` | 默认 **10MB**；广播另有 join 类型限制（FULL OUTER JOIN 无法走 BHJ） |
| `spark.sql.shuffle.partitions` | 默认 200，AQE 下只是**初始**分区数（上界不是结果） |
| `spark.sql.files.maxPartitionBytes` | 默认 128MB，决定读文件时的初始分区数（与 HDFS block 非 1:1） |
| `orderBy().limit(n)` | 会被优化成 `TakeOrderedAndProject`（内部一次单分区 Shuffle） |

### 改动范围

- **17 课课文** + `lessons.objective` / `description` 共 5 处（沿用 L4 教训：objective 是独立列，不在 content 七键 JSON 内）
- **26 道 quiz**（L5 21 + L6 5）；**correct_index 一个未动**，改的是选项文本与解析
- **《心智模型与比喻边界案例库》§6 九条目 + §7 八条目**全部按结论更正——该文档是写新课时参考的源头，也是 L4 出错的根因

### 验收

全局 66 课 / 660 题；L5、L6 各 9 课 90 题；每课 10 题；无重复题干；无 orphan quiz。seed 与真库逐题比对 0 处不符。关键词扫描剩 17 处命中，逐条人工确认为合法文本。

### 三段引导文案修缮（2026-09-11）

L5/L6/L7 的 review（上一课回顾）/ problem（本课要解决的问题）/ preview（下一课伏笔）原为建课时的「目录摘要」写法（L7 的 problem 平均不到 45 字，仅为 L0/L1 的三分之一）。已按 Level 0/1 调性 27 课 × 3 段全部重写：

| 字段 | 重写前（L5–L7 区间） | 重写后 |
|---|---|---|
| 上一课回顾 | 42–146 | **130–320 字（均 170）** |
| 本课要解决的问题 | 36–100 | **94–168 字（均 133）** |
| 下一课伏笔 | 37–127 | **184–284 字（均 220）** |

- 四条统一写法：回顾「承接 → 转折 → 悬念」+ 空行分段；问题「连续追问 + 你能得到什么」；伏笔「本课收获 → 自然追问 → 下一课：XXX」；全程第二人称
- 末课（L5-9 / L6-9 / L7-9）改为收束 + 🏁；L7-9 做全课程（Level 0→7）收束
- 比喻全部沿用案例库已登记道具；技术口径与已修复课文一致（「宽依赖**通常**需 Shuffle」「免 Shuffle 有两条路径」「Broadcast Join 不属于宽依赖」等）
- 扫描复检修掉 2 处风险表述：L5-3「需求的**必然**产物」、L6-3「**唯一**能让大表一次货都不飞」
- 顺手清理 `key_points` 里上一轮留下的 3 处重复词
- 脚本：`backend/rewrite_narrative_l567_20260911.py`（--dry / --apply）、`backend/preview_narrative_567_20260911.py`；预览页 `backend/_l567_narrative_preview.html`（已 gitignore）

---

## Level 7 技术审查与修复记录 —— 性能调优（2026-09-11，已完成）

Level 4 → L5/L6 之后，对执行与优化主线的最后一环 Level 7（lesson id 58–66 + 90 道 quiz）做同口径审查。详见 `CHANGELOG.md` 的 2026-09-11 条目。

### 结论

**L7 无 L4 那种「把定义说反」级别的 P0 错误，整体质量好于 L5。** 五段式 explanation（人话理解 / 心智模型 / 比喻的边界 / 技术定义 / 内部发生了什么）与边界条目写得很完整。但存在一个**系统性缺口：版本事实缺失**——全课没提「AQE 自 Spark 3.2.0 起默认开启」，导致第 4/5/6/7/9 课的多个关键动作在 3.x 上语义是错的。

### 核心事实（本项目口径以此为准）

| 项 | 正确口径 |
|---|---|
| AQE 总开关 | `spark.sql.adaptive.enabled` **自 Spark 3.2.0 起默认 true**（官方：enabled by default since 3.2.0）；三大能力自 3.0 引入 |
| AQE 子开关 | `coalescePartitions.enabled`（合并分区）、`skewJoin.enabled`（倾斜处理）默认均为 **true**（自 3.0.0） |
| 因此的正确动作 | 3.x 上不是「**开** AQE」，而是「**确认它有没有生效**」——倾斜专项尤其如此 |
| `spark.sql.shuffle.partitions` | AQE 开启时只是 shuffle 后的**初始**分区数（上界），运行时会被按真实数据量合并 |
| 静态 explain | AQE 开启后显示的可能是初始计划；运行时会改（如 SMJ → BHJ），最终以 Spark UI 为准 |
| 内存借用 | **不对称**：Execution 可直接驱逐 Storage，Storage 不能反向驱逐；User / Reserved **不参与借用** |
| 内存划分 | Reserved 固定 **300MB**；`spark.memory.fraction` 默认 0.6、`storageFraction` 默认 0.5；剩约 40% 为 User |
| 广播阈值 | `spark.sql.autoBroadcastJoinThreshold` 默认 **10MB** |
| 磁盘 spill | I/O 通常比内存慢 **1~2 个数量级**（不是「几个数量级」） |

### 改动范围

- **8 课课文**（58/59/60/61/62/63/64/66）+ **5 道题解析**（q646 / q650 / q666 / q674 / q684，correct_index 全未动）
- 3 处 `key_points`（61、63 各新增一条版本要点；64 修订一条）
- 乱码 2 处修复（U+FFFD，全库残留 0）
- 《心智模型与比喻边界案例库》§8 Level 7 五个条目更正 + 节首版本提示

### 验收

全局 66 课 / 660 题；每课 10 题；无 orphan；乱码 0；危险词扫描 9 处全为合法（否定式告诫 + 刻意干扰项）；脚本复跑 19 处全部 SKIP。seed 已全量回写。

### 待办

- **L0 / L1 未做技术审查**（早期课，三段文案结构完整）
- **L5 / L6 / L7 答案位置分布未核查**（L4 曾发现 A38/B45/C6/D1 的严重失衡）
- **全库 2 道跨 Level 重复题干**：`为什么「计划相同 ≠ 运行时性能相同」？`（q429 L4-8 / q519 L5-8）、`综合读图的第一步是？`（q425 L4-8 / q515 L5-8）——建议改 L5-8 那两题
- L2 / L3 旧口径技术债仍未修（用户决定）；L2/L3 三段文案未查

---

## V1.0 基线说明（2026-08-28）

本文件与同目录 `CHANGELOG.md` 同步建立。

- **`CURRENT_STATE.md`** = 当前事实（只看现在）。
- **`CHANGELOG.md`** = 演进历史（看怎么走到现在）。首个条目 `2026-08-28 — V1.0 基线` 已汇总自启动至本日的全部累计演进。

后续每完成一个阶段，只在 `CHANGELOG.md` 追加新日期条目，并视情况同步更新本文件的"总体状态"表与对应实现记录；不要改写历史基线条目。
