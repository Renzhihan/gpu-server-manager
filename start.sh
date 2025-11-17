#!/bin/bash

# GPU 服务器管理系统 - 启动脚本

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║          GPU 服务器管理系统 - 启动中                          ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# 激活 conda 环境
echo "激活 conda 环境: gpu-server-manager"
source /opt/conda/etc/profile.d/conda.sh
conda activate gpu-server-manager

# 检查配置文件
if [ ! -f ".env" ]; then
    echo "⚠️  警告: .env 文件不存在，请先配置环境变量"
    echo "提示: cp .env.example .env 然后编辑 .env 文件"
    exit 1
fi

if [ ! -f "config/servers.yaml" ]; then
    echo "⚠️  警告: config/servers.yaml 文件不存在，请先配置服务器信息"
    exit 1
fi

# 启动应用
echo "启动应用..."
echo ""
echo "💡 提示:"
echo "   HTTP:  python run.py"
echo "   HTTPS: python run.py --https (需要先运行 ./generate_ssl_cert.sh)"
echo ""

# 传递所有参数给 run.py
python run.py "$@"
