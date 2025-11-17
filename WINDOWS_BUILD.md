# Windows EXE 打包指南

## 📦 打包说明

本系统支持打包为Windows可执行文件（.exe），让用户无需配置Python环境即可一键运行。

---

## 🛠️ 打包步骤（开发者）

### 1. 安装打包工具

在**开发环境**（可以是Linux或Windows）安装PyInstaller：

```bash
pip install pyinstaller
```

### 2. 安装项目依赖

确保所有依赖已安装：

```bash
pip install -r requirements.txt
```

### 3. 执行打包

#### 方式一：使用spec文件（推荐）

```bash
pyinstaller build_windows.spec
```

#### 方式二：命令行打包

```bash
pyinstaller --name=GPU-Server-Manager \
  --add-data="app/templates:app/templates" \
  --add-data="app/static:app/static" \
  --add-data="config:config" \
  --hidden-import=flask \
  --hidden-import=paramiko \
  --hidden-import=yaml \
  --console \
  run.py
```

### 4. 打包输出

打包完成后，在 `dist/GPU-Server-Manager/` 目录下会生成：

```
dist/GPU-Server-Manager/
├── GPU-Server-Manager.exe  # 主程序
├── app/                     # 模板和静态文件
│   ├── templates/
│   └── static/
├── config/                  # 配置文件夹
├── _internal/              # Python运行时和依赖库
└── ... 其他文件
```

---

## 📁 发布包准备

### 创建发布包目录结构

```
GPU-Server-Manager-Windows/
├── GPU-Server-Manager.exe      # 主程序（从dist复制）
├── START_WINDOWS.bat            # 启动脚本
├── README.md                    # 使用说明
├── WINDOWS_USER_GUIDE.md        # Windows用户指南
├── app/                         # 应用文件（从dist复制）
├── config/                      # 配置目录
│   └── servers.yaml.example     # 配置示例
├── .env.example                 # 环境变量示例
└── _internal/                   # 运行时（从dist复制）
```

### 打包为压缩包

```bash
# 压缩整个目录
zip -r GPU-Server-Manager-Windows-v1.0.zip GPU-Server-Manager-Windows/
```

---

## 🚀 用户使用指南（Windows）

### 系统要求

- Windows 10 或更高版本
- 64位操作系统
- 无需安装Python（已打包）
- 网络连接（访问远程服务器）

### 使用步骤

#### 1. 解压软件包

将 `GPU-Server-Manager-Windows-v1.0.zip` 解压到任意目录，例如：
```
C:\GPU-Server-Manager\
```

#### 2. 配置服务器信息

编辑 `config\servers.yaml` 文件：

```yaml
servers:
  - name: "GPU Server 1"
    host: "202.117.43.222"
    port: 2233
    username: "lthpc"
    password: "Lthpc2019serc"
    gpu_enabled: true
    description: "2080ti"
```

#### 3. 启动程序

双击运行 `START_WINDOWS.bat`

或者直接双击 `GPU-Server-Manager.exe`

#### 4. 访问Web界面

程序启动后，会显示：
```
╔══════════════════════════════════════════════════════════════╗
║          GPU 服务器管理系统 - 启动成功                        ║
╠══════════════════════════════════════════════════════════════╣
║  访问地址: http://0.0.0.0:5000                             ║
║  运行模式: 开发模式                                          ║
║  安全传输: HTTP                                              ║
║  配置文件: config/servers.yaml                              ║
╚══════════════════════════════════════════════════════════════╝
```

打开浏览器访问：**http://localhost:5000**

#### 5. 登录系统

**管理员模式：**
- 选择"管理员模式"
- 输入密码：`GPU-admin@renzhihan-2025`
- 拥有完全控制权限

**用户模式：**
- 选择"用户模式"
- 无需密码
- 仅能查看和监控，无法管理

#### 6. 停止程序

在控制台窗口按 `Ctrl+C` 或直接关闭窗口。

---

## 🔧 配置说明

### 服务器配置

编辑 `config\servers.yaml`：

```yaml
servers:
  - name: "服务器名称"
    host: "IP地址或域名"
    port: SSH端口
    username: "SSH用户名"
    password: "SSH密码"
    gpu_enabled: true/false
    description: "服务器描述"
```

### 邮件配置（可选）

如需邮件通知功能，编辑 `.env` 文件：

```ini
# SMTP 邮件配置
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=your-email@gmail.com
```

### HTTPS配置（可选）

如需HTTPS：

1. 在程序目录下运行（需要安装OpenSSL）：
```bash
mkdir ssl
openssl req -x509 -newkey rsa:4096 -nodes -out ssl/cert.pem -keyout ssl/key.pem -days 365
```

2. 启动时添加 `--https` 参数：
```bash
GPU-Server-Manager.exe --https
```

---

## ⚠️ 常见问题

### Q1: 双击exe无反应？
**A:**
- 检查是否被杀毒软件拦截，添加到白名单
- 以管理员身份运行
- 查看日志文件（如果有）

### Q2: 提示端口5000被占用？
**A:** 使用其他端口：
```bash
GPU-Server-Manager.exe --port 8080
```

### Q3: 无法连接服务器？
**A:**
- 检查 `config\servers.yaml` 配置是否正确
- 确认服务器SSH端口可访问
- 检查防火墙设置

### Q4: 浏览器无法打开？
**A:**
- 确认程序已启动（控制台有输出）
- 尝试不同浏览器
- 清除浏览器缓存

### Q5: 文件管理显示空？
**A:**
- 已修复此Bug
- 确保使用最新版本

### Q6: 忘记管理员密码？
**A:**
- 默认密码：`GPU-admin@renzhihan-2025`
- 如需修改，联系开发者重新打包

---

## 📋 命令行参数

```bash
GPU-Server-Manager.exe [选项]

选项:
  --https         启用HTTPS（需要SSL证书）
  --host HOST     监听地址（默认: 0.0.0.0）
  --port PORT     监听端口（默认: 5000）
  --debug         启用调试模式
```

**示例：**
```bash
# HTTPS + 自定义端口
GPU-Server-Manager.exe --https --port 8443

# 仅本地访问
GPU-Server-Manager.exe --host 127.0.0.1
```

---

## 🔐 权限说明

### 管理员权限
- ✅ 查看所有信息
- ✅ 服务器管理
- ✅ GPU监控
- ✅ **Docker管理**（仅管理员）
- ✅ **用户管理**（仅管理员）
- ✅ 文件浏览和下载
- ✅ 任务监控
- ✅ 端口转发

### 用户权限
- ✅ 查看所有信息
- ✅ 服务器管理
- ✅ GPU监控
- ❌ Docker管理（禁止）
- ❌ 用户管理（禁止）
- ✅ 文件浏览和下载
- ✅ 任务监控
- ✅ 端口转发

---

## 🎯 打包优化建议

### 减小体积

1. **使用UPX压缩：**
```bash
pyinstaller --upx-dir=/path/to/upx build_windows.spec
```

2. **排除不必要的模块：**
在spec文件的`excludes`中添加：
```python
excludes=['tkinter', 'matplotlib', 'PIL', 'pytest']
```

### 性能优化

1. **使用单文件模式（可选）：**
修改spec文件：
```python
exe = EXE(
    ...
    onefile=True,  # 打包为单个exe文件
    ...
)
```

⚠️ **注意：** 单文件模式启动较慢，且可能被杀毒软件误报。

---

## 📦 发布清单

发布前确认：

- [ ] 测试所有核心功能
- [ ] 验证管理员/用户模式
- [ ] 检查配置文件示例
- [ ] 包含使用说明文档
- [ ] 测试不同Windows版本
- [ ] 杀毒软件白名单测试
- [ ] 更新版本号

---

## 🐛 调试

### 开发者调试模式

```bash
# 保留控制台输出
GPU-Server-Manager.exe --debug

# 查看详细日志
```

### 日志位置

日志文件：`logs/app.log`（如果配置了）

---

## 📞 技术支持

如遇问题：
1. 查看完整文档：`README.md`
2. 查看用户指南：`WINDOWS_USER_GUIDE.md`
3. 联系开发者或提交Issue

---

## 🆕 版本历史

### v1.0 (2025-01-XX)
- ✅ 首个Windows打包版本
- ✅ 用户/管理员双模式
- ✅ Docker和用户管理权限控制
- ✅ 文件管理只读模式
- ✅ 端口转发功能
- ✅ HTTPS支持

---

## 🎓 开发者注意事项

### 跨平台打包

- **Linux打包Windows exe：** 可能遇到兼容性问题
- **建议：** 在Windows环境打包Windows版本
- **虚拟机：** 可使用Windows虚拟机进行打包

### 依赖管理

确保 `requirements.txt` 包含所有依赖：
```
Flask==3.0.0
Flask-CORS==4.0.0
paramiko==3.4.0
PyYAML==6.0.1
APScheduler==3.10.4
psutil==5.9.6
python-dotenv==1.0.0
```

### 测试建议

打包后完整测试：
1. 清洁Windows环境测试（无Python）
2. 不同用户权限测试
3. 不同网络环境测试
4. 长时间运行稳定性测试

---

完成！Windows用户现在可以无需Python环境直接运行系统了。🎉
