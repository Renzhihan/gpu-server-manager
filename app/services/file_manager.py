"""
文件管理服务
提供远程文件系统的浏览、创建、删除等功能
"""
import base64
import json
from typing import Dict, List
from .ssh_manager import ssh_pool
from app.utils.security import (
    CommandSanitizer, validate_and_sanitize_path, escape_shell_arg
)
from app.services.audit_logger import audit_logger
from config.constants import Timeout, AuditEvent


class FileManager:
    """文件管理服务"""

    # 禁止删除的危险路径
    DANGEROUS_DELETE_PATHS = [
        '/', '/home', '/root', '/etc', '/var', '/usr',
        '/bin', '/sbin', '/lib', '/lib64', '/boot', '/dev',
        '/proc', '/sys', '/run', '/tmp', '/opt'
    ]

    @staticmethod
    def list_directory(
        server_name: str,
        path: str = '/',
        user: str = 'system'
    ) -> Dict:
        """
        列出目录内容

        Args:
            server_name: 服务器名称
            path: 目录路径
            user: 操作用户（用于审计日志）

        Returns:
            {
                'success': bool,
                'files': List[Dict],
                'error': str
            }
        """
        # 验证并清理路径
        is_valid, safe_path, error = validate_and_sanitize_path(path)
        if not is_valid:
            audit_logger.warning(
                AuditEvent.PATH_TRAVERSAL_ATTEMPT,
                f'路径验证失败: {path} - {error}',
                user=user
            )
            return {
                'success': False,
                'files': [],
                'error': error
            }

        remote_path = safe_path or '/'

        # 使用 Python 脚本在远端执行，路径通过 JSON 安全传递
        script = f"""
import os
import json
import stat
import sys
from datetime import datetime

try:
    import pwd
except ImportError:
    pwd = None

try:
    import grp
except ImportError:
    grp = None

path = {json.dumps(remote_path)}
if not path:
    path = '/'

def resolve_owner(uid):
    if pwd:
        try:
            return pwd.getpwuid(uid).pw_name
        except KeyError:
            return str(uid)
    return str(uid)

def resolve_group(gid):
    if grp:
        try:
            return grp.getgrgid(gid).gr_name
        except KeyError:
            return str(gid)
    return str(gid)

def format_size(num):
    units = ['B', 'K', 'M', 'G', 'T', 'P']
    value = float(num)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            if unit == 'B':
                return f"{{int(value)}}B"
            return f"{{value:.1f}}{{unit}}"
        value /= 1024
    return f"{{value:.1f}}P"

entries = []
try:
    with os.scandir(path) as iterator:
        for entry in iterator:
            try:
                stat_result = entry.stat(follow_symlinks=False)
            except Exception:
                continue
            info = {{
                'permissions': stat.filemode(stat_result.st_mode),
                'links': stat_result.st_nlink,
                'owner': resolve_owner(stat_result.st_uid),
                'group': resolve_group(stat_result.st_gid),
                'size': format_size(stat_result.st_size),
                'date': datetime.fromtimestamp(stat_result.st_mtime).strftime('%Y-%m-%d %H:%M'),
                'name': entry.name,
                'is_dir': entry.is_dir(follow_symlinks=False),
                'is_link': entry.is_symlink()
            }}
            entries.append(info)
except Exception as exc:
    print(json.dumps({{'success': False, 'files': [], 'error': str(exc)}} , ensure_ascii=False))
    sys.exit(0)

entries.sort(key=lambda item: (not item['is_dir'], item['name'].lower()))
print(json.dumps({{'success': True, 'files': entries, 'error': ''}}, ensure_ascii=False))
sys.exit(0)
"""

        encoded_script = base64.b64encode(script.encode('utf-8')).decode('ascii')
        command = (
            "python3 -c \"import base64, sys; "
            f"exec(compile(base64.b64decode('{encoded_script}'), '<remote_ls>', 'exec'))\""
        )

        result = ssh_pool.execute_command(
            server_name,
            command,
            timeout=Timeout.COMMAND_MEDIUM
        )

        if not result['success']:
            return {
                'success': False,
                'files': [],
                'error': result['stderr'] or '无法访问目录'
            }

        output = result['stdout'].strip()
        if not output:
            return {
                'success': False,
                'files': [],
                'error': '远端未返回目录信息'
            }

        try:
            payload = json.loads(output)
        except json.JSONDecodeError:
            return {
                'success': False,
                'files': [],
                'error': '解析目录信息失败'
            }

        if not payload.get('success'):
            return {
                'success': False,
                'files': [],
                'error': payload.get('error', '无法访问目录')
            }

        # 记录审计日志
        audit_logger.info(
            AuditEvent.FILE_LIST,
            f'列出目录: {safe_path} on {server_name}',
            user=user
        )

        return {
            'success': True,
            'files': payload.get('files', []),
            'error': ''
        }

    @staticmethod
    def create_directory(
        server_name: str,
        path: str,
        recursive: bool = True,
        user: str = 'system'
    ) -> Dict:
        """
        创建目录

        Args:
            server_name: 服务器名称
            path: 目录路径
            recursive: 是否递归创建
            user: 操作用户（用于审计日志）

        Returns:
            {
                'success': bool,
                'message': str,
                'error': str
            }
        """
        # 验证并清理路径
        is_valid, safe_path, error = validate_and_sanitize_path(path)
        if not is_valid:
            audit_logger.warning(
                AuditEvent.PATH_TRAVERSAL_ATTEMPT,
                f'创建目录路径验证失败: {path} - {error}',
                user=user
            )
            return {
                'success': False,
                'message': '',
                'error': error
            }

        # 构建安全命令
        command = CommandSanitizer.build_mkdir_command(safe_path, recursive)

        result = ssh_pool.execute_command(
            server_name,
            command,
            timeout=Timeout.COMMAND_SHORT
        )

        if result['success']:
            audit_logger.info(
                AuditEvent.DIRECTORY_CREATE,
                f'创建目录: {safe_path} on {server_name}',
                user=user
            )

        return {
            'success': result['success'],
            'message': f'目录 {safe_path} 创建成功' if result['success'] else '',
            'error': result['stderr'] if not result['success'] else ''
        }

    @staticmethod
    def delete_path(
        server_name: str,
        path: str,
        recursive: bool = False,
        user: str = 'system'
    ) -> Dict:
        """
        删除文件或目录

        Args:
            server_name: 服务器名称
            path: 文件/目录路径
            recursive: 是否递归删除
            user: 操作用户（用于审计日志）

        Returns:
            {
                'success': bool,
                'message': str,
                'error': str
            }
        """
        # 验证并清理路径
        is_valid, safe_path, error = validate_and_sanitize_path(path)
        if not is_valid:
            audit_logger.warning(
                AuditEvent.PATH_TRAVERSAL_ATTEMPT,
                f'删除路径验证失败: {path} - {error}',
                user=user
            )
            return {
                'success': False,
                'message': '',
                'error': error
            }

        # 额外的安全检查：禁止删除危险路径
        if safe_path in FileManager.DANGEROUS_DELETE_PATHS:
            audit_logger.warning(
                AuditEvent.SECURITY_VIOLATION,
                f'尝试删除危险路径: {safe_path}',
                user=user
            )
            return {
                'success': False,
                'message': '',
                'error': '禁止删除系统关键目录'
            }

        # 检查是否是危险路径的直接子目录（一级子目录）
        for dangerous in FileManager.DANGEROUS_DELETE_PATHS:
            if dangerous != '/' and safe_path.startswith(dangerous + '/'):
                # 检查是否只有一级深度
                remaining = safe_path[len(dangerous) + 1:]
                if '/' not in remaining and remaining:
                    # 这是危险路径的直接子目录，需要警告但允许
                    audit_logger.warning(
                        AuditEvent.FILE_DELETE,
                        f'删除系统目录下的项目: {safe_path} (需谨慎)',
                        user=user
                    )

        # 构建安全命令
        command = CommandSanitizer.build_rm_command(safe_path, recursive)

        result = ssh_pool.execute_command(
            server_name,
            command,
            timeout=Timeout.COMMAND_MEDIUM
        )

        if result['success']:
            audit_logger.info(
                AuditEvent.FILE_DELETE,
                f'删除路径: {safe_path} on {server_name}',
                user=user
            )

        return {
            'success': result['success'],
            'message': f'{safe_path} 删除成功' if result['success'] else '',
            'error': result['stderr'] if not result['success'] else ''
        }

    @staticmethod
    def get_disk_usage(server_name: str) -> Dict:
        """
        获取磁盘使用情况

        Args:
            server_name: 服务器名称

        Returns:
            {
                'success': bool,
                'disks': List[Dict],
                'error': str
            }
        """
        command = "df -h | grep -v 'tmpfs\\|loop'"

        result = ssh_pool.execute_command(
            server_name,
            command,
            timeout=Timeout.COMMAND_SHORT
        )

        if not result['success']:
            return {
                'success': False,
                'disks': [],
                'error': result['stderr'] or '获取磁盘使用情况失败'
            }

        disks = []
        lines = result['stdout'].strip().split('\n')

        for line in lines[1:]:  # 跳过表头
            if not line.strip():
                continue

            parts = line.split()
            if len(parts) >= 6:
                disks.append({
                    'filesystem': parts[0],
                    'size': parts[1],
                    'used': parts[2],
                    'available': parts[3],
                    'use_percent': parts[4],
                    'mounted': parts[5]
                })

        return {
            'success': True,
            'disks': disks,
            'error': ''
        }

    @staticmethod
    def download_file(
        server_name: str,
        file_path: str,
        user: str = 'system'
    ) -> Dict:
        """
        下载文件内容（base64 编码）

        Args:
            server_name: 服务器名称
            file_path: 文件路径
            user: 操作用户（用于审计日志）

        Returns:
            {
                'success': bool,
                'content': bytes,  # base64 解码后的内容
                'filename': str,
                'error': str
            }
        """
        # 验证并清理路径
        is_valid, safe_path, error = validate_and_sanitize_path(file_path)
        if not is_valid:
            audit_logger.warning(
                AuditEvent.PATH_TRAVERSAL_ATTEMPT,
                f'下载文件路径验证失败: {file_path} - {error}',
                user=user
            )
            return {
                'success': False,
                'content': b'',
                'filename': '',
                'error': error
            }

        # 检查文件是否存在
        check_cmd = f"test -f {escape_shell_arg(safe_path)} && echo 'exists' || echo 'not found'"
        check_result = ssh_pool.execute_command(
            server_name,
            check_cmd,
            timeout=Timeout.COMMAND_SHORT
        )

        if 'not found' in check_result.get('stdout', ''):
            return {
                'success': False,
                'content': b'',
                'filename': '',
                'error': '文件不存在'
            }

        # 使用 base64 编码传输
        command = f"base64 {escape_shell_arg(safe_path)}"
        result = ssh_pool.execute_command(
            server_name,
            command,
            timeout=Timeout.COMMAND_VERY_LONG
        )

        if not result['success']:
            return {
                'success': False,
                'content': b'',
                'filename': '',
                'error': f'读取文件失败: {result["stderr"]}'
            }

        try:
            content = base64.b64decode(result['stdout'])
            import os
            filename = os.path.basename(safe_path)

            # 记录审计日志
            audit_logger.info(
                AuditEvent.FILE_DOWNLOAD,
                f'下载文件: {safe_path} on {server_name}',
                user=user
            )

            return {
                'success': True,
                'content': content,
                'filename': filename,
                'error': ''
            }
        except Exception as e:
            return {
                'success': False,
                'content': b'',
                'filename': '',
                'error': f'处理文件失败: {str(e)}'
            }


# 全局文件管理实例
file_manager = FileManager()
