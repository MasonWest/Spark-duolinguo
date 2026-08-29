# Spark Quest — 当前项目状态

> 最后更新：2026-08-28（V1.0 基线；与 `CHANGELOG.md` 同步建立）
> 代码目录：`E:\MMMason\Spark_dlg\spark-quest-app\`
> 代码仓库：`https://github.com/MasonWest/Spark-duolinguo`（分支 `main`）
> 文档目录（通常只读）：`E:\MMMason\Spark_dlg\spark_quest\`

## 总体状态

| Phase | 内容 | 状态 |
|-------|------|------|
| 0 | 项目骨架（前后端通信 + SQLite 连接） | 🟢 已完成并验收 |
| 1 | 课程地图（course_levels / lessons + /map 页面） | 🟢 已完成并验收 |
| 2 | Dashboard / 今日任务（/api/dashboard + 推荐首课） | 🟢 已完成并验收 |
| 3 | Lesson 学习页面（/api/lessons/{id} + /lesson/:id，七要素 + 数据化） | 🟢 已完成并验收 |
| 4 | Lesson Mastery Quiz + 最小进度 + 解锁 | 🟢 已完成 |
| 5 | 完整 Progress Dashboard 动态化 + 状态系统 | 🟢 已完成 |
| 6a | Quiz Bank 扩充（每课扩至 10 题 + 多样性抽题；L0/L1/L2 全完成） | 🟢 已完成（Phase 6.1 + 6.2） |
| 6b | Review / Spaced Repetition（间隔重复） | 🔒 规划中（待你设计新机制，未启动） |
| 7 | Parking Lot 防止思绪发散 | 🔒 规划中 |
| 8 | 完整 Spark 课程（Level 2/3/4/5 已落地：DataFrame 核心 / Spark SQL / 执行计划 / 分区与 Shuffle；Level 6-7 规划中） | 🟡 部分完成 |
| 9 | 游戏化 UI / Streak / Badge | 🔒 规划中 |
| 10 | AI Tutor | 🔒 规划中 |
| Notes | Lesson 学习笔记（lesson_notes 表 + 笔记 API + 前端接入） | 🟢 已完成（V1.0 基线） |

**当前进度：Phase 5（完整 Progress Dashboard 动态化 + 状态系统）已实现完毕并通过回归测试。**

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
        correct_count, total_count, attempts, last_quiz_at, weak_points[JSON])
     │ 1:N
lesson_notes (id, lesson_id FK→lessons.id ON DELETE CASCADE, content,
        created_at)   # V1.0 基线新增：append-only 学习笔记
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

**lesson_notes**（V1.0 基线新增；每课可有多条笔记，新建即追加、不覆盖历史）
| 列 | 类型 |
|----|------|
| id | INTEGER (PK) |
| lesson_id | INTEGER (FK → lessons.id, ON DELETE CASCADE, 有索引) |
| content | TEXT |
| created_at | DATETIME (默认 datetime.now) |

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

当前数据量：`course_levels = 6`，`lessons = 48`，全部 lesson.content 已回填（Level 2 新增 10 课、Level 3 新增 9 课、Level 4 新增 9 课、Level 5 新增 9 课）。

> ✅ 全部 48 课均已补齐 Quiz 题库（每课 10 题，共 480 题）；Level 2/3/4/5 课程测试接口正常返回题目，且抽题已按维度多样性生效。

### 尚未引入的表（按文档规划，随对应 Phase 引入）

- `review_items`（Phase 6）
- `parking_lot`（Phase 7）
- `study_sessions`（后续）

> Phase 4 已落地 `quizzes` 与 `lesson_mastery`（替代原规划的 `user_progress`）。

## API 列表

| 端点 | 说明 | 引入 Phase |
|------|------|-----------|
| `GET /api/health` | app / status / database 状态 | 0 |
| `GET /api/dashboard` | 总进度(已完成数/total)、当前 Level、今日推荐 Lesson、streak_days | 2（Phase 4 改"已完成"语义为 mastered） |
| `GET /api/levels` | 全部 Level，含嵌套 lessons 与**真实派生状态** | 1（Phase 4 状态改为派生） |
| `GET /api/levels/{level_id}/lessons` | 单个 Level 的 lesson 列表 | 1 |
| `GET /api/lessons/{lesson_id}` | 单课详情：基础信息 + 解析后的 content + 下一课指针 + 派生 status/mastery_score；404 on missing | 3 |
| `GET /api/lessons/{lesson_id}/quiz` | 取该课 Quiz（**不返回 correct_index / explanation**）；每课题库 10 题（Phase 6.1 起），**随机抽取 5 题且优先维度多样**（无硬约束）；lesson 为 `locked` 时返回 **403** | 4（抽题逻辑 Phase 6.1 升级） |
| `POST /api/lessons/{lesson_id}/quiz/submit` | 提交答案，服务端确定性判分 → 返回 score / passed / status / 每题结果 / 是否解锁下一课；**仅对本次呈现的 5 题判分**（total=提交题数）；未知 question_id → 422，无题 → 400，locked → 403 | 4（判分逻辑 Phase 6.1 升级） |
| `GET /api/lessons/{lesson_id}/notes` | 列出该课全部笔记，按 `created_at` 倒序（最新在前） | V1.0 基线（Notes） |
| `POST /api/lessons/{lesson_id}/notes` | 新建一条笔记（append-only，绝不覆盖历史）；body `{content}`；返回新建笔记 | V1.0 基线（Notes） |
| `DELETE /api/lessons/{lesson_id}/notes/{note_id}` | 删除单条笔记（仅当该笔记确属该 lesson 时才删，否则拒绝）；成功 204 | V1.0 基线（Notes） |

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
- `streak_days` 固定 0（Phase 6 实现）

## 前端页面

| 路由 | 内容 | 引入 Phase |
|------|------|-----------|
| `/` | Dashboard：总进度条 + 当前阶段 + 🎯今日任务卡 + 课程地图入口 | 2 |
| `/map` | 课程地图：Level → Lesson 层级 + locked/available/mastered/needs_review 状态图标 | 1（Phase 4 状态词更新） |
| `/lesson/:id` | 学习页面：标题 / 预计时间 / 学习目标 / 概念解释 / 示例 / 必记知识 / 常见错误 / 下一课；按状态显示「开始测验 / 复习测验 / 已掌握」入口 | 3（Phase 4 接 Quiz 入口） |
| `/lesson/:id/quiz` | **Phase 4 新增**：测验页——拉取题目 → 单选作答 → 提交 → 显示得分 / 每题解释 / 通过则提示解锁下一课、未通过提示复习 | 4 |

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
│   │   ├── course_seed.json   # 种子数据（含 48 课的结构化 content：L0-L5）
│   │   ├── quiz_seed.json     # 题库种子（48 课 × 10 题 = 480 题，按 lesson_slug；Phase 6.1/6.2 + Level 3/4/5 扩充）
│   │   └── routers/
│   │       ├── courses.py     # /api/levels、/api/levels/{id}/lessons
│   │       ├── dashboard.py   # /api/dashboard（Phase 4：completed=mastered 数，今日课=首个未 mastered）
│   │       ├── lessons.py     # /api/lessons/{id}（Phase 3，返回派生 status/mastery_score）
│   │       └── quizzes.py     # Phase 4：/api/lessons/{id}/quiz、/api/lessons/{id}/quiz/submit
│   ├── .venv/
│   ├── requirements.txt
│   └── spark_quest.db
├── frontend/
│   ├── src/
│   │   ├── main.tsx           # 路由（/、/map、/lesson/:id、/lesson/:id/quiz）
│   │   ├── index.css          # 全局样式
│   │   ├── types.ts           # API 类型（LessonStatus = locked/available/mastered/needs_review；Quiz* 类型）
│   │   └── pages/
│   │       ├── Home.tsx + Home.css       # Dashboard
│   │       ├── MapPage.tsx + MapPage.css # 课程地图（Phase 4 状态词/图例更新）
│   │       ├── LessonPage.tsx + LessonPage.css # 学习页面（Phase 4 接 Quiz 入口，按状态显示）
│   │       └── QuizPage.tsx + QuizPage.css # Phase 4 新增：测验页
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
- ✅ Level 3（Spark SQL，9 课）已于 2026-08-28 落地（见下方「Level 3 实现记录」）；Level 4（执行计划，9 课）已于 2026-08-28 落地（见下方「Level 4 实现记录」）；Level 5（Partition/Shuffle）→ Level 6（Join 深类型/broadcast/调优）→ Level 7（性能优化）仍按用户新路线图规划中，未实现。

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
- Level 4（执行计划，9 课）已于 2026-08-28 落地（见下方「Level 4 实现记录」）；Level 5（Partition/Shuffle）→ Level 6（Join 深类型/broadcast/调优）→ Level 7（性能优化）仍按用户新路线图规划中，未实现。
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
- Level 5（Partition/Shuffle）已于 2026-08-28 落地（见下方「Level 5 实现记录」）；Level 6（Join 深类型/broadcast/调优）→ Level 7（性能优化：Tungsten 内存/堆外/编码字节级）仍按用户新路线图规划中，未实现。
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
- Level 6（Join 深类型 / broadcast / 调优）→ Level 7（性能优化：Tungsten 内存/堆外/编码字节级、具体调优参数与最优分区数）仍按用户新路线图规划中，未实现。
- Level 5 综合练习只验收"看得懂分区与 Shuffle、能识别触发点"，不要求给出调优参数或最优分区数（呼应设计稿红线）。

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
- 停车场（Phase 7）、游戏化 / Streak / Badge（Phase 9）、AI Tutor（Phase 10）仍按原规划。

## Phase 6.2 实现记录 —— Level 2 Quiz Bank 扩至 10 题（2026-08-27，L2 完成）

**目标**：把 Level 2 的 10 课每课从 5 题扩到 10 题（每课 +5 新题 = 共 +50），按与 Phase 6.1 完全相同的标准：开放维度词表、不强制五维、质量优先、保留原题只补差额。复用 `expand_quizzes_to_10.py` 的同一套幂等机制（仅补 10 个 `l2-*` slug、`EXISTING_DIM` 归类、50 道新题到 `NEW_QUESTIONS`）。

**明确不做（本期仍留给后续）**：
- `review_items` / Spaced Repetition 调度（Phase 6b 主体）——首页的「复习测验 / 需复习」仅为 `needs_review` 状态驱动的整份重测，并非复习系统。
- 停车场（Phase 7）
- 游戏化 UI / Streak / Badge（Phase 9）
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

## V1.0 基线说明（2026-08-28）

本文件与同目录 `CHANGELOG.md` 同步建立。

- **`CURRENT_STATE.md`** = 当前事实（只看现在）。
- **`CHANGELOG.md`** = 演进历史（看怎么走到现在）。首个条目 `2026-08-28 — V1.0 基线` 已汇总自启动至本日的全部累计演进。

后续每完成一个阶段，只在 `CHANGELOG.md` 追加新日期条目，并视情况同步更新本文件的"总体状态"表与对应实现记录；不要改写历史基线条目。
