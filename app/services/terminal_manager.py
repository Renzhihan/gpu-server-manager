"""
Web SSH 终端管理服务
使用 paramiko 和 WebSocket 实现浏览器中的 SSH 终端
"""
import threading
import time
from typing import Dict
from app.services.ssh_manager import ssh_manager


class TerminalSession:
    """SSH 终端会话"""

    def __init__(self, server_name: str, sid: str):
        self.server_name = server_name
        self.sid = sid
        self.channel = None
        self.client = None
        self.running = False
        self.read_thread = None

    def start(self, socketio):
        """启动终端会话"""
        try:
            # 获取 SSH 连接
            client = ssh_manager.get_client(self.server_name)
            if not client:
                return {'success': False, 'error': 'SSH 连接失败'}

            self.client = client
            # 创建交互式 shell
            self.channel = self.client.invoke_shell(term='xterm', width=120, height=30)
            self.channel.settimeout(0.1)
            self.running = True

            # 启动输出读取线程
            self.read_thread = threading.Thread(target=self._read_output, args=(socketio,))
            self.read_thread.daemon = True
            self.read_thread.start()

            return {'success': True}

        except Exception as e:
            if self.client:
                try:
                    self.client.close()
                except Exception:
                    pass
                self.client = None
            return {'success': False, 'error': str(e)}

    def _read_output(self, socketio):
        """读取终端输出并发送到客户端"""
        while self.running and self.channel:
            try:
                if self.channel.recv_ready():
                    data = self.channel.recv(4096)
                    if data:
                        # 通过 SocketIO 发送给客户端
                        socketio.emit('terminal_output',
                                    {'data': data.decode('utf-8', errors='ignore')},
                                    room=self.sid)
                else:
                    time.sleep(0.01)  # 避免过度占用 CPU
            except Exception as e:
                if self.running:
                    socketio.emit('terminal_output',
                                {'data': f'\r\n[错误] {str(e)}\r\n'},
                                room=self.sid)
                break

    def write_input(self, data: str):
        """写入用户输入到终端"""
        if self.channel and self.running:
            try:
                self.channel.send(data)
                return True
            except Exception as e:
                return False
        return False

    def resize(self, cols: int, rows: int):
        """调整终端大小"""
        if self.channel and self.running:
            try:
                self.channel.resize_pty(width=cols, height=rows)
                return True
            except Exception:
                return False
        return False

    def close(self):
        """关闭终端会话"""
        self.running = False
        if self.channel:
            try:
                self.channel.close()
            except Exception:
                pass
            self.channel = None
        if self.read_thread:
            self.read_thread.join(timeout=1)
        if self.client:
            try:
                self.client.close()
            except Exception:
                pass
            self.client = None


class TerminalManager:
    """终端会话管理器"""

    def __init__(self):
        self.sessions: Dict[str, TerminalSession] = {}
        self.lock = threading.Lock()

    def create_session(self, server_name: str, sid: str, socketio) -> Dict:
        """创建新的终端会话"""
        with self.lock:
            # 如果已存在会话，先关闭
            if sid in self.sessions:
                self.sessions[sid].close()

            # 创建新会话
            session = TerminalSession(server_name, sid)
            result = session.start(socketio)

            if result['success']:
                self.sessions[sid] = session

            return result

    def get_session(self, sid: str) -> TerminalSession:
        """获取终端会话"""
        return self.sessions.get(sid)

    def close_session(self, sid: str):
        """关闭终端会话"""
        with self.lock:
            session = self.sessions.pop(sid, None)
            if session:
                session.close()

    def close_all(self):
        """关闭所有会话"""
        with self.lock:
            for session in self.sessions.values():
                session.close()
            self.sessions.clear()


# 全局终端管理器实例
terminal_manager = TerminalManager()
