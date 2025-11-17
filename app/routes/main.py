from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from functools import wraps

bp = Blueprint('main', __name__)

# 管理员密码
ADMIN_PASSWORD = "GPU-admin@renzhihan-2025"


def login_required(f):
    """登录验证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('main.login_page'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """管理员权限验证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('main.login_page'))
        if session.get('role') != 'admin':
            return render_template('403.html'), 403
        return f(*args, **kwargs)
    return decorated_function


@bp.route('/login')
def login_page():
    """登录页面"""
    return render_template('login.html')


@bp.route('/login', methods=['POST'])
def login():
    """处理登录请求"""
    data = request.get_json()
    mode = data.get('mode')

    if mode == 'admin':
        password = data.get('password')
        if password == ADMIN_PASSWORD:
            session['logged_in'] = True
            session['role'] = 'admin'
            session.permanent = True  # 使session持久化
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': '密码错误'}), 401
    elif mode == 'user':
        session['logged_in'] = True
        session['role'] = 'user'
        session.permanent = True
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': '无效的模式'}), 400


@bp.route('/logout')
def logout():
    """退出登录"""
    session.clear()
    return redirect(url_for('main.login_page'))


@bp.route('/')
@login_required
def index():
    """首页 - 仪表盘"""
    return render_template('index.html')


@bp.route('/servers')
@login_required
def servers():
    """服务器管理页面"""
    return render_template('servers.html')


@bp.route('/gpu-monitor')
@login_required
def gpu_monitor():
    """GPU 监控页面"""
    return render_template('gpu_monitor.html')


@bp.route('/docker')
@admin_required
def docker():
    """Docker 管理页面 - 仅管理员"""
    return render_template('docker.html')


@bp.route('/users')
@admin_required
def users():
    """用户管理页面 - 仅管理员"""
    return render_template('users.html')


@bp.route('/files')
@login_required
def files():
    """文件管理页面"""
    return render_template('files.html')


@bp.route('/tasks')
@login_required
def tasks():
    """任务监控页面"""
    return render_template('tasks.html')


@bp.route('/port-forward')
@login_required
def port_forward():
    """端口转发管理页面"""
    return render_template('port_forward.html')
