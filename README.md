# Steam游戏爬虫MVP

一个简单的Steam新游戏监控系统，每天自动抓取Steam上的新游戏信息。

## 功能特性

- 🎮 每日自动抓取Steam新游戏
- 📊 游戏数据存储和管理
- 🌐 简洁的Web界面展示
- 🔄 RESTful API接口

## 技术栈

- **后端**: Django + Django REST Framework
- **爬虫**: Python + Requests + BeautifulSoup
- **前端**: 原生JavaScript + HTML/CSS
- **数据库**: SQLite (开发环境)

## 快速开始

### 方式一：一键安装（推荐）
```bash
# 运行安装脚本
./start.sh

# 创建演示数据（可选）
python3 demo_data.py

# 启动服务器
python3 run_server.py
```

### 方式二：手动安装
```bash
# 1. 安装依赖
pip3 install -r requirements.txt

# 2. 初始化数据库
cd backend
python3 manage.py makemigrations
python3 manage.py migrate

# 3. 创建管理员账户（可选）
python3 manage.py createsuperuser

# 4. 启动服务器
python3 manage.py runserver

# 5. 运行爬虫（新开终端）
python3 ../scraper/steam_scraper.py
```

### 访问应用
- **前端页面**: http://127.0.0.1:8000
- **API接口**: http://127.0.0.1:8000/api/
- **管理界面**: http://127.0.0.1:8000/admin/

## 项目结构

```
steam_scraper/
├── backend/           # Django后端
├── scraper/          # Steam爬虫
├── frontend/         # 前端页面
├── requirements.txt  # Python依赖
└── README.md        # 项目说明
```

## API接口

### 游戏相关
- `GET /api/games/` - 获取游戏列表（支持分页、搜索、排序）
- `GET /api/games/{id}/` - 获取游戏详情
- `GET /api/games/new_games/` - 获取新游戏列表
- `GET /api/games/free_games/` - 获取免费游戏列表
- `GET /api/games/on_sale/` - 获取打折游戏列表
- `GET /api/games/stats/` - 获取游戏统计信息

### 查询参数
- `search` - 搜索游戏名称、开发商等
- `ordering` - 排序字段（如：-scraped_at, price, -review_score）
- `is_free` - 筛选免费游戏
- `is_new` - 筛选新游戏
- `page` - 分页页码

## 功能演示

### 前端功能
1. **游戏列表展示** - 卡片式布局，显示游戏基本信息
2. **智能搜索** - 支持游戏名称、开发商等搜索
3. **多维筛选** - 新游戏、免费游戏、打折游戏分类
4. **灵活排序** - 按时间、价格、评分等排序
5. **游戏详情** - 点击游戏卡片查看详细信息
6. **响应式设计** - 支持手机、平板等设备

### 爬虫功能
1. **自动抓取** - 每日定时抓取Steam新游戏
2. **数据完整** - 游戏名称、价格、截图、标签等
3. **去重处理** - 避免重复数据
4. **错误处理** - 网络异常、API限制等容错
5. **日志记录** - 详细的运行日志

## 文件说明

### 核心文件
- `start.sh` - 一键安装脚本
- `run_server.py` - 服务器启动脚本
- `run_scraper.py` - 爬虫运行脚本
- `demo_data.py` - 演示数据创建脚本

### 后端目录 (backend/)
- `steam_project/` - Django项目配置
- `games/` - 游戏应用模块
- `templates/` - HTML模板
- `static/` - 静态资源（CSS、JS、图片）

### 爬虫目录 (scraper/)
- `steam_scraper.py` - 主爬虫程序
- `scheduler.py` - 定时任务调度器

## 扩展建议

### 功能扩展
1. **用户系统** - 注册登录、收藏游戏
2. **评论系统** - 用户评价和打分
3. **推荐算法** - 基于用户偏好推荐
4. **价格追踪** - 游戏价格历史记录
5. **邮件通知** - 新游戏、降价提醒

### 技术优化
1. **缓存系统** - Redis缓存热门数据
2. **队列系统** - Celery异步任务处理
3. **数据库优化** - PostgreSQL + 索引优化
4. **容器化部署** - Docker + Docker Compose
5. **监控告警** - 日志监控、性能监控

## 注意事项

⚠️ **重要提醒**
1. **遵守Steam服务条款** - 合理使用爬虫，避免过度请求
2. **网络礼仪** - 添加请求延迟，使用合适的User-Agent
3. **数据使用** - 仅用于学习研究，不用于商业用途
4. **定期维护** - Steam API可能变更，需要适时调整

## 故障排除

### 常见问题
1. **依赖安装失败**
   ```bash
   # 升级pip
   pip3 install --upgrade pip
   # 使用国内源
   pip3 install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/
   ```

2. **数据库迁移错误**
   ```bash
   # 删除迁移文件重新生成
   rm backend/games/migrations/0*.py
   cd backend && python3 manage.py makemigrations games
   ```

3. **爬虫数据为空**
   - 检查网络连接
   - 确认Steam API可访问
   - 运行演示数据脚本：`python3 demo_data.py`

4. **前端页面空白**
   - 确保Django服务器正在运行
   - 检查浏览器控制台错误信息
   - 确认静态文件路径正确 