"""
统一日志系统
提供应用级别的日志记录功能
"""
import logging
import os
from logging.handlers import RotatingFileHandler


class LoggerFactory:
    """日志工厂类"""

    _loggers = {}
    _initialized = False

    @classmethod
    def _setup_logging(cls):
        """初始化日志系统"""
        if cls._initialized:
            return

        # 创建日志目录
        log_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'logs'
        )
        os.makedirs(log_dir, exist_ok=True)

        cls._initialized = True

    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """
        获取或创建logger实例

        Args:
            name: logger名称（通常使用模块名）

        Returns:
            配置好的logger实例
        """
        cls._setup_logging()

        if name in cls._loggers:
            return cls._loggers[name]

        # 创建logger
        logger = logging.getLogger(name)
        logger.setLevel(logging.INFO)

        # 避免重复添加handler
        if not logger.handlers:
            # 创建日志目录
            log_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                'logs'
            )

            # 文件handler
            log_file = os.path.join(log_dir, 'app.log')
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5,
                encoding='utf-8'
            )
            file_handler.setLevel(logging.INFO)

            # 格式化
            formatter = logging.Formatter(
                '[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

            # 开发模式下同时输出到控制台
            if os.getenv('FLASK_ENV') == 'development':
                console_handler = logging.StreamHandler()
                console_handler.setLevel(logging.DEBUG)
                console_handler.setFormatter(formatter)
                logger.addHandler(console_handler)

        cls._loggers[name] = logger
        return logger


# 便捷函数
def get_logger(name: str) -> logging.Logger:
    """获取logger实例"""
    return LoggerFactory.get_logger(name)
