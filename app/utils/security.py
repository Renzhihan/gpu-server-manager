"""
安全工具模块
提供输入验证、命令转义、路径安全检查等功能
"""
import re
import shlex
import os
from typing import Tuple, Optional, List
from pathlib import PurePosixPath
from config.constants import (
    PathSecurity, CommandSecurity, UserValidation, AuditEvent
)


class InputValidator:
    """输入验证器"""

    @staticmethod
    def validate_username(username: str) -> Tuple[bool, str]:
        """
        验证 Linux 用户名

        Args:
            username: 用户名

        Returns:
            (is_valid, error_message)
        """
        if not username:
            return False, '用户名不能为空'

        if len(username) < UserValidation.USERNAME_MIN_LENGTH:
            return False, f'用户名至少需要 {UserValidation.USERNAME_MIN_LENGTH} 个字符'

        if len(username) > UserValidation.USERNAME_MAX_LENGTH:
            return False, f'用户名不能超过 {UserValidation.USERNAME_MAX_LENGTH} 个字符'

        if not re.match(UserValidation.USERNAME_PATTERN, username):
            return False, '用户名只能包含小写字母、数字、下划线和连字符，且必须以字母或下划线开头'

        if username.lower() in UserValidation.RESERVED_USERNAMES:
            return False, f'"{username}" 是系统保留用户名'

        return True, ''

    @staticmethod
    def validate_path(path: str, check_traversal: bool = True) -> Tuple[bool, str]:
        """
        验证文件路径安全性

        Args:
            path: 文件路径
            check_traversal: 是否检查路径遍历

        Returns:
            (is_valid, error_message)
        """
        if not path:
            return False, '路径不能为空'

        # 检查路径遍历攻击
        if check_traversal:
            # 规范化路径并检查
            try:
                # 使用 PurePosixPath 进行路径规范化
                normalized = str(PurePosixPath(path))

                # 检查是否包含 ..
                if '..' in path:
                    return False, '路径中不允许包含 ".."'

                # 检查危险模式
                for pattern in PathSecurity.DANGEROUS_PATTERNS:
                    if pattern in path and pattern != '..':  # .. 已经检查过
                        return False, f'路径中包含不安全字符: {pattern}'

            except Exception as e:
                return False, f'路径格式无效: {str(e)}'

        # 检查禁止访问的路径
        path_lower = path.lower()
        for forbidden in PathSecurity.FORBIDDEN_PATHS:
            if path_lower.startswith(forbidden.lower()):
                return False, f'禁止访问系统敏感路径: {forbidden}'

        return True, ''

    @staticmethod
    def validate_server_name(server_name: str) -> Tuple[bool, str]:
        """
        验证服务器名称

        Args:
            server_name: 服务器名称

        Returns:
            (is_valid, error_message)
        """
        if not server_name:
            return False, '服务器名称不能为空'

        # 只允许字母、数字、下划线、连字符
        if not re.match(r'^[a-zA-Z0-9_-]+$', server_name):
            return False, '服务器名称只能包含字母、数字、下划线和连字符'

        if len(server_name) > 64:
            return False, '服务器名称不能超过 64 个字符'

        return True, ''

    @staticmethod
    def validate_port(port: int) -> Tuple[bool, str]:
        """
        验证端口号

        Args:
            port: 端口号

        Returns:
            (is_valid, error_message)
        """
        try:
            port = int(port)
        except (ValueError, TypeError):
            return False, '端口必须是数字'

        if port < 1 or port > 65535:
            return False, '端口必须在 1-65535 范围内'

        return True, ''

    @staticmethod
    def validate_container_id(container_id: str) -> Tuple[bool, str]:
        """
        验证 Docker 容器 ID

        Args:
            container_id: 容器 ID 或名称

        Returns:
            (is_valid, error_message)
        """
        if not container_id:
            return False, '容器 ID 不能为空'

        # 容器 ID 是 12 位或 64 位十六进制，或者是容器名称
        if re.match(r'^[a-fA-F0-9]{12,64}$', container_id):
            return True, ''

        # 容器名称：字母、数字、下划线、连字符、斜杠
        if re.match(r'^[a-zA-Z0-9][a-zA-Z0-9_.-]*$', container_id):
            return True, ''

        return False, '容器 ID 格式无效'

    @staticmethod
    def validate_image_name(image_name: str) -> Tuple[bool, str]:
        """
        验证 Docker 镜像名称

        Args:
            image_name: 镜像名称

        Returns:
            (is_valid, error_message)
        """
        if not image_name:
            return False, '镜像名称不能为空'

        # 镜像名称格式：[registry/][namespace/]name[:tag][@digest]
        # 简化验证：只允许安全字符
        if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9_./:@-]*$', image_name):
            return False, '镜像名称包含非法字符'

        if len(image_name) > 256:
            return False, '镜像名称过长'

        return True, ''


class CommandSanitizer:
    """命令安全处理器"""

    @staticmethod
    def escape_shell_arg(arg: str) -> str:
        """
        转义 shell 参数，防止命令注入

        Args:
            arg: 原始参数

        Returns:
            转义后的参数
        """
        return shlex.quote(arg)

    @staticmethod
    def escape_for_chpasswd(username: str, password: str) -> str:
        """
        为 chpasswd 命令安全转义用户名和密码

        使用 base64 编码避免特殊字符问题

        Args:
            username: 用户名
            password: 密码

        Returns:
            安全的命令字符串
        """
        import base64

        # 将 username:password 进行 base64 编码
        credentials = f"{username}:{password}"
        encoded = base64.b64encode(credentials.encode()).decode()

        # 使用 base64 解码并传递给 chpasswd
        return f"echo {shlex.quote(encoded)} | base64 -d | chpasswd"

    @staticmethod
    def build_useradd_command(username: str, home_dir: Optional[str] = None) -> str:
        """
        安全构建 useradd 命令

        Args:
            username: 用户名（必须已验证）
            home_dir: 可选的主目录

        Returns:
            安全的命令字符串
        """
        # 用户名已经过验证，使用 shlex.quote 额外保护
        safe_username = shlex.quote(username)

        if home_dir:
            safe_home = shlex.quote(home_dir)
            return f"useradd -m -d {safe_home} {safe_username}"
        else:
            return f"useradd -m {safe_username}"

    @staticmethod
    def build_userdel_command(username: str, remove_home: bool = True) -> str:
        """
        安全构建 userdel 命令

        Args:
            username: 用户名（必须已验证）
            remove_home: 是否删除主目录

        Returns:
            安全的命令字符串
        """
        safe_username = shlex.quote(username)
        flag = '-r' if remove_home else ''
        return f"userdel {flag} {safe_username}".strip()

    @staticmethod
    def build_mkdir_command(path: str, recursive: bool = True) -> str:
        """
        安全构建 mkdir 命令

        Args:
            path: 目录路径（必须已验证）
            recursive: 是否递归创建

        Returns:
            安全的命令字符串
        """
        safe_path = shlex.quote(path)
        flag = '-p' if recursive else ''
        return f"mkdir {flag} {safe_path}".strip()

    @staticmethod
    def build_rm_command(path: str, recursive: bool = False) -> str:
        """
        安全构建 rm 命令

        Args:
            path: 文件/目录路径（必须已验证）
            recursive: 是否递归删除

        Returns:
            安全的命令字符串
        """
        safe_path = shlex.quote(path)
        flag = '-rf' if recursive else '-f'
        return f"rm {flag} {safe_path}"

    @staticmethod
    def is_dangerous_command(command: str) -> Tuple[bool, str]:
        """
        检查命令是否包含危险模式

        Args:
            command: 命令字符串

        Returns:
            (is_dangerous, matched_pattern)
        """
        command_lower = command.lower()
        for pattern in CommandSecurity.DANGEROUS_COMMANDS:
            if pattern.lower() in command_lower:
                return True, pattern
        return False, ''


class PathSanitizer:
    """路径安全处理器"""

    @staticmethod
    def normalize_path(path: str) -> str:
        """
        规范化路径

        Args:
            path: 原始路径

        Returns:
            规范化后的路径
        """
        if not path:
            return '/'

        # 使用 PurePosixPath 规范化（不访问文件系统）
        normalized = str(PurePosixPath(path))

        # 确保以 / 开头
        if not normalized.startswith('/'):
            normalized = '/' + normalized

        return normalized

    @staticmethod
    def is_subpath(path: str, parent: str) -> bool:
        """
        检查 path 是否是 parent 的子路径

        Args:
            path: 要检查的路径
            parent: 父路径

        Returns:
            是否是子路径
        """
        try:
            path_obj = PurePosixPath(path)
            parent_obj = PurePosixPath(parent)
            return path_obj.is_relative_to(parent_obj)
        except (ValueError, TypeError):
            return False

    @staticmethod
    def get_safe_path(path: str, allowed_roots: List[str] = None) -> Tuple[bool, str, str]:
        """
        获取安全的路径

        Args:
            path: 原始路径
            allowed_roots: 允许的根目录列表

        Returns:
            (is_safe, safe_path, error_message)
        """
        # 首先验证路径
        is_valid, error = InputValidator.validate_path(path)
        if not is_valid:
            return False, '', error

        # 规范化路径
        normalized = PathSanitizer.normalize_path(path)

        # 如果指定了允许的根目录，检查是否在允许范围内
        if allowed_roots:
            is_allowed = any(
                PathSanitizer.is_subpath(normalized, root)
                for root in allowed_roots
            )
            if not is_allowed:
                return False, '', f'路径不在允许的目录范围内'

        return True, normalized, ''


class RateLimiter:
    """
    API 速率限制器

    基于令牌桶算法实现
    """

    def __init__(self):
        self._buckets = {}  # {key: {'tokens': n, 'last_update': timestamp}}
        self._lock = __import__('threading').Lock()

    def is_allowed(
        self,
        key: str,
        max_requests: int = 60,
        window_seconds: int = 60
    ) -> Tuple[bool, dict]:
        """
        检查请求是否允许

        Args:
            key: 限制键（如 IP 地址）
            max_requests: 窗口内最大请求数
            window_seconds: 时间窗口（秒）

        Returns:
            (is_allowed, info)
        """
        import time

        current_time = time.time()

        with self._lock:
            if key not in self._buckets:
                self._buckets[key] = {
                    'tokens': max_requests - 1,
                    'last_update': current_time
                }
                return True, {
                    'remaining': max_requests - 1,
                    'reset_in': window_seconds
                }

            bucket = self._buckets[key]
            time_passed = current_time - bucket['last_update']

            # 补充令牌
            tokens_to_add = (time_passed / window_seconds) * max_requests
            bucket['tokens'] = min(max_requests, bucket['tokens'] + tokens_to_add)
            bucket['last_update'] = current_time

            if bucket['tokens'] >= 1:
                bucket['tokens'] -= 1
                return True, {
                    'remaining': int(bucket['tokens']),
                    'reset_in': int(window_seconds - time_passed % window_seconds)
                }
            else:
                return False, {
                    'remaining': 0,
                    'reset_in': int(window_seconds - time_passed % window_seconds),
                    'retry_after': int((1 - bucket['tokens']) * window_seconds / max_requests)
                }

    def reset(self, key: str):
        """重置指定键的限制"""
        with self._lock:
            if key in self._buckets:
                del self._buckets[key]


# 全局速率限制器实例
rate_limiter = RateLimiter()


def validate_and_sanitize_path(path: str) -> Tuple[bool, str, str]:
    """
    便捷函数：验证并清理路径

    Args:
        path: 原始路径

    Returns:
        (is_valid, sanitized_path, error_message)
    """
    return PathSanitizer.get_safe_path(path)


def validate_username(username: str) -> Tuple[bool, str]:
    """
    便捷函数：验证用户名

    Args:
        username: 用户名

    Returns:
        (is_valid, error_message)
    """
    return InputValidator.validate_username(username)


def escape_shell_arg(arg: str) -> str:
    """
    便捷函数：转义 shell 参数

    Args:
        arg: 原始参数

    Returns:
        转义后的参数
    """
    return CommandSanitizer.escape_shell_arg(arg)
