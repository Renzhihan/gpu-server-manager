# 🔒 安全配置指南

## ⚠️ 重要安全警告

本系统包含敏感的服务器管理功能，**不当配置可能导致严重的安全风险**。在部署到生产环境前，请务必完成以下安全加固步骤。

---

## 🚨 必须执行的安全配置（P0 级别）

### 1. 修改管理员密码

**默认密码极其不安全，必须立即修改！**

```bash
# 编辑 .env 文件
nano .env

# 设置强密码（至少16位，包含大小写字母、数字和特殊字符）
ADMIN_PASSWORD=Your_Very_Strong_Password_Here_2024!@#
```

**强密码要求：**
- 至少 16 个字符
- 包含大写字母、小写字母、数字和特殊字符
- 不包含常见单词或个人信息
- 定期更换（建议每90天）

### 2. 设置强随机 SECRET_KEY

**默认 SECRET_KEY 会导致 Session 可被伪造！**

```bash
# 生成强随机密钥
python -c "import secrets; print(secrets.token_hex(32))"

# 将生成的密钥写入 .env
SECRET_KEY=生成的64位十六进制字符串
```

### 3. 限制网络访问

**默认配置：** 绑定到 `0.0.0.0`，所有网络接口均可访问

**推荐配置：**

```bash
# 方案1：仅本机访问（最安全）
python run.py --host 127.0.0.1

# 方案2：仅内网访问
python run.py --host 192.168.1.100  # 使用内网IP

# 方案3：使用防火墙限制
sudo ufw allow from 192.168.1.0/24 to any port 5000
sudo ufw deny 5000
```

### 4. 保护配置文件权限

**敏感文件必须限制访问权限：**

```bash
# 限制配置文件权限（仅所有者可读写）
chmod 600 config/servers.yaml
chmod 600 .env
chmod 600 data/smtp_config.json

# 确保目录权限正确
chmod 700 config/
chmod 700 data/
```

---

## 🛡️ 强烈推荐的安全配置（P1 级别）

### 5. 启用 HTTPS

**HTTP 明文传输会暴露所有敏感数据！**

```bash
# 方案1：生成自签名证书（内网环境）
mkdir -p ssl
openssl req -x509 -newkey rsa:4096 -nodes \
  -keyout ssl/key.pem -out ssl/cert.pem -days 365 \
  -subj "/CN=localhost"

# 启动 HTTPS
python run.py --https

# 方案2：使用 Let's Encrypt 证书（公网环境）
# 需要配置 Nginx 反向代理
```

### 6. 使用 SSH 密钥而非密码

**SSH 密码明文存储在配置文件中，密钥更安全：**

```yaml
# config/servers.yaml - 推荐配置
servers:
  - name: "GPU Server 1"
    host: "192.168.1.100"
    username: "admin"
    key_file: "/path/to/private_key"  # 使用密钥
    # password: "xxx"  # 不要使用密码
```

**生成 SSH 密钥对：**
```bash
ssh-keygen -t ed25519 -C "gpu-manager"
ssh-copy-id -i ~/.ssh/id_ed25519.pub user@remote-server
```

### 7. 配置 CORS 白名单

**默认仅允许本地访问，如需其他域名，请明确指定：**

```bash
# .env 文件
CORS_ORIGINS=http://localhost:5000,http://127.0.0.1:5000,http://your-trusted-domain.com
```

### 8. 定期备份和审计

```bash
# 定期备份配置（删除敏感信息）
cp config/servers.yaml config/servers.yaml.backup
# 手动编辑 backup 文件，移除所有密码

# 查看访问日志
tail -f error.log

# 定期检查异常登录
grep "login" error.log
```

---

## 🔧 额外安全建议（P2 级别）

### 9. 使用反向代理

**通过 Nginx 提供额外的安全层：**

```nginx
# /etc/nginx/sites-available/gpu-manager
server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    # 安全头
    add_header Strict-Transport-Security "max-age=31536000" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;

    # 限流
    limit_req_zone $binary_remote_addr zone=login:10m rate=5r/m;

    location /login {
        limit_req zone=login burst=3;
        proxy_pass http://127.0.0.1:5000;
    }

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 10. 容器化部署

```dockerfile
# Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .

# 非 root 用户运行
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

CMD ["python", "run.py", "--host", "0.0.0.0"]
```

### 11. 监控和告警

```bash
# 安装 fail2ban 防止暴力破解
sudo apt install fail2ban

# 配置规则
cat > /etc/fail2ban/jail.local <<EOF
[gpu-manager]
enabled = true
port = 5000
filter = gpu-manager
logpath = /path/to/error.log
maxretry = 3
bantime = 3600
EOF
```

---

## 📊 安全检查清单

部署前请确认以下所有项目：

- [ ] ✅ 修改了管理员密码（非默认值）
- [ ] ✅ 设置了强随机 SECRET_KEY
- [ ] ✅ 限制了网络访问（不对公网开放）
- [ ] ✅ 配置文件权限正确（600）
- [ ] ✅ 启用了 HTTPS（生产环境必须）
- [ ] ✅ 使用 SSH 密钥而非密码
- [ ] ✅ 配置了 CORS 白名单
- [ ] ✅ 定期备份配置文件
- [ ] ⬜ 配置了反向代理（可选）
- [ ] ⬜ 启用了监控和日志（可选）
- [ ] ⬜ 定期安全审计（建议）

---

## 🚫 安全禁忌

**永远不要：**

1. ❌ 使用默认密码 `admin`
2. ❌ 将系统直接暴露到公网
3. ❌ 在配置文件中使用明文密码（优先使用密钥）
4. ❌ 禁用 HTTPS（生产环境）
5. ❌ 将 `config/servers.yaml` 提交到 Git
6. ❌ 将 `.env` 文件提交到 Git
7. ❌ 在不受信任的网络中使用（如公共 WiFi）
8. ❌ 与他人共享管理员密码
9. ❌ 忽略安全警告和日志
10. ❌ 长期不更新密码和密钥

---

## 📞 安全问题报告

如发现安全漏洞，请通过 GitHub Issues 私密报告，不要公开披露。

---

## 📚 参考资源

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Flask 安全最佳实践](https://flask.palletsprojects.com/en/latest/security/)
- [Paramiko 安全配置](https://docs.paramiko.org/en/stable/api/policy.html)

---

**记住：安全是一个持续的过程，不是一次性配置！**
