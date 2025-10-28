# 🚀 快速访问Django Admin（手机）

## 最简单的方法 - 只访问Admin

### 第1步：启动Django（终端1）
```bash
cd /Users/pineapple/code/steam_scraper/backend
python manage.py runserver 0.0.0.0:8000
```

### 第2步：启动ngrok（终端2）
```bash
ngrok http 8000
```

### 第3步：复制URL并访问

从ngrok输出中复制HTTPS URL，例如：
```
Forwarding  https://abc123.ngrok-free.app -> http://localhost:8000
```

### 第4步：手机浏览器访问
```
https://abc123.ngrok-free.app/admin/
```

✅ **完成！** 现在就可以登录Django Admin了！

---

## 如果出现"Invalid HTTP_HOST header"错误

编辑 `backend/steam_selection/settings.py`，确保第21行：

```python
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["*"] if DEBUG else [])
```

然后重启Django（Ctrl+C 后重新运行）。

---

## 如果需要同时访问前端应用

参考完整指南：`MOBILE_ACCESS_SETUP.md`

---

## 当前你的ngrok URL

根据你的配置，当前使用：
```
https://a7729fd21d33.ngrok-free.app
```

**手机访问地址**：
- Django Admin: `https://a7729fd21d33.ngrok-free.app/admin/`
- API: `https://a7729fd21d33.ngrok-free.app/api/`

⚠️ **注意**: 这是**前端**的ngrok URL。如果要访问Django Admin，需要为**后端**（端口8000）单独启动ngrok！

---

## 快速检查清单

访问Admin前确保：

- [ ] Django正在运行（`python manage.py runserver 0.0.0.0:8000`）
- [ ] ngrok正在运行（`ngrok http 8000`）
- [ ] 使用ngrok的HTTPS URL（不是http://localhost:8000）
- [ ] URL格式正确（https://xxx.ngrok-free.app/admin/）

---

## 为什么本地可以但手机不行？

因为：
- `localhost`和`127.0.0.1`只能在本机访问
- 手机在不同的网络/设备上
- 需要通过ngrok将本地服务暴露到公网

---

## 不想用ngrok？试试局域网

如果手机和电脑在同一WiFi：

1. 获取电脑IP（Mac）：
```bash
ifconfig | grep "inet " | grep -v 127.0.0.1
```

2. 假设IP是`192.168.1.100`，手机访问：
```
http://192.168.1.100:8000/admin/
```

⚠️ 注意：某些WiFi网络（如公司、学校）可能阻止设备间通信。


