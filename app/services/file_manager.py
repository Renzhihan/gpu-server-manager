import base64
import json
from typing import Dict, List
from .ssh_manager import ssh_pool


class FileManager:
    """文件管理服务"""

    @staticmethod
    def list_directory(server_name: str, path: str = '/') -> Dict:
        """
        列出目录内容

        返回格式: {
            'success': bool,
            'files': List[Dict],
            'error': str
        }
        """
        remote_path = path or '/'
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

        result = ssh_pool.execute_command(server_name, command, timeout=20)

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

        return {
            'success': True,
            'files': payload.get('files', []),
            'error': ''
        }

    @staticmethod
    def create_directory(server_name: str, path: str, recursive: bool = True) -> Dict:
        """
        创建目录

        返回格式: {
            'success': bool,
            'message': str,
            'error': str
        }
        """
        flag = '-p' if recursive else ''
        command = f"mkdir {flag} '{path}'"

        result = ssh_pool.execute_command(server_name, command, timeout=10)

        return {
            'success': result['success'],
            'message': f'目录 {path} 创建成功' if result['success'] else '',
            'error': result['stderr'] if not result['success'] else ''
        }

    @staticmethod
    def delete_path(server_name: str, path: str, recursive: bool = False) -> Dict:
        """
        删除文件或目录

        返回格式: {
            'success': bool,
            'message': str,
            'error': str
        }
        """
        flag = '-rf' if recursive else '-f'
        command = f"rm {flag} '{path}'"

        result = ssh_pool.execute_command(server_name, command, timeout=30)

        return {
            'success': result['success'],
            'message': f'{path} 删除成功' if result['success'] else '',
            'error': result['stderr'] if not result['success'] else ''
        }

    @staticmethod
    def get_disk_usage(server_name: str) -> Dict:
        """
        获取磁盘使用情况

        返回格式: {
            'success': bool,
            'disks': List[Dict],
            'error': str
        }
        """
        command = "df -h | grep -v 'tmpfs\\|loop'"

        result = ssh_pool.execute_command(server_name, command, timeout=10)

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


# 全局文件管理实例
file_manager = FileManager()
