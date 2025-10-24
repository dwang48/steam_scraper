# 后端功能实现概览（2025-10-20）

本文档总结了依据《system_architecture_and_prd.md》落地的 Django 后端能力，涵盖认证、团队汇总、报表导出、Feishu 推送以及 wishlist 增长监控等模块。

## 1. 认证与用户会话
- **Session 登录体系**：新增 `AuthViewSet`，使用 Django Session + CSRF，默认保持登录态。
- **Endpoints**
  | 方法 | 路径 | 说明 |
  | --- | --- | --- |
  | `POST` | `/api/auth/` | 自注册（username/email/password），成功后自动登录 |
  | `POST` | `/api/auth/login/` | 用户登录，支持用户名或邮箱，`remember_me=true` 时保持长会话 |
  | `POST` | `/api/auth/logout/` | 注销当前会话 |
  | `GET` | `/api/auth/me/` | 返回当前用户信息（未登录返回 `is_authenticated=false`） |
  | `GET` | `/api/auth/csrf/` | 获取 CSRF Token（前端首次交互时调用） |
- **返回格式**：统一返回 `UserSerializer` 字段（`id/username/email/first_name/last_name/display_name/is_authenticated`）。

## 2. 卡片滑动与 Watchlist 联动
- `SwipeActionViewSet` 现要求登录用户才能创建/查询。
- 支持按 `date` 查询历史：`GET /api/swipes/?date=2025-10-13`。
- Watchlist 行为自动写入 `WatchlistEntry`：
  - `POST /api/swipes/`，`action="watchlist"` 时更新 `status_history/current_status/check_count`，保留备注和最近一次操作用户。

## 3. 团队日报与报表输出
- **JSON 汇总**：`GET /api/reports/daily-summary/?date=2025-10-13`
  - 汇总字段：`total_actions`、`unique_users`、各动作数量、按点赞数排序的游戏列表（包含点赞/跳过/Watchlist 用户详情）。
- **Excel 导出**：`GET /api/reports/daily-summary/export/?date=2025-10-13`
  - 返回下载用的 XLSX， sheet 名 `Daily Summary`，含游戏名称、AppID、各动作人数及用户名列表。
- **Feishu 推送**：`POST /api/reports/daily-summary/push/ {"date": "2025-10-13"}`
  - 需在 `.env` 配置 `FEISHU_WEBHOOK_URL`。
  - 推送内容包含总操作数、参与人数以及 Top 30 游戏的点赞/跳过/Watchlist 概览。

## 4. Wishlist 增长榜
- **数据模型**：新增 `WishlistMomentum`，保存窗口（3d/7d）、基准值、增速、百分位、排名等信息。
- **每日计算命令**
  ```bash
  # Dry-run：查看 2025-10-13 的增长情况
  python backend/manage.py compute_wishlist_momentum --date 2025-10-13 --dry-run

  # 正式写入（默认计算 3d/7d）
  python backend/manage.py compute_wishlist_momentum --date 2025-10-13
  ```
  - 仅保留未发布游戏，对比窗口内首末快照，基于 followers/wishlists_est 推算增速。
  - 计算结果写入 `WishlistMomentum`（仅保留前 25% percentile）。
- **API 查询**：`GET /api/momentum/?window=3d&date=2025-10-13`
  - 若指定日期无数据，自动回退到最近一次计算记录。
  - 返回字段：`delta_followers`、`delta_per_day`、`delta_rate`、`percentile`、`rank`、以及快照元数据。

## 5. 现有 API 调整
- `GameSnapshotViewSet` 仍支持日期/标签/跟随者数过滤。
- `WatchlistEntryViewSet` 继续提供只读访问，可通过 `?status=` 过滤。
- `HealthViewSet` 保持不变。

## 6. 环境变量与依赖
- `.env` 新增 `FEISHU_WEBHOOK_URL`（若留空则 Feishu 推送接口返回配置缺失）。
- 依赖 `xlsxwriter`（requirements.txt 已包含），用于生成 Excel。
- 用户注册的密码使用 Django 内置校验规则，默认启用最小长度等策略。

## 7. 后续建议
- 在部署环境增加定时任务：每日导入爬虫快照后运行 `compute_wishlist_momentum`。
- 与前端协调登录流程（获取 CSRF、调用 `/api/auth/...`），并在 UI 中展示“未发布高增长榜”模块（消费 `/api/momentum/`）。
- 团队日报页面可选择调用 Excel/Feishu API，或后台计划任务自动推送。

以上改动全部写入数据库迁移（`backend/core/migrations/0002_wishlistmomentum.py`），执行 `python backend/manage.py migrate` 后即可生效。
