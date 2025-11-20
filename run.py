#!/usr/bin/env python3
"""
GPU 服务器管理系统 - 启动脚本
"""
import os
import sys
import argparse
import traceback
from datetime import datetime

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 设置日志文件
log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'error.log')

def log_error(message):
    """记录错误到日志文件"""
    try:
        with open(log_file, 'a', encoding='utf-8') as f:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            f.write(f"\n{'='*60}\n")
            f.write(f"[{timestamp}] 错误信息:\n")
            f.write(f"{message}\n")
            f.write(f"{'='*60}\n")
    except Exception as e:
        print(f"无法写入日志文件: {e}")

try:
    from app import create_app, socketio, SOCKETIO_AVAILABLE
    from app.services.task_monitor import task_monitor

    # 创建 Flask 应用
    app = create_app()

    # 启动任务监控
    task_monitor.start_monitoring()

except Exception as e:
    error_msg = f"应用初始化失败:\n{traceback.format_exc()}"
    log_error(error_msg)
    print(error_msg)
    print(f"\n错误详情已保存到: {log_file}")
    input("\n按回车键退出...")
    sys.exit(1)


if __name__ == '__main__':
    try:
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
                input("\n按回车键退出...")
                sys.exit(1)

        terminal_status = "支持 (xterm.js + WebSocket)" if SOCKETIO_AVAILABLE else "不可用 (需安装 Flask-SocketIO)"

        print(f"""
╔══════════════════════════════════════════════════════════════╗
║          GPU 服务器管理系统 - 启动成功                        ║
╠══════════════════════════════════════════════════════════════╣
║  访问地址: {protocol}://{host}:{port:<47}║
║  运行模式: {'开发模式' if debug else '生产模式':<52}║
║  安全传输: {'HTTPS ✅' if use_https else 'HTTP':<52}║
║  配置文件: config/servers.yaml                              ║
║  Web终端: {terminal_status:<51}║
╚══════════════════════════════════════════════════════════════╝
    """)

        if use_https:
            print("⚠️  使用自签名证书，浏览器会显示安全警告")
            print("   点击「高级」→「继续访问」即可\n")

        # 如果 SocketIO 可用，使用 socketio.run，否则使用 app.run
        if SOCKETIO_AVAILABLE and socketio:
            socketio.run(
                app,
                host=host,
                port=port,
                debug=debug,
                ssl_context=ssl_context,
                allow_unsafe_werkzeug=True
            )
        else:
            app.run(
                host=host,
                port=port,
                debug=debug,
                threaded=True,
                ssl_context=ssl_context
            )

    except KeyboardInterrupt:
        print("\n\n用户中断，正在停止...")
    except Exception as e:
        error_msg = f"应用运行时错误:\n{traceback.format_exc()}"
        log_error(error_msg)
        print("\n" + "="*60)
        print("❌ 应用运行出错！")
        print("="*60)
        print(error_msg)
        print(f"\n错误详情已保存到: {log_file}")
        input("\n按回车键退出...")
        sys.exit(1)
    finally:
        # 清理资源
        try:
            task_monitor.stop_monitoring()

            # 清理终端管理器 (如果可用)
            if SOCKETIO_AVAILABLE:
                try:
                    from app.services.terminal_manager import terminal_manager
                    terminal_manager.close_all()
                except ImportError:
                    pass

            print("\n应用已停止")
        except Exception as e:
            log_error(f"清理资源时出错:\n{traceback.format_exc()}")
