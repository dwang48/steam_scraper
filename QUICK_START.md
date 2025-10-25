# Steam Selection 快速启动指南

## 📦 安装依赖

### 后端依赖
```bash
# 进入项目根目录
cd /Users/pineapple/code/steam_scraper

# 安装/升级Python依赖（包含新增的django-cors-headers）
pip install -r requirements.txt
```

### 前端依赖
```bash
cd frontend
npm install
# 或使用 pnpm
pnpm install
```

## ⚙️ 环境配置

### 创建后端环境变量文件
在项目根目录创建`.env`文件：

```bash
# 基础配置
DJANGO_SECRET_KEY=your-secret-key-here
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

# CORS配置（前后端分离必须配置）
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173
CSRF_TRUSTED_ORIGINS=http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173

# 数据库（默认SQLite）
# DATABASE_URL=sqlite:///backend/db.sqlite3
```

### 创建前端环境变量文件
在`frontend`目录创建`.env`文件：

```bash
# Demo模式（使用Mock数据，无需后端）
VITE_DEMO_MODE=false

# API基础路径
VITE_API_BASE=/api
```

## 🚀 启动服务

### 方式1: 前后端分离启动（推荐开发环境）

**终端1 - 启动后端**:
```bash
cd backend
python manage.py runserver 8000
```

**终端2 - 启动前端**:
```bash
cd frontend
npm run dev
# 或
pnpm dev
```

访问: http://localhost:5173

### 方式2: Demo模式（仅前端，无需后端）

**修改前端环境变量**:
```bash
# frontend/.env
VITE_DEMO_MODE=true
```

**启动前端**:
```bash
cd frontend
npm run dev
```

## 🔧 数据库迁移

首次启动或模型变更后需要执行：

```bash
cd backend
python manage.py migrate
```

## 👤 创建管理员账号（可选）

```bash
cd backend
python manage.py createsuperuser
```

然后访问: http://localhost:8000/admin/

## 📊 测试API

### 健康检查
```bash
curl http://localhost:8000/api/health/
```

### 获取游戏列表
```bash
curl http://localhost:8000/api/games/?date=2025-10-13
```

### 获取当前用户
```bash
curl http://localhost:8000/api/auth/me/ \
  -H "Cookie: sessionid=your-session-id"
```

## 🐛 常见问题

### 1. CORS错误
**症状**: 浏览器控制台显示CORS错误

**解决方案**:
- 确认`.env`文件中配置了正确的`CORS_ALLOWED_ORIGINS`
- 确认前端地址在允许列表中
- 重启后端服务

### 2. CSRF验证失败
**症状**: POST请求返回403 Forbidden

**解决方案**:
- 确认前端正确获取并发送CSRF token
- 检查浏览器是否禁用了Cookie
- 确认`CSRF_TRUSTED_ORIGINS`配置正确

### 3. Session无法保持
**症状**: 登录后刷新页面需要重新登录

**解决方案**:
- 检查浏览器Cookie设置
- 确认前端请求使用`credentials: 'include'`
- 检查`SESSION_COOKIE_SAMESITE`配置

### 4. 端口被占用
**症状**: 启动失败，提示端口已被占用

**解决方案**:
```bash
# macOS/Linux - 查找占用端口的进程
lsof -ti:8000 | xargs kill -9  # 后端
lsof -ti:5173 | xargs kill -9  # 前端

# Windows
netstat -ano | findstr :8000
taskkill /PID <进程ID> /F
```

## 📱 访问地址

### 开发环境
- 前端: http://localhost:5173
- 后端API: http://localhost:8000/api/
- 后端管理: http://localhost:8000/admin/

### Demo模式
- 前端: http://localhost:5173
- 使用Mock数据，无需后端

## 🔄 更新代码后

```bash
# 更新后端依赖
pip install -r requirements.txt

# 执行数据库迁移
cd backend
python manage.py migrate

# 更新前端依赖
cd frontend
npm install

# 重启服务
```

## 📚 更多信息

- 完整代码审查报告: `CODE_REVIEW_REPORT.md`
- 系统架构文档: `docs/system_architecture_and_prd.md`
- 后端功能总结: `docs/backend_feature_summary.md`

## 💡 提示

1. **开发时推荐使用前后端分离模式**，这样可以利用热重载功能
2. **Demo模式适合演示和UI开发**，无需配置后端
3. **生产部署前请务必阅读** `CODE_REVIEW_REPORT.md` 的部署检查清单
4. **首次使用建议先创建管理员账号**，方便在后台管理数据

## 🎉 开始使用

现在你可以开始使用Steam Selection了！

1. 启动后端和前端服务
2. 访问 http://localhost:5173
3. 注册一个账号或使用Demo模式
4. 开始浏览和筛选游戏

祝你使用愉快！🎮

