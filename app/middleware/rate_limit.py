"""
API 速率限制中间件
提供全局和端点级别的速率限制
"""
from functools import wraps
from flask import request, jsonify, g
from app.utils.security import rate_limiter
from app.services.audit_logger import audit_logger
from config.constants import Limit, AuditEvent, HttpStatus


def get_client_ip():
    """获取客户端真实 IP"""
    forwarded_for = request.headers.get('X-Forwarded-For')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    return request.remote_addr or 'unknown'


def rate_limit(
    max_requests: int = Limit.API_RATE_LIMIT_DEFAULT,
    window_seconds: int = Limit.API_RATE_LIMIT_WINDOW,
    key_func=None,
    scope: str = 'global'
):
    """
    速率限制装饰器

    Args:
        max_requests: 时间窗口内最大请求数
        window_seconds: 时间窗口（秒）
        key_func: 自定义键生成函数
        scope: 限制范围 ('global', 'endpoint', 'user')

    Usage:
        @rate_limit(max_requests=10, window_seconds=60)
        def my_endpoint():
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 生成限制键
            if key_func:
                key = key_func()
            else:
                client_ip = get_client_ip()
                if scope == 'endpoint':
                    key = f"{client_ip}:{request.endpoint}"
                elif scope == 'user':
                    from flask import session
                    user = session.get('role', 'anonymous')
                    key = f"{user}:{request.endpoint}"
                else:
                    key = client_ip

            # 检查速率限制
            allowed, info = rate_limiter.is_allowed(key, max_requests, window_seconds)

            if not allowed:
                # 记录审计日志
                audit_logger.warning(
                    AuditEvent.RATE_LIMIT_EXCEEDED,
                    f'速率限制触发: {key} - {request.endpoint}',
                    user=get_client_ip()
                )

                response = jsonify({
                    'success': False,
                    'error': '请求过于频繁，请稍后再试',
                    'retry_after': info.get('retry_after', window_seconds)
                })
                response.status_code = HttpStatus.TOO_MANY_REQUESTS
                response.headers['Retry-After'] = str(info.get('retry_after', window_seconds))
                response.headers['X-RateLimit-Remaining'] = '0'
                response.headers['X-RateLimit-Reset'] = str(info.get('reset_in', window_seconds))
                return response

            # 添加速率限制头
            g.rate_limit_remaining = info.get('remaining', max_requests)
            g.rate_limit_reset = info.get('reset_in', window_seconds)

            return f(*args, **kwargs)
        return decorated_function
    return decorator


def add_rate_limit_headers(response):
    """添加速率限制响应头（在 after_request 中调用）"""
    if hasattr(g, 'rate_limit_remaining'):
        response.headers['X-RateLimit-Remaining'] = str(g.rate_limit_remaining)
    if hasattr(g, 'rate_limit_reset'):
        response.headers['X-RateLimit-Reset'] = str(g.rate_limit_reset)
    return response


class RateLimitMiddleware:
    """
    全局速率限制中间件

    在 Flask app 初始化时使用：
        rate_limit_middleware = RateLimitMiddleware(app)
    """

    def __init__(self, app=None, default_limit: int = Limit.API_RATE_LIMIT_DEFAULT):
        self.default_limit = default_limit
        self.exempt_endpoints = set()
        self.custom_limits = {}

        if app:
            self.init_app(app)

    def init_app(self, app):
        """初始化 Flask 应用"""
        app.before_request(self._check_rate_limit)
        app.after_request(add_rate_limit_headers)

    def exempt(self, endpoint: str):
        """
        豁免某个端点的速率限制

        Args:
            endpoint: 端点名称
        """
        self.exempt_endpoints.add(endpoint)

    def set_limit(self, endpoint: str, max_requests: int, window_seconds: int = 60):
        """
        为特定端点设置自定义限制

        Args:
            endpoint: 端点名称
            max_requests: 最大请求数
            window_seconds: 时间窗口
        """
        self.custom_limits[endpoint] = (max_requests, window_seconds)

    def _check_rate_limit(self):
        """检查请求速率限制"""
        # 跳过静态文件
        if request.endpoint and request.endpoint.startswith('static'):
            return None

        # 跳过豁免的端点
        if request.endpoint in self.exempt_endpoints:
            return None

        # 获取限制配置
        if request.endpoint in self.custom_limits:
            max_requests, window_seconds = self.custom_limits[request.endpoint]
        else:
            max_requests = self.default_limit
            window_seconds = Limit.API_RATE_LIMIT_WINDOW

        # 生成限制键
        client_ip = get_client_ip()
        key = f"{client_ip}:global"

        # 检查速率限制
        allowed, info = rate_limiter.is_allowed(key, max_requests, window_seconds)

        if not allowed:
            audit_logger.warning(
                AuditEvent.RATE_LIMIT_EXCEEDED,
                f'全局速率限制触发: {client_ip} - {request.endpoint}',
                user=client_ip
            )

            response = jsonify({
                'success': False,
                'error': '请求过于频繁，请稍后再试',
                'retry_after': info.get('retry_after', window_seconds)
            })
            response.status_code = HttpStatus.TOO_MANY_REQUESTS
            response.headers['Retry-After'] = str(info.get('retry_after', window_seconds))
            return response

        # 存储限制信息供 after_request 使用
        g.rate_limit_remaining = info.get('remaining', max_requests)
        g.rate_limit_reset = info.get('reset_in', window_seconds)

        return None


# 预定义的端点限制配置
ENDPOINT_LIMITS = {
    # 严格限制的端点
    'api.add_server': (Limit.API_RATE_LIMIT_STRICT, 60),
    'api.delete_server': (Limit.API_RATE_LIMIT_STRICT, 60),
    'api.create_user': (Limit.API_RATE_LIMIT_STRICT, 60),
    'api.delete_user': (Limit.API_RATE_LIMIT_STRICT, 60),
    'api.delete_path': (Limit.API_RATE_LIMIT_STRICT, 60),
    'api.container_action': (Limit.API_RATE_LIMIT_STRICT, 60),

    # 宽松限制的端点
    'api.health_check': (120, 60),
    'api.list_servers': (120, 60),
    'api.get_gpu_info': (120, 60),
}


def setup_rate_limiting(app):
    """
    设置应用的速率限制

    Args:
        app: Flask 应用实例
    """
    middleware = RateLimitMiddleware(app)

    # 豁免健康检查端点
    middleware.exempt('api.health_check')

    # 设置自定义限制
    for endpoint, (max_req, window) in ENDPOINT_LIMITS.items():
        middleware.set_limit(endpoint, max_req, window)

    return middleware
