"""
端口转发管理服务

支持 TensorBoard, MLflow, Jupyter 等可视化工具的端口转发
使用 SSH 隧道实现，密码通过环境变量传递避免命令行暴露
"""
import threading
import time
import os
import socket
import tempfile
from typing import Dict, List, Optional
from datetime import datetime
from .ssh_manager import ssh_pool
from app.services.audit_logger import audit_logger
from config.constants import PortRange, Timeout, AuditEvent
from app.utils.logger import get_logger

logger = get_logger(__name__)


class PortForwardManager:
    """端口转发管理器"""

    # 最大端口分配重试次数
    MAX_PORT_RETRY = 5

    def __init__(self):
        self.forwards = {}  # {forward_id: forward_info}
        self.forward_counter = 0
        self.lock = threading.Lock()
        self.forward_threads = {}  # {forward_id: thread}
        self.forward_processes = {}  # {forward_id: process}
        # 已预留的端口集合（用于防止 TOCTOU 竞态）
        self._reserved_ports: set = set()

    def create_forward(
        self,
        server_name: str,
        name: str,
        remote_port: int,
        local_port: int = None,
        tool_type: str = 'custom',
        user: str = 'system'
    ) -> Dict:
        """
        创建端口转发

        参数:
            server_name: 服务器名称
            name: 转发名称
            remote_port: 远程端口
            local_port: 本地端口（None=自动分配）
            tool_type: 工具类型 (tensorboard, mlflow, jupyter, custom)
            user: 操作用户（用于审计日志）

        返回: forward_info
        """
        with self.lock:
            # 自动分配本地端口（带预留机制防止竞态）
            if local_port is None:
                local_port = self._find_and_reserve_port()
                if local_port is None:
                    return {
                        'success': False,
                        'error': '无法分配可用端口，请稍后重试'
                    }
            else:
                # 用户指定端口，检查是否可用
                if not self._is_port_available(local_port):
                    return {
                        'success': False,
                        'error': f'本地端口 {local_port} 已被占用'
                    }
                # 预留用户指定的端口
                self._reserved_ports.add(local_port)

            self.forward_counter += 1
            forward_id = f"fwd_{self.forward_counter}_{int(time.time())}"

            forward_info = {
                'forward_id': forward_id,
                'server_name': server_name,
                'name': name,
                'remote_port': remote_port,
                'local_port': local_port,
                'tool_type': tool_type,
                'status': 'starting',
                'created_at': datetime.now().isoformat(),
                'stopped_at': None,
                'error': None
            }

            self.forwards[forward_id] = forward_info

            # 启动转发线程
            thread = threading.Thread(
                target=self._forward_worker,
                args=(forward_id, user),
                daemon=True
            )
            thread.start()
            self.forward_threads[forward_id] = thread

            # 记录审计日志
            audit_logger.info(
                AuditEvent.PORT_FORWARD_CREATE,
                f'创建端口转发: {name} ({server_name}:{remote_port} -> localhost:{local_port})',
                user=user
            )

            return {
                'success': True,
                'forward': forward_info
            }

    def _is_port_available(self, port: int) -> bool:
        """检查端口是否可用（包括系统级和应用级检查）"""
        # 检查是否已被本应用预留
        if port in self._reserved_ports:
            return False

        # 检查是否已被其他转发使用
        for fwd in self.forwards.values():
            if fwd['local_port'] == port and fwd['status'] in ('running', 'starting'):
                return False

        # 检查系统级端口可用性
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(('127.0.0.1', port))
                return True
        except OSError:
            return False

    def _find_and_reserve_port(self, start_port: int = None) -> Optional[int]:
        """
        查找并预留一个可用的本地端口

        使用原子操作防止 TOCTOU 竞态条件：
        1. 在持锁的情况下查找端口
        2. 立即添加到预留集合
        3. 验证系统级可用性
        """
        if start_port is None:
            start_port = PortRange.FORWARD_START

        for _ in range(self.MAX_PORT_RETRY):
            port = start_port
            max_port = PortRange.FORWARD_MAX

            while port <= max_port:
                if self._is_port_available(port):
                    # 立即预留端口
                    self._reserved_ports.add(port)
                    return port
                port += 1

            # 如果所有端口都被占用，等待一小段时间后重试
            time.sleep(0.1)

        return None

    def _release_reserved_port(self, port: int):
        """释放预留的端口"""
        with self.lock:
            self._reserved_ports.discard(port)

    def _find_free_port(self, start_port: int = PortRange.FORWARD_START) -> int:
        """查找可用的本地端口"""
        used_ports = set(
            fwd['local_port']
            for fwd in self.forwards.values()
            if fwd['status'] == 'running'
        )

        port = start_port
        while port in used_ports:
            port += 1
            if port > PortRange.FORWARD_MAX:
                port = start_port
                break

        return port

    def _forward_worker(self, forward_id: str, user: str = 'system'):
        """端口转发工作线程"""
        import subprocess

        forward = self.forwards.get(forward_id)
        if not forward:
            return

        server_name = forward['server_name']
        remote_port = forward['remote_port']
        local_port = forward['local_port']

        try:
            # 获取服务器配置
            servers = ssh_pool.get_server_list()
            server_config = None
            for s in servers:
                if s['name'] == server_name:
                    # 获取完整配置
                    server_config = ssh_pool.servers.get(server_name)
                    break

            if not server_config:
                raise Exception(f"未找到服务器配置: {server_name}")

            # 构建 SSH 端口转发命令
            ssh_command = [
                'ssh',
                '-N',  # 不执行远程命令
                '-L', f'{local_port}:localhost:{remote_port}',  # 本地转发
                '-o', 'StrictHostKeyChecking=accept-new',  # 首次连接接受新主机密钥
                '-o', 'ServerAliveInterval=60',
                '-o', 'ServerAliveCountMax=3',
                '-o', 'BatchMode=yes',  # 非交互模式
                '-p', str(server_config.get('port', 22)),
                f"{server_config['username']}@{server_config['host']}"
            ]

            # 准备环境变量和进程参数
            env = os.environ.copy()
            process_kwargs = {
                'stdout': subprocess.PIPE,
                'stderr': subprocess.PIPE,
                'env': env
            }

            # 处理认证方式
            if 'key_file' in server_config and server_config['key_file']:
                # 使用 SSH 密钥认证（推荐）
                ssh_command.extend(['-i', server_config['key_file']])
            elif 'password' in server_config and server_config['password']:
                # 使用密码认证 - 通过 SSHPASS 环境变量传递密码
                # 这比命令行参数更安全，因为环境变量不会在 ps 输出中显示
                env['SSHPASS'] = server_config['password']
                ssh_command = ['sshpass', '-e'] + ssh_command
            else:
                raise Exception("服务器未配置认证信息（密码或密钥）")

            forward['status'] = 'running'
            logger.info(f"端口转发启动: {server_name} - localhost:{local_port} -> remote:{remote_port}")

            # 启动 SSH 进程
            process = subprocess.Popen(ssh_command, **process_kwargs)
            forward['process_pid'] = process.pid
            self.forward_processes[forward_id] = process

            # 等待进程结束或状态变化
            while forward['status'] == 'running':
                # 检查进程是否还在运行
                if process.poll() is not None:
                    # 进程已结束
                    stderr = process.stderr.read().decode('utf-8', errors='ignore')
                    if stderr and 'Warning' not in stderr:
                        raise Exception(f"SSH 隧道意外终止: {stderr}")
                    break

                time.sleep(1)

            # 停止进程
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()

        except Exception as e:
            forward['status'] = 'error'
            forward['error'] = str(e)
            logger.error(f"端口转发错误 [{forward_id}]: {e}")
            audit_logger.error(
                AuditEvent.PORT_FORWARD_CREATE,
                f'端口转发失败: {forward.get("name", forward_id)} - {str(e)}',
                user=user
            )

        finally:
            forward['stopped_at'] = datetime.now().isoformat()
            if forward['status'] == 'running':
                forward['status'] = 'stopped'

            # 清理进程引用
            if forward_id in self.forward_processes:
                del self.forward_processes[forward_id]

            # 释放预留的端口
            self._release_reserved_port(local_port)

    def stop_forward(self, forward_id: str, user: str = 'system') -> bool:
        """停止端口转发"""
        with self.lock:
            if forward_id not in self.forwards:
                return False

            forward = self.forwards[forward_id]
            if forward['status'] == 'running':
                forward['status'] = 'stopping'

                # 终止进程
                process = self.forward_processes.get(forward_id)
                if process and process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=3)
                    except:
                        process.kill()

                # 等待线程结束
                thread = self.forward_threads.get(forward_id)
                if thread and thread.is_alive():
                    time.sleep(1)

                forward['status'] = 'stopped'
                forward['stopped_at'] = datetime.now().isoformat()

                # 记录审计日志
                audit_logger.info(
                    AuditEvent.PORT_FORWARD_STOP,
                    f'停止端口转发: {forward.get("name", forward_id)}',
                    user=user
                )

            return True

    def get_forward(self, forward_id: str) -> Optional[Dict]:
        """获取转发信息"""
        with self.lock:
            return self.forwards.get(forward_id)

    def list_forwards(self, server_name: Optional[str] = None) -> List[Dict]:
        """列出所有转发"""
        with self.lock:
            if server_name:
                return [
                    fwd for fwd in self.forwards.values()
                    if fwd['server_name'] == server_name
                ]
            return list(self.forwards.values())

    def delete_forward(self, forward_id: str, user: str = 'system') -> bool:
        """删除转发记录"""
        with self.lock:
            if forward_id in self.forwards:
                forward = self.forwards[forward_id]

                # 先停止
                self.stop_forward(forward_id, user)

                # 再删除
                del self.forwards[forward_id]
                if forward_id in self.forward_threads:
                    del self.forward_threads[forward_id]

                # 记录审计日志
                audit_logger.info(
                    AuditEvent.PORT_FORWARD_DELETE,
                    f'删除端口转发: {forward.get("name", forward_id)}',
                    user=user
                )

                return True
            return False

    def get_tool_suggestions(self) -> List[Dict]:
        """获取常用工具的端口建议"""
        return [
            {
                'name': 'TensorBoard',
                'type': 'tensorboard',
                'default_port': PortRange.TENSORBOARD,
                'icon': 'graph-up',
                'description': 'TensorFlow 可视化工具'
            },
            {
                'name': 'MLflow',
                'type': 'mlflow',
                'default_port': PortRange.MLFLOW,
                'icon': 'bar-chart-line',
                'description': 'ML 实验追踪平台'
            },
            {
                'name': 'Jupyter',
                'type': 'jupyter',
                'default_port': PortRange.JUPYTER,
                'icon': 'journal-code',
                'description': 'Jupyter Notebook'
            },
            {
                'name': 'Weights & Biases',
                'type': 'wandb',
                'default_port': PortRange.WANDB,
                'icon': 'activity',
                'description': 'W&B 本地服务'
            },
            {
                'name': 'Visdom',
                'type': 'visdom',
                'default_port': PortRange.VISDOM,
                'icon': 'eye',
                'description': 'PyTorch 可视化'
            }
        ]


# 全局端口转发管理器实例
port_forward_manager = PortForwardManager()
