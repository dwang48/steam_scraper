# 邮件发送最佳实践指南

## Gmail 发送限制详情

### 每日限制
- **个人 Gmail**: 500 封/天
- **Google Workspace**: 2000 封/天
- **每小时**: ~100 封
- **每分钟**: ~20 封

### 您的项目：每天 1 封邮件 ✅ 安全

## 避免被标记为垃圾邮件

### ✅ 好的做法
1. **规律发送时间** - 每天固定时间发送
2. **清晰主题行** - 如 "Steam New Games 2025-01-15"
3. **合理内容** - 避免过多大写字母、感叹号
4. **发件人认证** - 使用 App Password
5. **适当频率** - 每天 1 封完全安全

### ❌ 避免的做法
1. **批量发送** - 短时间内发送大量邮件
2. **垃圾关键词** - "FREE"、"URGENT"、"CLICK NOW"
3. **可疑链接** - 缩短链接或可疑域名
4. **HTML 过度** - 复杂的 HTML 格式
5. **无规律发送** - 随机时间大量发送

## 监控邮件状态

### 1. 检查发送状态
```python
# 在 steam_daily.py 中已有错误处理
def send_email(csv_path: Path):
    try:
        # ... SMTP 代码 ...
        logger.info("Email sent successfully to %s", to_email)
    except smtplib.SMTPException as e:
        logger.error("SMTP error: %s", e)
    except Exception as e:
        logger.error("Email sending failed: %s", e)
```

### 2. Gmail 发送历史检查
- 登录 Gmail
- 查看"已发送"文件夹
- 检查是否有退回邮件

### 3. 收件箱检查
- 确认邮件到达收件箱（不在垃圾邮件文件夹）
- 如果在垃圾邮件中，标记为"非垃圾邮件"

## 多收件人场景

如果将来需要发送给多个收件人：

### 安全数量
- **1-5 个收件人**: 完全安全
- **6-20 个收件人**: 建议使用密送 (BCC)
- **20+ 个收件人**: 考虑分批发送

### 分批发送示例
```python
import time

def send_to_multiple(recipients, csv_path):
    for i, email in enumerate(recipients):
        send_email_to_single(email, csv_path)
        if i > 0 and i % 10 == 0:  # 每 10 封邮件暂停
            time.sleep(60)  # 等待 1 分钟
```

## 替代方案

如果担心邮件限制，可考虑：

### 1. 云存储 + 通知
```python
# 上传到 Dropbox/Google Drive，发送下载链接
def upload_and_notify(csv_path):
    upload_url = upload_to_cloud(csv_path)
    send_simple_notification(upload_url)
```

### 2. 压缩附件
```python
import gzip

def compress_csv(csv_path):
    with open(csv_path, 'rb') as f_in:
        with gzip.open(f"{csv_path}.gz", 'wb') as f_out:
            f_out.writelines(f_in)
    return f"{csv_path}.gz"
```

### 3. 邮件服务提供商
- **SendGrid**: 每天 100 封免费
- **Mailgun**: 每月 5000 封免费  
- **AWS SES**: 每天 200 封免费

## 总结

您的使用场景（每天 1 封邮件给自己）：
- ✅ **完全安全**，不会触发任何限制
- ✅ **不会被标记为垃圾邮件**
- ✅ **可以长期稳定运行**

即使将来扩展到每天发送给 10-20 个收件人，也在安全范围内。 