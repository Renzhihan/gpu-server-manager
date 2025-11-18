import os
import sys
from dotenv import load_dotenv

load_dotenv()


class Config:
    """应用配置"""

    # Flask 配置
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    FLASK_ENV = os.getenv('FLASK_ENV', 'development')
    DEBUG = FLASK_ENV == 'development'

    # 服务器配置文件路径
    # PyInstaller 打包后优先使用外部配置文件，方便用户修改
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包后的环境
        BASE_DIR = os.path.dirname(sys.executable)
        SERVERS_CONFIG = os.path.join(BASE_DIR, 'config', 'servers.yaml')
    else:
        # 开发环境
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        SERVERS_CONFIG = os.path.join(os.path.dirname(__file__), 'servers.yaml')

    # SSH 连接配置
    SSH_TIMEOUT = 10  # 秒
    SSH_BANNER_TIMEOUT = 10
    SSH_AUTH_TIMEOUT = 10

    # GPU 监控配置
    GPU_MONITOR_INTERVAL = 5  # 秒
    GPU_HISTORY_LENGTH = 100  # 保留最近N条记录

    # Docker 配置
    DOCKER_API_VERSION = 'auto'

    # 任务监控配置
    TASK_CHECK_INTERVAL = 60  # 秒
    TASK_TIMEOUT = 86400  # 24小时

    # 邮件配置
    SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
    SMTP_USERNAME = os.getenv('SMTP_USERNAME', '')
    SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', '')
    SMTP_FROM = os.getenv('SMTP_FROM', '')
    SMTP_USE_TLS = True

    # 管理员配置
    ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
    ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin123')


class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True


class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
