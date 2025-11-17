from flask import Flask
from flask_cors import CORS
from config.settings import config
import os


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

    # 注册蓝图
    from app.routes import main, api
    app.register_blueprint(main.bp)
    app.register_blueprint(api.bp, url_prefix='/api')

    return app
