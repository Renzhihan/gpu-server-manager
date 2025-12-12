from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from functools import wraps
import os
from app.services.audit_logger import audit_logger
from app.services.login_protection import login_protection
from app.utils.logger import get_logger

logger = get_logger(__name__)

bp = Blueprint('main', __name__)

# 管理员密码 - 从环境变量读取，默认值要求用户修改
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'PLEASE_CHANGE_THIS_PASSWORD_IN_ENV_FILE')

# 安全警告：如果使用默认密码，在日志和控制台显示警告
if ADMIN_PASSWORD == 'PLEASE_CHANGE_THIS_PASSWORD_IN_ENV_FILE':
    logger.warning("="*60)
    logger.warning("安全警告：检测到使用默认管理员密码！")
    logger.warning("请立即修改 .env 文件中的 ADMIN_PASSWORD")
    logger.warning("安全建议：建议使用至少16位的强密码")
    logger.warning("="*60)


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
    # 获取客户端 IP 的锁定状态
    client_ip = _get_client_ip()
    lock_status = login_protection.get_status(client_ip)
    return render_template('login.html', lock_status=lock_status)


def _get_client_ip():
    """获取客户端真实 IP（考虑代理）"""
    forwarded_for = request.headers.get('X-Forwarded-For')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    return request.remote_addr or 'unknown'


@bp.route('/api/login-status')
def login_status():
    """获取当前 IP 的登录状态（用于前端轮询）"""
    client_ip = _get_client_ip()
    status = login_protection.get_status(client_ip)
    return jsonify(status)


@bp.route('/login', methods=['POST'])
def login():
    """处理登录请求"""
    data = request.get_json()
    mode = data.get('mode')
    client_ip = _get_client_ip()

    # 检查速率限制（仅对管理员模式生效）
    if mode == 'admin':
        allowed, lock_info = login_protection.check_rate_limit(client_ip)
        if not allowed:
            # 记录被锁定的尝试
            audit_logger.security_event(
                'BLOCKED_LOGIN_ATTEMPT',
                f'IP {client_ip} 在锁定期间尝试登录',
                severity='warning'
            )
            return jsonify({
                'success': False,
                'error': lock_info['message'],
                'locked': True,
                'remaining_seconds': lock_info.get('remaining_seconds', 0),
                'remaining_formatted': lock_info.get('remaining_formatted', '')
            }), 429  # Too Many Requests

    if mode == 'admin':
        password = data.get('password')
        if password == ADMIN_PASSWORD:
            # 登录成功，清除失败记录
            login_protection.record_successful_login(client_ip)
            session['logged_in'] = True
            session['role'] = 'admin'
            session.permanent = True  # 使session持久化
            # 记录审计日志
            audit_logger.login_success('admin', role='admin')
            return jsonify({'success': True})
        else:
            # 记录失败尝试
            result = login_protection.record_failed_attempt(client_ip)
            audit_logger.login_failed('admin', reason='密码错误')

            # 如果触发锁定，记录安全事件
            if result.get('locked'):
                audit_logger.security_event(
                    'ACCOUNT_LOCKED',
                    f'IP {client_ip} 因多次登录失败被锁定 {result.get("lockout_formatted", "")}',
                    severity='warning'
                )

            return jsonify({
                'success': False,
                'error': result['message'],
                'locked': result.get('locked', False),
                'remaining_attempts': result.get('remaining_attempts'),
                'lockout_seconds': result.get('lockout_seconds'),
                'lockout_formatted': result.get('lockout_formatted')
            }), 401
    elif mode == 'user':
        session['logged_in'] = True
        session['role'] = 'user'
        session.permanent = True
        # 记录审计日志
        audit_logger.login_success('user', role='user')
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': '无效的模式'}), 400


@bp.route('/logout')
def logout():
    """退出登录"""
    # 记录退出日志
    user = session.get('role', 'anonymous')
    audit_logger.logout(user)
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


@bp.route('/terminal')
@login_required
def terminal():
    """Web SSH 终端页面"""
    return render_template('terminal.html')
