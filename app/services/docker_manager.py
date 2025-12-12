import json
import shlex
from typing import Dict, List
from .ssh_manager import ssh_pool
from .audit_logger import audit_logger
from flask import session
from app.utils.logger import get_logger

logger = get_logger(__name__)


def get_current_user() -> str:
    """获取当前用户"""
    try:
        return session.get('role', 'system')
    except RuntimeError:
        return 'system'


class DockerManager:
    """Docker 管理服务"""

    @staticmethod
    def list_containers(server_name: str, all_containers: bool = False) -> Dict:
        """
        列出 Docker 容器

        返回格式: {
            'success': bool,
            'containers': List[Dict],
            'error': str
        }
        """
        flag = '-a' if all_containers else ''
        command = f"docker ps {flag} --format '{{{{json .}}}}'"

        result = ssh_pool.execute_command(server_name, command, timeout=15)

        if not result['success']:
            return {
                'success': False,
                'containers': [],
                'error': result['stderr'] or '无法获取容器列表'
            }

        containers = []
        for line in result['stdout'].strip().split('\n'):
            if line.strip():
                try:
                    container = json.loads(line)
                    containers.append({
                        'id': container.get('ID', ''),
                        'name': container.get('Names', ''),
                        'image': container.get('Image', ''),
                        'status': container.get('Status', ''),
                        'state': container.get('State', ''),
                        'ports': container.get('Ports', ''),
                        'created': container.get('CreatedAt', ''),
                    })
                except json.JSONDecodeError:
                    continue

        return {
            'success': True,
            'containers': containers,
            'error': ''
        }

    @staticmethod
    def list_images(server_name: str) -> Dict:
        """
        列出 Docker 镜像

        返回格式: {
            'success': bool,
            'images': List[Dict],
            'error': str
        }
        """
        command = "docker images --format '{{json .}}'"

        result = ssh_pool.execute_command(server_name, command, timeout=15)

        if not result['success']:
            return {
                'success': False,
                'images': [],
                'error': result['stderr'] or '无法获取镜像列表'
            }

        images = []
        for line in result['stdout'].strip().split('\n'):
            if line.strip():
                try:
                    image = json.loads(line)
                    images.append({
                        'id': image.get('ID', ''),
                        'repository': image.get('Repository', ''),
                        'tag': image.get('Tag', ''),
                        'size': image.get('Size', ''),
                        'created': image.get('CreatedAt', ''),
                    })
                except json.JSONDecodeError:
                    continue

        return {
            'success': True,
            'images': images,
            'error': ''
        }

    @staticmethod
    def pull_image(server_name: str, image_name: str) -> Dict:
        """
        拉取 Docker 镜像

        返回格式: {
            'success': bool,
            'message': str,
            'error': str
        }
        """
        # 安全处理镜像名称
        safe_image_name = shlex.quote(image_name)
        command = f"docker pull {safe_image_name}"

        result = ssh_pool.execute_command(server_name, command, timeout=300)

        # 记录审计日志
        user = get_current_user()
        if result['success']:
            audit_logger.docker_image_pull(user, server_name, image_name)
        else:
            audit_logger.error('DOCKER_IMAGE_PULL', f'拉取镜像失败: {image_name} on {server_name}', user=user)

        return {
            'success': result['success'],
            'message': result['stdout'] if result['success'] else '',
            'error': result['stderr'] if not result['success'] else ''
        }

    @staticmethod
    def container_action(server_name: str, container_id: str, action: str) -> Dict:
        """
        执行容器操作 (start, stop, restart, remove)

        返回格式: {
            'success': bool,
            'message': str,
            'error': str
        }
        """
        valid_actions = ['start', 'stop', 'restart', 'rm']
        if action not in valid_actions:
            return {
                'success': False,
                'message': '',
                'error': f'无效的操作: {action}'
            }

        # 安全处理容器 ID
        safe_container_id = shlex.quote(container_id)
        command = f"docker {action} {safe_container_id}"

        result = ssh_pool.execute_command(server_name, command, timeout=30)

        # 记录审计日志
        user = get_current_user()
        if result['success']:
            if action == 'start':
                audit_logger.docker_container_start(user, server_name, container_id)
            elif action == 'stop':
                audit_logger.docker_container_stop(user, server_name, container_id)
            elif action == 'rm':
                audit_logger.docker_container_remove(user, server_name, container_id)
            else:
                audit_logger.docker_operation(user, server_name, action, container_id)
        else:
            audit_logger.error('DOCKER', f'容器操作失败: {action} {container_id} on {server_name}', user=user)

        return {
            'success': result['success'],
            'message': f"容器 {container_id} {action} 成功" if result['success'] else '',
            'error': result['stderr'] if not result['success'] else ''
        }

    @staticmethod
    def get_container_logs(server_name: str, container_id: str, tail: int = 100) -> Dict:
        """
        获取容器日志

        返回格式: {
            'success': bool,
            'logs': str,
            'error': str
        }
        """
        command = f"docker logs --tail {tail} {container_id}"

        result = ssh_pool.execute_command(server_name, command, timeout=30)

        return {
            'success': result['success'],
            'logs': result['stdout'] if result['success'] else '',
            'error': result['stderr'] if not result['success'] else ''
        }


# 全局 Docker 管理实例
docker_manager = DockerManager()
