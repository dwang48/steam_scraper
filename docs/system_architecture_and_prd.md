# Steam每日新增游戏筛选系统（架构说明 & PRD）

## 1. 项目背景与目标
- **业务痛点**：小团队需要第一时间锁定每日新增的 Steam 游戏，快速判定“感兴趣/无感”，并沉淀成团队共识。
- **目标用户**：约 10 位内部评测/投研人员，频繁在手机与桌面端切换。
- **核心诉求**
  - 每日自动抓取新增游戏并清洗呈现，避免人工筛选。
  - 提供类似“刷卡片”体验，快捷完成 Like/Skip 记录。
  - 汇总团队偏好，按天输出结果（Excel 下载或推送至飞书）。
  - 支持账号体系，保证多人协作与数据隔离。

## 2. 系统架构概览
### 2.1 数据流
1. **爬虫层**：`steam_daily.py` 等脚本调用 Steam API 与网页端接口，产出结构化 CSV。
2. **导入层**：Django 管理命令 `import_daily_csv` 读取 CSV，落库至业务模型（`DiscoveryBatch`、`Game`、`GameSnapshot`）。
3. **服务层**：Django REST Framework 提供 `/api/games/`、`/api/swipes/` 等接口；认证采用 Django Session/Cookie。
4. **前端层**：React + Vite 单页应用调用上述接口，提供卡片式交互与详情页。
5. **用户行为回写**：前端通过 `/api/swipes/` 写入 Like/Skip；后端记录于 `SwipeAction` 表。
6. **输出层**（规划中）：基于 `SwipeAction` 聚合生成日报，支持 Excel 导出及飞书同步。

### 2.2 技术栈
| 层级 | 技术 | 说明 |
| --- | --- | --- |
| 爬虫/数据收集 | `requests`, `lxml`, `python-dateutil`, `python-dotenv` | 处理 Steam API、页面解析、愿望单估算 |
| 后端 | Django 5 + Django REST Framework | 标准 Admin + API 服务，当前数据库为 SQLite（`backend/db.sqlite3`） |
| 管理工具 | Django management command, CSV | 通过 `manage.py import_daily_csv` 导入每日数据 |
| 前端 | React 18 + Vite + TypeScript + TailwindCSS + SWR + Framer Motion | 移动优先（`frontend/src/App.tsx`） |
| 部署（规划） | Gunicorn/Uvicorn + Nginx 或容器化 | 需按环境配置 `.env` 与静态资源 |
| 协同输出 | Excel (`xlsxwriter`)、飞书 Webhook/自建应用 | 当前仅 CSV 导出，需新增 Excel/飞书集成 |

## 3. 后端架构
### 3.1 模块结构
- Django 项目位于 `backend/steam_selection/`，核心应用为 `backend/core/`。
- `backend/steam_selection/urls.py` 暴露 `/api/` 路径，接入 REST 路由。

### 3.2 数据模型（`backend/core/models.py`）
- `DiscoveryBatch`：记录每次爬虫导入的批次、来源、时间。
- `Game`：Steam 游戏基础信息，保证 `steam_appid` 唯一。
- `GameSnapshot`：与批次关联的快照，保存标签、追踪指标（粉丝数、愿望单预估等）。
- `WatchlistEntry`：早期关注列表（与历史 JSON 数据兼容）。
- `SwipeAction`：用户针对某次快照的 Like/Skip/Watchlist 行为。

### 3.3 API 设计（`backend/core/views.py`, `backend/core/serializers.py`）
| Endpoint | 方法 | 描述 | 认证 |
| --- | --- | --- | --- |
| `/api/games/` | GET | 按日期、关注数、标签筛选快照列表 | 匿名只读 |
| `/api/swipes/` | POST / GET | 写入或查询当前用户的 SwipeAction | POST 开放，GET 需登录 |
| `/api/watchlist/` | GET | 读取 WatchlistEntry | 匿名只读 |
| `/api/health/` | GET | 健康检查 | 匿名 |

> 当前认证默认依赖 Django Session（需在部署时启用登录视图或 API Token）。尚未提供注册/登录接口。

### 3.4 数据导入流程
1. 运行爬虫脚本（如 `steam_daily.py`）产出 `exports/new_games_YYYY-MM-DD.csv`。
2. 执行 `python backend/manage.py import_daily_csv <csv>` 导入数据库。
3. `import_daily_csv` 自动创建 `DiscoveryBatch`、更新 `Game`、插入 `GameSnapshot`，保留原始行至 `raw_payload` 字段，便于审计。

### 3.5 账户与权限（规划）
- 后端已使用 `AUTH_USER_MODEL`，`SwipeAction` 通过外键绑定用户。
- 需新增 Django Auth 端点（可采用 `rest_framework.authtoken` 或 `dj-rest-auth`），并在前端集成登录注册流程。

### 3.6 汇总输出（规划）
- **Excel 导出**：利用 `xlsxwriter` 将每日快照 + 团队偏好生成下载文件（API：`/api/reports/daily`）。
- **飞书同步**：通过飞书机器人或自建应用 webhook，将当天 Like/Skip Top 列表推送到指定群。
- **调度**：使用系统 cron 或 Django `crontab`/Celery，每日自动生成报表并触发通知。

### 3.7 Wishlist 增长监控（规划）
- **目标**：识别近 3 日 / 7 日内尚未发布的游戏中，SteamDB followers（即 wishlist 估算值）增长速度位列前 10%～25% 的项目，并按增长速度/总 wishlist 排序，供页面展示和团队快速跟进。
- **数据来源**：`GameSnapshot.followers`/`wishlists_est` 字段已经存储每日导入时的数值；需确保导入作业每日运行，形成连续时间序列。
- **计算方式**
  - 通过定时任务（Celery Beat 或 Django `crontab`）每日计算一次，选取 `release_date_raw` 为空或未来日期的快照作为“未发布”条件。
  - 以最新批次为基准，获取同一游戏过去 3 日、7 日的 followers / wishlist 数值，计算增量与增幅（增量 / 时间跨度 / 基数）。
  - 基于增幅分布计算分位数（P90、P75），筛选进入前 10%～25% 的游戏。
  - 生成榜单时按 `增量速度`（增量 / 天）和 `wishlists_est` 进行复合排序（优先速度，速度相同再看总量）。
- **落地方案**
  - 新增 Django service/management command：`compute_wishlist_growth`，计算结果写入新的模型（例如 `WishlistMomentum`，字段包含游戏、窗口类型、增量、增幅、排名、数据日期）。
  - 在 REST API 中提供 `/api/momentum/?window=7d` 之类的端点，前端读取后生成榜单模块。
  - 允许与 Excel/飞书输出共享同一份数据源，保持多渠道一致性。

## 4. 前端架构
### 4.1 项目结构
- 入口文件 `frontend/src/main.tsx`，根组件 `frontend/src/App.tsx`。
- 样式使用 Tailwind CSS，附加自定义 class（如 `.glass-panel`）。
- 组件按职责拆分：`CardStack`（卡片堆栈），`DetailSheet`（详情底部弹层），`ActionBar`（操作区），`TopBar`（日期+个人信息）。

### 4.2 状态与数据流
- **数据获取**：`useGameFeed` 钩子（`frontend/src/hooks/useGameFeed.ts`）通过 SWR 调用 `/api/games/?date=...`。
- **动作提交**：`useSwipe` 钩子（`frontend/src/hooks/useSwipe.ts`）向 `/api/swipes/` POST 用户操作。
- **本地状态**：`App.tsx` 用 `useState` 管理当前日期、卡片游标、Toast 状态等；`framer-motion` 负责动画。
- **Demo/真实切换**：`frontend/src/utils/api.ts` 根据 `VITE_DEMO_MODE` 切换 Mock/真实接口，默认使用真实后端。

### 4.3 体验设计
- 移动优先布局，`max-w-md` 限制在单列卡片视图，桌面端居中展示。
- 卡片支持滑动手势（`CardStack.tsx` 使用 `framer-motion` 的 drag）与按钮双操作。
- `DetailSheet` 使用 Radix Dialog + 动画浮层，展示游戏详情、语言、标签、Steam 链接等。

### 4.4 待完善部分
- 登录注册入口缺失（顶部目前展示 Demo 用户）；需根据后端 Session/Auth 方案实现。
- 缺少历史回顾/列表页；`/api/swipes/` GET 已就绪，可扩展“历史记录”“喜欢列表”视图。
- 飞书/Excel 导出尚未接入；需新增按钮或后台任务入口。
- Wishlist 增长榜单待接入；需在页面新增“未发布高增长”区块并适配移动端列表展示。

## 5. 数据与基础设施
- **数据库**：默认 SQLite（`backend/db.sqlite3`），推荐上线前迁移至 PostgreSQL/MySQL；模型均已设置索引。
- **环境配置**：`.env`（示例 `env_example.txt`）包含 Steam API Key、邮箱通知等配置。
- **部署建议**：后端运行 `gunicorn steam_selection.wsgi` 或 `uvicorn steam_selection.asgi`；前端构建 `pnpm build` 后静态托管。
- **日志 & 审计**：爬虫脚本使用 Python logging 输出；导入命令在数据库中保留 `DiscoveryBatch` 元数据；前端可考虑引入 Sentry。

## 6. 产品需求文档（PRD）
### 6.1 用户画像与场景
- **角色 A（投研）**：每天 10-15 分钟，在通勤途中使用手机刷卡片，标记感兴趣的独立游戏。
- **角色 B（发行/商务）**：工作日早上在桌面端查看团队意向列表，决定跟进顺序。
- **角色 C（项目管理）**：需要把团队筛选结果同步到飞书群，或导出 Excel 做长期追踪。

### 6.2 功能需求（MVP）
| 编号 | 需求 | 说明 | 优先级 |
| --- | --- | --- | --- |
| F1 | 账号注册/登录 | Django Session + 前端表单，支持邮箱+密码找回 | P0 |
| F2 | 用户资料 | 显示昵称、头像（可选），提供退出登录 | P1 |
| F3 | 每日新增卡片流 | 默认显示当天数据，可左右滑 Like/Skip、查看详情 | P0 |
| F4 | 时间维度切换 | 支持查看历史日期，限制未来日期 | P0 |
| F5 | 标签/类型筛选 | 依据 `source_tags`、`source_genres` 过滤 | P1 |
| F6 | Like/Skip 持久化 | 成功写入 `/api/swipes/`，失败提示重试 | P0 |
| F7 | 团队汇总视图 | 显示某日所有用户的 Like/Skip 列表，支持导出 | P0 |
| F8 | Excel 导出 | 生成包含游戏详情、点赞用户、备注的 XLSX | P1 |
| F9 | 飞书同步 | 通过 webhook 推送每日 Top Like 列表 | P2 |
| F10 | Watchlist 同步 | 支持把“Watchlist”动作写入 `WatchlistEntry` | P2 |
| F11 | Wishlist 增长榜 | 监测近 3/7 日未发布游戏的 wishlist 增速，筛选前 10%～25% 并前端展示 | P1 |

### 6.3 用户流程
1. 登录 / 注册 → 完成基础资料。
2. 进入“今日精选” → 浏览卡片 → 执行 Like/Skip。
3. 需要了解详情时打开 `DetailSheet`，跳转 Steam 商店查看更多。
4. 结束后可在“团队汇总”查看当天结果，并导出或同步飞书。

### 6.4 数据需求
- `SwipeAction` 需记录用户、游戏、批次、动作、备注、时间。
- 汇总逻辑按照日期聚合，分 “团队 Like 列表”“团队 Skip 列表”，保留每个动作的用户列表与备注。
- Excel/飞书内容模板需包含：游戏名称、Steam 链接、关注度（followers/wishlist）、动作人数。
- Wishlist 增长榜需要保存每日窗口的增量、增幅、排名等指标，并能追溯历史计算批次。

### 6.5 非功能需求
- **性能**：每日数据量约 50-200 条，响应时间指标 < 500ms（API）；前端首屏 < 3s。
- **安全**：密码加密存储、表单 CSRF 保护、接口限流。
- **可靠性**：爬虫失败时提供报警（邮件/飞书）；导入命令必须幂等。
- **可维护性**：所有脚本与服务需具备日志、配置文件化、文档化。

### 6.6 迭代规划（建议）
1. **里程碑 M1（基础闭环）**：完成 F1-F7，覆盖登录、卡片流、Like/Skip、团队汇总。
2. **里程碑 M2（效率工具）**：接入 Excel 导出、飞书推送；新增报表调度；上线 Wishlist 增长榜并与团队汇总互通。
3. **里程碑 M3（优化体验）**：补充高级筛选、历史记录视图、更多分析指标（如粉丝增长曲线）。

## 7. 风险与待办
- **认证链路缺失**：需确定使用 Django 自带页面还是 REST 登录接口，并在前端实现状态持久化与保护路由。
- **爬虫稳定性**：Steam 可能调整接口/反爬策略，需监控失败率并准备代理/重试策略。
- **数据一致性**：Like/Skip 行为依赖批次数据，需确保批次导入完成后再开放当天筛选。
- **飞书开放平台**：同步方案取决于是否已有飞书自建应用或仅使用机器人，开发前需确认权限。

---

本文档基于当前代码库（2025-10-13 数据批次）梳理。如有代码结构调整，请同步更新本说明与 PRD。
