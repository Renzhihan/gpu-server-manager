"""
审计日志服务
记录所有重要的安全事件和操作
"""
import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime
from flask import request, session
from functools import wraps
from config.constants import BufferSize, AuditEvent


class AuditLogger:
    """审计日志管理器"""

    def __init__(self):
        self.logger = None
        self._setup_logger()

    def _setup_logger(self):
        """配置审计日志记录器"""
        # 创建日志目录
        log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs')
        os.makedirs(log_dir, exist_ok=True)

        # 创建logger
        self.logger = logging.getLogger('audit')
        self.logger.setLevel(logging.INFO)

        # 避免重复添加handler
        if not self.logger.handlers:
            # 文件handler - 滚动日志
            log_file = os.path.join(log_dir, 'audit.log')
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=BufferSize.LOG_MAX_BYTES,
                backupCount=BufferSize.LOG_BACKUP_COUNT,
                encoding='utf-8'
            )

            # 日志格式：[时间] [级别] [IP] [用户] [操作] 详细信息
            formatter = logging.Formatter(
                '[%(asctime)s] [%(levelname)s] [%(ip)s] [%(user)s] [%(action)s] %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

            # 控制台handler（可选，用于调试）
            if os.getenv('FLASK_ENV') == 'development':
                console_handler = logging.StreamHandler()
                console_handler.setFormatter(formatter)
                self.logger.addHandler(console_handler)

    def _get_client_ip(self):
        """获取客户端真实IP（考虑代理）"""
        try:
            if request:
                forwarded_for = request.headers.get('X-Forwarded-For')
                if forwarded_for:
                    return forwarded_for.split(',')[0].strip()
                return request.remote_addr or 'unknown'
        except RuntimeError:
            # 在请求上下文之外调用
            pass
        return 'system'

    def _get_current_user(self):
        """获取当前用户"""
        try:
            if session:
                return session.get('role', 'anonymous')
        except RuntimeError:
            pass
        return 'system'

    def log(self, level, action, message, user=None, **extra):
        """
        记录审计日志

        Args:
            level: 日志级别 (info, warning, error, critical)
            action: 操作类型 (使用 AuditEvent 常量)
            message: 详细信息
            user: 用户标识（None 则自动获取）
            **extra: 额外的上下文信息
        """
        ip = self._get_client_ip()
        if user is None:
            user = self._get_current_user()

        # 额外信息
        extra_info = {
            'ip': ip,
            'user': user,
            'action': action.upper() if isinstance(action, str) else action
        }
        extra_info.update(extra)

        # 根据级别记录
        log_func = getattr(self.logger, level.lower(), self.logger.info)
        log_func(message, extra=extra_info)

    def info(self, action, message, user=None, **extra):
        """记录信息级别日志"""
        self.log('info', action, message, user, **extra)

    def warning(self, action, message, user=None, **extra):
        """记录警告级别日志"""
        self.log('warning', action, message, user, **extra)

    def error(self, action, message, user=None, **extra):
        """记录错误级别日志"""
        self.log('error', action, message, user, **extra)

    def critical(self, action, message, user=None, **extra):
        """记录严重错误日志"""
        self.log('critical', action, message, user, **extra)

    # ==================== 认证相关 ====================

    def login_success(self, user, role='user'):
        """登录成功"""
        self.info(AuditEvent.LOGIN_SUCCESS, f'登录成功 - 角色: {role}', user=user)

    def login_failed(self, username='unknown', reason='密码错误'):
        """登录失败"""
        self.warning(AuditEvent.LOGIN_FAILED, f'登录失败 - 原因: {reason}', user=username)

    def logout(self, user):
        """退出登录"""
        self.info(AuditEvent.LOGOUT, '用户退出', user=user)

    def account_locked(self, ip, duration):
        """账户锁定"""
        self.warning(
            AuditEvent.ACCOUNT_LOCKED,
            f'IP {ip} 因多次登录失败被锁定 {duration}'
        )

    # ==================== 服务器操作 ====================

    def server_add(self, user, server_name):
        """添加服务器"""
        self.info(AuditEvent.SERVER_ADD, f'添加服务器: {server_name}', user=user)

    def server_delete(self, user, server_name):
        """删除服务器"""
        self.warning(AuditEvent.SERVER_DELETE, f'删除服务器: {server_name}', user=user)

    def server_modify(self, user, server_name):
        """修改服务器配置"""
        self.info(AuditEvent.SERVER_MODIFY, f'修改服务器: {server_name}', user=user)

    def ssh_connect(self, user, server_name, success=True):
        """SSH连接"""
        if success:
            self.info(AuditEvent.SERVER_CONNECT, f'SSH连接成功: {server_name}', user=user)
        else:
            self.error(AuditEvent.SERVER_CONNECT, f'SSH连接失败: {server_name}', user=user)

    # ==================== 用户管理 ====================

    def user_create(self, operator, username, server_name):
        """创建用户"""
        self.info(
            AuditEvent.USER_CREATE,
            f'创建用户: {username} on {server_name}',
            user=operator
        )

    def user_delete(self, operator, username, server_name):
        """删除用户"""
        self.warning(
            AuditEvent.USER_DELETE,
            f'删除用户: {username} on {server_name}',
            user=operator
        )

    def user_password_change(self, operator, username, server_name):
        """修改用户密码"""
        self.info(
            AuditEvent.USER_PASSWORD_CHANGE,
            f'修改用户密码: {username} on {server_name}',
            user=operator
        )

    # ==================== 文件操作 ====================

    def file_list(self, user, server_name, path):
        """列出目录"""
        self.info(AuditEvent.FILE_LIST, f'列出目录: {path} on {server_name}', user=user)

    def file_download(self, user, server_name, path):
        """下载文件"""
        self.info(AuditEvent.FILE_DOWNLOAD, f'下载文件: {path} on {server_name}', user=user)

    def file_delete(self, user, server_name, path):
        """删除文件"""
        self.warning(AuditEvent.FILE_DELETE, f'删除文件: {path} on {server_name}', user=user)

    def directory_create(self, user, server_name, path):
        """创建目录"""
        self.info(AuditEvent.DIRECTORY_CREATE, f'创建目录: {path} on {server_name}', user=user)

    def file_access(self, user, server_name, file_path, operation='read'):
        """文件访问（通用）"""
        self.info('FILE_ACCESS', f'{operation.upper()} {file_path} on {server_name}', user=user)

    # ==================== Docker 操作 ====================

    def docker_container_start(self, user, server_name, container):
        """启动容器"""
        self.info(
            AuditEvent.DOCKER_CONTAINER_START,
            f'启动容器: {container} on {server_name}',
            user=user
        )

    def docker_container_stop(self, user, server_name, container):
        """停止容器"""
        self.info(
            AuditEvent.DOCKER_CONTAINER_STOP,
            f'停止容器: {container} on {server_name}',
            user=user
        )

    def docker_container_remove(self, user, server_name, container):
        """删除容器"""
        self.warning(
            AuditEvent.DOCKER_CONTAINER_REMOVE,
            f'删除容器: {container} on {server_name}',
            user=user
        )

    def docker_image_pull(self, user, server_name, image):
        """拉取镜像"""
        self.info(
            AuditEvent.DOCKER_IMAGE_PULL,
            f'拉取镜像: {image} on {server_name}',
            user=user
        )

    def docker_operation(self, user, server_name, operation, container=''):
        """Docker操作（通用）"""
        msg = f'{operation}'
        if container:
            msg += f' 容器: {container}'
        self.info('DOCKER', f'{msg} on {server_name}', user=user)

    # ==================== 端口转发 ====================

    def port_forward_create(self, user, name, server_name, remote_port, local_port):
        """创建端口转发"""
        self.info(
            AuditEvent.PORT_FORWARD_CREATE,
            f'创建端口转发: {name} ({server_name}:{remote_port} -> localhost:{local_port})',
            user=user
        )

    def port_forward_stop(self, user, name):
        """停止端口转发"""
        self.info(AuditEvent.PORT_FORWARD_STOP, f'停止端口转发: {name}', user=user)

    def port_forward_delete(self, user, name):
        """删除端口转发"""
        self.info(AuditEvent.PORT_FORWARD_DELETE, f'删除端口转发: {name}', user=user)

    # ==================== 任务监控 ====================

    def task_create(self, user, task_name, server_name, monitor_type):
        """创建任务"""
        self.info(
            AuditEvent.TASK_CREATE,
            f'创建任务: {task_name} on {server_name} (类型: {monitor_type})',
            user=user
        )

    def task_delete(self, user, task_id):
        """删除任务"""
        self.info(AuditEvent.TASK_DELETE, f'删除任务: {task_id}', user=user)

    # ==================== 终端会话 ====================

    def terminal_session(self, user, server_name, action='create'):
        """终端会话"""
        self.info('TERMINAL', f'终端会话 {action}: {server_name}', user=user)

    # ==================== 安全事件 ====================

    def security_event(self, event_type, description, severity='warning'):
        """安全事件"""
        log_func = getattr(self, severity.lower(), self.warning)
        log_func(AuditEvent.SECURITY_VIOLATION, f'{event_type}: {description}')

    def path_traversal_attempt(self, user, path):
        """路径遍历尝试"""
        self.warning(
            AuditEvent.PATH_TRAVERSAL_ATTEMPT,
            f'路径遍历尝试: {path}',
            user=user
        )

    def command_injection_attempt(self, user, command):
        """命令注入尝试"""
        self.warning(
            AuditEvent.COMMAND_INJECTION_ATTEMPT,
            f'命令注入尝试: {command[:100]}...',
            user=user
        )

    def rate_limit_exceeded(self, ip, endpoint):
        """速率限制触发"""
        self.warning(
            AuditEvent.RATE_LIMIT_EXCEEDED,
            f'速率限制触发: {endpoint}',
            user=ip
        )

    # ==================== 系统事件 ====================

    def system_event(self, event, description):
        """系统事件"""
        self.info('SYSTEM', f'{event}: {description}', user='system')

    def access_page(self, user, page):
        """访问页面"""
        self.info('ACCESS', f'访问页面: {page}', user=user)

    def api_call(self, user, endpoint, method='GET'):
        """API调用"""
        self.info('API', f'{method} {endpoint}', user=user)


def audit_required(action):
    """
    装饰器：自动记录函数调用的审计日志

    使用方法:
    @audit_required('USER_CREATE')
    def create_user(username):
        ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = 'system'
            try:
                if session:
                    user = session.get('role', 'anonymous')
            except RuntimeError:
                pass

            # 记录操作开始
            audit_logger.info(action, f'开始执行: {f.__name__}', user=user)

            try:
                result = f(*args, **kwargs)
                # 操作成功
                audit_logger.info(action, f'执行成功: {f.__name__}', user=user)
                return result
            except Exception as e:
                # 操作失败
                audit_logger.error(action, f'执行失败: {f.__name__} - {str(e)}', user=user)
                raise

        return decorated_function
    return decorator


# 全局审计日志实例
audit_logger = AuditLogger()
