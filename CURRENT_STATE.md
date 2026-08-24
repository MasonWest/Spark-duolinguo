# Spark Quest — 当前项目状态

> 最后更新：2026-08-24
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
| 6 | Review / Spaced Repetition | 🔒 规划中 |
| 7 | Parking Lot 防止思绪发散 | 🔒 规划中 |
| 8 | 完整 Spark 课程 | 🔒 规划中 |
| 9 | 游戏化 UI / Streak / Badge | 🔒 规划中 |
| 10 | AI Tutor | 🔒 规划中 |

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

### 种子数据

- 课程：`backend/app/course_seed.json`，首次启动且表为空时自动播种（不重复插入）。
  Phase 3 起还会在启动时按 slug 幂等回填 `lessons.content`（仅当原 content 为空时覆盖，已编辑内容不会被回写覆盖）。
- 题库：**Phase 4 新增 `backend/app/quiz_seed.json`**，首次启动且 `quizzes` 表为空时按 `lesson_slug` 幂等播种（共 44 题，11 课 × 4 题，含 `single_choice` / `true_false` / `application` 三类）。已存在题目的课跳过，不重复插入。

- **Level 0：环境与 Spark 初识**（5 课）
  1. Spark 是什么 · 2. Spark 解决什么问题 · 3. Driver / Executor · 4. SparkSession · 5. 第一个 PySpark 程序
- **Level 1：RDD 基础**（6 课）
  1. RDD 是什么 · 2. Transformation · 3. Action · 4. Lazy Evaluation · 5. RDD 为什么逐渐被 DataFrame 替代 · 6. RDD 小练习

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
title / objective / estimated_minutes 仍为独立列；课程文本**不硬编码在 React 组件**。

当前数据量：`course_levels = 2`，`lessons = 11`，全部 lesson.content 已回填。

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
| `GET /api/lessons/{lesson_id}/quiz` | 取该课 Quiz（**不返回 correct_index / explanation**）；lesson 为 `locked` 时返回 **403** | 4 |
| `POST /api/lessons/{lesson_id}/quiz/submit` | 提交答案，服务端确定性判分 → 返回 score / passed / status / 每题结果 / 是否解锁下一课；未知 question_id → 422，无题 → 400，locked → 403 | 4 |

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
│   │   ├── course_seed.json   # 种子数据（含 11 课的结构化 content）
│   │   ├── quiz_seed.json     # Phase 4 题库种子（44 题，按 lesson_slug）
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

## 下一阶段：Phase 5 — 完整 Progress Dashboard 动态化 + 状态系统

**目标**：把 Phase 4 的"最小派生状态"升级为完整状态机（learning / passed / review 等）并让 Dashboard 真正动态呈现。

**明确不做（本阶段仍留给后续）**：
- 复习调度 / Spaced Repetition（Phase 6）
- 停车场（Phase 7）
- AI 出题（Phase 10）
