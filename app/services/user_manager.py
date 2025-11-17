from typing import Dict, List
from .ssh_manager import ssh_pool


class UserManager:
    """用户管理服务"""

    @staticmethod
    def create_user(server_name: str, username: str, password: str, home_dir: str = None) -> Dict:
        """
        创建新用户

        返回格式: {
            'success': bool,
            'message': str,
            'error': str
        }
        """
        # 构建创建用户命令
        if home_dir:
            useradd_cmd = f"useradd -m -d {home_dir} {username}"
        else:
            useradd_cmd = f"useradd -m {username}"

        # 执行创建用户命令
        result = ssh_pool.execute_command(server_name, useradd_cmd, timeout=15)

        if not result['success']:
            return {
                'success': False,
                'message': '',
                'error': result['stderr'] or '创建用户失败'
            }

        # 设置密码
        passwd_cmd = f"echo '{username}:{password}' | chpasswd"
        passwd_result = ssh_pool.execute_command(server_name, passwd_cmd, timeout=10)

        if not passwd_result['success']:
            # 密码设置失败，尝试删除已创建的用户
            ssh_pool.execute_command(server_name, f"userdel -r {username}", timeout=10)
            return {
                'success': False,
                'message': '',
                'error': '设置密码失败'
            }

        return {
            'success': True,
            'message': f'用户 {username} 创建成功',
            'error': ''
        }

    @staticmethod
    def delete_user(server_name: str, username: str, remove_home: bool = True) -> Dict:
        """
        删除用户

        返回格式: {
            'success': bool,
            'message': str,
            'error': str
        }
        """
        flag = '-r' if remove_home else ''
        command = f"userdel {flag} {username}"

        result = ssh_pool.execute_command(server_name, command, timeout=15)

        return {
            'success': result['success'],
            'message': f'用户 {username} 删除成功' if result['success'] else '',
            'error': result['stderr'] if not result['success'] else ''
        }

    @staticmethod
    def change_password(server_name: str, username: str, new_password: str) -> Dict:
        """
        修改用户密码

        返回格式: {
            'success': bool,
            'message': str,
            'error': str
        }
        """
        command = f"echo '{username}:{new_password}' | chpasswd"

        result = ssh_pool.execute_command(server_name, command, timeout=10)

        return {
            'success': result['success'],
            'message': f'用户 {username} 密码修改成功' if result['success'] else '',
            'error': result['stderr'] if not result['success'] else ''
        }

    @staticmethod
    def list_users(server_name: str) -> Dict:
        """
        列出系统用户

        返回格式: {
            'success': bool,
            'users': List[Dict],
            'error': str
        }
        """
        # 获取普通用户（UID >= 1000）
        command = "awk -F: '$3 >= 1000 && $1 != \"nobody\" {print $1,$3,$6,$7}' /etc/passwd"

        result = ssh_pool.execute_command(server_name, command, timeout=10)

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
