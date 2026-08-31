# Spark Duolinguo

Duolingo 风格的个人 Spark 学习系统（学习约束器）。

**当前规模**：8 个 Level · 66 课 · 660 道题（每课固定 10 题）。课程主线（Level 0 → Level 7）已全部落地。

## 核心闭环

这个项目不只是一个「能看的课程列表」，而是一条完整的学习闭环：

```text
学一课 → 5 题测验（≥80%，即 4/5 掌握）→ 解锁下一课
                  ↓
            进入间隔复习周期
                  ↓
   到期 → 5 题复习 → 5/5 通过 → 间隔延长一档
                  ↓ 未全对
         重读本课 → 立即再战 → 直到 5/5
```

> 两处都是「从该课 10 题题库里抽 5 题」，但门槛不同：学习测验 4/5 即通过，间隔复习必须 5/5。

关键设计：复习是**在已掌握课程之上的附加调度**，不改变学习状态，也不新增第五种状态。

## 技术栈

| 层 | 技术 | 端口 |
|----|------|------|
| 前端 | React 18 + Vite 5 + TypeScript | 6001 |
| 后端 | FastAPI + Uvicorn + SQLAlchemy | 9000 |
| 数据库 | SQLite | - |

单用户本地应用，无登录、无 user_id。前端通过 Vite 开发代理访问 `/api/*`，无需关心跨域。

## 快速开始

### 启动

仓库未纳入一键启动脚本，按下面两步即可拉起前后端（两个终端）。

```bash
# 1. 后端
cd backend
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 9000 --reload

# 2. 前端
cd frontend
npm run dev
```

然后访问 <http://localhost:6001>。

> **端口说明**：前端必须用 6001。此前用过的 6000 被 Chromium 列入 `ERR_UNSAFE_PORT`（X11 保留），
> 浏览器会报「网页似乎有问题或已永久移动」而无法访问。

> **首次搭建**（已完成，仅供重建参考）：
> ```bash
> # 后端
> python -m venv .venv
> .venv\Scripts\pip install -r requirements.txt
> # 前端
> npm install
> ```

## 目录结构

```text
spark-quest-app/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI 入口 + 路由注册
│   │   ├── database.py        # engine / Base / init_db（建表 + 播种 + 自动迁移）
│   │   ├── models.py          # ORM：course_levels / lessons / quizzes / lesson_mastery / lesson_notes
│   │   ├── schemas.py         # Pydantic 响应模型
│   │   ├── services.py        # 课程顺序、状态派生、复习调度内核
│   │   ├── migrate.py         # 幂等迁移（PRAGMA 检测 + ALTER），init_db 自动调用
│   │   ├── course_seed.json   # 课程种子（8 Level / 66 课）
│   │   ├── quiz_seed.json     # 题库种子（66 课 × 10 题 = 660 题）
│   │   └── routers/
│   │       ├── courses.py     # /api/levels、/api/levels/{id}/lessons
│   │       ├── dashboard.py   # /api/dashboard
│   │       ├── lessons.py     # /api/lessons/{id}（详情 + 笔记增删查）
│   │       ├── quizzes.py     # /api/lessons/{id}/quiz、/submit
│   │       └── review.py      # /api/review/*（Phase 6b 间隔复习）
│   ├── seed_level2..7.py      # 各 Level 课程内容播种脚本
│   ├── expand_quizzes_to_10.py# 题库扩充脚本
│   ├── .venv/                 # Python 虚拟环境
│   ├── requirements.txt
│   └── spark_quest.db         # SQLite（首次启动自动生成并播种）
├── frontend/
│   ├── src/
│   │   ├── main.tsx           # 路由入口
│   │   ├── index.css          # 全局样式 + 共用按钮
│   │   ├── types.ts           # API 数据类型
│   │   ├── components/
│   │   │   └── RichText.tsx   # 富文本渲染（行内代码 `x` / 加粗 **x**）
│   │   └── pages/
│   │       ├── Home.tsx       # Dashboard（进度 + 今日任务 + 🔁今日复习）
│   │       ├── MapPage.tsx    # 课程地图（Level → Lesson + 状态 + 待复习角标）
│   │       ├── LessonPage.tsx # 学习页（七要素 + 笔记 + 间隔复习入口）
│   │       ├── QuizPage.tsx   # 课后测验（从 10 题题库抽 5 题）
│   │       └── ReviewPage.tsx # 间隔复习（5 题，Phase 6b）
│   ├── index.html
│   ├── package.json
│   └── vite.config.ts         # 端口 6001，/api 代理到 127.0.0.1:9000
├── CURRENT_STATE.md           # 当前事实基线（权威）
├── CHANGELOG.md               # 演进历史
└── README.md
```

## 页面

| 路由 | 说明 |
|------|------|
| `/` | Dashboard：总进度 + 当前 Level + 🎯今日任务 + 🔁今日复习 |
| `/map` | 课程地图：8 个 Level → 66 课，含 locked / available / mastered / needs_review 状态与 🔁 待复习角标 |
| `/lesson/:id` | 学习页：学习目标 / 上一课回顾 / 概念解释 / 示例 / 必记 / 常见错误 / 本课问题 / 下一课伏笔 / 📝 我的笔记 |
| `/lesson/:id/quiz` | 课后测验：从该课 10 题题库抽 5 题，提交即时评分 + 每题解析 |
| `/review/:id` | 间隔复习：5 题，5/5 才算通过（Phase 6b） |

## API

| 端点 | 说明 | Phase |
|------|------|-------|
| `GET /api/health` | 健康检查 | 0 |
| `GET /api/dashboard` | 总进度、当前 Level、今日推荐、**今日复习列表** | 2 / 6b |
| `GET /api/levels` | 全部 Level，含嵌套 lessons 与派生状态 | 1 |
| `GET /api/levels/{level_id}/lessons` | 单个 Level 的 lesson 列表 | 1 |
| `GET /api/lessons/{lesson_id}` | 单课详情 + 解析后的 content + 下一课指针 | 3 |
| `GET /api/lessons/{lesson_id}/quiz` | 从该课 10 题题库抽 5 道（不泄露答案，locked 课返回 403） | 4 / 6a |
| `POST /api/lessons/{lesson_id}/quiz/submit` | 提交评分，≥80% 判定掌握并解锁下一课 | 4 |
| `GET /api/lessons/{lesson_id}/notes` | 取该课笔记（按创建时间倒序） | 5.x |
| `POST /api/lessons/{lesson_id}/notes` | 新增笔记（每次新增、不覆盖历史；空内容 400） | 5.x |
| `DELETE /api/lessons/{lesson_id}/notes/{note_id}` | 删除单条笔记（跨课误删 404 防护） | 5.x |
| `GET /api/review/due` | 今日到期复习列表（含逾期天数） | 6b |
| `GET /api/review/{lesson_id}` | 抽 5 道复习题（不泄露答案；只需 mastered，不看是否到期） | 6b |
| `POST /api/review/{lesson_id}/submit` | 批改 + 重新调度（必须恰好 5 题，否则 422） | 6b |

## 数据模型

5 张表，首次启动自动建表并播种（数据库为空时才播种，不会重复插入）。

```text
course_levels (id, title, description, order_index, status)
     │ 1:N
lessons (id, level_id, title, slug, description, objective,
         estimated_minutes, order_index, prerequisites, content[JSON])
     │ 1:N                          │ 1:1
quizzes                        lesson_mastery
(id, lesson_id, type, prompt,  (id, lesson_id UNIQUE, status, score,
 options[JSON], correct_index,  correct_count, total_count, attempts,
 explanation, order_index,      last_quiz_at, weak_points[JSON],
 dimension)                     first_mastered_at, srs_stage,
                                next_review_at, last_review_at,
lesson_notes                    review_count)
(id, lesson_id, content, created_at)
```

后 5 列是 Phase 6b 为间隔复习新增的调度字段（由 `migrate.py` 幂等添加）。

### Lesson 状态（由 `lesson_mastery` 实时派生，非存储占位）

- `locked`：前置课尚未 mastered
- `available`：已解锁、尚未测验
- `mastered`：测验 ≥ 80%（**粘性**：重测低于 80% 不降级、不重锁后续课）
- `needs_review`：测验 < 80%

> 复习**不是**第五种状态。它只是 `mastered` 课程之上的附加调度信息：
> 复习失败不会把课程打回 `needs_review`，也不会改动 `status / score / attempts / last_quiz_at`。

## 间隔复习系统（Phase 6b）

**复习单位是 Lesson，不是单道题。** 采用简单可解释的固定间隔阶梯，不做 SM-2、不做遗忘曲线拟合。

### 间隔阶梯

```text
1 → 3 → 7 → 14 → 30 → 60 → 120 天（120 天后封顶，不再无限增长）
```

| 事件 | 处理 |
|------|------|
| 首次掌握（`available` → `mastered`） | 写入 `first_mastered_at` 锚点，`srs_stage=0`，下次复习 = **+1 天** |
| 复习通过（**5/5**） | `srs_stage + 1`，`review_count + 1`，下次复习 = `now + INTERVALS[新 stage]` |
| 复习失败（< 5/5） | **`srs_stage` 保持不变**，只插入一次短期巩固：下次复习 = **+3 天**；错题 id 写入 `weak_points` |

### 三个容易搞错的设计点

1. **`srs_stage` 是权威调度状态，`review_count` 只是统计。**
   两者职责分离，禁止用 `review_count` 反推 `srs_stage`
   （因为失败与「通过 stage 0」的间隔都是 3 天，从 `next_review_at` 也反推不出档位）。

2. **失败不降级。**
   失败的含义是「插入一次短期巩固」，不是打回重学：
   `stage=3（14 天）→ 失败 → 3 天后重考 → 通过后 stage=4（30 天）`。

3. **「下一次调度」与「能否立即重做」是两个概念，已刻意解耦。**
   复习失败后 `next_review_at` 推到 3 天后，但 `GET /api/review/{id}` 只看课程是否 `mastered`，
   **不看是否到期**——用户重读完本课可以立刻再挑战，不会被 `next_review_at` 挡住。

### 出题规则

- 从该课 10 题题库中抽 **5 道**（与学习测验相同的抽题器，弱维度优先逻辑共用）
- 优先覆盖不同 `dimension`（concept / why / mechanism / apply / comparison / debug）
- 上一轮答错题目所属的 dimension 会被**适度提前**（仅作为排序偏好，不是权重模型）
- 通过门槛是 **5/5**，4/5 不算通过 —— 比学习测验的 4/5 严格一档
- 复习提交强制校验恰好 5 题，否则 422

## 开发阶段状态

| Phase | 内容 | 状态 |
|-------|------|------|
| 0 | 项目骨架（前后端通信 + SQLite 连接） | ✅ 已完成并验收 |
| 1 | 课程地图（course_levels / lessons + /map） | ✅ 已完成并验收 |
| 2 | Dashboard / 今日任务 | ✅ 已完成并验收 |
| 3 | Lesson 学习页面（七要素 + 数据化） | ✅ 已完成并验收 |
| 4 | Lesson Mastery Quiz + 最小进度 + 解锁 | ✅ 已完成 |
| 5 | Progress Dashboard 动态化 + 状态系统 | ✅ 已完成 |
| 5.x | Lesson 学习笔记 | ✅ 已完成 |
| 6a | Quiz Bank 扩充（每课 10 题 + 多样性抽题） | ✅ 已完成 |
| **6b** | **间隔复习闭环（Spaced Repetition）** | ✅ **已完成并验收（37 项端到端断言全过）** |
| 7 | Parking Lot 防止思绪发散 | 🔒 规划中 |
| 8 | 完整 Spark 课程（Level 0–7 主线） | ✅ 已完成（课程主线收官） |
| 9 | 游戏化 UI / Streak / Badge | 🔒 规划中 |
| 10 | AI Tutor | 🔒 规划中 |

遵循最小可运行原则：每个 Phase 只实现本阶段功能，业务表随对应 Phase 引入。

## 课程主线（Level 0–7）

| Level | 主题 | 课数 |
|-------|------|------|
| 0 | 环境与 Spark 初识 | 5 |
| 1 | RDD 基础 | 6 |
| 2 | DataFrame 核心 | 10 |
| 3 | Spark SQL | 9 |
| 4 | 执行计划 | 9 |
| 5 | 分区与 Shuffle | 9 |
| 6 | JOIN 深类型与 Broadcast | 9 |
| 7 | 性能调优 | 9 |

## 已知问题

- **Level 2–7 的题库存在出题模式缺陷**：答案位置严重偏向 A（约 49%），且约 88% 的题目「最长的选项就是答案」，
  导致可以靠猜答案蒙混过关。Level 0/1 已修复（110 题的 330 个干扰项全部重写 + 位置洗牌，
  A/B/C/D 分布 28/28/27/27，「最长即答案」降到 30%）。Level 2–7 的 550 题待修。

## 相关文档

- `CURRENT_STATE.md` —— **当前事实基线**（架构、数据模型、API、目录结构的权威来源）
- `CHANGELOG.md` —— 演进历史，每个阶段一个条目

## 截图

| 页面 | 截图 |
|------|------|
| Dashboard | `dashboard_preview.png` |
| 课程地图 | `map_preview.png` |

> 截图为 Phase 2/3 时期录制，当前 Dashboard 已新增「🔁 今日复习」区块、课程地图已新增待复习角标，其余布局一致。
