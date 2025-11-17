# HTTPS 和端口转发功能说明

## 🔐 功能一：HTTPS 安全传输

### 简介
启用 HTTPS 后，所有数据通过加密通道传输，确保管理员密码、服务器密码等敏感信息安全。

### 快速开始

#### 1. 生成SSL证书
```bash
cd /home/server/gpu-server-manager
./generate_ssl_cert.sh
```

**执行结果：**
```
正在生成 SSL 自签名证书...
✅ SSL 证书生成成功！

证书位置：
  证书: ./ssl/cert.pem
  密钥: ./ssl/key.pem

⚠️  注意事项：
  1. 这是自签名证书，浏览器会显示安全警告
  2. 点击「高级」→「继续访问」即可
  3. 生产环境建议使用 Let's Encrypt 正式证书
```

#### 2. 启动HTTPS服务

**方式一：使用start.sh脚本**
```bash
./start.sh --https
```

**方式二：直接使用Python**
```bash
python run.py --https
```

#### 3. 访问系统
```
HTTPS: https://localhost:5000
或
HTTPS: https://<服务器IP>:5000
```

### 浏览器警告处理

**首次访问会看到安全警告（自签名证书）：**

**Chrome浏览器：**
1. 显示"您的连接不是私密连接"
2. 点击 **"高级"**
3. 点击 **"继续访问localhost（不安全）"**

**Firefox浏览器：**
1. 显示"警告：潜在的安全风险"
2. 点击 **"高级"**
3. 点击 **"接受风险并继续"**

### 命令行参数

```bash
python run.py --help

可选参数:
  --https              启用 HTTPS (需要先生成证书)
  --host HOST          监听地址 (默认: 0.0.0.0)
  --port PORT          监听端口 (默认: 5000)
  --debug              启用调试模式
```

**示例：**
```bash
# HTTPS + 自定义端口
python run.py --https --port 8443

# HTTPS + 仅本地访问
python run.py --https --host 127.0.0.1
```

### 生产环境使用Let's Encrypt

**对于有公网域名的服务器：**

```bash
# 1. 安装 certbot
sudo apt install certbot

# 2. 获取证书（需要域名指向服务器）
sudo certbot certonly --standalone -d yourdomain.com

# 3. 证书路径
# 证书: /etc/letsencrypt/live/yourdomain.com/fullchain.pem
# 密钥: /etc/letsencrypt/live/yourdomain.com/privkey.pem

# 4. 复制证书到项目
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem ssl/cert.pem
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem ssl/key.pem
sudo chmod 644 ssl/*.pem

# 5. 启动HTTPS
python run.py --https
```

---

## 🔀 功能二：端口转发管理

### 简介
通过SSH隧道将远程服务器上的端口映射到本地，方便访问：
- **TensorBoard** - TensorFlow可视化
- **MLflow** - 机器学习实验追踪
- **Jupyter Notebook** - 交互式开发环境
- **Weights & Biases** - W&B本地服务
- **Visdom** - PyTorch可视化

### 使用场景

#### 场景1：查看远程TensorBoard
```
服务器上运行：
$ tensorboard --logdir=./logs --port=6006

本地访问：
1. 进入"端口转发"页面
2. 点击"TensorBoard"卡片
3. 选择服务器
4. 自动填充端口 6006
5. 点击"创建转发"
6. 点击"打开"按钮 → 在浏览器中查看TensorBoard
```

#### 场景2：访问远程Jupyter
```
服务器上运行：
$ jupyter notebook --no-browser --port=8888

本地访问：
1. 创建端口转发（Jupyter, 8888）
2. 访问 http://localhost:16007（自动分配的本地端口）
3. 输入token即可使用
```

#### 场景3：查看MLflow实验
```
服务器上运行：
$ mlflow ui --port=5000

本地访问：
1. 创建端口转发（MLflow, 5000）
2. 在本地浏览器访问追踪结果
```

### 功能特性

#### ✅ 快捷工具模板
点击常用工具卡片，自动填充配置：
- **TensorBoard**: 6006
- **MLflow**: 5000
- **Jupyter**: 8888
- **W&B**: 8080
- **Visdom**: 8097

#### ✅ 自动端口分配
- 本地端口留空 → 系统自动分配（16006起）
- 避免端口冲突

#### ✅ 状态监控
- ✅ **运行中** - 绿色，可打开
- ⚠️ **启动中** - 黄色
- ❌ **错误** - 红色，显示错误信息
- ⏹️ **已停止** - 灰色

#### ✅ 快速访问
转发运行后，点击 **"打开"** 按钮直接跳转到本地端口

### 操作步骤

#### 1. 创建端口转发

**方式一：使用快捷模板**
```
1. 点击"新建端口转发"
2. 点击想要的工具卡片（如TensorBoard）
3. 选择服务器
4. 点击"创建转发"
```

**方式二：自定义配置**
```
1. 点击"新建端口转发"
2. 填写：
   - 服务器: GPU Server 1
   - 名称: 我的训练可视化
   - 远程端口: 6006
   - 本地端口: 留空（自动分配）
3. 点击"创建转发"
```

#### 2. 访问转发服务

**转发创建成功后：**
```
状态显示为"运行中"
点击"打开"按钮 → 自动在新标签页打开
或手动访问: http://localhost:<显示的本地端口>
```

#### 3. 停止转发

```
点击"停止"按钮
状态变为"已停止"
```

#### 4. 删除转发

```
点击垃圾桶图标
确认删除
```

### 技术原理

**SSH本地端口转发：**
```bash
ssh -N -L <本地端口>:localhost:<远程端口> user@server
```

**示例：**
```bash
# 将远程6006端口映射到本地16006
ssh -N -L 16006:localhost:6006 lthpc@202.117.43.222 -p 2233
```

**后台自动执行：**
- 系统自动管理SSH隧道进程
- 连接断开自动标记错误
- 支持多个同时转发

### 依赖检查

**系统需要安装sshpass（用于密码认证）：**

```bash
# Ubuntu/Debian
sudo apt install sshpass

# CentOS/RHEL
sudo yum install sshpass

# 验证安装
which sshpass
```

**如果不想使用密码，可以配置SSH密钥：**
```bash
# 生成密钥
ssh-keygen -t rsa

# 复制公钥到服务器
ssh-copy-id -p 2233 lthpc@202.117.43.222
```

### 常见问题

#### Q1: 转发显示"错误"状态？
**A:** 检查：
1. 服务器上的服务是否在运行
2. 远程端口号是否正确
3. SSH连接是否正常
4. 本地端口是否被占用

#### Q2: 打开链接无法访问？
**A:**
1. 等待几秒，SSH隧道建立需要时间
2. 检查远程服务是否绑定到 `0.0.0.0` 而不是 `127.0.0.1`
3. 确认防火墙未阻止本地端口

#### Q3: 如何同时转发多个端口？
**A:**
直接创建多个转发，系统会自动分配不同的本地端口

#### Q4: 转发会占用服务器资源吗？
**A:**
仅占用一个SSH连接，几乎不消耗资源

---

## 📊 对比总结

| 功能 | 更新前 | ✅ 更新后 |
|-----|--------|----------|
| **数据传输** | HTTP明文 | HTTPS加密 ✅ |
| **TensorBoard访问** | 手动SSH转发 | 一键创建转发 ✅ |
| **MLflow访问** | 手动配置 | 快捷模板 ✅ |
| **端口管理** | 命令行管理 | Web界面管理 ✅ |
| **多工具支持** | ❌ 无 | TensorBoard/MLflow/Jupyter等 ✅ |

---

## 🚀 实战示例

### 示例1：深度学习训练可视化

**服务器端：**
```bash
# 训练脚本
python train.py --logdir=./logs

# 启动TensorBoard
tensorboard --logdir=./logs --port=6006
```

**本地管理端：**
```
1. 打开"端口转发"页面
2. 点击"TensorBoard"
3. 选择服务器 → 自动填充端口6006
4. 创建转发
5. 点击"打开" → 实时查看训练曲线
```

### 示例2：多实验对比（MLflow）

**服务器端：**
```bash
# 运行多个实验
python experiment1.py
python experiment2.py

# 启动MLflow UI
mlflow ui --port=5000
```

**本地管理端：**
```
1. 创建端口转发（MLflow, 5000）
2. 访问本地端口
3. 对比不同实验的参数和指标
```

### 示例3：同时监控多台服务器

```
服务器1：
  - TensorBoard (6006) → 本地16006
  - Jupyter (8888) → 本地16007

服务器2：
  - MLflow (5000) → 本地16008
  - Visdom (8097) → 本地16009

同时打开4个标签页监控所有服务！
```

---

## 📝 最佳实践

### HTTPS使用建议

1. **开发环境：** 使用自签名证书即可
2. **生产环境：** 使用Let's Encrypt正式证书
3. **内网部署：** 可考虑HTTP（已在防火墙内）
4. **公网暴露：** 必须使用HTTPS

### 端口转发建议

1. **命名规范：** 使用清晰的名称，如"ResNet训练-TensorBoard"
2. **及时清理：** 任务结束后删除不用的转发
3. **端口规划：** 服务器上使用统一的端口号范围
4. **安全考虑：** 转发仅绑定到localhost，不暴露到外网

---

## 🛠️ 故障排除

### HTTPS无法启动

```bash
# 检查证书文件
ls -l ssl/

# 重新生成证书
rm -rf ssl/
./generate_ssl_cert.sh

# 检查端口占用
sudo lsof -i :5000
```

### 端口转发失败

```bash
# 测试SSH连接
ssh -p 2233 lthpc@202.117.43.222 "echo test"

# 手动测试转发
ssh -N -L 16006:localhost:6006 lthpc@202.117.43.222 -p 2233

# 检查远程服务
ssh -p 2233 lthpc@202.117.43.222 "netstat -tln | grep 6006"
```

---

## 📞 获取帮助

如有问题，请：
1. 查看完整文档：`README.md`
2. 查看快速开始：`QUICK_START.md`
3. 查看新功能说明：`NEW_FEATURES.md`
4. 提交 Issue 或联系管理员
