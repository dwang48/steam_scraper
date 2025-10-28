# 📱 手机访问Django Admin完整配置指南

## 问题说明

要从外部手机访问Django admin，需要将**后端Django服务**也通过ngrok暴露，而不仅仅是前端。

## 🚀 完整部署方案

### 方案A：仅访问Django Admin（推荐最简单）

如果你只想从手机访问Django Admin管理后台：

#### 1. 启动Django后端
```bash
cd backend
python manage.py runserver 0.0.0.0:8000
```

#### 2. 为后端启动ngrok
```bash
# 新开一个终端
ngrok http 8000
```

你会看到类似输出：
```
Forwarding  https://xxxx-xxxx-xxxx.ngrok-free.app -> http://localhost:8000
```

#### 3. 直接访问Django Admin

在手机浏览器中打开：
```
https://你的后端ngrok地址.ngrok-free.app/admin/
```

例如：`https://b123456.ngrok-free.app/admin/`

✅ **这样就可以直接访问Django Admin了！**

### 方案B：前端+后端都通过ngrok（完整方案）

如果你想让手机同时访问前端应用和后端API：

#### 步骤1：启动前端开发服务器
```bash
# 终端1
cd frontend
npm run dev
# 或
pnpm dev
```

#### 步骤2：为前端启动ngrok
```bash
# 终端2
ngrok http 5173
```

记录前端URL，例如：`https://a7729fd21d33.ngrok-free.app`

#### 步骤3：启动Django后端
```bash
# 终端3
cd backend
python manage.py runserver 0.0.0.0:8000
```

#### 步骤4：为后端启动ngrok
```bash
# 终端4
ngrok http 8000
```

记录后端URL，例如：`https://b8888888.ngrok-free.app`

#### 步骤5：配置后端settings.py

编辑 `backend/steam_selection/settings.py`，添加两个ngrok URL：

```python
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
    "https://a7729fd21d33.ngrok-free.app",  # 前端ngrok URL
])

CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
    "https://a7729fd21d33.ngrok-free.app",  # 前端ngrok URL
    "https://b8888888.ngrok-free.app",      # 后端ngrok URL（新增）
])
```

#### 步骤6：配置前端环境变量

在 `frontend` 目录创建 `.env.local` 文件：

```bash
# 指向后端的ngrok URL（注意：包含/api路径）
VITE_API_BASE=https://b8888888.ngrok-free.app/api
```

⚠️ **重要**: URL末尾是`/api`而不是`/`

#### 步骤7：重启前端开发服务器

按 `Ctrl+C` 停止前端服务器，然后重新运行：
```bash
npm run dev
# 或
pnpm dev
```

#### 步骤8：重启Django后端

按 `Ctrl+C` 停止Django，然后重新运行：
```bash
python manage.py runserver 0.0.0.0:8000
```

#### 步骤9：手机访问

- **前端应用**: 访问前端ngrok URL（例如：`https://a7729fd21d33.ngrok-free.app`）
- **Django Admin**: 访问后端ngrok URL + /admin/（例如：`https://b8888888.ngrok-free.app/admin/`）

## 📝 配置检查清单

### 后端配置 (settings.py)

- [ ] `ALLOWED_HOSTS` 包含 `["*"]` 或具体的ngrok域名
- [ ] `CORS_ALLOWED_ORIGINS` 包含前端ngrok URL
- [ ] `CSRF_TRUSTED_ORIGINS` 包含前端和后端的ngrok URL
- [ ] `USE_HTTPS = True`（如果使用）
- [ ] Django已重启

### 前端配置 (.env.local)

- [ ] `VITE_API_BASE` 指向后端ngrok URL（包含/api路径）
- [ ] 前端开发服务器已重启

### Ngrok

- [ ] 前端ngrok正在运行（如果需要）
- [ ] 后端ngrok正在运行
- [ ] URL已正确复制（包含https://）

## 🔧 常见问题

### Q1: 访问Django Admin显示"Invalid HTTP_HOST header"

**原因**: `ALLOWED_HOSTS` 没有包含ngrok域名

**解决方案1** (快速): 在settings.py中设置
```python
ALLOWED_HOSTS = ["*"]  # 允许所有主机（仅开发环境）
```

**解决方案2** (推荐): 指定具体域名
```python
ALLOWED_HOSTS = [
    "localhost", 
    "127.0.0.1",
    ".ngrok-free.app",  # 允许所有ngrok-free.app子域名
    ".ngrok.io",        # 允许所有ngrok.io子域名
]
```

### Q2: Django Admin CSS样式丢失

**原因**: 静态文件配置问题

**解决方案**:
```bash
# 在backend目录运行
python manage.py collectstatic --no-input
```

然后在settings.py中确保：
```python
DEBUG = True  # 开发环境保持为True
```

### Q3: 前端无法连接到后端API

**检查**:
1. 前端的`.env.local`是否正确配置了`VITE_API_BASE`（包含/api路径）
2. 后端ngrok是否在运行
3. 后端URL是否在CORS_ALLOWED_ORIGINS中
4. 前端是否已重启

**示例配置**:
```bash
# frontend/.env.local
VITE_API_BASE=https://你的后端ngrok地址.ngrok-free.app/api
```

### Q4: ngrok显示"Too Many Connections"或速度很慢

**原因**: ngrok免费版有限制

**解决方案**:
- 升级到ngrok付费版
- 或使用本地网络访问（见方案C）

### Q5: 每次重启ngrok URL都变化

**原因**: ngrok免费版不提供固定域名

**解决方案**:
- **临时方案**: 每次更新settings.py和frontend/.env.local中的URL
- **永久方案**: 升级到ngrok付费版获取固定域名
- **替代方案**: 使用方案C（局域网访问）

**快速更新脚本**:
```bash
# 每次ngrok重启后，只需要：
# 1. 更新 backend/steam_selection/settings.py 中的ngrok URLs
# 2. 更新 frontend/.env.local 中的 VITE_API_BASE
# 3. 重启Django和前端开发服务器
```

## 🏠 方案C：局域网访问（无需ngrok）

如果手机和电脑在同一WiFi网络：

### 1. 获取电脑IP地址

**Mac/Linux**:
```bash
ifconfig | grep "inet " | grep -v 127.0.0.1
```

**Windows**:
```bash
ipconfig
```

例如得到IP: `192.168.1.100`

### 2. 启动Django
```bash
python manage.py runserver 0.0.0.0:8000
```

### 3. 配置settings.py
```python
ALLOWED_HOSTS = ["*"]  # 或添加具体IP
CSRF_TRUSTED_ORIGINS = [
    "http://192.168.1.100:8000",
    "http://192.168.1.100:5173",
]
```

### 4. 手机访问

- **Django Admin**: `http://192.168.1.100:8000/admin/`
- **前端**: `http://192.168.1.100:5173/`

⚠️ **注意**: 某些公司/学校网络可能阻止设备间通信

## 🎯 推荐配置

### 仅测试Django Admin
→ 使用**方案A**（最简单）

### 完整测试前端+后端
→ 使用**方案B**（完整但复杂）

### 在家或办公室局域网
→ 使用**方案C**（最快最稳定）

## 📱 实际操作示例

假设你现在想访问Django Admin：

```bash
# 1. 启动Django
cd /Users/pineapple/code/steam_scraper/backend
python manage.py runserver 0.0.0.0:8000

# 2. 新终端启动ngrok
ngrok http 8000

# 3. 看到URL类似：https://xyz123.ngrok-free.app
# 4. 手机浏览器打开：https://xyz123.ngrok-free.app/admin/
# 5. 登录即可！
```

就这么简单！

## 🔐 安全提示

⚠️ **重要**: 这些配置仅用于开发和测试

**不要在生产环境**:
- 使用 `ALLOWED_HOSTS = ["*"]`
- 使用 `DEBUG = True`
- 暴露开发服务器到公网

## 需要帮助？

如果还有问题，请提供：
1. 你使用的是哪个方案（A/B/C）
2. 具体的错误信息
3. Django的终端日志
4. Ngrok的终端输出

