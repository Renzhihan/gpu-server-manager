# 文件管理和用户管理更新说明

## 📋 更新概览

本次更新修复了文件管理的Bug，并进行了重大安全和功能增强：

1. ✅ 修复文件管理显示空文件夹的Bug
2. ✅ 文件管理改为只读模式（仅预览和下载）
3. ✅ 用户管理增强：支持工作目录创建 + Docker容器自动配置

---

## 1. 文件管理Bug修复

### 问题描述
文件管理界面浏览任何目录都显示为空。

### 根本原因
`app/services/file_manager.py` 第34行代码错误：
```python
for line in lines[1:]:  # 跳过第一行
```

这会跳过`ls -lh`输出的第一行，但逻辑处理不当导致所有文件都被跳过。

### 解决方案
修改为：
```python
for line in lines:
    # 跳过空行和"total xxx"行
    if not line.strip() or line.startswith('total '):
        continue
```

**修改文件：** `app/services/file_manager.py:31-52`

---

## 2. 文件管理只读模式

### 安全增强
为防止误操作，文件管理现在为**只读模式**，所有危险操作已移除。

### 功能对比

| 功能 | 更新前 | ✅ 更新后 |
|-----|--------|----------|
| **浏览文件** | ✅ 支持 | ✅ 支持 |
| **下载文件** | ✅ 支持 | ✅ 支持（增强）|
| **预览文件** | ❌ 不支持 | ✅ 新增！|
| **创建文件夹** | ✅ 支持 | ❌ 已移除 |
| **删除文件** | ✅ 支持 | ❌ 已移除 |

### 新增功能：文件预览

**支持预览：**
- 文本文件（.txt, .log, .py, .sh, .yaml等）
- 配置文件
- 脚本文件
- 最多显示前1000行

**使用方式：**
1. 浏览到文件所在目录
2. 点击文件的 **"👁 预览"** 按钮
3. 在弹窗中查看文件内容（前1000行）
4. 可直接点击 **"下载此文件"** 按钮下载

**安全保护：**
- 禁止执行危险命令（rm, mv, cp, sudo等）
- 只读访问，无法修改服务器文件
- 仅支持head命令预览，无法执行任意命令

**修改文件：**
- `app/templates/files.html` - 移除创建/删除按钮，添加预览功能
- `app/routes/api.py` - 新增 `/api/servers/<server>/execute` 端点（带安全限制）

---

## 3. 用户管理增强版

### 功能概览

创建用户时，现在可以一键完成：
1. ✅ 创建系统用户账号
2. ✅ 创建并配置工作目录
3. ✅ 自动创建Docker容器（支持2080ti/3090服务器自适应）

### 界面改进

**新增配置选项：**

#### 📁 工作目录配置
```
☑ 创建工作目录
  └─ 工作目录路径: /data/users/user001
     → 自动创建目录
     → 自动设置权限（chown + chmod 755）
```

#### 🐳 Docker容器配置
```
☑ 创建Docker容器
  ├─ Docker镜像:      pytorch/pytorch:latest
  ├─ 容器名称:        user001 (自动填充)
  ├─ SSH端口映射:     9910 → 容器:22
  ├─ 卷映射:          /:/home
  └─ 命令预览:        实时显示即将执行的docker命令
```

### 智能特性

#### 1️⃣ 自动路径填充
勾选"创建工作目录"后，自动建议路径：
```
用户名: user001
  → 自动填充: /data/users/user001
```

#### 2️⃣ Docker命令实时预览
输入配置时，实时显示将要执行的命令：
```
docker run -it -d \
  -p 9910:22 \
  -v /:/home \
  --gpus all \
  --ipc=host \
  --pid=host \
  --name=user001 \
  pytorch/pytorch:latest
```

#### 3️⃣ 服务器类型自适应
**自动检测服务器类型：**
- **2080ti服务器** → 使用 `nvidia-docker run`
- **其他服务器**   → 使用 `docker run`

**检测逻辑：**
```javascript
// 根据服务器名称或描述判断
if (serverName.includes('2080')) {
    command = 'nvidia-docker run ...';
} else {
    command = 'docker run ...';
}
```

#### 4️⃣ 常用镜像快捷按钮
点击徽章快速填充：
- 🔵 **PyTorch** → `pytorch/pytorch:latest`
- 🟢 **TensorFlow** → `tensorflow/tensorflow:latest-gpu`

### 使用场景

#### 场景A：创建用户 + 工作目录
```
1. 填写用户名: user001, 密码: ******
2. ☑ 创建工作目录
   路径: /data/users/user001
3. 点击"创建用户"

结果：
✅ 系统用户创建成功
✅ 工作目录创建成功: /data/users/user001
```

#### 场景B：创建用户 + Docker容器
```
1. 填写用户名: user002, 密码: ******
2. ☑ 创建Docker容器
   镜像: pytorch/pytorch:latest
   SSH端口: 9910
   卷映射: /:/home
3. 点击"创建用户"

结果：
✅ 系统用户创建成功
✅ Docker容器创建成功
   容器名: user002
   SSH端口: 9910
   镜像: pytorch/pytorch:latest
   命令类型: docker (或nvidia-docker)
```

#### 场景C：完整配置（用户 + 目录 + 容器）
```
1. 用户名: user003, 密码: ******
2. ☑ 创建工作目录: /data/users/user003
3. ☑ 创建Docker容器
   镜像: tensorflow/tensorflow:latest-gpu
   容器名: tf-user003
   SSH端口: 9911
   卷映射: /data:/workspace

结果：
✅ 系统用户创建成功
✅ 工作目录创建成功: /data/users/user003
✅ Docker容器创建成功
   容器名: tf-user003
   SSH端口: 9911
   镜像: tensorflow/tensorflow:latest-gpu
   命令类型: docker
```

### Docker命令详解

**标准命令格式：**
```bash
docker run -it -d \
  -p <主机端口>:22 \            # SSH端口映射
  -v <主机路径>:<容器路径> \    # 卷映射
  --gpus all \                  # 启用所有GPU
  --ipc=host \                  # 共享IPC命名空间
  --pid=host \                  # 共享PID命名空间
  --name=<容器名> \             # 容器名称
  <镜像名>                      # Docker镜像
```

**参数说明：**

| 参数 | 说明 | 默认值 | 示例 |
|-----|------|--------|------|
| `-p` | 端口映射 | 9910:22 | 主机9910端口映射到容器22端口 |
| `-v` | 卷映射 | /:/home | 主机根目录映射到容器/home |
| `--gpus` | GPU访问 | all | 容器可访问所有GPU |
| `--ipc=host` | IPC模式 | host | 与主机共享IPC |
| `--pid=host` | PID模式 | host | 与主机共享PID |
| `--name` | 容器名 | 用户名 | 容器标识符 |

### 技术实现

**后端API：** `POST /api/users/<server>/create-advanced`

**请求格式：**
```json
{
  "username": "user001",
  "password": "pass123",
  "work_dir": "/data/users/user001",
  "docker_config": {
    "image": "pytorch/pytorch:latest",
    "container_name": "user001",
    "ssh_port": 9910,
    "volume_mapping": "/:/home"
  }
}
```

**响应格式：**
```json
{
  "success": true,
  "message": "用户 user001 创建成功",
  "details": "✅ 系统用户创建成功\n✅ 工作目录创建成功: /data/users/user001\n✅ Docker容器创建成功\n   容器名: user001\n   SSH端口: 9910\n   镜像: pytorch/pytorch:latest\n   命令类型: docker"
}
```

**执行流程：**
1. 创建系统用户（调用 `user_manager.create_user()`）
2. 如果配置了工作目录，执行：
   ```bash
   mkdir -p '/data/users/user001' && \
   chown user001:user001 '/data/users/user001' && \
   chmod 755 '/data/users/user001'
   ```
3. 如果配置了Docker容器：
   - 检测服务器类型（description中是否包含'2080'）
   - 选择命令类型（nvidia-docker 或 docker）
   - 执行docker run命令
4. 返回详细结果

**修改文件：**
- `app/templates/users.html` - 完全重写用户创建界面
- `app/routes/api.py:321-383` - 新增 `create_user_advanced` 端点

---

## 📊 功能对比总结

### 文件管理

| 功能 | 更新前 | ✅ 更新后 |
|-----|--------|----------|
| 显示文件 | ❌ Bug（显示空） | ✅ 修复 |
| 浏览目录 | ✅ 支持 | ✅ 支持（增强）|
| 下载文件 | ✅ 支持 | ✅ 支持 |
| **预览文件** | ❌ 不支持 | ✅ **新增！** |
| 创建文件夹 | ✅ 支持 | ❌ 移除（安全）|
| 删除文件 | ✅ 支持 | ❌ 移除（安全）|
| 面包屑导航 | ✅ 支持 | ✅ 保持 |
| 路径记忆 | ✅ 支持 | ✅ 保持 |

### 用户管理

| 功能 | 更新前 | ✅ 更新后 |
|-----|--------|----------|
| 创建用户 | ✅ 基础功能 | ✅ 保持 |
| **创建工作目录** | ❌ 不支持 | ✅ **新增！** |
| **Docker容器** | ❌ 不支持 | ✅ **新增！** |
| **镜像选择** | ❌ 不支持 | ✅ **新增！** |
| **端口映射** | ❌ 不支持 | ✅ **新增！** |
| **卷映射** | ❌ 不支持 | ✅ **新增！** |
| **命令预览** | ❌ 不支持 | ✅ **新增！** |
| **2080ti适配** | ❌ 不支持 | ✅ **新增！** |

---

## 🎯 使用建议

### 文件管理
- ✅ 使用预览功能快速查看日志文件
- ✅ 下载重要文件到本地备份
- ⚠️ 需要修改文件请SSH登录服务器操作

### 用户管理
- ✅ 新用户建议同时创建工作目录和Docker容器
- ✅ 2080ti服务器自动使用nvidia-docker
- ✅ 端口号建议递增（9910, 9911, 9912...）
- ✅ 使用命令预览确认配置正确
- ⚠️ 容器名和端口号不能重复

---

## 🔧 修改的文件清单

### 文件管理
1. `app/services/file_manager.py` - 修复Bug（34-52行）
2. `app/templates/files.html` - 移除危险操作，添加预览
3. `app/routes/api.py` - 新增 `/api/servers/<server>/execute` 端点

### 用户管理
1. `app/templates/users.html` - 完全重写创建用户界面
2. `app/routes/api.py` - 新增 `/api/users/<server>/create-advanced` 端点

---

## 🚀 现在可以测试

```bash
cd /home/server/gpu-server-manager
python run.py
```

**访问：** http://localhost:5000

**测试清单：**
- [ ] 文件管理：浏览目录是否正常显示文件
- [ ] 文件预览：点击"预览"按钮查看文本文件
- [ ] 文件下载：下载文件是否正常
- [ ] 用户创建：基础创建（仅用户名+密码）
- [ ] 用户创建：创建工作目录
- [ ] 用户创建：创建Docker容器
- [ ] 用户创建：完整配置（用户+目录+容器）
- [ ] 2080ti服务器：确认使用nvidia-docker
- [ ] 其他服务器：确认使用docker

---

## 📝 注意事项

### 文件预览
- 仅支持文本文件预览
- 最多显示前1000行
- 二进制文件会显示乱码（请直接下载）

### Docker容器
- 容器名必须唯一
- SSH端口号不能重复
- 镜像需要在服务器上已下载或可拉取
- 首次拉取大镜像可能需要较长时间

### 权限
- 工作目录默认权限：755
- 工作目录所有者：创建的用户
- Docker容器以root身份运行

---

所有功能已就绪！🎉
