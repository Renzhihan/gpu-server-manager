import paramiko
import yaml
import threading
from typing import Dict, Optional, List
from config.settings import Config


class SSHConnectionPool:
    """SSH 连接池管理器"""

    def __init__(self, config_file: str):
        self.config_file = config_file
        self.servers = {}
        self.connections = {}
        self.lock = threading.Lock()
        self._load_servers()

    def _load_servers(self):
        """加载服务器配置"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                self.servers = {
                    server['name']: server
                    for server in config.get('servers', [])
                }
        except Exception as e:
            print(f"加载服务器配置失败: {e}")
            self.servers = {}

    def reload_servers(self):
        """重新加载服务器配置"""
        with self.lock:
            self._load_servers()

    def get_server_list(self) -> List[Dict]:
        """获取服务器列表"""
        return [
            {
                'name': name,
                'host': config.get('host'),
                'port': config.get('port', 22),
                'gpu_enabled': config.get('gpu_enabled', False),
                'description': config.get('description', ''),
            }
            for name, config in self.servers.items()
        ]

    def _create_connection(self, server_name: str) -> Optional[paramiko.SSHClient]:
        """创建 SSH 连接"""
        if server_name not in self.servers:
            raise ValueError(f"服务器 {server_name} 不存在")

        server_config = self.servers[server_name]
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            connect_params = {
                'hostname': server_config['host'],
                'port': server_config.get('port', 22),
                'username': server_config['username'],
                'timeout': Config.SSH_TIMEOUT,
                'banner_timeout': Config.SSH_BANNER_TIMEOUT,
                'auth_timeout': Config.SSH_AUTH_TIMEOUT,
            }

            # 优先使用密钥，否则使用密码
            if 'key_file' in server_config:
                connect_params['key_filename'] = server_config['key_file']
            elif 'password' in server_config:
                connect_params['password'] = server_config['password']
            else:
                raise ValueError(f"服务器 {server_name} 缺少认证信息")

            client.connect(**connect_params)
            return client

        except Exception as e:
            print(f"连接服务器 {server_name} 失败: {e}")
            client.close()
            return None

    def get_connection(self, server_name: str) -> Optional[paramiko.SSHClient]:
        """获取 SSH 连接（如果不存在则创建）"""
        with self.lock:
            # 检查现有连接是否可用
            if server_name in self.connections:
                client = self.connections[server_name]
                try:
                    # 测试连接是否存活
                    client.exec_command('echo test', timeout=5)
                    return client
                except:
                    # 连接失效，移除并重新创建
                    try:
                        client.close()
                    except:
                        pass
                    del self.connections[server_name]

            # 创建新连接
            client = self._create_connection(server_name)
            if client:
                self.connections[server_name] = client
            return client

    def get_client(self, server_name: str) -> Optional[paramiko.SSHClient]:
        """
        创建独立的 SSH 客户端（不加入连接池）
        主要用于需要独占会话的场景，例如 Web 终端
        """
        return self._create_connection(server_name)

    def execute_command(self, server_name: str, command: str, timeout: int = 30) -> Dict:
        """
        在指定服务器上执行命令

        返回格式: {
            'success': bool,
            'stdout': str,
            'stderr': str,
            'exit_code': int
        }
        """
        client = self.get_connection(server_name)
        if not client:
            return {
                'success': False,
                'stdout': '',
                'stderr': '无法连接到服务器',
                'exit_code': -1
            }

        try:
            stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
            exit_code = stdout.channel.recv_exit_status()

            return {
                'success': exit_code == 0,
                'stdout': stdout.read().decode('utf-8', errors='ignore'),
                'stderr': stderr.read().decode('utf-8', errors='ignore'),
                'exit_code': exit_code
            }
        except Exception as e:
            return {
                'success': False,
                'stdout': '',
                'stderr': str(e),
                'exit_code': -1
            }

    def close_all(self):
        """关闭所有连接"""
        with self.lock:
            for client in self.connections.values():
                try:
                    client.close()
                except:
                    pass
            self.connections.clear()


# 全局 SSH 连接池实例
ssh_pool = SSHConnectionPool(Config.SERVERS_CONFIG)
