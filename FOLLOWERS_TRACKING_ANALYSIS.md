# 多平台游戏Followers增速追踪系统分析

## 📋 需求分析

### 核心需求
- 追踪Steam、itch.io、TapTap三个平台的游戏followers数量
- 只追踪followers > 100的游戏
- 按24小时计算增速ratio
- 找出增速最快的游戏

### 技术挑战
- 需要时间序列数据存储
- 需要高频率数据采集
- 需要跨平台数据标准化
- 需要增速计算和排名算法

## 🏗️ 架构设计

### 1. 数据库设计

#### 必需的表结构：

```sql
-- 游戏基本信息表
CREATE TABLE games (
    id VARCHAR(50) PRIMARY KEY,
    platform VARCHAR(20) NOT NULL,
    title VARCHAR(500),
    author VARCHAR(200),
    url VARCHAR(500),
    genre VARCHAR(100),
    price VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_platform (platform),
    INDEX idx_title (title),
    UNIQUE KEY uk_platform_id (platform, id)
);

-- followers历史记录表
CREATE TABLE followers_history (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    game_id VARCHAR(50) NOT NULL,
    platform VARCHAR(20) NOT NULL,
    followers_count INT NOT NULL,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_game_time (game_id, recorded_at),
    INDEX idx_platform_time (platform, recorded_at),
    INDEX idx_followers_count (followers_count)
);

-- 增速统计表
CREATE TABLE growth_stats (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    game_id VARCHAR(50) NOT NULL,
    platform VARCHAR(20) NOT NULL,
    period_start TIMESTAMP NOT NULL,
    period_end TIMESTAMP NOT NULL,
    followers_start INT NOT NULL,
    followers_end INT NOT NULL,
    growth_count INT NOT NULL,
    growth_ratio DECIMAL(10,4) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_game_period (game_id, period_start, period_end),
    INDEX idx_growth_ratio (growth_ratio),
    INDEX idx_platform_period (platform, period_start, period_end)
);
```

### 2. 存储空间估算

#### 假设追踪数据：
- Steam: ~5,000 游戏 (followers > 100)
- itch.io: ~2,000 游戏 
- TapTap: ~1,000 游戏
- 总计: ~8,000 游戏

#### 存储需求计算：
```
每条followers记录: ~50 bytes
每天记录频率: 24次 (每小时一次)
每天新增数据: 8,000 × 24 × 50 = 9.6 MB/天
每月数据量: 9.6 MB × 30 = 288 MB/月
每年数据量: 288 MB × 12 = 3.46 GB/年
```

## 💻 代码修改需求

### 1. 现有代码需要的修改

#### Steam Daily (已有followers支持)
```python
# ✅ 已有followers获取功能
# 需要添加：数据库存储集成
def store_followers_to_db(game_id, followers_count):
    # 存储到followers_history表
    pass
```

#### itch.io Daily 
```python
# ❌ 缺少followers获取功能
# 需要添加：
def fetch_itch_followers_count(game_url):
    """
    itch.io没有直接followers概念
    可以用以下替代指标：
    - 游戏下载量 (downloads)
    - 评分人数 (rating count)
    - 评论数量 (comments)
    """
    pass
```

#### TapTap Daily
```python
# ❌ 缺少followers获取功能
# 需要添加：
def fetch_taptap_followers_count(game_id):
    """
    TapTap可以获取：
    - 关注数 (followers)
    - 预约数 (pre-orders)
    - 评论数 (reviews)
    """
    pass
```

### 2. 新增核心模块

#### followers_tracker.py (已创建)
- 多平台followers数据采集
- 时间序列数据存储
- 增速计算算法
- 排名和报告生成

#### 调度脚本
```python
# schedule_followers_tracking.py
import schedule
import time
from followers_tracker import FollowersTracker

def run_hourly_tracking():
    tracker = FollowersTracker()
    tracker.run_tracking_cycle()

# 每小时运行一次
schedule.every().hour.do(run_hourly_tracking)

while True:
    schedule.run_pending()
    time.sleep(60)
```

## 🗄️ 数据库部署选择

### 选项1: RDS MySQL (推荐)
```
优点：
- 自动备份和恢复
- 自动扩展
- 高可用性
- 维护简单

成本：
- db.t3.micro: $0.017/小时 = $12.24/月
- 存储: 20GB = $2.30/月
- 总计: ~$15/月
```

### 选项2: EC2 上的 MySQL
```
优点：
- 成本较低
- 完全控制

缺点：
- 需要手动维护
- 备份复杂
- 可能影响应用性能

额外成本：
- 主要是存储和备份
- 估计 +$5/月
```

## 💰 服务器成本分析

### 现有 EC2 t2.micro 限制
```
规格：
- 1 vCPU
- 1 GB 内存
- 低到中等网络性能
- 免费套餐：750小时/月

问题：
- 内存可能不足以同时运行多个爬虫
- CPU可能无法处理高频数据采集
- 网络带宽可能成为瓶颈
```

### 升级建议

#### 选项1: 升级到 t3.small
```
规格：
- 2 vCPU
- 2 GB 内存
- 更好的网络性能

成本：
- $0.0208/小时 = $15.00/月
- 比免费套餐增加 $15/月
```

#### 选项2: 保留t2.micro + 添加RDS
```
优点：
- 分离数据库和应用
- 更好的性能和可靠性
- 应用服务器负载降低

成本：
- EC2: $0 (免费套餐)
- RDS: $15/月
- 总计: $15/月
```

### 网络成本
```
数据传输估算：
- 每天API请求: 8,000 × 24 = 192,000 次
- 平均响应大小: 5KB
- 每日数据传输: 192,000 × 5KB = 960MB
- 每月数据传输: 960MB × 30 = 28.8GB

AWS数据传输成本：
- 前1GB: 免费
- 接下来27.8GB: $0.09/GB = $2.50/月
```

## 📊 总成本估算

### 最小化成本方案
```
- EC2 t2.micro: $0 (免费套餐)
- RDS db.t3.micro: $15/月
- 数据传输: $2.50/月
- 存储: $2.30/月
- 总计: ~$20/月
```

### 推荐方案
```
- EC2 t3.small: $15/月
- RDS db.t3.micro: $15/月
- 数据传输: $2.50/月
- 存储: $2.30/月
- 备份: $3/月
- 总计: ~$38/月
```

## 🚀 实施计划

### 阶段1: 数据库和核心功能 (Week 1-2)
1. 部署RDS MySQL数据库
2. 实施followers_tracker.py
3. 修改现有daily脚本集成数据库

### 阶段2: 平台特定功能 (Week 3-4)
1. 为itch.io添加followers获取功能
2. 为TapTap添加followers获取功能
3. 实施错误处理和重试机制

### 阶段3: 调度和监控 (Week 5)
1. 部署定时任务
2. 添加监控和告警
3. 性能优化

### 阶段4: 测试和上线 (Week 6)
1. 完整测试
2. 生产环境部署
3. 数据验证

## 🔧 技术优化建议

### 1. 性能优化
- 使用连接池减少数据库连接开销
- 实施批量插入减少数据库操作
- 添加缓存层减少重复请求

### 2. 可靠性优化
- 实施重试机制处理网络错误
- 添加备份和灾难恢复计划
- 监控和告警系统

### 3. 扩展性考虑
- 使用队列系统处理高并发
- 考虑数据库分片处理大数据量
- 微服务架构便于维护

## 📈 预期收益

### 1. 数据价值
- 实时游戏热度追踪
- 早期爆款游戏发现
- 市场趋势分析

### 2. 商业价值
- 游戏发行商的市场分析工具
- 投资者的决策支持数据
- 游戏媒体的新闻线索

### 3. 技术价值
- 时间序列数据处理经验
- 多平台数据集成经验
- 高频数据采集技术

## ⚠️ 风险评估

### 1. 技术风险
- 平台反爬虫措施
- API变更导致数据中断
- 数据库性能瓶颈

### 2. 成本风险
- 数据量增长超出预期
- 平台限制导致更多请求
- 服务器升级需求

### 3. 合规风险
- 平台服务条款限制
- 数据使用政策变化
- 隐私保护要求

## 🎯 结论

**建议采用推荐方案（~$38/月）**：

### 优势：
- 技术架构清晰，易于维护
- 性能足够应对预期负载
- 成本控制在合理范围内
- 具有良好的扩展性

### 实施建议：
1. 先从Steam平台开始验证概念
2. 逐步添加其他平台
3. 持续监控成本和性能
4. 根据实际使用情况调整配置

**预期ROI**：如果系统能够成功识别爆款游戏，其商业价值将远超过$38/月的运营成本。 