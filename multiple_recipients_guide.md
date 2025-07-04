# 多收件人邮件配置指南

## 1. 单个收件人（当前配置）
```bash
TO_EMAIL=michaelwang970403@gmail.com
```

## 2. 多个收件人配置

### 在 .env 文件中设置多个邮箱（用逗号分隔）
```bash
# 多个收件人示例
TO_EMAIL=user1@gmail.com,user2@yahoo.com,user3@outlook.com

# 支持空格（会自动去除）
TO_EMAIL=user1@gmail.com, user2@yahoo.com, user3@outlook.com

# 团队成员示例
TO_EMAIL=michael@company.com,sarah@company.com,john@company.com,team-lead@company.com
```

## 3. 安全发送数量建议

### ✅ 推荐数量
- **1-5 个收件人**: 完全安全，无需额外设置
- **6-10 个收件人**: 安全，已内置 2 秒延迟
- **11-20 个收件人**: 可行，建议增加延迟时间

### ⚠️ 大量收件人（20+）
如需发送给更多人，建议：
1. 分批发送
2. 使用专业邮件服务
3. 考虑邮件列表服务

## 4. 修改延迟时间

如果收件人较多（10+），可以增加延迟：

### 编辑 steam_daily.py 中的延迟设置
```python
# 找到这一行：
time.sleep(2)  # 2 second delay between emails

# 修改为更长延迟：
time.sleep(5)  # 5 second delay between emails
```

## 5. 测试多收件人设置

### 创建测试收件人列表
```bash
# 在 .env 中临时设置
TO_EMAIL=your-test1@gmail.com,your-test2@gmail.com
```

### 运行测试
```bash
python test_email.py
```

### 查看发送日志
运行脚本后会看到类似输出：
```
INFO | Sending email to 3 recipients
INFO | Email sent successfully to user1@gmail.com (1/3)
INFO | Email sent successfully to user2@yahoo.com (2/3)
INFO | Email sent successfully to user3@outlook.com (3/3)
INFO | Email sending complete: 3 successful, 0 failed
```

## 6. 故障排除

### 部分收件人失败
如果某些邮箱发送失败，脚本会：
- 继续发送给其他收件人
- 记录失败的邮箱和错误信息
- 在最后显示成功/失败统计

### 常见失败原因
1. **邮箱地址格式错误**
2. **收件人邮箱已满**
3. **收件人服务器临时不可用**
4. **被收件人服务器标记为垃圾邮件**

## 7. 高级配置选项

### 自定义延迟时间
```bash
# 在 .env 中添加
EMAIL_DELAY_SECONDS=3
```

### 批量大小控制
```bash
# 每批发送数量
EMAIL_BATCH_SIZE=5
```

### 实现示例（可选）
```python
# 在 steam_daily.py 中可以添加这些配置
EMAIL_DELAY = int(os.environ.get("EMAIL_DELAY_SECONDS", "2"))
BATCH_SIZE = int(os.environ.get("EMAIL_BATCH_SIZE", "10"))
```

## 8. 邮件内容个性化（可选）

如果想要针对不同收件人个性化内容：

```python
# 可以创建收件人配置文件
recipients_config = {
    "boss@company.com": "Dear Boss,\n\nHere are today's new Steam games...",
    "team@company.com": "Hi Team,\n\nDaily Steam update attached...",
    "default": "Attached are the new unreleased Steam games..."
}
```

## 9. 示例完整配置

### .env 文件示例
```bash
# SMTP 配置
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASS=your-app-password

# 多个收件人
TO_EMAIL=manager@company.com,analyst@company.com,intern@company.com
FROM_EMAIL=steam-bot@company.com

# 可选配置
MAX_WORKERS=32
EMAIL_DELAY_SECONDS=3
```

这样配置后，每天的 Steam 游戏数据会自动发送给所有指定的收件人！ 