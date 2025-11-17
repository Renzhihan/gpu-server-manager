# 快速开始指南

## 1. 配置服务器信息

编辑 `config/servers.yaml` 文件，添加你的 GPU 服务器：

```bash
vi config/servers.yaml
```

示例配置：

```yaml
servers:
  - name: "GPU Server 1"
    host: "192.168.1.101"  # 修改为实际IP
    port: 22
    username: "root"       # 修改为实际用户名
    password: "your-password"  # 修改为实际密码
    gpu_enabled: true
    description: "主训练服务器"
```

**安全建议：** 使用 SSH 密钥代替密码

```yaml
servers:
  - name: "GPU Server 1"
    host: "192.168.1.101"
    port: 22
    username: "root"
    key_file: "/root/.ssh/id_rsa"  # SSH 私钥路径
    gpu_enabled: true
```

## 2. 配置邮件通知（可选）

编辑 `.env` 文件：

```bash
vi .env
```

修改邮件配置：

```bash
# Gmail 示例（需要开启应用专用密码）
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password  # 应用专用密码，非账号密码
SMTP_FROM=your-email@gmail.com
```

**Gmail 应用专用密码设置：**
1. 访问 https://myaccount.google.com/apppasswords
2. 生成应用专用密码
3. 将密码填入 `SMTP_PASSWORD`

## 3. 启动应用

### 方法一：使用启动脚本（推荐）

```bash
./start.sh
```

### 方法二：手动启动

```bash
# 激活 conda 环境
conda activate gpu-server-manager

# 启动应用
python run.py
```

## 4. 访问系统

在浏览器中打开：

```
http://localhost:5000
```

或从其他电脑访问：

```
http://<服务器IP>:5000
```

## 5. 功能测试

### 测试 GPU 监控
1. 进入"GPU 监控"页面
2. 选择一台 GPU 服务器
3. 查看 GPU 使用情况

### 测试 Docker 管理
1. 进入"Docker 管理"页面
2. 选择一台服务器
3. 查看容器和镜像列表

### 测试任务监控 + 邮件通知
1. 在服务器上运行一个测试任务：
   ```bash
   # 在 GPU 服务器上执行
   sleep 60 &
   echo $!  # 记下 PID
   ```

2. 在"任务监控"页面添加监控：
   - 服务器：选择对应服务器
   - 任务名称：测试任务
   - PID：填入上面的 PID
   - 通知邮箱：填入你的邮箱
   - 超时时间：120 秒

3. 等待任务完成，检查是否收到邮件

## 常见问题

### Q1: 无法连接到服务器？

**检查项：**
- SSH 端口是否正确
- 用户名密码是否正确
- 网络是否连通：`ping <服务器IP>`
- SSH 是否可用：`ssh user@host`

### Q2: GPU 信息显示失败？

**检查项：**
- 服务器是否安装了 `nvidia-smi`
- 在服务器上手动执行：`nvidia-smi`

### Q3: Docker 功能不可用？

**检查项：**
- 服务器是否安装了 Docker
- 当前用户是否有 Docker 权限
- 在服务器上手动执行：`docker ps`

### Q4: 邮件通知不工作？

**检查项：**
- `.env` 文件中的 SMTP 配置是否正确
- Gmail 用户需要使用应用专用密码
- 检查防火墙是否阻止了 SMTP 端口（587）

### Q5: 如何停止服务？

按 `Ctrl + C` 停止服务

## 生产环境部署建议

### 1. 使用反向代理（Nginx）

```nginx
server {
    listen 80;
    server_name gpu-manager.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 2. 使用 Gunicorn（生产级 WSGI 服务器）

```bash
gunicorn --bind 0.0.0.0:5000 --workers 4 run:app
```

### 3. 使用 Docker Compose

```bash
docker-compose up -d
```

### 4. 设置开机自启（systemd）

创建 `/etc/systemd/system/gpu-manager.service`：

```ini
[Unit]
Description=GPU Server Manager
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/home/server/gpu-server-manager
ExecStart=/opt/conda/envs/gpu-server-manager/bin/python run.py
Restart=always

[Install]
WantedBy=multi-user.target
```

启用服务：

```bash
systemctl daemon-reload
systemctl enable gpu-manager
systemctl start gpu-manager
```

## 安全提醒

⚠️ **重要：**
- 修改默认的 `SECRET_KEY`（在 `.env` 文件中）
- 使用 SSH 密钥代替密码
- 限制访问来源（防火墙/安全组）
- 定期备份 `config/servers.yaml` 和 `.env` 文件

## 获取帮助

如有问题，请查看：
- 完整文档：`README.md`
- 日志输出：查看终端输出的错误信息
