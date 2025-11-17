#!/usr/bin/env python3
"""
GPU 服务器管理系统 - 启动脚本
"""
import os
import sys
import argparse

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.services.task_monitor import task_monitor

# 创建 Flask 应用
app = create_app()

# 启动任务监控
task_monitor.start_monitoring()


if __name__ == '__main__':
    # 命令行参数解析
    parser = argparse.ArgumentParser(description='GPU 服务器管理系统')
    parser.add_argument('--https', action='store_true', help='启用 HTTPS (需要先生成证书)')
    parser.add_argument('--host', default=os.getenv('FLASK_HOST', '0.0.0.0'), help='监听地址')
    parser.add_argument('--port', type=int, default=int(os.getenv('FLASK_PORT', 5000)), help='监听端口')
    parser.add_argument('--debug', action='store_true', help='启用调试模式')
    args = parser.parse_args()

    # 配置参数
    host = args.host
    port = args.port
    debug = args.debug or (os.getenv('FLASK_ENV', 'development') == 'development')
    use_https = args.https

    # SSL 配置
    ssl_context = None
    protocol = 'http'

    if use_https:
        cert_file = 'ssl/cert.pem'
        key_file = 'ssl/key.pem'

        if os.path.exists(cert_file) and os.path.exists(key_file):
            ssl_context = (cert_file, key_file)
            protocol = 'https'
            print("✅ SSL 证书加载成功")
        else:
            print("❌ SSL 证书未找到！")
            print("   请先运行: ./generate_ssl_cert.sh")
            sys.exit(1)

    print(f"""
╔══════════════════════════════════════════════════════════════╗
║          GPU 服务器管理系统 - 启动成功                        ║
╠══════════════════════════════════════════════════════════════╣
║  访问地址: {protocol}://{host}:{port:<47}║
║  运行模式: {'开发模式' if debug else '生产模式':<52}║
║  安全传输: {'HTTPS ✅' if use_https else 'HTTP':<52}║
║  配置文件: config/servers.yaml                              ║
╚══════════════════════════════════════════════════════════════╝
    """)

    if use_https:
        print("⚠️  使用自签名证书，浏览器会显示安全警告")
        print("   点击「高级」→「继续访问」即可\n")

    try:
        app.run(
            host=host,
            port=port,
            debug=debug,
            threaded=True,
            ssl_context=ssl_context
        )
    finally:
        # 清理资源
        task_monitor.stop_monitoring()
        print("\n应用已停止")
