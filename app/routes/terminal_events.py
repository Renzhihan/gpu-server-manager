"""
Web SSH 终端 SocketIO 事件处理
"""
from flask_socketio import emit, disconnect
from flask import session, request
from app.services.terminal_manager import terminal_manager


def register_terminal_events(socketio):
    """注册终端相关的 SocketIO 事件"""

    @socketio.on('connect')
    def handle_connect():
        """客户端连接"""
        # 检查登录状态
        if 'logged_in' not in session:
            disconnect()
            return False
        print(f"[Terminal] Client connected: {request.sid}")

    @socketio.on('disconnect')
    def handle_disconnect():
        """客户端断开连接"""
        terminal_manager.close_session(request.sid)
        print(f"[Terminal] Client disconnected: {request.sid}")

    @socketio.on('create_terminal')
    def handle_create_terminal(data):
        """创建新的终端会话"""
        server_name = data.get('server_name')

        if not server_name:
            emit('terminal_error', {'error': '未指定服务器'})
            return

        # 创建终端会话
        result = terminal_manager.create_session(server_name, request.sid, socketio)

        if result['success']:
            emit('terminal_ready', {'server_name': server_name})
        else:
            emit('terminal_error', {'error': result.get('error', '未知错误')})

    @socketio.on('terminal_input')
    def handle_terminal_input(data):
        """处理终端输入"""
        session_obj = terminal_manager.get_session(request.sid)
        if session_obj:
            input_data = data.get('data', '')
            session_obj.write_input(input_data)

    @socketio.on('terminal_resize')
    def handle_terminal_resize(data):
        """调整终端大小"""
        session_obj = terminal_manager.get_session(request.sid)
        if session_obj:
            cols = data.get('cols', 80)
            rows = data.get('rows', 24)
            session_obj.resize(cols, rows)
