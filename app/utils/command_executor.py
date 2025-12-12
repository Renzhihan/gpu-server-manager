"""
统一命令执行器
提供安全的命令执行框架，消除代码重复
"""
from typing import Dict, Optional, Callable, Any
from abc import ABC, abstractmethod
from app.services.ssh_manager import ssh_pool
from app.services.audit_logger import audit_logger
from app.utils.security import (
    InputValidator, CommandSanitizer, PathSanitizer,
    validate_and_sanitize_path, validate_username
)
from config.constants import Timeout, AuditEvent


class CommandResult:
    """命令执行结果"""

    def __init__(
        self,
        success: bool,
        data: Any = None,
        message: str = '',
        error: str = ''
    ):
        self.success = success
        self.data = data
        self.message = message
        self.error = error

    def to_dict(self) -> Dict:
        """转换为字典"""
        result = {
            'success': self.success,
            'error': self.error
        }
        if self.data is not None:
            if isinstance(self.data, dict):
                result.update(self.data)
            else:
                result['data'] = self.data
        if self.message:
            result['message'] = self.message
        return result


class BaseExecutor(ABC):
    """
    命令执行器基类

    提供统一的：
    - 输入验证
    - 命令构建
    - 执行和错误处理
    - 审计日志记录
    """

    def __init__(self, server_name: str, user: str = 'system'):
        """
        初始化执行器

        Args:
            server_name: 服务器名称
            user: 操作用户（用于审计日志）
        """
        self.server_name = server_name
        self.user = user
        self._validated = False

    def validate_server(self) -> CommandResult:
        """验证服务器名称"""
        is_valid, error = InputValidator.validate_server_name(self.server_name)
        if not is_valid:
            return CommandResult(False, error=error)

        # 检查服务器是否存在
        servers = ssh_pool.get_server_list()
        if not any(s['name'] == self.server_name for s in servers):
            return CommandResult(False, error=f'服务器 "{self.server_name}" 不存在')

        self._validated = True
        return CommandResult(True)

    def execute_command(
        self,
        command: str,
        timeout: int = Timeout.COMMAND_DEFAULT,
        audit_event: str = None,
        audit_detail: str = None
    ) -> Dict:
        """
        执行命令

        Args:
            command: 要执行的命令
            timeout: 超时时间
            audit_event: 审计事件类型
            audit_detail: 审计详情

        Returns:
            执行结果字典
        """
        if not self._validated:
            validation = self.validate_server()
            if not validation.success:
                return validation.to_dict()

        result = ssh_pool.execute_command(self.server_name, command, timeout=timeout)

        # 记录审计日志
        if audit_event:
            if result['success']:
                audit_logger.info(
                    audit_event,
                    audit_detail or f'执行命令成功',
                    user=self.user
                )
            else:
                audit_logger.warning(
                    audit_event,
                    f'{audit_detail or "执行命令"} 失败: {result.get("stderr", "")}',
                    user=self.user
                )

        return result


class UserCommandExecutor(BaseExecutor):
    """用户管理命令执行器"""

    def create_user(
        self,
        username: str,
        password: str,
        home_dir: Optional[str] = None
    ) -> CommandResult:
        """
        创建用户

        Args:
            username: 用户名
            password: 密码
            home_dir: 可选的主目录

        Returns:
            CommandResult
        """
        # 验证用户名
        is_valid, error = validate_username(username)
        if not is_valid:
            audit_logger.warning(
                AuditEvent.SECURITY_VIOLATION,
                f'用户名验证失败: {error}',
                user=self.user
            )
            return CommandResult(False, error=error)

        # 验证主目录路径
        if home_dir:
            is_valid, safe_path, error = validate_and_sanitize_path(home_dir)
            if not is_valid:
                return CommandResult(False, error=f'主目录路径无效: {error}')
            home_dir = safe_path

        # 验证服务器
        validation = self.validate_server()
        if not validation.success:
            return validation

        # 构建安全的 useradd 命令
        useradd_cmd = CommandSanitizer.build_useradd_command(username, home_dir)
        result = self.execute_command(useradd_cmd, timeout=Timeout.COMMAND_MEDIUM)

        if not result['success']:
            return CommandResult(
                False,
                error=result.get('stderr') or '创建用户失败'
            )

        # 设置密码 - 使用安全的方式
        passwd_cmd = CommandSanitizer.escape_for_chpasswd(username, password)
        passwd_result = self.execute_command(passwd_cmd, timeout=Timeout.COMMAND_SHORT)

        if not passwd_result['success']:
            # 密码设置失败，回滚用户创建
            rollback_cmd = CommandSanitizer.build_userdel_command(username, True)
            self.execute_command(rollback_cmd, timeout=Timeout.COMMAND_SHORT)
            return CommandResult(False, error='设置密码失败')

        # 记录审计日志
        audit_logger.info(
            AuditEvent.USER_CREATE,
            f'创建用户: {username}',
            user=self.user
        )

        return CommandResult(
            True,
            message=f'用户 {username} 创建成功'
        )

    def delete_user(self, username: str, remove_home: bool = True) -> CommandResult:
        """
        删除用户

        Args:
            username: 用户名
            remove_home: 是否删除主目录

        Returns:
            CommandResult
        """
        # 验证用户名
        is_valid, error = validate_username(username)
        if not is_valid:
            return CommandResult(False, error=error)

        # 验证服务器
        validation = self.validate_server()
        if not validation.success:
            return validation

        # 构建安全的 userdel 命令
        userdel_cmd = CommandSanitizer.build_userdel_command(username, remove_home)
        result = self.execute_command(userdel_cmd, timeout=Timeout.COMMAND_MEDIUM)

        if result['success']:
            audit_logger.info(
                AuditEvent.USER_DELETE,
                f'删除用户: {username}',
                user=self.user
            )
            return CommandResult(True, message=f'用户 {username} 删除成功')
        else:
            return CommandResult(
                False,
                error=result.get('stderr') or '删除用户失败'
            )

    def change_password(self, username: str, new_password: str) -> CommandResult:
        """
        修改用户密码

        Args:
            username: 用户名
            new_password: 新密码

        Returns:
            CommandResult
        """
        # 验证用户名
        is_valid, error = validate_username(username)
        if not is_valid:
            return CommandResult(False, error=error)

        # 验证服务器
        validation = self.validate_server()
        if not validation.success:
            return validation

        # 使用安全的密码设置方式
        passwd_cmd = CommandSanitizer.escape_for_chpasswd(username, new_password)
        result = self.execute_command(passwd_cmd, timeout=Timeout.COMMAND_SHORT)

        if result['success']:
            audit_logger.info(
                AuditEvent.USER_PASSWORD_CHANGE,
                f'修改用户密码: {username}',
                user=self.user
            )
            return CommandResult(True, message=f'用户 {username} 密码修改成功')
        else:
            return CommandResult(
                False,
                error=result.get('stderr') or '修改密码失败'
            )


class FileCommandExecutor(BaseExecutor):
    """文件管理命令执行器"""

    def create_directory(self, path: str, recursive: bool = True) -> CommandResult:
        """
        创建目录

        Args:
            path: 目录路径
            recursive: 是否递归创建

        Returns:
            CommandResult
        """
        # 验证路径
        is_valid, safe_path, error = validate_and_sanitize_path(path)
        if not is_valid:
            audit_logger.warning(
                AuditEvent.PATH_TRAVERSAL_ATTEMPT,
                f'路径验证失败: {path} - {error}',
                user=self.user
            )
            return CommandResult(False, error=error)

        # 验证服务器
        validation = self.validate_server()
        if not validation.success:
            return validation

        # 构建安全命令
        mkdir_cmd = CommandSanitizer.build_mkdir_command(safe_path, recursive)
        result = self.execute_command(mkdir_cmd, timeout=Timeout.COMMAND_SHORT)

        if result['success']:
            audit_logger.info(
                AuditEvent.DIRECTORY_CREATE,
                f'创建目录: {safe_path}',
                user=self.user
            )
            return CommandResult(True, message=f'目录 {safe_path} 创建成功')
        else:
            return CommandResult(
                False,
                error=result.get('stderr') or '创建目录失败'
            )

    def delete_path(self, path: str, recursive: bool = False) -> CommandResult:
        """
        删除文件或目录

        Args:
            path: 文件/目录路径
            recursive: 是否递归删除

        Returns:
            CommandResult
        """
        # 验证路径
        is_valid, safe_path, error = validate_and_sanitize_path(path)
        if not is_valid:
            audit_logger.warning(
                AuditEvent.PATH_TRAVERSAL_ATTEMPT,
                f'路径验证失败: {path} - {error}',
                user=self.user
            )
            return CommandResult(False, error=error)

        # 额外的安全检查：禁止删除根目录和重要系统目录
        dangerous_paths = ['/', '/home', '/root', '/etc', '/var', '/usr', '/bin', '/sbin']
        if safe_path in dangerous_paths:
            audit_logger.warning(
                AuditEvent.SECURITY_VIOLATION,
                f'尝试删除危险路径: {safe_path}',
                user=self.user
            )
            return CommandResult(False, error='禁止删除系统关键目录')

        # 验证服务器
        validation = self.validate_server()
        if not validation.success:
            return validation

        # 构建安全命令
        rm_cmd = CommandSanitizer.build_rm_command(safe_path, recursive)
        result = self.execute_command(rm_cmd, timeout=Timeout.COMMAND_MEDIUM)

        if result['success']:
            audit_logger.info(
                AuditEvent.FILE_DELETE,
                f'删除路径: {safe_path}',
                user=self.user
            )
            return CommandResult(True, message=f'{safe_path} 删除成功')
        else:
            return CommandResult(
                False,
                error=result.get('stderr') or '删除失败'
            )


class DockerCommandExecutor(BaseExecutor):
    """Docker 命令执行器"""

    def container_action(self, container_id: str, action: str) -> CommandResult:
        """
        执行容器操作

        Args:
            container_id: 容器 ID 或名称
            action: 操作类型 (start, stop, restart, rm)

        Returns:
            CommandResult
        """
        # 验证容器 ID
        is_valid, error = InputValidator.validate_container_id(container_id)
        if not is_valid:
            return CommandResult(False, error=error)

        # 验证操作类型
        from config.constants import CommandSecurity
        if action not in CommandSecurity.DOCKER_ACTIONS:
            return CommandResult(False, error=f'无效的操作: {action}')

        # 验证服务器
        validation = self.validate_server()
        if not validation.success:
            return validation

        # 构建安全命令
        safe_id = CommandSanitizer.escape_shell_arg(container_id)
        command = f"docker {action} {safe_id}"
        result = self.execute_command(command, timeout=Timeout.COMMAND_MEDIUM)

        # 记录审计日志
        event_map = {
            'start': AuditEvent.DOCKER_CONTAINER_START,
            'stop': AuditEvent.DOCKER_CONTAINER_STOP,
            'restart': AuditEvent.DOCKER_CONTAINER_START,
            'rm': AuditEvent.DOCKER_CONTAINER_REMOVE
        }

        if result['success']:
            audit_logger.info(
                event_map.get(action, 'DOCKER_OPERATION'),
                f'Docker {action}: {container_id}',
                user=self.user
            )
            return CommandResult(True, message=f'容器 {container_id} {action} 成功')
        else:
            return CommandResult(
                False,
                error=result.get('stderr') or f'{action} 操作失败'
            )

    def pull_image(self, image_name: str) -> CommandResult:
        """
        拉取镜像

        Args:
            image_name: 镜像名称

        Returns:
            CommandResult
        """
        # 验证镜像名称
        is_valid, error = InputValidator.validate_image_name(image_name)
        if not is_valid:
            return CommandResult(False, error=error)

        # 验证服务器
        validation = self.validate_server()
        if not validation.success:
            return validation

        # 构建安全命令
        safe_name = CommandSanitizer.escape_shell_arg(image_name)
        command = f"docker pull {safe_name}"
        result = self.execute_command(
            command,
            timeout=Timeout.COMMAND_DOCKER_PULL
        )

        if result['success']:
            audit_logger.info(
                AuditEvent.DOCKER_IMAGE_PULL,
                f'拉取镜像: {image_name}',
                user=self.user
            )
            return CommandResult(True, message=result.get('stdout', ''))
        else:
            return CommandResult(
                False,
                error=result.get('stderr') or '拉取镜像失败'
            )
