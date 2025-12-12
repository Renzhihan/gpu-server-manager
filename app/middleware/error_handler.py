"""
全局异常处理器

统一处理应用中的异常，提供：
1. 一致的错误响应格式
2. 自动日志记录
3. 开发/生产环境区分
"""
import traceback
import uuid
from functools import wraps
from flask import Flask, jsonify, request, g
from typing import Tuple, Any, Callable

from app.exceptions import (
    AppException,
    ValidationError,
    AuthenticationError,
    AuthorizationError,
    ResourceNotFoundError,
    SSHError,
    SecurityError,
    RateLimitError
)
from app.utils.logger import get_logger, log_exception
from app.services.audit_logger import audit_logger
from config.constants import HttpStatus

logger = get_logger(__name__)


def register_error_handlers(app: Flask):
    """
    注册全局错误处理器

    Args:
        app: Flask 应用实例
    """

    @app.before_request
    def before_request():
        """请求前处理：生成追踪ID"""
        g.trace_id = str(uuid.uuid4())[:8]
        g.request_start_time = __import__('time').time()

    @app.after_request
    def after_request(response):
        """请求后处理：添加追踪ID到响应头"""
        if hasattr(g, 'trace_id'):
            response.headers['X-Trace-ID'] = g.trace_id
        return response

    @app.errorhandler(AppException)
    def handle_app_exception(error: AppException):
        """处理应用自定义异常"""
        trace_id = getattr(g, 'trace_id', 'unknown')

        # 记录日志
        if error.http_status >= 500:
            logger.error(f"[{trace_id}] {error.code}: {error.message}", extra={'details': error.details})
        else:
            logger.warning(f"[{trace_id}] {error.code}: {error.message}")

        response = error.to_dict()
        response['trace_id'] = trace_id

        return jsonify(response), error.http_status

    @app.errorhandler(ValidationError)
    def handle_validation_error(error: ValidationError):
        """处理验证错误"""
        return handle_app_exception(error)

    @app.errorhandler(AuthenticationError)
    def handle_auth_error(error: AuthenticationError):
        """处理认证错误"""
        # 记录安全审计
        audit_logger.warning(
            'AUTHENTICATION_FAILED',
            f'{error.code}: {error.message}',
            user='anonymous'
        )
        return handle_app_exception(error)

    @app.errorhandler(SecurityError)
    def handle_security_error(error: SecurityError):
        """处理安全错误"""
        trace_id = getattr(g, 'trace_id', 'unknown')

        # 记录安全审计
        audit_logger.security_event(
            error.code,
            f'{error.message} - trace_id={trace_id}',
            severity='warning'
        )

        return handle_app_exception(error)

    @app.errorhandler(RateLimitError)
    def handle_rate_limit_error(error: RateLimitError):
        """处理速率限制错误"""
        response = error.to_dict()
        response['trace_id'] = getattr(g, 'trace_id', 'unknown')

        resp = jsonify(response)
        resp.headers['Retry-After'] = str(error.details.get('retry_after', 60))
        return resp, error.http_status

    @app.errorhandler(400)
    def handle_bad_request(error):
        """处理 400 错误"""
        trace_id = getattr(g, 'trace_id', 'unknown')
        return jsonify({
            'success': False,
            'error': '请求参数错误',
            'code': 'BAD_REQUEST',
            'trace_id': trace_id
        }), 400

    @app.errorhandler(401)
    def handle_unauthorized(error):
        """处理 401 错误"""
        trace_id = getattr(g, 'trace_id', 'unknown')
        return jsonify({
            'success': False,
            'error': '未授权访问',
            'code': 'UNAUTHORIZED',
            'trace_id': trace_id
        }), 401

    @app.errorhandler(403)
    def handle_forbidden(error):
        """处理 403 错误"""
        trace_id = getattr(g, 'trace_id', 'unknown')
        return jsonify({
            'success': False,
            'error': '禁止访问',
            'code': 'FORBIDDEN',
            'trace_id': trace_id
        }), 403

    @app.errorhandler(404)
    def handle_not_found(error):
        """处理 404 错误"""
        trace_id = getattr(g, 'trace_id', 'unknown')
        return jsonify({
            'success': False,
            'error': '资源不存在',
            'code': 'NOT_FOUND',
            'trace_id': trace_id
        }), 404

    @app.errorhandler(405)
    def handle_method_not_allowed(error):
        """处理 405 错误"""
        trace_id = getattr(g, 'trace_id', 'unknown')
        return jsonify({
            'success': False,
            'error': '方法不允许',
            'code': 'METHOD_NOT_ALLOWED',
            'trace_id': trace_id
        }), 405

    @app.errorhandler(429)
    def handle_too_many_requests(error):
        """处理 429 错误"""
        trace_id = getattr(g, 'trace_id', 'unknown')
        return jsonify({
            'success': False,
            'error': '请求过于频繁',
            'code': 'TOO_MANY_REQUESTS',
            'trace_id': trace_id
        }), 429

    @app.errorhandler(500)
    def handle_internal_error(error):
        """处理 500 错误"""
        trace_id = getattr(g, 'trace_id', 'unknown')

        # 记录详细错误（仅日志）
        logger.error(f"[{trace_id}] 内部服务器错误: {error}", exc_info=True)

        # 返回通用错误信息（不暴露内部细节）
        response = {
            'success': False,
            'error': '服务器内部错误',
            'code': 'INTERNAL_ERROR',
            'trace_id': trace_id
        }

        # 开发模式下返回详细信息
        if app.debug:
            response['debug'] = {
                'exception': str(error),
                'traceback': traceback.format_exc()
            }

        return jsonify(response), 500

    @app.errorhandler(Exception)
    def handle_unexpected_exception(error):
        """处理未预期的异常"""
        trace_id = getattr(g, 'trace_id', 'unknown')

        # 记录详细错误
        logger.error(
            f"[{trace_id}] 未处理的异常: {type(error).__name__}: {error}",
            exc_info=True
        )

        response = {
            'success': False,
            'error': '服务器内部错误，请稍后重试',
            'code': 'UNEXPECTED_ERROR',
            'trace_id': trace_id
        }

        # 开发模式下返回详细信息
        if app.debug:
            response['debug'] = {
                'exception_type': type(error).__name__,
                'exception_message': str(error),
                'traceback': traceback.format_exc()
            }

        return jsonify(response), 500


def handle_service_errors(func: Callable) -> Callable:
    """
    服务层错误处理装饰器

    自动捕获并转换常见异常为应用异常

    Usage:
        @handle_service_errors
        def my_service_function():
            ...
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except AppException:
            # 已经是应用异常，直接抛出
            raise
        except FileNotFoundError as e:
            from app.exceptions import FileNotFoundError as AppFileNotFoundError
            raise AppFileNotFoundError(f"文件不存在: {e}")
        except PermissionError as e:
            from app.exceptions import AuthorizationError
            raise AuthorizationError(f"权限不足: {e}")
        except TimeoutError as e:
            from app.exceptions import SSHTimeoutError
            raise SSHTimeoutError(f"操作超时: {e}")
        except ConnectionError as e:
            from app.exceptions import SSHConnectionError
            raise SSHConnectionError(f"连接失败: {e}")
        except ValueError as e:
            from app.exceptions import ValidationError
            raise ValidationError(f"参数无效: {e}")
        except Exception as e:
            # 未知异常，记录并转换
            log_exception(logger, e, f"服务函数 {func.__name__} 执行失败")
            from app.exceptions import SystemError
            raise SystemError(f"操作失败: {type(e).__name__}")

    return wrapper


def api_error_response(
    error: str,
    code: str = 'ERROR',
    http_status: int = HttpStatus.BAD_REQUEST,
    details: dict = None
) -> Tuple[Any, int]:
    """
    生成标准 API 错误响应

    Args:
        error: 错误信息
        code: 错误代码
        http_status: HTTP 状态码
        details: 额外详情

    Returns:
        (response, status_code)
    """
    trace_id = getattr(g, 'trace_id', 'unknown')
    response = {
        'success': False,
        'error': error,
        'code': code,
        'trace_id': trace_id
    }
    if details:
        response['details'] = details

    return jsonify(response), http_status


def api_success_response(
    data: Any = None,
    message: str = None,
    http_status: int = HttpStatus.OK
) -> Tuple[Any, int]:
    """
    生成标准 API 成功响应

    Args:
        data: 响应数据
        message: 成功信息
        http_status: HTTP 状态码

    Returns:
        (response, status_code)
    """
    response = {'success': True}

    if message:
        response['message'] = message
    if data is not None:
        if isinstance(data, dict):
            response.update(data)
        else:
            response['data'] = data

    return jsonify(response), http_status
