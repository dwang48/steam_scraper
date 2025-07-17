# Multi-Platform Game Followers Tracking System

一个完整的多平台游戏Followers增速追踪系统，支持Steam、Itch.io和TapTap平台，能够追踪游戏的followers增长速度并识别增长最快的游戏。

## 🎯 功能特点

### 核心功能
- **多平台支持**: Steam、Itch.io、TapTap三大平台
- **24小时增速追踪**: 自动计算24小时内的followers增长
- **阈值过滤**: 只追踪followers数量超过100的游戏
- **增长排名**: 自动识别增长最快的游戏
- **数据持久化**: MySQL数据库存储历史数据
- **定时调度**: 自动化的小时级数据收集

### 技术特性
- **高性能**: 优化的数据库设计和索引
- **可扩展**: 易于添加新平台支持
- **可部署**: Docker容器化部署
- **可监控**: 完整的日志和健康检查
- **可测试**: 全面的测试套件

## 📊 系统架构

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Steam API     │    │   Itch.io Web   │    │   TapTap Web    │
│   (API调用)     │    │   (网页爬取)    │    │   (网页爬取)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │ Followers       │
                    │ Tracker         │
                    │ (核心追踪系统)  │
                    └─────────────────┘
                                 │
                    ┌─────────────────┐
                    │ MySQL Database  │
                    │ - games         │
                    │ - followers_    │
                    │   history       │
                    │ - growth_stats  │
                    └─────────────────┘
                                 │
                    ┌─────────────────┐
                    │ Scheduler       │
                    │ (定时任务)      │
                    └─────────────────┘
```

## 🚀 快速开始

### 方法1: Docker部署 (推荐)

```bash
# 1. 克隆项目
git clone <repository-url>
cd steam_scraper

# 2. 配置环境变量
cp env_followers_tracking.txt .env
# 编辑.env文件，配置Steam API密钥等

# 3. 启动服务
docker-compose up -d

# 4. 查看日志
docker-compose logs -f followers-tracker
```

### 方法2: 本地部署

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置数据库
mysql -u root -p
CREATE DATABASE game_followers;
CREATE USER 'followers_user'@'localhost' IDENTIFIED BY 'password';
GRANT ALL PRIVILEGES ON game_followers.* TO 'followers_user'@'localhost';

# 3. 配置环境变量
export DB_HOST=localhost
export DB_USER=followers_user
export DB_PASSWORD=password
export DB_NAME=game_followers
export STEAM_API_KEY=your_steam_api_key

# 4. 运行测试
python test_followers_system.py

# 5. 启动系统
python schedule_followers_tracking.py
```

## 📁 项目结构

```
steam_scraper/
├── followers_tracker.py          # 核心追踪系统
├── schedule_followers_tracking.py # 定时调度器
├── test_followers_system.py      # 测试套件
├── steam_daily.py                # Steam平台爬虫
├── itch_daily.py                 # Itch.io平台爬虫
├── taptap_daily.py               # TapTap平台爬虫
├── cost_analysis.py              # 成本分析工具
├── deploy_followers_tracking.sh  # 部署脚本
├── followers-tracker.service     # Systemd服务文件
├── Dockerfile                    # Docker镜像构建
├── docker-compose.yml            # Docker编排文件
├── init.sql                      # 数据库初始化脚本
├── requirements.txt              # Python依赖
├── env_followers_tracking.txt    # 环境变量模板
├── FOLLOWERS_TRACKING_ANALYSIS.md # 系统分析文档
├── QUICK_START_GUIDE.md          # 快速开始指南
└── README_FOLLOWERS_TRACKING.md  # 本文档
```

## 🔧 配置说明

### 环境变量

| 变量名 | 描述 | 默认值 | 必需 |
|--------|------|--------|------|
| `DB_HOST` | 数据库主机地址 | `localhost` | 是 |
| `DB_PORT` | 数据库端口 | `3306` | 否 |
| `DB_USER` | 数据库用户名 | `root` | 是 |
| `DB_PASSWORD` | 数据库密码 | - | 是 |
| `DB_NAME` | 数据库名称 | `game_followers` | 是 |
| `STEAM_API_KEY` | Steam API密钥 | - | 是 |
| `MIN_FOLLOWERS` | 最小followers阈值 | `100` | 否 |
| `MAX_GAMES_PER_PLATFORM` | 每平台最大游戏数 | `1000` | 否 |
| `NOTIFICATION_EMAIL` | 通知邮箱 | - | 否 |

### 数据库配置

系统使用MySQL作为数据存储，包含以下表：

- **games**: 游戏基本信息
- **followers_history**: followers历史数据
- **growth_stats**: 增长统计数据

详细的数据库设计请参考 `init.sql` 文件。

## 📈 使用方法

### 命令行使用

```bash
# 运行一次追踪
python followers_tracker.py

# 启动定时调度
python schedule_followers_tracking.py

# 运行测试
python test_followers_system.py

# 分析成本
python cost_analysis.py
```

### 查看数据

```sql
-- 查看增长最快的游戏
SELECT * FROM top_growth_games LIMIT 10;

-- 查看平台统计
SELECT * FROM platform_stats;

-- 查看特定游戏的历史数据
SELECT * FROM followers_history 
WHERE game_id = 'your_game_id' 
ORDER BY created_at DESC;
```

### API集成

```python
from followers_tracker import FollowersTracker

# 创建追踪器实例
tracker = FollowersTracker()

# 初始化数据库
tracker.init_database()

# 运行追踪周期
top_games = tracker.run_tracking_cycle()

# 获取增长最快的游戏
top_games = tracker.get_top_growth_games(limit=10)
```

## 🔍 监控和维护

### 日志管理

```bash
# 查看实时日志
tail -f followers_tracker.log

# 查看系统服务日志
sudo journalctl -u followers-tracker.service -f

# 查看Docker容器日志
docker-compose logs -f followers-tracker
```

### 性能监控

```sql
-- 查看数据库大小
SELECT 
    table_name,
    round(((data_length + index_length) / 1024 / 1024), 2) as size_mb
FROM information_schema.tables 
WHERE table_schema = 'game_followers';

-- 查看追踪统计
SELECT 
    platform,
    COUNT(*) as total_games,
    AVG(current_followers) as avg_followers
FROM games g
JOIN growth_stats gs ON g.id = gs.game_id
GROUP BY platform;
```

### 数据清理

```sql
-- 清理90天前的历史数据
CALL CleanOldData(90);

-- 手动清理
DELETE FROM followers_history 
WHERE created_at < DATE_SUB(NOW(), INTERVAL 90 DAY);
```

## 💰 成本分析

### 基础配置 (AWS t2.micro)
- **月成本**: $23.46
- **适用场景**: 测试和小规模使用
- **支持游戏数**: ~1,000

### 推荐配置 (AWS t3.small)
- **月成本**: $38.43
- **适用场景**: 生产环境
- **支持游戏数**: ~5,000

### 高性能配置 (AWS t3.medium)
- **月成本**: $65.65
- **适用场景**: 大规模数据处理
- **支持游戏数**: ~10,000+

详细成本分析请参考 `FOLLOWERS_TRACKING_ANALYSIS.md` 文档。

## 🛠️ 开发和扩展

### 添加新平台

```python
# 在followers_tracker.py中添加新平台方法
def fetch_newplatform_followers(self, game_id):
    """新平台followers获取"""
    # 实现平台特定的逻辑
    pass

# 在run_tracking_cycle中添加调用
elif platform == 'newplatform':
    followers = self.fetch_newplatform_followers(game_id)
```

### 自定义通知

```python
# 在schedule_followers_tracking.py中自定义通知
def send_custom_notification(top_games):
    """发送自定义通知"""
    # 实现通知逻辑（邮件、Slack、Discord等）
    pass
```

### 扩展数据分析

```python
# 添加新的分析功能
def analyze_growth_trends(self, days=7):
    """分析增长趋势"""
    # 实现趋势分析逻辑
    pass
```

## 🔒 安全考虑

- **API密钥管理**: 使用环境变量存储敏感信息
- **数据库安全**: 使用专用用户和权限控制
- **网络安全**: 配置防火墙和访问控制
- **数据加密**: 生产环境建议使用SSL/TLS

## 📋 故障排除

### 常见问题

1. **数据库连接失败**
   ```bash
   # 检查MySQL服务状态
   sudo systemctl status mysql
   
   # 测试连接
   mysql -u followers_user -p game_followers
   ```

2. **Steam API限制**
   ```bash
   # 检查API密钥
   curl "https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/?key=YOUR_KEY&steamids=76561197960434622"
   ```

3. **爬取失败**
   ```bash
   # 检查网络连接
   curl -I https://store.steampowered.com/
   curl -I https://itch.io/
   ```

### 性能优化

- 调整数据库连接池大小
- 优化SQL查询和索引
- 增加请求间隔减少被封IP的风险
- 使用缓存减少重复请求

## 📄 许可证

MIT License - 详见LICENSE文件

## 🤝 贡献指南

1. Fork项目
2. 创建功能分支
3. 提交更改
4. 推送到分支
5. 创建Pull Request

## 📞 支持

如果遇到问题或有建议，请：
1. 查看文档和FAQ
2. 运行测试套件诊断问题
3. 查看日志文件
4. 提交Issue或联系开发者

---

🎮 **Happy Game Tracking!** 🚀 