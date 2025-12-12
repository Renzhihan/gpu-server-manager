"""
统一异常类体系

提供结构化的异常处理，便于：
1. 精确捕获和处理特定类型的错误
2. 向客户端返回一致的错误响应
3. 记录详细的错误日志用于调试
"""
from typing import Optional, Dict, Any
from config.constants import HttpStatus


class AppException(Exception):
    """应用基础异常类

    所有自定义异常的基类，提供：
    - 错误代码 (code)
    - 用户友好的错误信息 (message)
    - HTTP 状态码 (http_status)
    - 额外的上下文信息 (details)
    """

    code: str = "INTERNAL_ERROR"
    message: str = "内部错误"
    http_status: int = HttpStatus.INTERNAL_ERROR

    def __init__(
        self,
        message: Optional[str] = None,
        code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        http_status: Optional[int] = None
    ):
        self.message = message or self.__class__.message
        self.code = code or self.__class__.code
        self.details = details or {}
        self.http_status = http_status or self.__class__.http_status
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典，用于 API 响应"""
        result = {
            'success': False,
            'error': self.message,
            'code': self.code
        }
        if self.details:
            result['details'] = self.details
        return result

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"


# ==================== 验证相关异常 ====================

class ValidationError(AppException):
    """输入验证错误"""
    code = "VALIDATION_ERROR"
    message = "输入验证失败"
    http_status = HttpStatus.BAD_REQUEST


class InvalidParameterError(ValidationError):
    """无效参数"""
    code = "INVALID_PARAMETER"
    message = "参数无效"


class MissingParameterError(ValidationError):
    """缺少必需参数"""
    code = "MISSING_PARAMETER"
    message = "缺少必需参数"


class InvalidFormatError(ValidationError):
    """格式无效"""
    code = "INVALID_FORMAT"
    message = "格式无效"


# ==================== 认证授权异常 ====================

class AuthenticationError(AppException):
    """认证错误"""
    code = "AUTHENTICATION_ERROR"
    message = "认证失败"
    http_status = HttpStatus.UNAUTHORIZED


class InvalidCredentialsError(AuthenticationError):
    """凭证无效"""
    code = "INVALID_CREDENTIALS"
    message = "用户名或密码错误"


class SessionExpiredError(AuthenticationError):
    """会话过期"""
    code = "SESSION_EXPIRED"
    message = "会话已过期，请重新登录"


class AccountLockedError(AuthenticationError):
    """账户锁定"""
    code = "ACCOUNT_LOCKED"
    message = "账户已被锁定"


class AuthorizationError(AppException):
    """授权错误"""
    code = "AUTHORIZATION_ERROR"
    message = "没有权限执行此操作"
    http_status = HttpStatus.FORBIDDEN


# ==================== 资源相关异常 ====================

class ResourceNotFoundError(AppException):
    """资源不存在"""
    code = "NOT_FOUND"
    message = "资源不存在"
    http_status = HttpStatus.NOT_FOUND


class ServerNotFoundError(ResourceNotFoundError):
    """服务器不存在"""
    code = "SERVER_NOT_FOUND"
    message = "服务器不存在"


class UserNotFoundError(ResourceNotFoundError):
    """用户不存在"""
    code = "USER_NOT_FOUND"
    message = "用户不存在"


class FileNotFoundError(ResourceNotFoundError):
    """文件不存在"""
    code = "FILE_NOT_FOUND"
    message = "文件不存在"


class ContainerNotFoundError(ResourceNotFoundError):
    """容器不存在"""
    code = "CONTAINER_NOT_FOUND"
    message = "容器不存在"


class ResourceConflictError(AppException):
    """资源冲突"""
    code = "CONFLICT"
    message = "资源已存在"
    http_status = HttpStatus.CONFLICT


class ServerExistsError(ResourceConflictError):
    """服务器已存在"""
    code = "SERVER_EXISTS"
    message = "服务器名称已存在"


class UserExistsError(ResourceConflictError):
    """用户已存在"""
    code = "USER_EXISTS"
    message = "用户已存在"


# ==================== SSH 连接异常 ====================

class SSHError(AppException):
    """SSH 相关错误基类"""
    code = "SSH_ERROR"
    message = "SSH 操作失败"
    http_status = HttpStatus.BAD_GATEWAY


class SSHConnectionError(SSHError):
    """SSH 连接失败"""
    code = "SSH_CONNECTION_FAILED"
    message = "无法连接到服务器"


class SSHAuthenticationError(SSHError):
    """SSH 认证失败"""
    code = "SSH_AUTH_FAILED"
    message = "SSH 认证失败，请检查用户名和密码/密钥"


class SSHTimeoutError(SSHError):
    """SSH 超时"""
    code = "SSH_TIMEOUT"
    message = "SSH 连接超时"


class SSHCommandError(SSHError):
    """命令执行失败"""
    code = "COMMAND_FAILED"
    message = "命令执行失败"

    def __init__(
        self,
        message: Optional[str] = None,
        command: Optional[str] = None,
        exit_code: Optional[int] = None,
        stderr: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.get('details', {})
        if command:
            details['command'] = command[:100]  # 截断避免日志过长
        if exit_code is not None:
            details['exit_code'] = exit_code
        if stderr:
            details['stderr'] = stderr[:500]
        kwargs['details'] = details
        super().__init__(message, **kwargs)


# ==================== 安全相关异常 ====================

class SecurityError(AppException):
    """安全相关错误"""
    code = "SECURITY_ERROR"
    message = "安全检查失败"
    http_status = HttpStatus.FORBIDDEN


class PathTraversalError(SecurityError):
    """路径遍历攻击"""
    code = "PATH_TRAVERSAL"
    message = "检测到非法路径访问"


class CommandInjectionError(SecurityError):
    """命令注入攻击"""
    code = "COMMAND_INJECTION"
    message = "检测到非法命令"


class RateLimitError(SecurityError):
    """速率限制"""
    code = "RATE_LIMIT_EXCEEDED"
    message = "请求过于频繁，请稍后再试"
    http_status = HttpStatus.TOO_MANY_REQUESTS


class DangerousOperationError(SecurityError):
    """危险操作"""
    code = "DANGEROUS_OPERATION"
    message = "禁止执行危险操作"


# ==================== 业务逻辑异常 ====================

class BusinessError(AppException):
    """业务逻辑错误"""
    code = "BUSINESS_ERROR"
    message = "业务处理失败"
    http_status = HttpStatus.BAD_REQUEST


class ConfigurationError(BusinessError):
    """配置错误"""
    code = "CONFIGURATION_ERROR"
    message = "配置无效"


class OperationFailedError(BusinessError):
    """操作失败"""
    code = "OPERATION_FAILED"
    message = "操作执行失败"


class PortForwardError(BusinessError):
    """端口转发错误"""
    code = "PORT_FORWARD_ERROR"
    message = "端口转发失败"


class DockerError(BusinessError):
    """Docker 操作错误"""
    code = "DOCKER_ERROR"
    message = "Docker 操作失败"


class EmailError(BusinessError):
    """邮件发送错误"""
    code = "EMAIL_ERROR"
    message = "邮件发送失败"


# ==================== 系统异常 ====================

class SystemError(AppException):
    """系统级错误"""
    code = "SYSTEM_ERROR"
    message = "系统错误"
    http_status = HttpStatus.INTERNAL_ERROR


class DatabaseError(SystemError):
    """数据库错误"""
    code = "DATABASE_ERROR"
    message = "数据库操作失败"


class FileSystemError(SystemError):
    """文件系统错误"""
    code = "FILESYSTEM_ERROR"
    message = "文件系统操作失败"


class ExternalServiceError(SystemError):
    """外部服务错误"""
    code = "EXTERNAL_SERVICE_ERROR"
    message = "外部服务不可用"
    http_status = HttpStatus.BAD_GATEWAY
