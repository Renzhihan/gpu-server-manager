from flask import Flask
from flask_cors import CORS
from config.settings import config
import os
from app.utils.logger import get_logger

logger = get_logger(__name__)

# SocketIO 实例 (可选依赖)
socketio = None
try:
    from flask_socketio import SocketIO
    # 延迟创建实例，在 create_app 中初始化
    SOCKETIO_AVAILABLE = True
except ImportError:
    SOCKETIO_AVAILABLE = False
    logger = get_logger('app.socketio')
    logger.warning("Flask-SocketIO 未安装，Web 终端功能将不可用")
    logger.info("安装命令: pip install Flask-SocketIO==5.3.5")


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

    # Session 安全配置
    app.config['SESSION_COOKIE_HTTPONLY'] = True  # 防止 XSS 攻击窃取 Cookie
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # 防止 CSRF 攻击
    # 注意：SESSION_COOKIE_SECURE 需要 HTTPS，仅在启用 HTTPS 时设置
    # 如果使用 --https 启动，这将在 run.py 中动态设置

    # 启用 CORS - 限制为本地访问以增强安全性
    # 生产环境应进一步限制为具体的可信域名
    allowed_origins = os.getenv('CORS_ORIGINS', 'http://localhost:5000,http://127.0.0.1:5000').split(',')
    CORS(app, origins=allowed_origins, supports_credentials=True)

    # 初始化 API 速率限制
    from app.middleware.rate_limit import setup_rate_limiting
    setup_rate_limiting(app)
    logger.info("API 速率限制已启用")

    # 注册全局异常处理器
    from app.middleware.error_handler import register_error_handlers
    register_error_handlers(app)
    logger.info("全局异常处理器已注册")

    # 初始化 SocketIO (如果可用)
    global socketio
    if SOCKETIO_AVAILABLE:
        # 创建并初始化 SocketIO 实例
        # PyInstaller 环境通过 hiddenimports 包含异步驱动，让其自动选择
        socketio = SocketIO()
        # 限制 WebSocket CORS 为相同的允许来源
        allowed_origins = os.getenv('CORS_ORIGINS', 'http://localhost:5000,http://127.0.0.1:5000').split(',')
        socketio.init_app(app, cors_allowed_origins=allowed_origins)

    # 注册蓝图
    from app.routes import main, api
    app.register_blueprint(main.bp)
    app.register_blueprint(api.bp, url_prefix='/api')

    # 注册 SocketIO 事件 (如果可用)
    if SOCKETIO_AVAILABLE and socketio:
        try:
            from app.routes.terminal_events import register_terminal_events
            register_terminal_events(socketio)
            logger.info("终端事件处理模块加载成功")
        except ImportError as exc:
            logger.error(f"终端事件处理模块加载失败: {exc}")
        except Exception as exc:
            logger.error(f"终端事件注册失败: {exc}")

    # 存储功能可用性标志
    app.config['SOCKETIO_AVAILABLE'] = SOCKETIO_AVAILABLE

    return app
