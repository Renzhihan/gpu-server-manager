"""
审计日志服务
记录所有重要的安全事件和操作
"""
import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime
from flask import request
from functools import wraps


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
            # 文件handler - 滚动日志，每个文件最大10MB，保留10个备份
            log_file = os.path.join(log_dir, 'audit.log')
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=10*1024*1024,  # 10MB
                backupCount=10,
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
        # 优先获取X-Forwarded-For（代理后的真实IP）
        if request:
            forwarded_for = request.headers.get('X-Forwarded-For')
            if forwarded_for:
                return forwarded_for.split(',')[0].strip()
            return request.remote_addr or 'unknown'
        return 'system'

    def log(self, level, action, message, user='anonymous', **extra):
        """
        记录审计日志

        Args:
            level: 日志级别 (info, warning, error, critical)
            action: 操作类型 (login, logout, access, modify, delete, etc.)
            message: 详细信息
            user: 用户标识
            **extra: 额外的上下文信息
        """
        ip = self._get_client_ip()

        # 额外信息
        extra_info = {
            'ip': ip,
            'user': user,
            'action': action.upper()
        }
        extra_info.update(extra)

        # 根据级别记录
        log_func = getattr(self.logger, level.lower(), self.logger.info)
        log_func(message, extra=extra_info)

    def info(self, action, message, user='anonymous', **extra):
        """记录信息级别日志"""
        self.log('info', action, message, user, **extra)

    def warning(self, action, message, user='anonymous', **extra):
        """记录警告级别日志"""
        self.log('warning', action, message, user, **extra)

    def error(self, action, message, user='anonymous', **extra):
        """记录错误级别日志"""
        self.log('error', action, message, user, **extra)

    def critical(self, action, message, user='anonymous', **extra):
        """记录严重错误日志"""
        self.log('critical', action, message, user, **extra)

    # 便捷方法：常见操作

    def login_success(self, user, role='user'):
        """登录成功"""
        self.info('LOGIN', f'登录成功 - 角色: {role}', user=user)

    def login_failed(self, username='unknown', reason='密码错误'):
        """登录失败"""
        self.warning('LOGIN', f'登录失败 - 原因: {reason}', user=username)

    def logout(self, user):
        """退出登录"""
        self.info('LOGOUT', '用户退出', user=user)

    def access_page(self, user, page):
        """访问页面"""
        self.info('ACCESS', f'访问页面: {page}', user=user)

    def api_call(self, user, endpoint, method='GET'):
        """API调用"""
        self.info('API', f'{method} {endpoint}', user=user)

    def server_add(self, user, server_name):
        """添加服务器"""
        self.info('SERVER_ADD', f'添加服务器: {server_name}', user=user)

    def server_delete(self, user, server_name):
        """删除服务器"""
        self.warning('SERVER_DELETE', f'删除服务器: {server_name}', user=user)

    def server_modify(self, user, server_name):
        """修改服务器配置"""
        self.info('SERVER_MODIFY', f'修改服务器: {server_name}', user=user)

    def ssh_connect(self, user, server_name, success=True):
        """SSH连接"""
        if success:
            self.info('SSH_CONNECT', f'SSH连接成功: {server_name}', user=user)
        else:
            self.error('SSH_CONNECT', f'SSH连接失败: {server_name}', user=user)

    def terminal_session(self, user, server_name, action='create'):
        """终端会话"""
        self.info('TERMINAL', f'终端会话{action}: {server_name}', user=user)

    def docker_operation(self, user, server_name, operation, container=''):
        """Docker操作"""
        msg = f'{operation}'
        if container:
            msg += f' 容器: {container}'
        self.info('DOCKER', f'{msg} on {server_name}', user=user)

    def file_access(self, user, server_name, file_path, operation='read'):
        """文件访问"""
        self.info('FILE', f'{operation.upper()} {file_path} on {server_name}', user=user)

    def security_event(self, event_type, description, severity='warning'):
        """安全事件"""
        log_func = getattr(self, severity.lower(), self.warning)
        log_func('SECURITY', f'{event_type}: {description}')

    def system_event(self, event, description):
        """系统事件"""
        self.info('SYSTEM', f'{event}: {description}', user='system')


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
            if request and hasattr(request, 'user'):
                user = request.user
            elif request and 'role' in (request.args or {}):
                user = request.args.get('role', 'anonymous')

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
