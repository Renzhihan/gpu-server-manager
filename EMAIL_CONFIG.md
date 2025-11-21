# 📧 邮件通知配置指南

GPU 服务器管理系统支持邮件通知功能，当监控的任务完成或 GPU 空闲时会自动发送邮件提醒。

## 配置步骤

### 1. 编辑 `.env` 配置文件

在项目根目录找到 `.env` 文件（如果不存在，复制 `.env.example` 并重命名为 `.env`）。

### 2. 配置 SMTP 邮箱信息

```env
# 邮件配置
SMTP_SERVER=smtp.gmail.com          # SMTP 服务器地址
SMTP_PORT=587                        # SMTP 端口（通常 587 或 465）
SMTP_USERNAME=your-email@gmail.com  # 发件人邮箱
SMTP_PASSWORD=your-app-password     # 邮箱授权码（不是登录密码）
SMTP_FROM=your-email@gmail.com      # 显示的发件人（可选，默认使用 SMTP_USERNAME）
```

### 3. 常见邮箱配置示例

#### Gmail
```env
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-16-digit-app-password
```

**获取 Gmail 应用专用密码：**
1. 登录 Gmail 账号
2. 访问 [应用专用密码](https://myaccount.google.com/apppasswords)
3. 选择应用：选择"邮件"，设备：选择"其他"
4. 生成并复制 16 位密码

#### QQ 邮箱
```env
SMTP_SERVER=smtp.qq.com
SMTP_PORT=587
SMTP_USERNAME=your-qq@qq.com
SMTP_PASSWORD=your-authorization-code
```

**获取 QQ 邮箱授权码：**
1. 登录 QQ 邮箱网页版
2. 设置 → 账户 → POP3/IMAP/SMTP/Exchange/CardDAV/CalDAV服务
3. 开启"IMAP/SMTP服务"
4. 生成授权码

#### 163 邮箱
```env
SMTP_SERVER=smtp.163.com
SMTP_PORT=587
SMTP_USERNAME=your-email@163.com
SMTP_PASSWORD=your-authorization-code
```

#### Outlook
```env
SMTP_SERVER=smtp-mail.outlook.com
SMTP_PORT=587
SMTP_USERNAME=your-email@outlook.com
SMTP_PASSWORD=your-password
```

### 4. 重启应用

修改 `.env` 文件后，需要重启应用以使配置生效。

## 使用邮件通知

### 在任务监控中使用

1. 创建进程监控或 GPU 空闲监控任务时
2. 在"邮件通知"字段填入收件人邮箱（支持多个，用逗号分隔）
3. 任务完成时会自动发送邮件

### 测试邮件配置

可以通过 API 测试邮件发送：

```bash
curl -X POST http://localhost:5000/api/email/send \
  -H "Content-Type: application/json" \
  -d '{
    "to_emails": ["test@example.com"],
    "subject": "测试邮件",
    "body": "这是一封测试邮件"
  }'
```

### 检查邮件配置状态

```bash
curl http://localhost:5000/api/email/status
```

返回示例：
```json
{
  "success": true,
  "configured": true,
  "smtp_server": "smtp.gmail.com",
  "smtp_from": "your-email@gmail.com"
}
```

## 常见问题

### ❌ 提示"邮件通知未配置"

**原因：** `.env` 文件中的 `SMTP_USERNAME` 或 `SMTP_PASSWORD` 为空或使用默认占位符。

**解决：** 按照上述步骤配置真实的邮箱信息。

### ❌ 邮件发送失败

**可能原因：**
1. **授权码错误**：确保使用应用专用密码/授权码，而非邮箱登录密码
2. **SMTP 服务未开启**：检查邮箱是否开启 SMTP 服务
3. **网络问题**：确保服务器能访问 SMTP 服务器
4. **端口错误**：尝试 587（TLS）或 465（SSL）

**调试方法：**
- 查看应用后台日志，会显示详细错误信息
- 检查任务详情中的 `email_status` 字段：
  - `sent`：发送成功
  - `failed`：发送失败
  - `no_email`：未配置收件人

### ⚠️ Gmail 安全警告

如果使用 Gmail 并遇到"不够安全的应用"警告：
1. 必须使用应用专用密码，不能使用账号密码
2. 确保账号已开启两步验证

## 安全建议

1. **不要将 `.env` 文件提交到版本控制系统**（已在 `.gitignore` 中忽略）
2. **定期更换授权码**
3. **使用专用邮箱**，避免使用重要的个人邮箱
4. **限制收件人**，避免邮件被滥用

## 邮件内容示例

任务完成时，会收到格式化的 HTML 邮件，包含：
- ✅ 任务状态（成功/失败/超时）
- 📋 任务名称
- 🖥️ 服务器名称
- 📝 详细信息（进程 PID、GPU 状态等）
- ⏰ 完成时间
