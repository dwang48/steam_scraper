# Ngrok部署指南

## 问题说明

当通过ngrok部署前端时，如果后端没有正确配置CSRF和CORS信任源，会出现403 Forbidden错误：

```
Forbidden: /api/swipes/
[26/Oct/2025 20:16:50] "POST /api/swipes/ HTTP/1.1" 403 122
```

这是因为Django的CSRF保护机制阻止了来自不受信任域名的请求。

## 解决方案

### 步骤1：创建.env配置文件

在项目根目录（`steam_scraper/`）创建`.env`文件：

```bash
# Django配置
DJANGO_DEBUG=True
DJANGO_SECRET_KEY=your-secret-key-here
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,.ngrok.io,.ngrok-free.app

# CORS和CSRF配置 - 替换YOUR_NGROK_URL为你的实际ngrok URL
# 例如：https://abc123.ngrok.io
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000,https://YOUR_NGROK_URL
CSRF_TRUSTED_ORIGINS=http://localhost:5173,http://localhost:3000,https://YOUR_NGROK_URL

# 使用ngrok HTTPS时设置为True
USE_HTTPS=True
```

### 步骤2：获取你的ngrok URL

1. 启动ngrok（前端）：
```bash
cd frontend
ngrok http 5173
```

2. 复制ngrok提供的HTTPS URL，例如：`https://abc123.ngrok.io`

### 步骤3：更新.env文件

将上面的`YOUR_NGROK_URL`替换为你实际的ngrok URL：

```bash
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000,https://abc123.ngrok.io
CSRF_TRUSTED_ORIGINS=http://localhost:5173,http://localhost:3000,https://abc123.ngrok.io
USE_HTTPS=True
```

**注意事项：**
- ✅ 使用完整的URL（包括 `https://`）
- ✅ 不要在URL末尾加斜杠
- ✅ 多个URL之间用逗号分隔，不要有空格
- ✅ ngrok每次重启会生成新的URL（免费版），需要重新配置

### 步骤4：重启Django后端

```bash
cd backend
python manage.py runserver
```

### 步骤5：在手机上访问

使用手机浏览器访问你的ngrok URL（例如：`https://abc123.ngrok.io`）

## 完整部署流程

### 前端（通过ngrok）

```bash
# 终端1：启动前端开发服务器
cd frontend
npm run dev  # 或 pnpm dev

# 终端2：启动ngrok
ngrok http 5173
```

### 后端（本地或服务器）

```bash
# 终端3：启动Django后端
cd backend
python manage.py runserver 0.0.0.0:8000
```

如果后端也需要通过ngrok访问：

```bash
# 终端4：为后端启动ngrok
ngrok http 8000
```

然后在前端的`.env.local`中配置后端URL：
```bash
VITE_API_BASE_URL=https://your-backend-ngrok-url.ngrok.io
```

## 常见问题

### Q1: ngrok每次重启URL都变化怎么办？

**免费版ngrok：** 每次需要重新配置`.env`中的URL并重启Django。

**付费版ngrok：** 可以使用固定域名。

### Q2: 仍然出现403错误？

检查：
1. ✅ `.env`文件在正确的位置（`steam_scraper/.env`）
2. ✅ ngrok URL拼写正确（包括https://）
3. ✅ 已重启Django服务器
4. ✅ 浏览器清除缓存和cookies

### Q3: 为什么本地PC可以但手机不行？

本地PC使用的是`localhost:5173`（在默认信任列表中），而手机通过ngrok使用不同的域名。

### Q4: 如何在后端日志中查看请求来源？

在Django后端，查看请求的Origin和Referer：

```python
# 可以在views.py中临时添加日志
print(f"Origin: {request.META.get('HTTP_ORIGIN')}")
print(f"Referer: {request.META.get('HTTP_REFERER')}")
```

## 安全提示

⚠️ **开发环境配置，不要用于生产环境**

生产环境应该：
1. 设置 `DJANGO_DEBUG=False`
2. 使用强密钥（`DJANGO_SECRET_KEY`）
3. 限制 `DJANGO_ALLOWED_HOSTS` 为实际域名
4. 配置正确的SSL证书
5. 使用环境变量管理敏感信息

## 配置文件参考

完整的`.env`示例已更新在 `env_example.txt` 文件中。

## 技术细节

### 配置说明

1. **CORS_ALLOWED_ORIGINS**: 允许前端跨域访问后端API
2. **CSRF_TRUSTED_ORIGINS**: Django信任的CSRF token来源
3. **USE_HTTPS**: 启用HTTPS相关的cookie设置
   - `SESSION_COOKIE_SAMESITE="None"` - 允许跨域发送cookie
   - `SESSION_COOKIE_SECURE=True` - 仅通过HTTPS发送cookie
   - `CSRF_COOKIE_SAMESITE="None"` - 允许跨域CSRF token

### 为什么需要这些配置？

当前端和后端在不同域名时（例如ngrok的URL），浏览器的同源策略会阻止：
- 跨域API请求（需要CORS）
- 跨域cookie传递（需要SameSite=None）
- CSRF token验证（需要信任来源）

通过正确配置这些选项，可以安全地在开发环境中进行跨域测试。

