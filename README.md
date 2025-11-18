# GPU Server Manager

<div align="center">

**基于 Web 的多服务器 GPU 资源管理平台**

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0+-green.svg)](https://flask.palletsprojects.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

</div>

## 📋 项目简介

GPU Server Manager 是一个轻量级的 Web 管理平台，专为管理多台远程 GPU 服务器而设计。通过 SSH 协议实现无代理远程管理，提供直观的 Web 界面用于监控 GPU 状态、管理用户、操作 Docker 容器等。

### ✨ 核心特性

- 🖥️ **多服务器管理** - 统一管理多台 GPU 服务器，集中监控资源
- 📊 **实时 GPU 监控** - 基于 nvidia-smi 实时显示 GPU 使用情况
- 🔐 **双模式认证** - 管理员/用户双角色，细粒度权限控制
- 🐳 **Docker 集成** - 远程管理 Docker 容器，支持 nvidia-docker
- 👥 **用户管理** - 创建用户、配置工作目录、自动部署容器环境
- 📁 **文件管理** - 只读文件浏览、预览与下载功能
- 🌐 **端口转发** - 支持 TensorBoard、Jupyter、MLflow 等服务访问
- 📧 **邮件通知** - 任务完成自动邮件提醒
- 📦 **一键打包** - 支持 Windows EXE 打包，无需配置 Python 环境

## 🚀 快速开始

### 系统要求

- Python 3.11+
- 远程服务器需安装 nvidia-smi（GPU 监控）
- 远程服务器需安装 Docker（容器管理功能）

### 安装部署

#### 方法一：源码运行

```bash
# 克隆项目
git clone https://github.com/Renzhihan/gpu-server-manager.git
cd gpu-server-manager

# 安装依赖
pip install -r requirements.txt

# 配置服务器信息
cp config/servers.yaml.example config/servers.yaml
# 编辑 servers.yaml 填入实际服务器信息

# 配置环境变量（可选）
cp .env.example .env
# 编辑 .env 配置邮件等功能

# 运行应用
python run.py
```

访问 http://localhost:5000

#### 方法二：Windows EXE（推荐 Windows 用户）

1. 从 [Releases](https://github.com/Renzhihan/gpu-server-manager/releases) 下载最新版本的 Windows 打包文件
2. 解压到任意目录
3. 双击运行 `START_WINDOWS.bat` 启动脚本
   - **首次运行**：会自动创建 `config/servers.yaml` 配置文件模板
   - 按提示编辑 `config\servers.yaml` 填入服务器信息
   - 再次运行脚本即可启动
4. 浏览器访问 http://localhost:5000

**修改配置：** 直接编辑 `config\servers.yaml` 文件（用记事本即可），保存后重启应用生效

## ⚙️ 配置说明

### 服务器配置 (config/servers.yaml)

```yaml
servers:
  - name: "GPU Server 1"
    host: "192.168.1.100"        # 服务器 IP 或域名
    port: 22                      # SSH 端口
    username: "your_username"     # SSH 用户名
    password: "your_password"     # SSH 密码
    # key_file: "/path/to/key"   # 或使用私钥认证
    gpu_enabled: true             # 是否启用 GPU 监控
    description: "RTX 3090"       # 服务器描述
```

**重要提示：**
- 描述中包含 "2080" 的服务器会自动使用 `nvidia-docker` 命令
- 其他服务器使用标准 `docker` 命令

### 环境变量配置 (.env)

```bash
# Flask 配置
FLASK_ENV=development
SECRET_KEY=your-secret-key-change-this
FLASK_PORT=5000

# 邮件配置（可选）
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM=your-email@gmail.com
```

## 🔑 认证说明

系统支持两种登录模式：

### 管理员模式
- **密码：** `admin`
- **权限：** 完整访问权限，包括 Docker 管理和用户管理

### 用户模式
- **密码：** 无需密码，直接选择用户模式登录
- **权限：** 只读访问，可查看 GPU 状态、文件浏览等

## 📚 功能模块

### 1. 仪表板
- 服务器连接状态监控
- 实时 GPU 使用率、显存占用
- 进程列表与资源分配

### 2. Docker 管理（管理员）
- 容器列表查看（运行中/已停止）
- 容器启动/停止/删除
- 容器日志查看
- 一键部署新容器

### 3. 用户管理（管理员）
- 创建系统用户
- 配置工作目录（自动创建并授权）
- 自动部署 Docker 开发环境
- 支持自定义镜像、端口映射、卷挂载
- 用户密码管理

### 4. 文件管理
- 目录浏览（只读）
- 文件预览（前 1000 行）
- 文件下载

### 5. 端口转发
- TensorBoard 可视化
- Jupyter Notebook 远程访问
- MLflow 实验追踪
- 自定义端口映射

### 6. 任务监控
- 定时任务管理
- 任务执行历史
- 邮件通知提醒

## 🛠️ 开发指南

### 项目结构

```
gpu-server-manager/
├── app/
│   ├── routes/          # 路由模块
│   │   ├── main.py      # 主页面路由 + 认证
│   │   └── api.py       # API 接口
│   ├── services/        # 业务逻辑
│   │   ├── ssh_manager.py      # SSH 连接管理
│   │   ├── gpu_monitor.py      # GPU 监控
│   │   ├── docker_manager.py   # Docker 管理
│   │   ├── user_manager.py     # 用户管理
│   │   ├── file_manager.py     # 文件管理
│   │   └── email_service.py    # 邮件服务
│   ├── templates/       # HTML 模板
│   └── static/          # 静态资源
├── config/
│   ├── settings.py      # 配置加载
│   └── servers.yaml     # 服务器配置（需自行创建）
├── run.py               # 启动入口
└── requirements.txt     # Python 依赖

```

### 本地开发

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# 安装开发依赖
pip install -r requirements.txt

# 以调试模式运行
FLASK_ENV=development python run.py
```

### 打包 Windows EXE

项目已配置 GitHub Actions 自动构建，推送 tag 即可自动打包：

```bash
git tag v1.0.0
git push origin v1.0.0
```

也可本地手动打包（需在 Windows 环境）：

```bash
pip install pyinstaller
pyinstaller build_windows.spec
```

## 🔒 安全建议

- ⚠️ **生产环境部署时请务必修改默认管理员密码**（在 `app/routes/main.py:7` 中修改）
- 🔐 建议使用 SSH 密钥认证代替密码
- 🌐 建议配置 HTTPS（可使用 Nginx 反向代理）
- 🛡️ 限制管理平台仅内网访问，或配置防火墙规则
- 📁 妥善保管 `config/servers.yaml`，避免敏感信息泄露

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 提交 Pull Request

## 📄 开源协议

本项目采用 MIT 协议开源 - 详见 [LICENSE](LICENSE) 文件

## 🙏 致谢

- [Flask](https://flask.palletsprojects.com/) - Web 框架
- [Paramiko](https://www.paramiko.org/) - SSH 实现
- [Bootstrap](https://getbootstrap.com/) - UI 框架
- [nvidia-smi](https://developer.nvidia.com/nvidia-system-management-interface) - GPU 监控工具

## 📧 联系方式

如有问题或建议，欢迎提交 [Issue](https://github.com/Renzhihan/gpu-server-manager/issues)

---

<div align="center">
Made with ❤️ by Renzhihan
</div>
