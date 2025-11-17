"""
端口转发管理服务

支持 TensorBoard, MLflow, Jupyter 等可视化工具的端口转发
"""
import threading
import time
from typing import Dict, List, Optional
from datetime import datetime
from .ssh_manager import ssh_pool


class PortForwardManager:
    """端口转发管理器"""

    def __init__(self):
        self.forwards = {}  # {forward_id: forward_info}
        self.forward_counter = 0
        self.lock = threading.Lock()
        self.forward_threads = {}  # {forward_id: thread}

    def create_forward(
        self,
        server_name: str,
        name: str,
        remote_port: int,
        local_port: int = None,
        tool_type: str = 'custom'
    ) -> Dict:
        """
        创建端口转发

        参数:
            server_name: 服务器名称
            name: 转发名称
            remote_port: 远程端口
            local_port: 本地端口（None=自动分配）
            tool_type: 工具类型 (tensorboard, mlflow, jupyter, custom)

        返回: forward_info
        """
        with self.lock:
            # 自动分配本地端口
            if local_port is None:
                local_port = self._find_free_port()

            # 检查端口冲突
            for fwd in self.forwards.values():
                if fwd['local_port'] == local_port and fwd['status'] == 'running':
                    return {
                        'success': False,
                        'error': f'本地端口 {local_port} 已被占用'
                    }

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
                args=(forward_id,),
                daemon=True
            )
            thread.start()
            self.forward_threads[forward_id] = thread

            return {
                'success': True,
                'forward': forward_info
            }

    def _find_free_port(self, start_port: int = 16006) -> int:
        """查找可用的本地端口"""
        used_ports = set(
            fwd['local_port']
            for fwd in self.forwards.values()
            if fwd['status'] == 'running'
        )

        port = start_port
        while port in used_ports:
            port += 1
            if port > 20000:  # 防止无限循环
                port = start_port
                break

        return port

    def _forward_worker(self, forward_id: str):
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
                    server_config = s
                    break

            if not server_config:
                raise Exception(f"未找到服务器配置: {server_name}")

            # 构建 SSH 端口转发命令
            # ssh -N -L local_port:localhost:remote_port user@host -p port
            ssh_command = [
                'ssh',
                '-N',  # 不执行远程命令
                '-L', f'{local_port}:localhost:{remote_port}',  # 本地转发
                '-o', 'StrictHostKeyChecking=no',
                '-o', 'UserKnownHostsFile=/dev/null',
                '-o', 'ServerAliveInterval=60',
                '-p', str(server_config['port']),
                f"{server_config['username']}@{server_config['host']}"
            ]

            # 使用 sshpass 传递密码（如果有）
            if 'password' in server_config and server_config['password']:
                ssh_command = ['sshpass', '-p', server_config['password']] + ssh_command

            forward['status'] = 'running'
            print(f"✅ 端口转发启动: {server_name} - localhost:{local_port} -> remote:{remote_port}")

            # 启动 SSH 进程
            process = subprocess.Popen(
                ssh_command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            forward['process_pid'] = process.pid

            # 等待进程结束或状态变化
            while forward['status'] == 'running':
                # 检查进程是否还在运行
                if process.poll() is not None:
                    # 进程已结束
                    stderr = process.stderr.read().decode('utf-8', errors='ignore')
                    if stderr:
                        raise Exception(f"SSH 隧道意外终止: {stderr}")
                    break

                time.sleep(1)

            # 停止进程
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=5)

        except Exception as e:
            forward['status'] = 'error'
            forward['error'] = str(e)
            print(f"❌ 端口转发错误 [{forward_id}]: {e}")

        finally:
            forward['stopped_at'] = datetime.now().isoformat()
            if forward['status'] == 'running':
                forward['status'] = 'stopped'

    def stop_forward(self, forward_id: str) -> bool:
        """停止端口转发"""
        with self.lock:
            if forward_id not in self.forwards:
                return False

            forward = self.forwards[forward_id]
            if forward['status'] == 'running':
                forward['status'] = 'stopping'

                # 等待线程结束
                thread = self.forward_threads.get(forward_id)
                if thread and thread.is_alive():
                    # 给线程1秒时间自行结束
                    time.sleep(1)

                forward['status'] = 'stopped'
                forward['stopped_at'] = datetime.now().isoformat()

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

    def delete_forward(self, forward_id: str) -> bool:
        """删除转发记录"""
        with self.lock:
            if forward_id in self.forwards:
                # 先停止
                self.stop_forward(forward_id)
                # 再删除
                del self.forwards[forward_id]
                if forward_id in self.forward_threads:
                    del self.forward_threads[forward_id]
                return True
            return False

    def get_tool_suggestions(self) -> List[Dict]:
        """获取常用工具的端口建议"""
        return [
            {
                'name': 'TensorBoard',
                'type': 'tensorboard',
                'default_port': 6006,
                'icon': 'graph-up',
                'description': 'TensorFlow 可视化工具'
            },
            {
                'name': 'MLflow',
                'type': 'mlflow',
                'default_port': 5000,
                'icon': 'bar-chart-line',
                'description': 'ML 实验追踪平台'
            },
            {
                'name': 'Jupyter',
                'type': 'jupyter',
                'default_port': 8888,
                'icon': 'journal-code',
                'description': 'Jupyter Notebook'
            },
            {
                'name': 'Weights & Biases',
                'type': 'wandb',
                'default_port': 8080,
                'icon': 'activity',
                'description': 'W&B 本地服务'
            },
            {
                'name': 'Visdom',
                'type': 'visdom',
                'default_port': 8097,
                'icon': 'eye',
                'description': 'PyTorch 可视化'
            }
        ]


# 全局端口转发管理器实例
port_forward_manager = PortForwardManager()
