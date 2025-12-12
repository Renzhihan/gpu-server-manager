"""
统一日志系统

提供应用级别的日志记录功能，包括：
1. 日志分级记录
2. 敏感数据自动过滤
3. 结构化日志支持
4. 日志轮转
"""
import logging
import os
import re
import json
from logging.handlers import RotatingFileHandler
from typing import Optional, Any, Dict
from functools import wraps
import time


# ==================== 敏感数据过滤器 ====================

class SensitiveDataFilter(logging.Filter):
    """
    敏感数据过滤器

    自动检测并脱敏日志中的敏感信息，如密码、密钥、Token等
    """

    # 敏感字段关键词（不区分大小写）
    SENSITIVE_KEYWORDS = [
        'password', 'passwd', 'pwd', 'secret', 'token', 'key',
        'credential', 'auth', 'apikey', 'api_key', 'access_token',
        'private_key', 'ssh_key', 'bearer', 'authorization'
    ]

    # 敏感数据正则模式
    SENSITIVE_PATTERNS = [
        # 密码字段: password=xxx, "password": "xxx"
        (r'(["\']?(?:password|passwd|pwd|secret|token|key|credential)["\']?\s*[:=]\s*)["\']?([^"\'\s,}\]]+)["\']?',
         r'\1***REDACTED***'),
        # Authorization header
        (r'(Authorization["\']?\s*[:=]\s*["\']?(?:Bearer|Basic)\s+)[^\s"\']+',
         r'\1***REDACTED***'),
        # API Keys (长字符串)
        (r'(["\']?(?:api[_-]?key|apikey|access[_-]?token)["\']?\s*[:=]\s*["\']?)([a-zA-Z0-9_-]{20,})["\']?',
         r'\1***REDACTED***'),
        # SSH 私钥
        (r'(-----BEGIN[^-]+PRIVATE KEY-----)[\s\S]*?(-----END[^-]+PRIVATE KEY-----)',
         r'\1\n***PRIVATE KEY REDACTED***\n\2'),
    ]

    def __init__(self, name: str = ''):
        super().__init__(name)
        # 预编译正则表达式
        self._compiled_patterns = [
            (re.compile(pattern, re.IGNORECASE), replacement)
            for pattern, replacement in self.SENSITIVE_PATTERNS
        ]

    def filter(self, record: logging.LogRecord) -> bool:
        """过滤日志记录，脱敏敏感数据"""
        if record.msg:
            record.msg = self._mask_sensitive_data(str(record.msg))

        # 处理 args
        if record.args:
            if isinstance(record.args, dict):
                record.args = {
                    k: self._mask_sensitive_data(str(v)) if self._is_sensitive_key(k) else v
                    for k, v in record.args.items()
                }
            elif isinstance(record.args, tuple):
                record.args = tuple(
                    self._mask_sensitive_data(str(arg)) if isinstance(arg, str) else arg
                    for arg in record.args
                )

        return True

    def _mask_sensitive_data(self, text: str) -> str:
        """脱敏文本中的敏感数据"""
        if not text:
            return text

        result = text
        for pattern, replacement in self._compiled_patterns:
            result = pattern.sub(replacement, result)

        return result

    def _is_sensitive_key(self, key: str) -> bool:
        """检查键名是否为敏感字段"""
        key_lower = key.lower()
        return any(kw in key_lower for kw in self.SENSITIVE_KEYWORDS)


# ==================== 日志工厂 ====================

class LoggerFactory:
    """日志工厂类"""

    _loggers: Dict[str, logging.Logger] = {}
    _initialized = False
    _log_dir: Optional[str] = None
    _sensitive_filter: Optional[SensitiveDataFilter] = None

    @classmethod
    def _setup_logging(cls):
        """初始化日志系统"""
        if cls._initialized:
            return

        # 创建日志目录
        cls._log_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'logs'
        )
        os.makedirs(cls._log_dir, exist_ok=True)

        # 创建全局敏感数据过滤器
        cls._sensitive_filter = SensitiveDataFilter()

        cls._initialized = True

    @classmethod
    def get_logger(cls, name: str, level: int = logging.INFO) -> logging.Logger:
        """
        获取或创建logger实例

        Args:
            name: logger名称（通常使用模块名）
            level: 日志级别

        Returns:
            配置好的logger实例
        """
        cls._setup_logging()

        if name in cls._loggers:
            return cls._loggers[name]

        # 创建logger
        logger = logging.getLogger(name)
        logger.setLevel(level)

        # 添加敏感数据过滤器
        logger.addFilter(cls._sensitive_filter)

        # 避免重复添加handler
        if not logger.handlers:
            # 文件handler - 应用日志
            app_log_file = os.path.join(cls._log_dir, 'app.log')
            file_handler = RotatingFileHandler(
                app_log_file,
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=5,
                encoding='utf-8'
            )
            file_handler.setLevel(logging.INFO)
            file_handler.addFilter(cls._sensitive_filter)

            # 格式化
            formatter = logging.Formatter(
                '[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

            # 错误日志单独文件
            error_log_file = os.path.join(cls._log_dir, 'error.log')
            error_handler = RotatingFileHandler(
                error_log_file,
                maxBytes=10 * 1024 * 1024,
                backupCount=10,
                encoding='utf-8'
            )
            error_handler.setLevel(logging.ERROR)
            error_handler.setFormatter(formatter)
            error_handler.addFilter(cls._sensitive_filter)
            logger.addHandler(error_handler)

            # 开发模式下同时输出到控制台
            if os.getenv('FLASK_ENV') == 'development':
                console_handler = logging.StreamHandler()
                console_handler.setLevel(logging.DEBUG)
                console_handler.setFormatter(formatter)
                console_handler.addFilter(cls._sensitive_filter)
                logger.addHandler(console_handler)

        cls._loggers[name] = logger
        return logger

    @classmethod
    def get_error_logger(cls) -> logging.Logger:
        """获取专用错误日志记录器"""
        return cls.get_logger('error', logging.ERROR)


# ==================== 便捷函数 ====================

def get_logger(name: str) -> logging.Logger:
    """获取logger实例"""
    return LoggerFactory.get_logger(name)


def log_exception(logger: logging.Logger, exc: Exception, context: str = ''):
    """
    记录异常信息

    Args:
        logger: 日志记录器
        exc: 异常对象
        context: 上下文信息
    """
    exc_type = type(exc).__name__
    exc_msg = str(exc)

    if context:
        logger.error(f"{context} - [{exc_type}] {exc_msg}", exc_info=True)
    else:
        logger.error(f"[{exc_type}] {exc_msg}", exc_info=True)


def log_api_call(logger: logging.Logger):
    """
    API 调用日志装饰器

    记录 API 调用的入参、出参和耗时
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            func_name = func.__name__

            # 记录入参（过滤敏感信息）
            logger.debug(f"API调用开始: {func_name}")

            try:
                result = func(*args, **kwargs)
                elapsed = (time.time() - start_time) * 1000

                # 记录成功
                logger.info(f"API调用完成: {func_name} - {elapsed:.2f}ms")
                return result

            except Exception as e:
                elapsed = (time.time() - start_time) * 1000
                logger.error(f"API调用失败: {func_name} - {elapsed:.2f}ms - {type(e).__name__}: {e}")
                raise

        return wrapper
    return decorator


# ==================== 结构化日志辅助 ====================

class StructuredLogger:
    """
    结构化日志辅助类

    提供 JSON 格式的日志输出，便于日志聚合和分析
    """

    def __init__(self, logger: logging.Logger):
        self.logger = logger

    def log(self, level: int, event: str, **kwargs):
        """记录结构化日志"""
        log_data = {
            'event': event,
            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
            **kwargs
        }
        self.logger.log(level, json.dumps(log_data, ensure_ascii=False, default=str))

    def info(self, event: str, **kwargs):
        self.log(logging.INFO, event, **kwargs)

    def warning(self, event: str, **kwargs):
        self.log(logging.WARNING, event, **kwargs)

    def error(self, event: str, **kwargs):
        self.log(logging.ERROR, event, **kwargs)

    def debug(self, event: str, **kwargs):
        self.log(logging.DEBUG, event, **kwargs)


def get_structured_logger(name: str) -> StructuredLogger:
    """获取结构化日志记录器"""
    return StructuredLogger(get_logger(name))
