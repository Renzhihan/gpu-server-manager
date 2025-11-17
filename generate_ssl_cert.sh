#!/bin/bash
# SSL 自签名证书生成脚本

CERT_DIR="./ssl"
CERT_FILE="$CERT_DIR/cert.pem"
KEY_FILE="$CERT_DIR/key.pem"

# 创建 SSL 目录
mkdir -p "$CERT_DIR"

# 检查证书是否已存在
if [ -f "$CERT_FILE" ] && [ -f "$KEY_FILE" ]; then
    echo "SSL 证书已存在："
    echo "  证书: $CERT_FILE"
    echo "  密钥: $KEY_FILE"
    read -p "是否重新生成？(y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "跳过证书生成"
        exit 0
    fi
fi

echo "正在生成 SSL 自签名证书..."

# 生成私钥和证书（有效期 365 天）
openssl req -x509 -newkey rsa:4096 -nodes \
    -out "$CERT_FILE" \
    -keyout "$KEY_FILE" \
    -days 365 \
    -subj "/C=CN/ST=Beijing/L=Beijing/O=GPU Server Manager/OU=IT/CN=localhost"

if [ $? -eq 0 ]; then
    echo "✅ SSL 证书生成成功！"
    echo ""
    echo "证书位置："
    echo "  证书: $CERT_FILE"
    echo "  密钥: $KEY_FILE"
    echo ""
    echo "⚠️  注意事项："
    echo "  1. 这是自签名证书，浏览器会显示安全警告"
    echo "  2. 点击「高级」→「继续访问」即可"
    echo "  3. 生产环境建议使用 Let's Encrypt 正式证书"
    echo ""
    echo "使用 HTTPS 启动："
    echo "  python run.py --https"
else
    echo "❌ 证书生成失败"
    exit 1
fi
