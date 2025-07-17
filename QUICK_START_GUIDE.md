# Followers Tracking System - Quick Start Guide

## 🚀 快速开始

这是一个完整的多平台游戏Followers增速追踪系统，支持Steam、Itch.io和TapTap平台。

### 系统要求

- Python 3.8+
- MySQL 5.7+ 或 8.0+
- 4GB+ RAM (推荐8GB)
- 10GB+ 磁盘空间

### 1. 环境准备

#### 安装依赖
```bash
pip install -r requirements.txt
```

#### 数据库设置
```bash
# 创建数据库
mysql -u root -p
CREATE DATABASE game_followers CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'followers_user'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON game_followers.* TO 'followers_user'@'localhost';
FLUSH PRIVILEGES;
```

### 2. 配置环境变量

复制环境配置文件：
```bash
cp env_followers_tracking.txt .env
```

编辑 `.env` 文件，填入你的配置：
```bash
# 数据库配置
DB_HOST=localhost
DB_PORT=3306
DB_USER=followers_user
DB_PASSWORD=your_password
DB_NAME=game_followers

# 追踪配置
MIN_FOLLOWERS=100
MAX_GAMES_PER_PLATFORM=1000

# Steam API配置
STEAM_API_KEY=your_steam_api_key

# 通知配置（可选）
NOTIFICATION_EMAIL=your_email@example.com
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@example.com
SMTP_PASSWORD=your_app_password
```

### 3. 初始化系统

#### 测试系统
```bash
# 运行测试套件
python test_followers_system.py
```

#### 手动运行一次
```bash
# 初始化数据库并运行一次追踪
python followers_tracker.py
```

### 4. 设置定时任务

#### 方法1: 使用内置调度器
```bash
# 启动调度器（前台运行）
python schedule_followers_tracking.py

# 后台运行
nohup python schedule_followers_tracking.py > followers_tracker.log 2>&1 &
```

#### 方法2: 使用Systemd服务
```bash
# 复制服务文件
sudo cp followers-tracker.service /etc/systemd/system/

# 启用并启动服务
sudo systemctl daemon-reload
sudo systemctl enable followers-tracker.service
sudo systemctl start followers-tracker.service

# 检查状态
sudo systemctl status followers-tracker.service
```

#### 方法3: 使用Cron
```bash
# 编辑cron任务
crontab -e

# 添加以下行（每小时运行一次）
0 * * * * cd /path/to/steam_scraper && python followers_tracker.py >> followers_tracker.log 2>&1
```

### 5. 监控和管理

#### 查看日志
```bash
# 实时查看日志
tail -f followers_tracker.log

# 查看服务日志
sudo journalctl -u followers-tracker.service -f
```

#### 检查数据库
```bash
mysql -u followers_user -p game_followers

# 查看追踪的游戏数量
SELECT platform, COUNT(*) as count FROM games GROUP BY platform;

# 查看最近的增速统计
SELECT * FROM growth_stats ORDER BY updated_at DESC LIMIT 10;

# 查看增速最快的游戏
SELECT g.platform, g.title, gs.growth_count, gs.growth_ratio 
FROM growth_stats gs 
JOIN games g ON gs.game_id = g.id 
WHERE gs.growth_count > 0 
ORDER BY gs.growth_ratio DESC 
LIMIT 10;
```

### 6. 常见问题

#### Q: 数据库连接失败
A: 检查MySQL服务是否运行，确认用户名密码正确
```bash
sudo systemctl status mysql
mysql -u followers_user -p
```

#### Q: Steam API限制
A: 检查API密钥是否有效，注意请求频率限制
```bash
# 测试API密钥
curl "https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/?key=YOUR_API_KEY&steamids=76561197960434622"
```

#### Q: 抓取失败率过高
A: 调整请求间隔和超时设置
```bash
# 在followers_tracker.py中调整
time.sleep(2)  # 增加请求间隔
```

#### Q: 磁盘空间不足
A: 定期清理历史数据
```bash
# 保留90天数据
DELETE FROM followers_history WHERE created_at < DATE_SUB(NOW(), INTERVAL 90 DAY);
```

### 7. 高级配置

#### 自定义平台适配
```python
# 在followers_tracker.py中添加新平台
def fetch_custom_platform_followers(self, game_id):
    """自定义平台followers获取"""
    # 实现你的逻辑
    pass
```

#### 设置告警
```python
# 在schedule_followers_tracking.py中配置告警
def send_growth_alert(top_games):
    """发送增速告警"""
    if len(top_games) > 0:
        # 发送邮件或其他通知
        pass
```

### 8. 生产环境部署

#### 使用Docker (推荐)
```bash
# 构建镜像
docker build -t followers-tracker .

# 运行容器
docker run -d --name followers-tracker \
  --env-file .env \
  --restart unless-stopped \
  followers-tracker
```

#### AWS部署
```bash
# 使用部署脚本
./deploy_followers_tracking.sh
```

### 9. 数据分析

#### 导出数据
```bash
# 导出增速统计
mysql -u followers_user -p game_followers -e "
SELECT 
    g.platform,
    g.title,
    gs.growth_count,
    gs.growth_ratio,
    gs.updated_at
FROM growth_stats gs
JOIN games g ON gs.game_id = g.id
ORDER BY gs.growth_ratio DESC
" > growth_report.csv
```

#### 创建仪表板
系统数据可以导入到Grafana、Tableau等工具中创建可视化仪表板。

### 10. 扩展功能

- **多语言支持**: 添加不同语言的游戏标题识别
- **价格追踪**: 扩展系统支持价格变化监控
- **社交媒体集成**: 集成Twitter、Discord等社交平台数据
- **预测模型**: 使用机器学习预测游戏增长趋势

## 🔧 故障排除

### 常用命令
```bash
# 重启服务
sudo systemctl restart followers-tracker.service

# 查看错误日志
sudo journalctl -u followers-tracker.service --no-pager

# 手动运行测试
python test_followers_system.py

# 查看进程
ps aux | grep followers

# 检查网络连接
curl -I https://store.steampowered.com/
curl -I https://itch.io/
```

### 性能优化
- 调整数据库连接池大小
- 使用缓存减少重复请求
- 优化SQL查询索引
- 考虑使用异步请求

## 📞 技术支持

如果遇到问题，可以：
1. 查看日志文件
2. 运行测试套件
3. 检查系统资源使用情况
4. 确认网络连接状态

系统设计为高可用和可扩展，适合长期运行和大规模数据处理。 