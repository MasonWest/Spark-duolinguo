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
