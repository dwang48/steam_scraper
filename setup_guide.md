# Steam Daily Crawler 部署设置指南

## 1. 邮件服务设置

### Gmail 设置（推荐）
1. **开启两步验证**：登录 Google 账户，开启两步验证
2. **生成应用密码**：
   - 访问：https://myaccount.google.com/apppasswords
   - 选择"邮件"和设备
   - 生成 16 位应用密码（例如：`abcd efgh ijkl mnop`）

### 其他邮件服务商设置
```bash
# QQ邮箱
SMTP_HOST=smtp.qq.com
SMTP_PORT=587

# 163邮箱  
SMTP_HOST=smtp.163.com
SMTP_PORT=587

# Outlook/Hotmail
SMTP_HOST=smtp-mail.outlook.com
SMTP_PORT=587

# 阿里云邮箱
SMTP_HOST=smtp.mxhichina.com
SMTP_PORT=587
```

## 2. 环境变量配置

创建 `.env` 文件（复制 `env_example.txt` 并修改）：

```bash
cp env_example.txt .env
nano .env  # 或使用其他编辑器
```

修改内容：
```bash
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_actual_email@gmail.com
SMTP_PASS=your_16_digit_app_password
TO_EMAIL=recipient@example.com
FROM_EMAIL=your_actual_email@gmail.com
MAX_WORKERS=32
```

## 3. 定时执行设置

### 方法一：Linux/Mac cron（推荐）

编辑 crontab：
```bash
crontab -e
```

添加定时任务（美西时间早上8点 = UTC 16:00）：
```bash
# 每天 UTC 16:00 (美西 08:00) 执行
0 16 * * * cd /path/to/steam_scraper && source venv/bin/activate && python steam_daily.py >> logs/steam_daily.log 2>&1
```

创建日志目录：
```bash
mkdir -p logs
```

### 方法二：Windows 任务计划程序

1. 打开"任务计划程序"
2. 创建基本任务
3. 设置触发器：每天，时间选择对应的本地时间
4. 操作：启动程序
   - 程序：`python`
   - 参数：`steam_daily.py`
   - 起始于：脚本所在目录

### 方法三：Python 内置调度器（简单测试用）

创建 `scheduler.py`：
```python
import schedule
import time
import subprocess
import os

def run_crawler():
    print(f"Starting crawler at {time.strftime('%Y-%m-%d %H:%M:%S')}")
    result = subprocess.run(['python', 'steam_daily.py'], 
                          capture_output=True, text=True)
    print(f"Exit code: {result.returncode}")
    if result.stdout:
        print(f"Output: {result.stdout}")
    if result.stderr:
        print(f"Error: {result.stderr}")

# 每天美西时间 08:00 执行（需要设置服务器时区）
schedule.every().day.at("08:00").do(run_crawler)

print("Scheduler started. Waiting for 08:00 daily...")
while True:
    schedule.run_pending()
    time.sleep(60)
```

## 4. 测试配置

### 测试邮件发送
```bash
python -c "
import os
from dotenv import load_dotenv
load_dotenv()

import smtplib
from email.message import EmailMessage

msg = EmailMessage()
msg['Subject'] = 'Steam Crawler Test'
msg['From'] = os.environ['SMTP_USER']
msg['To'] = os.environ['TO_EMAIL']
msg.set_content('Test email from Steam crawler')

with smtplib.SMTP(os.environ['SMTP_HOST'], int(os.environ['SMTP_PORT'])) as smtp:
    smtp.starttls()
    smtp.login(os.environ['SMTP_USER'], os.environ['SMTP_PASS'])
    smtp.send_message(msg)
print('Test email sent successfully!')
"
```

### 测试脚本运行
```bash
# 首次运行（建立基线）
python steam_daily.py

# 查看输出日志
tail -f logs/steam_daily.log  # 如果使用 cron
```

## 5. 常见问题

### Gmail 认证失败
- 确保开启了两步验证
- 使用应用密码，不是账户密码
- 检查 `SMTP_USER` 是否正确

### 时区问题
- cron 使用服务器本地时间
- 如果服务器是 UTC，美西早上8点 = UTC 16:00
- 夏令时期间可能需要调整

### 权限问题
```bash
chmod +x steam_daily.py
# 确保 Python 虚拟环境路径正确
which python  # 确认 Python 路径
```

## 6. 生产环境建议

1. **日志轮转**：
```bash
# 在 cron 中使用 logrotate
0 16 * * * cd /path/to/steam_scraper && source venv/bin/activate && python steam_daily.py >> logs/steam_daily_$(date +\%F).log 2>&1
```

2. **错误监控**：
```bash
# 失败时发送通知邮件
0 16 * * * cd /path/to/steam_scraper && source venv/bin/activate && python steam_daily.py || echo "Steam crawler failed" | mail -s "Crawler Error" admin@example.com
```

3. **资源限制**：
```bash
# 限制 CPU 和内存使用
0 16 * * * nice -n 10 timeout 30m python steam_daily.py
``` 