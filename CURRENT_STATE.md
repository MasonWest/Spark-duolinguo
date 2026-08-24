# Spark Quest — 当前项目状态

> 最后更新：2026-08-24
> 代码目录：`E:\MMMason\Spark_dlg\spark-quest-app\`
> 文档目录（只读）：`E:\MMMason\Spark_dlg\spark_quest\`

## 总体状态

| Phase | 内容 | 状态 |
|-------|------|------|
| 0 | 项目骨架（前后端通信 + SQLite 连接） | 🟢 已完成并验收 |
| 1 | 课程地图（course_levels / lessons + /map 页面） | 🟢 已完成并验收 |
| 2 | Dashboard / 今日任务（/api/dashboard + 推荐首课） | 🟢 已完成并验收 |
| 3 | Lesson 学习页面（/api/lessons/{id} + /lesson/:id，七要素 + 数据化） | 🟢 已完成，待用户验收 |
| 4 | Lesson Mastery Quiz + 最小进度 + 解锁 | 🔵 下一阶段（设计中） |
| 5 | 完整 Progress Dashboard 动态化 + 状态系统 | 🔒 规划中 |
| 6 | Review / Spaced Repetition | 🔒 规划中 |
| 7 | Parking Lot 防止思绪发散 | 🔒 规划中 |
| 8 | 完整 Spark 课程 | 🔒 规划中 |
| 9 | 游戏化 UI / Streak / Badge | 🔒 规划中 |
| 10 | AI Tutor | 🔒 规划中 |

**当前进度：Phase 3 已实现完毕，等待用户验收；验收通过后进入 Phase 4（Lesson Mastery Quiz + 最小进度 + 解锁）。**

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

仅两张业务表（Phase 1 引入）。Phase 0 不建表，Phase 2 未新增表，**Phase 3 未改 schema**——结构化课程内容以 JSON 文本形式存于既有 `lessons.content` 列。

```text
course_levels (id, title, description, order_index, status)
     │ 1:N
lessons (id, level_id FK→course_levels.id, title, slug, description,
        objective, estimated_minutes, order_index, prerequisites, content)
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

### 种子数据

来自 `backend/app/course_seed.json`，首次启动且表为空时自动播种（不重复插入）。
Phase 3 起还会在启动时按 slug 幂等回填 `lessons.content`（仅当原 content 为空时覆盖，已编辑内容不会被回写覆盖）。

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

- `quizzes`（Phase 4）
- `user_progress`（Phase 4：最小进度 + 解锁）
- `review_items`（Phase 6）
- `parking_lot`（Phase 7）
- `study_sessions`（后续）

## API 列表

| 端点 | 说明 | 引入 Phase |
|------|------|-----------|
| `GET /api/health` | app / status / database 状态 | 0 |
| `GET /api/dashboard` | 总进度(0/total)、当前 Level、今日推荐 Lesson、streak_days | 2 |
| `GET /api/levels` | 全部 Level，含嵌套 lessons 与占位状态 | 1 |
| `GET /api/levels/{level_id}/lessons` | 单个 Level 的 lesson 列表 | 1 |
| `GET /api/lessons/{lesson_id}` | 单课详情：基础信息 + 解析后的 content + 下一课指针；404 on missing | 3 |

### 占位状态逻辑（Phase 5 前的临时规则）

- 全课程第一个 Lesson = `available`（🔵 可学习）
- 其余全部 = `locked`（🔒 未解锁）
- 无 `passed`（🟢）—— 真实进度系统在 Phase 5

### Dashboard 推荐规则（Phase 2）

取课程顺序中第一个 `available` 的 Lesson = 第一个 Lesson（id 1「Spark 是什么」）。
当前 Level = 该 Lesson 所属 Level。`completed` 固定 0（无进度表）。

## 前端页面

| 路由 | 内容 | 引入 Phase |
|------|------|-----------|
| `/` | Dashboard：总进度条 + 当前阶段 + 🎯今日任务卡 + 课程地图入口 | 2 |
| `/map` | 课程地图：Level → Lesson 层级 + locked/available/passed 状态图标 | 1 |
| `/lesson/:id` | 学习页面：标题 / 预计时间 / 学习目标 / 概念解释 / 示例 / 必记知识 / 常见错误 / 下一课 | 3 |

## 目录结构

```text
spark-quest-app/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI 入口 + 路由注册 + lifespan
│   │   ├── database.py        # engine / Base / init_db（建表 + 种子 + content 回填）
│   │   ├── models.py          # ORM：CourseLevel、Lesson
│   │   ├── schemas.py         # Pydantic 响应模型（LessonOut/LevelOut/Dashboard/LessonDetail）
│   │   ├── services.py        # 共享逻辑：first_lesson_id、lesson_status
│   │   ├── course_seed.json   # 种子数据（含 11 课的结构化 content）
│   │   └── routers/
│   │       ├── courses.py     # /api/levels、/api/levels/{id}/lessons
│   │       ├── dashboard.py   # /api/dashboard
│   │       └── lessons.py     # /api/lessons/{id}（Phase 3）
│   ├── .venv/
│   ├── requirements.txt
│   └── spark_quest.db
├── frontend/
│   ├── src/
│   │   ├── main.tsx           # 路由（/、/map、/lesson/:id）
│   │   ├── index.css          # 全局样式
│   │   ├── types.ts           # API 类型（含 LessonDetail）
│   │   └── pages/
│   │       ├── Home.tsx + Home.css       # Dashboard
│   │       ├── MapPage.tsx + MapPage.css # 课程地图
│   │       └── LessonPage.tsx + LessonPage.css # 学习页面（Phase 3）
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

## 浏览器自动化能力（已就绪，用于 UI 验证）

- `agent-browser`（全局 CLI，v0.27.0）已安装，Chromium 位于 `C:\Users\Administrator\.agent-browser`
- 用法：`agent-browser open <url>` → `agent-browser screenshot --full <path>` → `agent-browser close`

## 下一阶段：Phase 4 — Lesson Mastery Quiz + 最小进度 + 解锁

**目标**：在每课 `/lesson/:id` 之后接 Mastery Quiz，并打通「测验 → 最小进度 → 解锁下一课」的最小可运行闭环。

**应实现**：
- 新增 `quizzes` 表（Phase 4 引入）
- 课后 quiz 提交、即时反馈、显示解释、记录分数（单选 + 判断，≥80% 通过）
- 通过/失败的 UI 状态
- 新增 `user_progress` 最小进度表（Phase 4 引入，随本阶段落地）
- 完成 lesson 后写入 progress；通过即解锁下一个 lesson
- 前端按真实 progress 显示 locked / available / passed
- Dashboard 今日任务与进度的最小可用版

**明确不做**（留给后续 Phase）：
- 完整状态系统 learning / review / mastered（Phase 5）
- Dashboard 动态化与状态系统完整呈现（Phase 5）
- 复习调度（Phase 6）
- 停车场（Phase 7）
- AI 出题（Phase 10）

**完成标准（待 Phase 4 启动时细化）**：
- 单课 quiz 答完显示分数与每题解释
- 通过即解锁下一课；失败入复习队列
- 进度真实落库，地图状态随 progress 变化
