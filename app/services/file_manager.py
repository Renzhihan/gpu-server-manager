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
        # 使用 ls -lh 获取详细信息
        command = f"ls -lhA --time-style=long-iso '{path}' 2>&1"

        result = ssh_pool.execute_command(server_name, command, timeout=15)

        if not result['success']:
            return {
                'success': False,
                'files': [],
                'error': result['stderr'] or '无法访问目录'
            }

        files = []
        lines = result['stdout'].strip().split('\n')

        for line in lines:
            # 跳过空行和"total xxx"行
            if not line.strip() or line.startswith('total '):
                continue

            # 解析ls -lh输出
            parts = line.split(maxsplit=8)
            if len(parts) >= 9:
                files.append({
                    'permissions': parts[0],
                    'links': parts[1],
                    'owner': parts[2],
                    'group': parts[3],
                    'size': parts[4],
                    'date': f"{parts[5]} {parts[6]}",
                    'name': parts[8],
                    'is_dir': parts[0].startswith('d'),
                    'is_link': parts[0].startswith('l')
                })

        return {
            'success': True,
            'files': files,
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
