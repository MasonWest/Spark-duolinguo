# Spark Quest

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
│   │   ├── database.py        # engine / Base / init_db（建表 + 播种）
│   │   ├── models.py          # ORM 模型：course_levels、lessons
│   │   ├── schemas.py         # Pydantic 响应模型（含 Dashboard）
│   │   ├── services.py        # 课程共享逻辑（首个 available lesson、状态）
│   │   ├── course_seed.json   # 课程种子数据（Level 0 + Level 1）
│   │   └── routers/
│   │       ├── courses.py     # /api/levels、/api/levels/{id}/lessons
│   │       └── dashboard.py   # /api/dashboard
│   ├── .venv/                 # Python 虚拟环境
│   ├── requirements.txt
│   └── spark_quest.db         # SQLite 数据库（首次启动自动生成并播种）
├── frontend/
│   ├── src/
│   │   ├── main.tsx           # 路由入口（/ 和 /map）
│   │   ├── index.css          # 全局样式
│   │   ├── types.ts           # API 数据类型
│   │   └── pages/
│   │       ├── Home.tsx       # 首页：标题 + 后端连接状态
│   │       └── MapPage.tsx    # 课程地图（Level → Lesson + 状态）
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts         # 端口 5173，/api 代理到 localhost:9000
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
- `/map`：课程地图（Level → Lesson，含 locked / available / passed 状态）

## API 说明（Phase 2）

| 端点 | 说明 |
|------|------|
| `GET /api/health` | 健康检查，返回 app / status / database 状态 |
| `GET /api/dashboard` | 总进度(0/total)、当前 Level、今日推荐 Lesson |
| `GET /api/levels` | 全部 Level，含嵌套 lessons 与占位状态 |
| `GET /api/levels/{level_id}/lessons` | 单个 Level 的 lesson 列表 |

课程数据存储于 SQLite（`course_levels` / `lessons` 两张表，1:N 外键关系），
首次启动自动播种 Level 0 + Level 1；数据库为空时才会播种，不会重复插入。

前端通过 Vite 开发代理访问 `/api/*`，无需关心跨域。

## 开发阶段状态

- [x] Phase 0：项目初始化（前后端通信 + SQLite 连接验证）
- [x] Phase 1：课程地图（course_levels / lessons + /map 页面）
- [x] Phase 2：首页 Dashboard 与今日任务（/api/dashboard + 推荐首课）
- [ ] Phase 3：学习页面
- [ ] Phase 4：Quiz
- [ ] Phase 5：进度系统
- [ ] Phase 6：复习系统
- [ ] Phase 7：防发散停车场
- [ ] Phase 8：课程内容扩充
- [ ] Phase 9：UI/UX 优化
- [ ] Phase 10：AI

遵循最小可运行原则：每个 Phase 只实现本阶段功能，业务表随对应 Phase 引入。
