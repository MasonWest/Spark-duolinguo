# Spark Duolinguo

Duolingo 风格的个人 Spark 学习系统（学习约束器）。

## 技术栈

| 层 | 技术 | 端口 |
|----|------|------|
| 前端 | React 18 + Vite 5 + TypeScript | 6001 |
| 后端 | FastAPI + Uvicorn | 9000 |
| 数据库 | SQLite（SQLAlchemy） | - |

产品文档位于 `E:\MMMason\Spark_dlg\spark_quest\`（与本代码目录相互独立，文档不随代码修改）。

## 目录结构

```text
spark-quest-app/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI 入口 + 路由注册
│   │   ├── database.py        # engine / Base / init_db（建表 + 课程播种 + 测验播种 + content 回填）
│   │   ├── models.py          # ORM 模型：course_levels、lessons、quizzes、lesson_mastery
│   │   ├── schemas.py         # Pydantic 响应模型（含 Dashboard / LessonDetail / Quiz）
│   │   ├── services.py        # 课程共享逻辑（课程顺序、派生 lesson 状态、掌握分）
│   │   ├── course_seed.json   # 课程种子数据（3 个 Level、11 课）
│   │   ├── quiz_seed.json     # 测验种子数据（每课 4 题，共 44 题）
│   │   └── routers/
│   │       ├── courses.py     # /api/levels、/api/levels/{id}/lessons
│   │       ├── dashboard.py   # /api/dashboard
│   │       ├── lessons.py     # /api/lessons/{lesson_id}（Phase 3）
│   │       └── quizzes.py     # /api/lessons/{id}/quiz、/submit（Phase 4）
│   ├── .venv/                 # Python 虚拟环境
│   ├── requirements.txt
│   └── spark_quest.db         # SQLite 数据库（首次启动自动生成并播种）
├── frontend/
│   ├── src/
│   │   ├── main.tsx           # 路由入口（/、/map、/lesson/:id、/lesson/:id/quiz）
│   │   ├── index.css          # 全局样式
│   │   ├── types.ts           # API 数据类型（含 Quiz / LessonMastery）
│   │   └── pages/
│   │       ├── Home.tsx       # 首页 Dashboard
│   │       ├── MapPage.tsx    # 课程地图（Level → Lesson + 状态）
│   │       ├── LessonPage.tsx # 学习页面（Phase 3）
│   │       └── QuizPage.tsx   # 课后测验页面（Phase 4）
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts         # 端口 6001，/api 代理到 127.0.0.1:9000
└── README.md
```

## 启动方式

需要两个终端。

### 1. 启动后端（端口 9000）

```bash
cd spark-quest-app/backend
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 9000 --reload
```

> 首次搭建时创建虚拟环境并安装依赖（已完成，仅供重建参考）：
>
> ```bash
> python -m venv .venv
> .venv\Scripts\pip install -r requirements.txt
> ```

### 2. 启动前端（端口 6001）

```bash
cd spark-quest-app/frontend
npm run dev
```

> 首次搭建时安装依赖（已完成）：`npm install`
>
> **重要**：前端端口必须使用 Chromium/Chrome 允许的端口（6001 是安全端口）。
> 之前用过的 6000 端口在 Chromium 列为 `ERR_UNSAFE_PORT`（X11 协议保留），会导致浏览器
> 报"网页似乎有问题或已永久移动"而无法访问。

### 3. 访问

打开浏览器：<http://localhost:6001>

- `/`：Dashboard（总进度 + 当前 Level + 🎯今日任务 + 课程地图入口）
- `/map`：课程地图（Level → Lesson，含 locked / available / mastered / needs_review 状态）
- `/lesson/:id`：学习页面（标题 / 预计时间 / 学习目标 / 概念解释 / 示例 / 必记 / 常见错误 / 下一课）
- `/lesson/:id/quiz`：课后测验（单选 / 判断 / 简单应用题，提交即时评分 + 每题解析）

## API 说明

| 端点 | 说明 | 引入 Phase |
|------|------|-----------|
| `GET /api/health` | 健康检查，返回 app / status / database 状态 | 0 |
| `GET /api/dashboard` | 总进度(mastered/total)、当前 Level、今日推荐 Lesson | 2 |
| `GET /api/levels` | 全部 Level，含嵌套 lessons 与派生状态 | 1 |
| `GET /api/levels/{level_id}/lessons` | 单个 Level 的 lesson 列表 | 1 |
| `GET /api/lessons/{lesson_id}` | 单课详情：基础信息 + 解析后的 content + 下一课指针 | 3 |
| `GET /api/lessons/{lesson_id}/quiz` | 取该课测验题目（不泄露答案，locked 课返回 403） | 4 |
| `POST /api/lessons/{lesson_id}/quiz/submit` | 提交答案，服务端评分，更新掌握状态并解锁下一课 | 4 |

数据库共 4 张表：`course_levels`、`lessons`、`quizzes`、`lesson_mastery`。
首次启动自动播种课程（Level 0/1/2、11 课）与每课测验（44 题）；数据库为空时才会播种，不会重复插入。

**Lesson 状态（由 `lesson_mastery` 实时派生，非占位）：**
- `locked`：前置课尚未 mastered，未解锁
- `available`：已解锁、尚未测验
- `mastered`：测验 ≥ 80%（粘性：re-quiz 低于 80% 不降级、不重锁后续课）
- `needs_review`：测验 < 80%

前端通过 Vite 开发代理访问 `/api/*`，无需关心跨域。

## 开发阶段状态

- [x] Phase 0：项目初始化（前后端通信 + SQLite 连接验证）
- [x] Phase 1：课程地图（course_levels / lessons + /map 页面）
- [x] Phase 2：首页 Dashboard 与今日任务（/api/dashboard + 推荐首课）
- [x] Phase 3：学习页面（/api/lessons/{id} + /lesson/:id，七要素 + 数据化）
- [x] Phase 4：Lesson Mastery Quiz + 最小进度 + 解锁（测验闭环 + 状态派生 + 解锁）
- [ ] Phase 5：完整 Progress Dashboard 动态化 + 状态系统
- [ ] Phase 6：复习系统（基于 weak_points 的 Review / Spaced Repetition）
- [ ] Phase 7：防发散停车场
- [ ] Phase 8：课程内容扩充
- [ ] Phase 9：游戏化 UI / Streak / Badge
- [ ] Phase 10：AI

遵循最小可运行原则：每个 Phase 只实现本阶段功能，业务表随对应 Phase 引入。
