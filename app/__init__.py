from flask import Flask
from flask_cors import CORS
from config.settings import config
import os

# SocketIO 实例 (可选依赖)
socketio = None
try:
    from flask_socketio import SocketIO
    socketio = SocketIO()
    SOCKETIO_AVAILABLE = True
except ImportError:
    SOCKETIO_AVAILABLE = False
    print("[警告] Flask-SocketIO 未安装，Web 终端功能将不可用")
    print("       安装命令: pip install Flask-SocketIO==5.3.5")


def create_app(config_name=None):
    """Flask 应用工厂函数"""
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')

    app = Flask(__name__)
    app.config.from_object(config.get(config_name, config['default']))

    # 配置 Session
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'gpu-server-manager-secret-key-2025')
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['PERMANENT_SESSION_LIFETIME'] = 86400 * 7  # 7天

    # 启用 CORS
    CORS(app)

    # 初始化 SocketIO (如果可用)
    if SOCKETIO_AVAILABLE and socketio:
        # PyInstaller 环境下不指定 async_mode，让它自动选择
        socketio.init_app(app, cors_allowed_origins="*")

    # 注册蓝图
    from app.routes import main, api
    app.register_blueprint(main.bp)
    app.register_blueprint(api.bp, url_prefix='/api')

    # 注册 SocketIO 事件 (如果可用)
    if SOCKETIO_AVAILABLE and socketio:
        try:
            from app.routes.terminal_events import register_terminal_events
            register_terminal_events(socketio)
        except ImportError:
            print("[警告] 终端事件处理模块加载失败")

    # 存储功能可用性标志
    app.config['SOCKETIO_AVAILABLE'] = SOCKETIO_AVAILABLE

    return app
