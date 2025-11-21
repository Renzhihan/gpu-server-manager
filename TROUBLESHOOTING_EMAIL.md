# 📧 邮件发送问题排查指南

## "list index out of range" 错误

### 可能的原因

1. **邮箱地址格式问题**
   - 邮箱地址包含特殊字符
   - 邮箱地址格式不正确
   - 配置文件中的邮箱地址损坏

2. **SMTP 库内部错误**
   - Python smtplib 解析邮箱地址失败
   - 邮件头格式问题

### 排查步骤

#### 步骤1：查看详细日志

系统已添加详细的调试日志。在测试邮件发送时，查看控制台输出：

```bash
# 如果是开发环境，直接运行
python run.py

# 查看输出中的调试信息：
[邮件调试] 尝试发送邮件:
  服务器: smtp.163.com:465
  加密: SSL
  发件人: your@163.com
  收件人: ['your@163.com']
[邮件调试] SSL 连接成功
[邮件调试] 登录成功
[邮件调试] 邮件发送成功
```

如果出现错误，会看到：
```
[邮件错误] 索引错误: list index out of range
```

#### 步骤2：检查配置文件

查看 `data/smtp_config.json`：

```bash
cat data/smtp_config.json
```

确认内容格式正确：
```json
{
  "smtp_server": "smtp.163.com",
  "smtp_port": 465,
  "smtp_username": "your_email@163.com",
  "smtp_password": "your_auth_code",
  "smtp_from": "your_email@163.com",
  "smtp_use_tls": false,
  "smtp_use_ssl": true
}
```

**注意检查：**
- `smtp_username` 必须是完整的邮箱地址
- 邮箱地址不能有空格或特殊字符
- `smtp_password` 是授权码，不是登录密码

#### 步骤3：重新配置

如果配置文件有问题，建议：

1. **删除配置文件重新配置**
   ```bash
   rm data/smtp_config.json
   ```

2. **使用快速配置模板**
   - 进入任务监控页面
   - 点击"立即配置"
   - 点击 **163邮箱** 按钮（自动填充）
   - 手动填写：
     - 邮箱账号：`your_email@163.com`（完整邮箱）
     - 密码：授权码（不是登录密码！）
   - 点击"测试配置"

#### 步骤4：测试简化配置

如果问题持续，尝试最简化配置：

```python
# 在 Python 环境中测试
from app.services.email_service import EmailService

# 手动设置简单配置
config = {
    'smtp_server': 'smtp.163.com',
    'smtp_port': 465,
    'smtp_username': 'your@163.com',  # 你的163邮箱
    'smtp_password': 'YOUR_AUTH_CODE',  # 授权码
    'smtp_from': 'your@163.com',
    'smtp_use_tls': False,
    'smtp_use_ssl': True
}

EmailService.save_smtp_config(config)

# 测试发送
result = EmailService.send_email(
    to_emails=['your@163.com'],
    subject='测试邮件',
    body='这是测试'
)

print(result)
```

---

## 163 邮箱特殊注意事项

### 授权码获取

1. 登录 163 邮箱网页版
2. 设置 → POP3/SMTP/IMAP
3. 开启 **IMAP/SMTP服务**
4. 获取 **客户端授权密码**
5. 这个授权密码通常是一个随机字符串

### 正确的配置

```
SMTP 服务器：smtp.163.com
端口：465
加密方式：SSL ✅（重要！）
邮箱账号：完整邮箱地址（例如：zhangsan@163.com）
密码：授权码（不是登录密码！）
```

### 常见错误

❌ **错误1：使用了登录密码**
```
密码：输入的是登录密码
```
✅ 正确：使用授权码
```
密码：授权码（例如：ABC123XYZ789）
```

❌ **错误2：端口配置错误**
```
端口：587
加密：TLS
```
✅ 正确（163邮箱）：
```
端口：465
加密：SSL
```

❌ **错误3：邮箱格式不完整**
```
邮箱账号：zhangsan
```
✅ 正确：
```
邮箱账号：zhangsan@163.com
```

---

## 快速解决方案

### 方案A：使用 QQ 邮箱代替

如果 163 邮箱持续出现问题，建议改用 QQ 邮箱：

1. **更稳定**：QQ 邮箱的 SMTP 服务更稳定
2. **更简单**：配置过程相同
3. **速度快**：发送速度更快

配置方法：
```
SMTP 服务器：smtp.qq.com
端口：587
加密：TLS
邮箱：your@qq.com
密码：QQ邮箱授权码
```

### 方案B：检查网络环境

有时问题可能是网络导致的：

```bash
# 测试能否连接到 163 SMTP 服务器
telnet smtp.163.com 465

# 或使用 nc
nc -zv smtp.163.com 465
```

如果无法连接，可能是：
- 防火墙阻止
- 网络限制
- 服务器无法访问外网

---

## 已知问题和解决方案

### 问题1：list index out of range

**症状**：点击"测试配置"后显示此错误，日志显示"登录成功"之后出现错误

**根本原因**：
- 163邮箱对邮件格式要求严格，`send_message()` 方法在解析邮件地址时会出现索引错误
- 发件人地址格式不正确（如只填写了名称，没有邮箱地址）

**已修复**：
- v1.0.8 版本已修复此问题
- 使用 `sendmail()` 替代 `send_message()`，更明确地指定发送者和接收者
- 增强发件人地址验证，确保包含 '@' 符号

**如果仍然遇到此问题**：
1. 删除 `data/smtp_config.json` 重新配置
2. 确保邮箱地址格式正确（必须是完整的邮箱地址，如 `your@163.com`）
3. 使用快速配置模板（点击"163邮箱"按钮）
4. 查看控制台详细日志
5. 更新到最新版本

### 问题2：认证失败

**症状**：提示用户名或密码错误

**解决方案**：
- 163/126 邮箱：必须使用授权码
- QQ 邮箱：必须使用授权码
- Gmail：必须使用应用专用密码
- Outlook：可以使用登录密码

### 问题3：Connection unexpectedly closed 或 SSL: WRONG_VERSION_NUMBER

**症状**：
- "Connection unexpectedly closed" - 连接意外关闭
- "SSL: WRONG_VERSION_NUMBER" - SSL版本错误

**原因**：
- 端口和加密方式不匹配
- 465 端口必须使用 SSL 加密
- 587 端口必须使用 TLS 加密

**解决方案**：
1. **使用 465 端口**：必须选择 **SSL** 加密
   ```
   端口：465
   加密：SSL ✓
   ```

2. **使用 587 端口**：必须选择 **TLS** 加密
   ```
   端口：587
   加密：TLS ✓
   ```

3. **163邮箱推荐配置**：
   ```
   SMTP 服务器：smtp.163.com
   端口：465
   加密：SSL
   ```

4. **使用快速配置模板**：
   - 点击"163邮箱"按钮会自动设置正确的端口和加密方式

---

## 获取帮助

### 查看日志

运行程序时，控制台会输出详细日志：

```
[邮件调试] 尝试发送邮件:
[邮件调试] 服务器: smtp.163.com:465
[邮件调试] 加密: SSL
[邮件调试] 发件人: xxx@163.com
[邮件调试] 收件人: ['xxx@163.com']
...
```

### 提交 Issue

如果问题持续，请在 GitHub 提交 Issue，并附上：

1. 使用的邮箱类型（163/QQ/Gmail等）
2. 配置信息（**隐藏密码**）
3. 完整的错误日志
4. 系统环境（Windows/Linux/Mac）

---

## 成功案例

### 163 邮箱成功配置示例

```json
{
  "smtp_server": "smtp.163.com",
  "smtp_port": 465,
  "smtp_username": "zhangsan@163.com",
  "smtp_password": "ABCDEFGHIJKLMNOP",
  "smtp_from": "zhangsan@163.com",
  "smtp_use_tls": false,
  "smtp_use_ssl": true
}
```

### 测试输出（成功）

```
[邮件调试] 尝试发送邮件:
  服务器: smtp.163.com:465
  加密: SSL
  发件人: zhangsan@163.com
  收件人: ['zhangsan@163.com']
[邮件调试] SSL 连接成功
[邮件调试] 登录成功
[邮件调试] 邮件发送成功
```

---

## 最后的建议

1. **使用快速配置模板** - 不要手动输入，点击163邮箱按钮
2. **确认使用授权码** - 不是登录密码
3. **查看详细日志** - 控制台会显示每一步
4. **先测试再保存** - 使用"测试配置"功能
5. **考虑换邮箱** - QQ邮箱通常更稳定

如果按照以上步骤仍无法解决，请提供详细日志以便进一步诊断。
