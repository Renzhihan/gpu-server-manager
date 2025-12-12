"""
用户管理服务
提供 Linux 系统用户的创建、删除、密码管理等功能
"""
from typing import Dict, List
from .ssh_manager import ssh_pool
from app.utils.security import (
    InputValidator, CommandSanitizer,
    validate_username, validate_and_sanitize_path
)
from app.services.audit_logger import audit_logger
from config.constants import Timeout, AuditEvent
from app.utils.logger import get_logger

logger = get_logger(__name__)


class UserManager:
    """用户管理服务"""

    @staticmethod
    def create_user(
        server_name: str,
        username: str,
        password: str,
        home_dir: str = None,
        user: str = 'system'
    ) -> Dict:
        """
        创建新用户

        Args:
            server_name: 服务器名称
            username: 用户名
            password: 密码
            home_dir: 可选的主目录路径
            user: 操作用户（用于审计日志）

        Returns:
            {
                'success': bool,
                'message': str,
                'error': str
            }
        """
        # 验证用户名
        is_valid, error = validate_username(username)
        if not is_valid:
            audit_logger.warning(
                AuditEvent.SECURITY_VIOLATION,
                f'用户名验证失败: {username} - {error}',
                user=user
            )
            return {
                'success': False,
                'message': '',
                'error': error
            }

        # 验证主目录路径
        if home_dir:
            is_valid, safe_home, error = validate_and_sanitize_path(home_dir)
            if not is_valid:
                return {
                    'success': False,
                    'message': '',
                    'error': f'主目录路径无效: {error}'
                }
            home_dir = safe_home

        # 构建安全的 useradd 命令
        useradd_cmd = CommandSanitizer.build_useradd_command(username, home_dir)

        # 执行创建用户命令
        result = ssh_pool.execute_command(
            server_name,
            useradd_cmd,
            timeout=Timeout.COMMAND_MEDIUM
        )

        if not result['success']:
            return {
                'success': False,
                'message': '',
                'error': result['stderr'] or '创建用户失败'
            }

        # 设置密码 - 使用安全的 base64 编码方式
        passwd_cmd = CommandSanitizer.escape_for_chpasswd(username, password)
        passwd_result = ssh_pool.execute_command(
            server_name,
            passwd_cmd,
            timeout=Timeout.COMMAND_SHORT
        )

        if not passwd_result['success']:
            # 密码设置失败，回滚用户创建
            rollback_cmd = CommandSanitizer.build_userdel_command(username, True)
            ssh_pool.execute_command(
                server_name,
                rollback_cmd,
                timeout=Timeout.COMMAND_SHORT
            )
            return {
                'success': False,
                'message': '',
                'error': '设置密码失败'
            }

        # 记录审计日志
        audit_logger.info(
            AuditEvent.USER_CREATE,
            f'创建用户: {username} on {server_name}',
            user=user
        )

        return {
            'success': True,
            'message': f'用户 {username} 创建成功',
            'error': ''
        }

    @staticmethod
    def delete_user(
        server_name: str,
        username: str,
        remove_home: bool = True,
        user: str = 'system'
    ) -> Dict:
        """
        删除用户

        Args:
            server_name: 服务器名称
            username: 用户名
            remove_home: 是否删除主目录
            user: 操作用户（用于审计日志）

        Returns:
            {
                'success': bool,
                'message': str,
                'error': str
            }
        """
        # 验证用户名
        is_valid, error = validate_username(username)
        if not is_valid:
            return {
                'success': False,
                'message': '',
                'error': error
            }

        # 构建安全的 userdel 命令
        command = CommandSanitizer.build_userdel_command(username, remove_home)

        result = ssh_pool.execute_command(
            server_name,
            command,
            timeout=Timeout.COMMAND_MEDIUM
        )

        if result['success']:
            audit_logger.info(
                AuditEvent.USER_DELETE,
                f'删除用户: {username} on {server_name}',
                user=user
            )

        return {
            'success': result['success'],
            'message': f'用户 {username} 删除成功' if result['success'] else '',
            'error': result['stderr'] if not result['success'] else ''
        }

    @staticmethod
    def change_password(
        server_name: str,
        username: str,
        new_password: str,
        user: str = 'system'
    ) -> Dict:
        """
        修改用户密码

        Args:
            server_name: 服务器名称
            username: 用户名
            new_password: 新密码
            user: 操作用户（用于审计日志）

        Returns:
            {
                'success': bool,
                'message': str,
                'error': str
            }
        """
        # 验证用户名
        is_valid, error = validate_username(username)
        if not is_valid:
            return {
                'success': False,
                'message': '',
                'error': error
            }

        # 使用安全的密码设置方式
        command = CommandSanitizer.escape_for_chpasswd(username, new_password)

        result = ssh_pool.execute_command(
            server_name,
            command,
            timeout=Timeout.COMMAND_SHORT
        )

        if result['success']:
            audit_logger.info(
                AuditEvent.USER_PASSWORD_CHANGE,
                f'修改用户密码: {username} on {server_name}',
                user=user
            )

        return {
            'success': result['success'],
            'message': f'用户 {username} 密码修改成功' if result['success'] else '',
            'error': result['stderr'] if not result['success'] else ''
        }

    @staticmethod
    def list_users(server_name: str) -> Dict:
        """
        列出系统用户

        Args:
            server_name: 服务器名称

        Returns:
            {
                'success': bool,
                'users': List[Dict],
                'error': str
            }
        """
        # 获取普通用户（UID >= 1000）
        command = "awk -F: '$3 >= 1000 && $1 != \"nobody\" {print $1,$3,$6,$7}' /etc/passwd"

        result = ssh_pool.execute_command(
            server_name,
            command,
            timeout=Timeout.COMMAND_SHORT
        )

        if not result['success']:
            return {
                'success': False,
                'users': [],
                'error': result['stderr'] or '获取用户列表失败'
            }

        users = []
        for line in result['stdout'].strip().split('\n'):
            if line.strip():
                parts = line.split()
                if len(parts) >= 4:
                    users.append({
                        'username': parts[0],
                        'uid': parts[1],
                        'home': parts[2],
                        'shell': parts[3]
                    })

        return {
            'success': True,
            'users': users,
            'error': ''
        }


# 全局用户管理实例
user_manager = UserManager()
