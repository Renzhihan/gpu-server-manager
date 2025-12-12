import paramiko
import yaml
import threading
import weakref
import time
import os
from typing import Dict, Optional, List
from config.settings import Config
from app.utils.logger import get_logger

logger = get_logger(__name__)


class SSHConnectionPool:
    """SSH 连接池管理器

    服务器配置管理说明：
    - 配置存储在 config/servers.yaml 文件中
    - 支持通过网页端添加/编辑/删除服务器
    - 支持 YAML 格式的批量导入
    - 不再支持直接编辑本地 YAML 文件后热加载
    """

    def __init__(self, config_file: str):
        self.config_file = config_file
        self.servers: Dict[str, dict] = {}
        self.connections: Dict[str, paramiko.SSHClient] = {}
        self.lock = threading.Lock()
        # 使用弱引用追踪独立客户端，避免内存泄漏
        self._standalone_clients: weakref.WeakSet = weakref.WeakSet()
        # 清理线程
        self._cleanup_thread: Optional[threading.Thread] = None
        self._cleanup_running = False
        self._load_servers()
        # 启动定期清理线程
        self._start_cleanup_thread()

    def _load_servers(self):
        """加载服务器配置"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f) or {}
                    self.servers = {
                        server['name']: server
                        for server in config.get('servers', [])
                    }
                    logger.info(f"成功加载 {len(self.servers)} 个服务器配置")
            else:
                logger.warning(f"配置文件不存在: {self.config_file}，将创建空配置")
                self.servers = {}
                self._save_servers()
        except Exception as e:
            logger.error(f"加载服务器配置失败: {e}")
            self.servers = {}

    def _save_servers(self):
        """保存服务器配置到文件"""
        try:
            # 确保目录存在
            config_dir = os.path.dirname(self.config_file)
            if config_dir and not os.path.exists(config_dir):
                os.makedirs(config_dir, exist_ok=True)

            config = {'servers': list(self.servers.values())}
            with open(self.config_file, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
            logger.info(f"服务器配置已保存: {len(self.servers)} 个服务器")
            return True
        except Exception as e:
            logger.error(f"保存服务器配置失败: {e}")
            return False

    def reload_servers(self):
        """重新加载服务器配置（从内存中的配置刷新连接池）"""
        with self.lock:
            # 关闭所有现有连接
            for client in self.connections.values():
                try:
                    client.close()
                except Exception:
                    pass
            self.connections.clear()
            logger.info("服务器连接池已刷新")

    def add_server(self, server_config: dict) -> Dict:
        """添加服务器

        Args:
            server_config: 服务器配置字典，包含 name, host, port, username, password/key_file 等

        Returns:
            {'success': bool, 'message': str, 'error': str}
        """
        with self.lock:
            name = server_config.get('name')
            if not name:
                return {'success': False, 'error': '服务器名称不能为空'}

            if name in self.servers:
                return {'success': False, 'error': f'服务器名称 "{name}" 已存在'}

            # 验证必填字段
            required_fields = ['host', 'username']
            for field in required_fields:
                if not server_config.get(field):
                    return {'success': False, 'error': f'缺少必填字段: {field}'}

            # 验证认证方式
            if not server_config.get('password') and not server_config.get('key_file'):
                return {'success': False, 'error': '必须提供密码或SSH密钥文件路径'}

            # 设置默认值
            server_config.setdefault('port', 22)
            server_config.setdefault('gpu_enabled', True)
            server_config.setdefault('description', '')

            self.servers[name] = server_config

            if self._save_servers():
                return {'success': True, 'message': f'服务器 "{name}" 已添加'}
            else:
                del self.servers[name]
                return {'success': False, 'error': '保存配置失败'}

    def update_server(self, original_name: str, server_config: dict) -> Dict:
        """更新服务器配置

        Args:
            original_name: 原服务器名称
            server_config: 新的服务器配置

        Returns:
            {'success': bool, 'message': str, 'error': str}
        """
        with self.lock:
            if original_name not in self.servers:
                return {'success': False, 'error': f'服务器 "{original_name}" 不存在'}

            new_name = server_config.get('name', original_name)

            # 检查新名称是否冲突
            if new_name != original_name and new_name in self.servers:
                return {'success': False, 'error': f'服务器名称 "{new_name}" 已存在'}

            # 保留旧配置中未更新的字段
            old_config = self.servers[original_name].copy()
            for key, value in server_config.items():
                if value is not None and value != '':
                    old_config[key] = value

            # 如果名称变更，需要删除旧的
            if new_name != original_name:
                del self.servers[original_name]
                # 关闭旧连接
                if original_name in self.connections:
                    try:
                        self.connections[original_name].close()
                    except Exception:
                        pass
                    del self.connections[original_name]

            old_config['name'] = new_name
            self.servers[new_name] = old_config

            if self._save_servers():
                return {'success': True, 'message': f'服务器配置已更新'}
            else:
                return {'success': False, 'error': '保存配置失败'}

    def delete_server(self, server_name: str) -> Dict:
        """删除服务器

        Args:
            server_name: 服务器名称

        Returns:
            {'success': bool, 'message': str, 'error': str}
        """
        with self.lock:
            if server_name not in self.servers:
                return {'success': False, 'error': f'服务器 "{server_name}" 不存在'}

            # 关闭连接
            if server_name in self.connections:
                try:
                    self.connections[server_name].close()
                except Exception:
                    pass
                del self.connections[server_name]

            del self.servers[server_name]

            if self._save_servers():
                return {'success': True, 'message': f'服务器 "{server_name}" 已删除'}
            else:
                return {'success': False, 'error': '保存配置失败'}

    def import_servers(self, yaml_content: str, mode: str = 'merge') -> Dict:
        """从 YAML 内容导入服务器配置

        Args:
            yaml_content: YAML 格式的配置内容
            mode: 导入模式
                - 'merge': 合并，同名服务器跳过
                - 'overwrite': 同名服务器覆盖
                - 'replace': 完全替换现有配置

        Returns:
            {'success': bool, 'message': str, 'imported': int, 'skipped': int, 'errors': list}
        """
        with self.lock:
            try:
                config = yaml.safe_load(yaml_content)
                if not config or 'servers' not in config:
                    return {'success': False, 'error': 'YAML 格式无效，需要包含 servers 列表'}

                servers_to_import = config.get('servers', [])
                if not isinstance(servers_to_import, list):
                    return {'success': False, 'error': 'servers 必须是列表'}

                imported = 0
                skipped = 0
                errors = []

                if mode == 'replace':
                    # 关闭所有连接
                    for client in self.connections.values():
                        try:
                            client.close()
                        except Exception:
                            pass
                    self.connections.clear()
                    self.servers.clear()

                for server in servers_to_import:
                    name = server.get('name')
                    if not name:
                        errors.append('跳过无名称的服务器配置')
                        continue

                    # 验证必填字段
                    if not server.get('host') or not server.get('username'):
                        errors.append(f'服务器 "{name}" 缺少必填字段 (host/username)')
                        continue

                    if not server.get('password') and not server.get('key_file'):
                        errors.append(f'服务器 "{name}" 缺少认证信息 (password/key_file)')
                        continue

                    # 设置默认值
                    server.setdefault('port', 22)
                    server.setdefault('gpu_enabled', True)
                    server.setdefault('description', '')

                    if name in self.servers:
                        if mode == 'overwrite' or mode == 'replace':
                            self.servers[name] = server
                            imported += 1
                        else:
                            skipped += 1
                    else:
                        self.servers[name] = server
                        imported += 1

                if self._save_servers():
                    return {
                        'success': True,
                        'message': f'导入完成: {imported} 个成功, {skipped} 个跳过',
                        'imported': imported,
                        'skipped': skipped,
                        'errors': errors
                    }
                else:
                    return {'success': False, 'error': '保存配置失败'}

            except yaml.YAMLError as e:
                return {'success': False, 'error': f'YAML 解析错误: {str(e)}'}
            except Exception as e:
                return {'success': False, 'error': f'导入失败: {str(e)}'}

    def export_servers(self, include_credentials: bool = False) -> Dict:
        """导出服务器配置为 YAML

        Args:
            include_credentials: 是否包含密码（默认不包含）

        Returns:
            {'success': bool, 'yaml': str, 'count': int}
        """
        with self.lock:
            servers_list = []
            for server in self.servers.values():
                server_copy = server.copy()
                if not include_credentials:
                    # 移除敏感信息
                    server_copy.pop('password', None)
                    # 保留 key_file 路径（不是敏感信息）
                servers_list.append(server_copy)

            config = {'servers': servers_list}
            yaml_content = yaml.dump(config, allow_unicode=True, default_flow_style=False, sort_keys=False)

            return {
                'success': True,
                'yaml': yaml_content,
                'count': len(servers_list)
            }

    def get_server_list(self) -> List[Dict]:
        """获取服务器列表（不包含敏感信息）"""
        return [
            {
                'name': name,
                'host': config.get('host'),
                'port': config.get('port', 22),
                'username': config.get('username'),
                'gpu_enabled': config.get('gpu_enabled', False),
                'description': config.get('description', ''),
                'has_password': bool(config.get('password')),
                'key_file': config.get('key_file', ''),
            }
            for name, config in self.servers.items()
        ]

    def _create_connection(self, server_name: str) -> Optional[paramiko.SSHClient]:
        """创建 SSH 连接"""
        if server_name not in self.servers:
            raise ValueError(f"服务器 {server_name} 不存在")

        server_config = self.servers[server_name]
        client = paramiko.SSHClient()

        # SSH 主机密钥策略：
        # - WarningPolicy: 记录未知主机但允许连接（推荐用于内网环境）
        # - AutoAddPolicy: 自动接受未知主机（便捷但不安全，原默认行为）
        # - RejectPolicy: 拒绝未知主机（最安全但需要预先配置 known_hosts）
        # 使用 WarningPolicy 在安全性和易用性之间取得平衡
        client.set_missing_host_key_policy(paramiko.WarningPolicy())

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
            logger.error(f"连接服务器 {server_name} 失败: {e}")
            client.close()
            return None

    def get_connection(self, server_name: str) -> Optional[paramiko.SSHClient]:
        """获取 SSH 连接（如果不存在则创建）"""
        with self.lock:
            # 检查现有连接是否可用
            if server_name in self.connections:
                client = self.connections[server_name]
                try:
                    # 测试连接是否存活（正确读取响应避免缓冲区堆积）
                    transport = client.get_transport()
                    if transport is None or not transport.is_active():
                        raise Exception("Transport not active")
                    # 执行简单命令并读取响应
                    stdin, stdout, stderr = client.exec_command('echo test', timeout=5)
                    # 等待命令完成并读取输出（防止缓冲区堆积）
                    stdout.channel.recv_exit_status()
                    stdout.read()
                    stderr.read()
                    return client
                except Exception as e:
                    # 连接失效，移除并重新创建
                    logger.debug(f"SSH 连接健康检查失败 [{server_name}]: {e}")
                    try:
                        client.close()
                    except Exception:
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

        注意：调用者负责关闭连接。系统会定期清理僵死连接作为安全网。
        """
        client = self._create_connection(server_name)
        if client:
            # 使用弱引用追踪，便于定期清理检查
            self._standalone_clients.add(client)
        return client

    def _start_cleanup_thread(self):
        """启动定期清理线程"""
        if self._cleanup_thread is not None and self._cleanup_thread.is_alive():
            return

        self._cleanup_running = True
        self._cleanup_thread = threading.Thread(
            target=self._cleanup_loop,
            daemon=True,
            name="SSHConnectionCleanup"
        )
        self._cleanup_thread.start()
        logger.debug("SSH 连接清理线程已启动")

    def _cleanup_loop(self):
        """定期清理失效连接"""
        cleanup_interval = 300  # 每 5 分钟检查一次

        while self._cleanup_running:
            try:
                time.sleep(cleanup_interval)
                self._cleanup_stale_connections()
            except Exception as e:
                logger.error(f"SSH 连接清理错误: {e}")

    def _cleanup_stale_connections(self):
        """清理失效的连接"""
        cleaned_pool = 0
        cleaned_standalone = 0

        with self.lock:
            # 清理连接池中的失效连接
            stale_servers = []
            for server_name, client in self.connections.items():
                try:
                    transport = client.get_transport()
                    if transport is None or not transport.is_active():
                        stale_servers.append(server_name)
                except Exception:
                    stale_servers.append(server_name)

            for server_name in stale_servers:
                try:
                    self.connections[server_name].close()
                except Exception:
                    pass
                del self.connections[server_name]
                cleaned_pool += 1

            # 弱引用集合会自动清理已被垃圾回收的对象
            # 这里检查仍存活但已断开的连接
            for client in list(self._standalone_clients):
                try:
                    transport = client.get_transport()
                    if transport is None or not transport.is_active():
                        try:
                            client.close()
                        except Exception:
                            pass
                        cleaned_standalone += 1
                except Exception:
                    pass

        if cleaned_pool > 0 or cleaned_standalone > 0:
            logger.info(f"SSH 连接清理完成: 连接池 {cleaned_pool} 个, 独立连接 {cleaned_standalone} 个")

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
        # 停止清理线程
        self._cleanup_running = False

        with self.lock:
            # 关闭连接池中的连接
            for server_name, client in self.connections.items():
                try:
                    transport = client.get_transport()
                    if transport:
                        transport.close()
                    client.close()
                except Exception as e:
                    logger.warning(f"关闭SSH连接时出错 [{server_name}]: {e}")
            self.connections.clear()

            # 关闭独立客户端（尽力而为，因为是弱引用）
            for client in list(self._standalone_clients):
                try:
                    transport = client.get_transport()
                    if transport:
                        transport.close()
                    client.close()
                except Exception:
                    pass

        logger.info("所有 SSH 连接已关闭")


# 全局 SSH 连接池实例
ssh_pool = SSHConnectionPool(Config.SERVERS_CONFIG)
# 向后兼容：提供 ssh_manager 别名
ssh_manager = ssh_pool
