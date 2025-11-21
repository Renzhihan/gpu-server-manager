# 🖥️ GPU Server Manager

<div align="center">

**企业级 GPU 集群管理平台 | 轻量 · 高效 · 易用**

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0+-000000?style=flat&logo=flask&logoColor=white)](https://flask.palletsprojects.com)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat)](LICENSE)
[![GitHub Release](https://img.shields.io/github/v/release/Renzhihan/gpu-server-manager?style=flat)](https://github.com/Renzhihan/gpu-server-manager/releases)

[功能特性](#-功能特性) · [快速开始](#-快速开始) · [使用文档](#-使用文档) · [配置说明](#️-配置说明)

</div>

---

## 📋 项目简介

GPU Server Manager 是一个基于 Web 的 GPU 集群管理平台，专为深度学习研究团队和 AI 实验室设计。通过简洁的 Web 界面，实现多台 GPU 服务器的统一管理、资源监控和任务调度。

**核心优势：**
- 🚀 **零部署成本** - 无需在远程服务器安装任何Agent，仅通过SSH协议即可管理
- 📊 **实时监控** - GPU利用率、显存占用、进程管理一目了然
- 🔐 **权限分级** - 管理员/用户双角色，适配不同使用场景
- 💻 **开箱即用** - Windows可执行文件一键启动，Linux源码运行极简配置

---

## ✨ 功能特性

### 🎯 核心功能

| 功能模块 | 功能描述 | 适用场景 |
|---------|---------|---------|
| **GPU 实时监控** | 多服务器GPU状态集中展示，显存/利用率/温度实时更新 | 资源利用率监控 |
| **进程管理** | 查看GPU进程详情，支持一键终止异常进程 | 资源抢占管理 |
| **任务监控** | 进程完成自动通知，GPU空闲邮件提醒 | 长时训练任务监控 |
| **端口转发** | 内网服务一键映射，支持TensorBoard/Jupyter | 远程实验管理 |
| **Web终端** | 浏览器直接SSH访问，无需本地客户端 | 快速命令行操作 |

### 🛠️ 管理功能（管理员）

| 功能 | 说明 |
|------|------|
| **Docker管理** | 容器启停/日志查看/镜像拉取，支持nvidia-docker |
| **用户管理** | 批量创建用户，自动配置环境，一键部署开发容器 |
| **文件浏览** | 只读文件系统访问，支持预览和下载 |
| **服务器配置** | Web界面动态添加/编辑服务器，无需重启 |
| **邮件通知** | SMTP配置可视化，支持QQ/163/Gmail等主流邮箱 |

---

## 🚀 快速开始

### 系统要求

| 组件 | 要求 | 说明 |
|------|------|------|
| **控制端** | Python 3.11+ 或 Windows 10+ | 运行管理平台的设备 |
| **远程服务器** | nvidia-smi | GPU监控功能依赖 |
| **可选依赖** | Docker | 容器管理功能需要 |

### 🪟 Windows 用户（推荐）

**一键启动，无需配置Python环境：**

1. 下载最新版本
   ```
   访问：https://github.com/Renzhihan/gpu-server-manager/releases
   下载：GPU-Server-Manager-Windows.zip
   ```

2. 解压并启动
   ```
   1. 解压到任意目录
   2. 双击运行 START_WINDOWS.bat
   3. 首次运行会自动创建配置文件模板
   4. 编辑 config\servers.yaml 填入服务器信息
   5. 再次运行启动脚本
   ```

3. 访问管理界面
   ```
   浏览器打开：http://localhost:5000
   管理员密码：admin
   ```

### 🐧 Linux/Mac 用户

**源码运行，灵活定制：**

```bash
# 1. 克隆项目
git clone https://github.com/Renzhihan/gpu-server-manager.git
cd gpu-server-manager

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置服务器
cp config/servers.yaml.example config/servers.yaml
vim config/servers.yaml  # 填入实际服务器信息

# 4. 启动服务
python run.py

# 5. 访问界面
# 浏览器打开：http://localhost:5000
```

---

## 📖 使用文档

### 登录认证

系统提供两种登录模式：

| 模式 | 密码 | 权限范围 |
|------|------|---------|
| **管理员模式** | `admin` | 完整权限：GPU监控、Docker管理、用户管理、文件操作 |
| **用户模式** | 无需密码 | 只读权限：GPU监控、文件浏览 |

> ⚠️ **安全提示**：生产环境请修改默认密码（文件：`app/routes/main.py` 第7行）

### 主要操作流程

#### 1️⃣ 添加GPU服务器

**方式一：Web界面添加（推荐）**
```
仪表板 → 服务器管理 → 添加服务器 → 填写配置 → 测试连接 → 保存
```

**方式二：编辑配置文件**
```yaml
# config/servers.yaml
servers:
  - name: "实验室服务器A"
    host: "192.168.1.100"
    port: 22
    username: "admin"
    password: "your_password"
    # 或使用SSH密钥
    # key_file: "/path/to/private_key"
    gpu_enabled: true
    description: "RTX 4090 x8"
```

#### 2️⃣ 监控GPU资源

```
GPU监控 → 选择服务器 → 查看实时状态
- 显存占用柱状图
- GPU利用率实时曲线
- 运行进程详细列表
- 空闲/使用中/高负载统计
```

#### 3️⃣ 创建任务监控

```
任务监控 → 新建监控任务 → 选择类型

进程监控：监控指定PID，任务结束时邮件通知
GPU空闲监听：监听GPU卡，空闲时邮件提醒
```

**邮件配置（首次使用）：**
```
任务监控 → 配置邮件 → 选择邮箱服务商
支持：QQ邮箱、163邮箱、Gmail、Outlook
一键应用配置模板，填入授权码即可
```

#### 4️⃣ 端口转发

```
端口转发 → 创建转发 → 选择工具类型

内置模板：
- TensorBoard (端口6006)
- Jupyter Notebook (端口8888)
- MLflow (端口5000)
- 自定义端口
```

---

## ⚙️ 配置说明

### 服务器配置文件

**配置文件位置：** `config/servers.yaml`

**完整配置示例：**
```yaml
servers:
  # 服务器1：使用密码认证
  - name: "GPU-Server-01"
    host: "192.168.1.100"
    port: 22
    username: "root"
    password: "your_secure_password"
    gpu_enabled: true
    description: "RTX 3090 x4"

  # 服务器2：使用SSH密钥认证
  - name: "GPU-Server-02"
    host: "192.168.1.101"
    port: 22
    username: "admin"
    key_file: "/home/user/.ssh/id_rsa"
    gpu_enabled: true
    description: "A100 x2"

  # 服务器3：2080Ti服务器（自动使用nvidia-docker）
  - name: "Legacy-Server"
    host: "192.168.1.102"
    port: 22
    username: "user"
    password: "password"
    gpu_enabled: true
    description: "2080Ti x8"  # 包含"2080"会自动切换nvidia-docker
```

**参数说明：**

| 参数 | 必填 | 说明 | 示例 |
|------|------|------|------|
| `name` | ✅ | 服务器名称（唯一标识） | "实验室服务器A" |
| `host` | ✅ | IP地址或域名 | "192.168.1.100" |
| `port` | ✅ | SSH端口 | 22 |
| `username` | ✅ | SSH用户名 | "root" |
| `password` | ⚠️ | SSH密码（与key_file二选一） | "your_password" |
| `key_file` | ⚠️ | SSH私钥路径（与password二选一） | "/path/to/key" |
| `gpu_enabled` | ❌ | 是否启用GPU监控 | true（默认） |
| `description` | ❌ | 服务器描述 | "RTX 3090 x4" |

> 💡 **提示**：description包含"2080"的服务器会自动使用`nvidia-docker`命令，其他使用`docker`

### 环境变量配置（可选）

**配置文件：** `.env`

```bash
# Flask基础配置
FLASK_ENV=production          # 生产环境设置为production
SECRET_KEY=change-this-key    # ⚠️ 务必修改为随机字符串
FLASK_PORT=5000              # Web服务端口

# SMTP邮件配置（也可在Web界面配置）
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your@gmail.com
SMTP_PASSWORD=your_app_password
SMTP_FROM=your@gmail.com
SMTP_USE_TLS=True
```

---

## 🛡️ 安全建议

### 生产环境部署检查清单

- [ ] **修改默认密码** - 修改 `app/routes/main.py` 中的管理员密码
- [ ] **配置SECRET_KEY** - 在 `.env` 中设置强随机SECRET_KEY
- [ ] **使用SSH密钥** - 优先使用密钥认证而非密码
- [ ] **配置HTTPS** - 使用Nginx反向代理并配置SSL证书
- [ ] **限制访问** - 仅允许内网IP访问或配置VPN
- [ ] **定期备份** - 备份 `config/servers.yaml` 配置文件
- [ ] **日志审计** - 定期检查系统日志和操作记录

### 网络安全建议

**推荐部署架构：**
```
用户 → VPN/内网 → Nginx(HTTPS) → GPU Manager(localhost:5000) → SSH → GPU服务器
```

**Nginx反向代理示例：**
```nginx
server {
    listen 443 ssl;
    server_name gpu-manager.yourdomain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## 🛠️ 高级功能

### GPU负载测试工具

项目内置GPU负载测试脚本，用于测试任务监控功能：

```bash
# 占满GPU 0，使用90%显存，运行300秒
python test_gpu_load.py -g 0 -m 0.9 -d 300

# 同时占满多个GPU
python test_gpu_load.py -g 0,1,2 -m 0.85 -d 600

# 查看帮助
python test_gpu_load.py -h
```

**详细文档：** 参见 `GPU_TEST_GUIDE.md`

### 自动化部署

**使用systemd管理服务（Linux）：**

```bash
# 创建服务文件
sudo vim /etc/systemd/system/gpu-manager.service
```

```ini
[Unit]
Description=GPU Server Manager
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/gpu-server-manager
ExecStart=/usr/bin/python3 /path/to/gpu-server-manager/run.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# 启用并启动服务
sudo systemctl enable gpu-manager
sudo systemctl start gpu-manager

# 查看状态
sudo systemctl status gpu-manager
```

---

## 📊 项目结构

```
gpu-server-manager/
├── app/
│   ├── routes/                  # 路由层
│   │   ├── main.py             # 页面路由 + 认证
│   │   └── api.py              # REST API接口
│   ├── services/                # 业务逻辑层
│   │   ├── ssh_manager.py      # SSH连接池管理
│   │   ├── gpu_monitor.py      # GPU状态监控
│   │   ├── docker_manager.py   # Docker容器管理
│   │   ├── user_manager.py     # Linux用户管理
│   │   ├── file_manager.py     # 文件系统操作
│   │   ├── email_service.py    # 邮件通知服务
│   │   ├── task_monitor.py     # 任务监控调度
│   │   └── port_forward.py     # SSH端口转发
│   ├── templates/               # Jinja2模板
│   └── static/                  # 静态资源
├── config/
│   ├── settings.py             # 配置加载
│   └── servers.yaml            # 服务器配置（需创建）
├── data/                        # 运行时数据（自动创建）
│   ├── smtp_config.json        # SMTP配置
│   └── user_prefs.json         # 用户偏好设置
├── test_gpu_load.py            # GPU负载测试工具
├── run.py                       # 应用入口
├── requirements.txt             # Python依赖
└── build_windows.spec          # PyInstaller配置
```

---

## 🔧 开发指南

### 本地开发环境

```bash
# 1. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# 2. 安装依赖
pip install -r requirements.txt

# 3. 开发模式运行（自动重载）
FLASK_ENV=development python run.py
```

### 添加新功能

**创建新路由：**
```python
# app/routes/api.py
@bp.route('/your-endpoint', methods=['POST'])
def your_function():
    # 业务逻辑
    return jsonify({'success': True})
```

**创建新服务：**
```python
# app/services/your_service.py
class YourService:
    def your_method(self):
        # 实现逻辑
        pass
```

### 构建Windows EXE

**自动构建（推荐）：**
```bash
# 推送到main分支自动构建开发版
git push origin main

# 或创建tag构建正式版
git tag v1.0.9
git push origin v1.0.9
```

**本地构建：**
```bash
pip install pyinstaller
pyinstaller build_windows.spec
# 产物位于 dist/GPU-Server-Manager/
```

---

## 📄 开源协议

本项目采用 [MIT License](LICENSE) 开源协议。

**这意味着您可以：**
- ✅ 商业使用
- ✅ 修改代码
- ✅ 分发副本
- ✅ 私有使用

**条件：**
- 📋 保留原作者版权声明

---

## 📮 问题反馈

遇到问题或有功能建议？欢迎提交Issue！

**提交Issue前请：**
1. 搜索已有Issue，避免重复
2. 提供详细的错误信息和日志
3. 说明操作系统和Python版本
4. 附上配置文件（隐藏敏感信息）

**Issue模板：**
```
**问题描述**
简要描述遇到的问题

**复现步骤**
1. 进入xxx页面
2. 点击xxx按钮
3. 出现xxx错误

**环境信息**
- 操作系统：Windows 11 / Ubuntu 22.04
- Python版本：3.11.5
- 浏览器：Chrome 120

**错误日志**
（粘贴完整错误信息）
```

**联系方式：**
- 🐛 [提交Bug](https://github.com/Renzhihan/gpu-server-manager/issues/new)
- 💡 [功能建议](https://github.com/Renzhihan/gpu-server-manager/issues/new)
- 📧 邮件：通过GitHub联系

---

<div align="center">

**⭐ 如果这个项目对您有帮助，请给个Star支持一下！ ⭐**

</div>
