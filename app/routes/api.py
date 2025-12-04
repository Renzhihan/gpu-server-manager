from flask import Blueprint, request, jsonify, session
from app.services.ssh_manager import ssh_pool
from app.services.gpu_monitor import gpu_monitor
from app.services.docker_manager import docker_manager
from app.services.user_manager import user_manager
from app.services.file_manager import file_manager
from app.services.email_service import email_service
from app.services.task_monitor import task_monitor
from app.services.port_forward import port_forward_manager
from app.services.audit_logger import audit_logger
from config.settings import Config
import json
import os

bp = Blueprint('api', __name__)


def get_current_user():
    """获取当前用户"""
    return session.get('role', 'anonymous')

# 用户偏好设置文件路径
USER_PREFS_FILE = os.path.join(os.path.dirname(__file__), '../../data/user_prefs.json')


def load_user_prefs():
    """加载用户偏好设置"""
    try:
        if os.path.exists(USER_PREFS_FILE):
            with open(USER_PREFS_FILE, 'r') as f:
                return json.load(f)
    except:
        pass
    return {}


def save_user_prefs(prefs):
    """保存用户偏好设置"""
    try:
        os.makedirs(os.path.dirname(USER_PREFS_FILE), exist_ok=True)
        with open(USER_PREFS_FILE, 'w') as f:
            json.dump(prefs, f)
    except Exception as e:
        print(f"保存用户偏好失败: {e}")


# ==================== 服务器管理 API ====================

@bp.route('/servers', methods=['GET'])
def list_servers():
    """获取服务器列表"""
    servers = ssh_pool.get_server_list()
    return jsonify({'success': True, 'servers': servers})


@bp.route('/servers/add', methods=['POST'])
def add_server():
    """添加服务器"""
    import yaml

    data = request.get_json()
    user = get_current_user()

    # 验证必填字段
    required_fields = ['name', 'host', 'port', 'username']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'success': False, 'error': f'缺少必填字段: {field}'}), 400

    # 验证密码或密钥至少提供一个
    if not data.get('password') and not data.get('key_file'):
        return jsonify({'success': False, 'error': '必须提供密码或SSH密钥文件路径'}), 400

    try:
        # 读取现有配置
        servers_config_path = Config.SERVERS_CONFIG
        with open(servers_config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f) or {}

        if 'servers' not in config:
            config['servers'] = []

        # 检查服务器名称是否已存在
        if any(s['name'] == data['name'] for s in config['servers']):
            return jsonify({'success': False, 'error': f'服务器名称 "{data["name"]}" 已存在'}), 400

        # 构建新服务器配置
        new_server = {
            'name': data['name'],
            'host': data['host'],
            'port': int(data['port']),
            'username': data['username'],
            'gpu_enabled': data.get('gpu_enabled', True),
            'description': data.get('description', '')
        }

        if data.get('password'):
            new_server['password'] = data['password']
        if data.get('key_file'):
            new_server['key_file'] = data['key_file']

        # 添加到配置
        config['servers'].append(new_server)

        # 保存配置
        with open(servers_config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

        # 重新加载服务器配置
        ssh_pool.reload_servers()

        # 记录审计日志
        audit_logger.server_add(user, data['name'])

        return jsonify({'success': True, 'message': '服务器已添加'})

    except Exception as e:
        return jsonify({'success': False, 'error': f'添加服务器失败: {str(e)}'}), 500


@bp.route('/servers/<server_name>/update', methods=['PUT'])
def update_server(server_name):
    """更新服务器配置"""
    import yaml

    data = request.get_json()

    try:
        # 读取现有配置
        servers_config_path = Config.SERVERS_CONFIG
        with open(servers_config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f) or {}

        if 'servers' not in config:
            return jsonify({'success': False, 'error': '服务器配置文件无效'}), 500

        # 查找要更新的服务器
        server_found = False
        for i, server in enumerate(config['servers']):
            if server['name'] == server_name:
                server_found = True

                # 更新字段
                if 'host' in data:
                    config['servers'][i]['host'] = data['host']
                if 'port' in data:
                    config['servers'][i]['port'] = int(data['port'])
                if 'username' in data:
                    config['servers'][i]['username'] = data['username']
                if 'password' in data:
                    config['servers'][i]['password'] = data['password']
                if 'key_file' in data:
                    config['servers'][i]['key_file'] = data['key_file']
                if 'gpu_enabled' in data:
                    config['servers'][i]['gpu_enabled'] = data['gpu_enabled']
                if 'description' in data:
                    config['servers'][i]['description'] = data['description']

                # 如果提供了新名称，则更新名称
                if 'name' in data and data['name'] != server_name:
                    # 检查新名称是否已存在
                    if any(s['name'] == data['name'] for s in config['servers'] if s['name'] != server_name):
                        return jsonify({'success': False, 'error': f'服务器名称 "{data["name"]}" 已存在'}), 400
                    config['servers'][i]['name'] = data['name']

                break

        if not server_found:
            return jsonify({'success': False, 'error': '服务器不存在'}), 404

        # 保存配置
        with open(servers_config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

        # 重新加载服务器配置
        ssh_pool.reload_servers()

        return jsonify({'success': True, 'message': '服务器配置已更新'})

    except Exception as e:
        return jsonify({'success': False, 'error': f'更新服务器失败: {str(e)}'}), 500


@bp.route('/servers/<server_name>/delete', methods=['DELETE'])
def delete_server(server_name):
    """删除服务器"""
    import yaml

    try:
        # 读取现有配置
        servers_config_path = Config.SERVERS_CONFIG
        with open(servers_config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f) or {}

        if 'servers' not in config:
            return jsonify({'success': False, 'error': '服务器配置文件无效'}), 500

        # 查找并删除服务器
        original_count = len(config['servers'])
        config['servers'] = [s for s in config['servers'] if s['name'] != server_name]

        if len(config['servers']) == original_count:
            return jsonify({'success': False, 'error': '服务器不存在'}), 404

        # 保存配置
        with open(servers_config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

        # 重新加载服务器配置
        ssh_pool.reload_servers()

        return jsonify({'success': True, 'message': '服务器已删除'})

    except Exception as e:
        return jsonify({'success': False, 'error': f'删除服务器失败: {str(e)}'}), 500


@bp.route('/servers/reload', methods=['POST'])
def reload_servers():
    """重新加载服务器配置"""
    ssh_pool.reload_servers()
    return jsonify({'success': True, 'message': '服务器配置已重新加载'})


@bp.route('/servers/<server_name>/test', methods=['GET'])
def test_connection(server_name):
    """测试服务器连接"""
    result = ssh_pool.execute_command(server_name, 'echo "test"', timeout=5)
    return jsonify(result)


@bp.route('/servers/test-all', methods=['GET'])
def test_all_connections():
    """一键测试所有服务器连接"""
    servers = ssh_pool.get_server_list()
    results = []

    for server in servers:
        server_name = server['name']
        result = ssh_pool.execute_command(server_name, 'echo "test"', timeout=10)
        results.append({
            'name': server_name,
            'host': server['host'],
            'success': result['success'],
            'error': result['stderr'] if not result['success'] else ''
        })

    return jsonify({
        'success': True,
        'results': results,
        'total': len(results),
        'connected': sum(1 for r in results if r['success']),
        'failed': sum(1 for r in results if not r['success'])
    })


@bp.route('/servers/<server_name>/execute', methods=['POST'])
def execute_command_on_server(server_name):
    """在服务器上执行命令（只读操作）"""
    data = request.get_json()
    command = data.get('command')

    if not command:
        return jsonify({'success': False, 'error': '缺少命令参数'}), 400

    # 安全检查：禁止危险命令
    dangerous_patterns = ['rm ', 'mv ', 'cp ', 'dd ', 'mkfs', 'fdisk', 'parted', '>', '>>', 'sudo', 'su ']
    for pattern in dangerous_patterns:
        if pattern in command.lower():
            return jsonify({'success': False, 'error': f'禁止执行危险命令: {pattern}'}), 403

    result = ssh_pool.execute_command(server_name, command, timeout=30)
    return jsonify(result)


@bp.route('/servers/<server_name>/info', methods=['GET'])
def get_server_info(server_name):
    """获取服务器系统信息"""
    commands = {
        'hostname': 'hostname',
        'uptime': 'uptime -p',
        'kernel': 'uname -r',
        'cpu': "grep 'model name' /proc/cpuinfo | head -1 | awk -F: '{print $2}' | sed 's/^[ \t]*//'",
        'cpu_count': "grep -c ^processor /proc/cpuinfo",
        'memory': "free -h | awk '/^Mem:/ {print $2}'",
        'memory_used': "free -h | awk '/^Mem:/ {print $3}'",
    }

    info = {}
    for key, cmd in commands.items():
        result = ssh_pool.execute_command(server_name, cmd, timeout=10)
        info[key] = result['stdout'].strip() if result['success'] else 'N/A'

    return jsonify({'success': True, 'info': info})


# ==================== GPU 监控 API ====================

@bp.route('/gpu/<server_name>', methods=['GET'])
def get_gpu_info(server_name):
    """获取 GPU 信息"""
    result = gpu_monitor.get_gpu_info(server_name)
    return jsonify(result)


@bp.route('/gpu/<server_name>/processes', methods=['GET'])
def get_gpu_processes(server_name):
    """获取 GPU 进程信息"""
    gpu_id = request.args.get('gpu_id', type=int)
    result = gpu_monitor.get_gpu_processes(server_name, gpu_id)
    return jsonify(result)


@bp.route('/gpu/<server_name>/all-processes', methods=['GET'])
def get_all_gpu_processes(server_name):
    """获取所有 GPU 上运行的详细进程信息"""
    # 使用 nvidia-smi pmon 获取进程和GPU的对应关系
    # pmon 格式: gpu pid type sm mem enc dec command
    command = "nvidia-smi pmon -c 1 2>/dev/null | grep -v '#' | awk 'NR>1 && $2 != \"-\" {print $1,$2,$8}'"
    result = ssh_pool.execute_command(server_name, command, timeout=10)

    if not result['success']:
        return jsonify({
            'success': False,
            'processes': [],
            'error': result['stderr'] or '无法获取进程信息'
        })

    processes = []
    lines = [line.strip() for line in result['stdout'].strip().split('\n') if line.strip()]

    if not lines:
        return jsonify({
            'success': True,
            'processes': [],
            'error': ''
        })

    # 获取 GPU 信息用于映射
    gpu_info_result = gpu_monitor.get_gpu_info(server_name)
    gpu_map = {gpu['id']: gpu['name'] for gpu in gpu_info_result.get('gpus', [])}

    # 收集所有PID以便批量查询
    pids = set()
    gpu_pid_map = {}

    for line in lines:
        parts = line.split()
        if len(parts) >= 3:
            try:
                gpu_id = int(parts[0])
                pid = int(parts[1])
                process_name = parts[2] if len(parts) > 2 else 'unknown'

                pids.add(pid)
                gpu_pid_map[pid] = {
                    'gpu_id': gpu_id,
                    'process_name': process_name
                }
            except (ValueError, IndexError):
                continue

    # 批量获取进程信息
    if pids:
        # 获取显存使用
        memory_cmd = "nvidia-smi --query-compute-apps=pid,used_memory --format=csv,noheader,nounits"
        memory_result = ssh_pool.execute_command(server_name, memory_cmd, timeout=10)
        memory_map = {}
        if memory_result['success']:
            for line in memory_result['stdout'].strip().split('\n'):
                if line.strip():
                    parts = line.split(',')
                    if len(parts) >= 2:
                        try:
                            pid = int(parts[0].strip())
                            mem = int(parts[1].strip())
                            memory_map[pid] = mem
                        except:
                            pass

        # 获取用户和启动时间
        pids_str = ','.join(map(str, pids))
        ps_cmd = f"ps -o pid=,user=,lstart= -p {pids_str} 2>/dev/null"
        ps_result = ssh_pool.execute_command(server_name, ps_cmd, timeout=10)

        ps_map = {}
        if ps_result['success']:
            for line in ps_result['stdout'].strip().split('\n'):
                if line.strip():
                    parts = line.strip().split(maxsplit=2)
                    if len(parts) >= 3:
                        try:
                            pid = int(parts[0])
                            user = parts[1]
                            start_time = parts[2]
                            ps_map[pid] = {'user': user, 'start_time': start_time}
                        except:
                            pass

        # 组装结果
        for pid, gpu_info in gpu_pid_map.items():
            gpu_id = gpu_info['gpu_id']
            processes.append({
                'gpu_id': gpu_id,
                'gpu_name': gpu_map.get(gpu_id, f'GPU {gpu_id}'),
                'pid': pid,
                'process_name': gpu_info['process_name'],
                'memory_used': memory_map.get(pid, 0),
                'user': ps_map.get(pid, {}).get('user', 'unknown'),
                'start_time': ps_map.get(pid, {}).get('start_time', 'unknown')
            })

    return jsonify({
        'success': True,
        'processes': processes,
        'error': ''
    })


# ==================== Docker 管理 API ====================

@bp.route('/docker/<server_name>/containers', methods=['GET'])
def list_containers(server_name):
    """列出 Docker 容器"""
    all_containers = request.args.get('all', 'false').lower() == 'true'
    result = docker_manager.list_containers(server_name, all_containers)
    return jsonify(result)


@bp.route('/docker/<server_name>/images', methods=['GET'])
def list_images(server_name):
    """列出 Docker 镜像"""
    result = docker_manager.list_images(server_name)
    return jsonify(result)


@bp.route('/docker/<server_name>/images/pull', methods=['POST'])
def pull_image(server_name):
    """拉取 Docker 镜像"""
    data = request.get_json()
    image_name = data.get('image_name')

    if not image_name:
        return jsonify({'success': False, 'error': '缺少镜像名称'}), 400

    result = docker_manager.pull_image(server_name, image_name)
    return jsonify(result)


@bp.route('/docker/<server_name>/containers/<container_id>/<action>', methods=['POST'])
def container_action(server_name, container_id, action):
    """执行容器操作 (start, stop, restart, remove)"""
    result = docker_manager.container_action(server_name, container_id, action)
    return jsonify(result)


@bp.route('/docker/<server_name>/containers/<container_id>/logs', methods=['GET'])
def get_container_logs(server_name, container_id):
    """获取容器日志"""
    tail = request.args.get('tail', 100, type=int)
    result = docker_manager.get_container_logs(server_name, container_id, tail)
    return jsonify(result)


# ==================== 用户管理 API ====================

@bp.route('/users/<server_name>', methods=['GET'])
def list_users(server_name):
    """列出用户"""
    result = user_manager.list_users(server_name)
    return jsonify(result)


@bp.route('/users/<server_name>/create', methods=['POST'])
def create_user(server_name):
    """创建用户"""
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    home_dir = data.get('home_dir')

    if not username or not password:
        return jsonify({'success': False, 'error': '缺少用户名或密码'}), 400

    result = user_manager.create_user(server_name, username, password, home_dir)
    return jsonify(result)


@bp.route('/users/<server_name>/create-advanced', methods=['POST'])
def create_user_advanced(server_name):
    """创建用户（增强版：支持工作目录和Docker容器）"""
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    work_dir = data.get('work_dir')
    docker_config = data.get('docker_config')

    if not username or not password:
        return jsonify({'success': False, 'error': '缺少用户名或密码'}), 400

    details = []

    # 1. 创建系统用户
    result = user_manager.create_user(server_name, username, password, None)
    if not result['success']:
        return jsonify(result)

    details.append(f"✅ 系统用户创建成功")

    # 2. 创建工作目录
    if work_dir:
        mkdir_cmd = f"mkdir -p '{work_dir}' && chown {username}:{username} '{work_dir}' && chmod 755 '{work_dir}'"
        mkdir_result = ssh_pool.execute_command(server_name, mkdir_cmd, timeout=30)
        if mkdir_result['success']:
            details.append(f"✅ 工作目录创建成功: {work_dir}")
        else:
            details.append(f"⚠️ 工作目录创建失败: {mkdir_result['stderr']}")

    # 3. 创建Docker容器
    if docker_config:
        image = docker_config.get('image')
        container_name = docker_config.get('container_name', username)
        ssh_port = docker_config.get('ssh_port', 9910)
        volume_mapping = docker_config.get('volume_mapping', '/:/home')

        # 获取服务器配置，判断是否为2080ti
        servers = ssh_pool.get_server_list()
        server_info = next((s for s in servers if s['name'] == server_name), None)
        is_2080ti = '2080' in server_info.get('description', '').lower() if server_info else False

        docker_cmd = 'nvidia-docker' if is_2080ti else 'docker'

        # 构建docker run命令
        docker_run_cmd = f"{docker_cmd} run -it -d -p {ssh_port}:22 -v {volume_mapping} --gpus all --ipc=host --pid=host --name={container_name} {image}"

        docker_result = ssh_pool.execute_command(server_name, docker_run_cmd, timeout=120)

        if docker_result['success'] or 'already in use' not in docker_result['stderr'].lower():
            details.append(f"✅ Docker容器创建成功")
            details.append(f"   容器名: {container_name}")
            details.append(f"   SSH端口: {ssh_port}")
            details.append(f"   镜像: {image}")
            details.append(f"   命令类型: {docker_cmd}")
        else:
            details.append(f"⚠️ Docker容器创建失败: {docker_result['stderr']}")

    return jsonify({
        'success': True,
        'message': f'用户 {username} 创建成功',
        'details': '\n'.join(details)
    })


@bp.route('/users/<server_name>/<username>/delete', methods=['DELETE'])
def delete_user(server_name, username):
    """删除用户"""
    remove_home = request.args.get('remove_home', 'true').lower() == 'true'
    result = user_manager.delete_user(server_name, username, remove_home)
    return jsonify(result)


@bp.route('/users/<server_name>/<username>/password', methods=['PUT'])
def change_password(server_name, username):
    """修改密码"""
    data = request.get_json()
    new_password = data.get('new_password')

    if not new_password:
        return jsonify({'success': False, 'error': '缺少新密码'}), 400

    result = user_manager.change_password(server_name, username, new_password)
    return jsonify(result)


# ==================== 文件管理 API ====================

@bp.route('/files/<server_name>/list', methods=['GET'])
def list_directory(server_name):
    """列出目录"""
    path = request.args.get('path', '/')
    result = file_manager.list_directory(server_name, path)
    return jsonify(result)


@bp.route('/files/<server_name>/mkdir', methods=['POST'])
def create_directory(server_name):
    """创建目录"""
    data = request.get_json()
    path = data.get('path')
    recursive = data.get('recursive', True)

    if not path:
        return jsonify({'success': False, 'error': '缺少路径'}), 400

    result = file_manager.create_directory(server_name, path, recursive)
    return jsonify(result)


@bp.route('/files/<server_name>/delete', methods=['DELETE'])
def delete_path(server_name):
    """删除文件或目录"""
    data = request.get_json()
    path = data.get('path')
    recursive = data.get('recursive', False)

    if not path:
        return jsonify({'success': False, 'error': '缺少路径'}), 400

    result = file_manager.delete_path(server_name, path, recursive)
    return jsonify(result)


@bp.route('/files/<server_name>/disk', methods=['GET'])
def get_disk_usage(server_name):
    """获取磁盘使用情况"""
    result = file_manager.get_disk_usage(server_name)
    return jsonify(result)


@bp.route('/files/<server_name>/download', methods=['GET'])
def download_file(server_name):
    """下载文件（支持文本和二进制文件）"""
    from flask import send_file, Response
    import tempfile
    import os as os_module
    import base64

    file_path = request.args.get('path')
    if not file_path:
        return jsonify({'success': False, 'error': '缺少文件路径'}), 400

    # 检查文件是否存在
    check_cmd = f"test -f '{file_path}' && echo 'exists' || echo 'not found'"
    check_result = ssh_pool.execute_command(server_name, check_cmd, timeout=10)

    if 'not found' in check_result.get('stdout', ''):
        return jsonify({'success': False, 'error': '文件不存在'}), 404

    # 使用 base64 编码传输以支持二进制文件
    command = f"base64 '{file_path}'"
    result = ssh_pool.execute_command(server_name, command, timeout=120)

    if not result['success']:
        return jsonify({'success': False, 'error': f'读取文件失败: {result["stderr"]}'}), 500

    try:
        # 解码 base64
        file_content = base64.b64decode(result['stdout'])

        # 获取文件名
        filename = os_module.path.basename(file_path)

        # 直接返回文件内容
        return Response(
            file_content,
            mimetype='application/octet-stream',
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"'
            }
        )
    except Exception as e:
        return jsonify({'success': False, 'error': f'处理文件失败: {str(e)}'}), 500


# ==================== 任务监控 API ====================

@bp.route('/tasks', methods=['GET'])
def list_tasks():
    """列出所有任务"""
    server_name = request.args.get('server_name')
    tasks = task_monitor.list_tasks(server_name)
    return jsonify({'success': True, 'tasks': tasks})


@bp.route('/tasks/create', methods=['POST'])
def create_task():
    """创建任务监控"""
    try:
        data = request.get_json()
        server_name = data.get('server_name')
        task_name = data.get('task_name')
        monitor_type = data.get('monitor_type', 'process')  # 'process' 或 'gpu_idle'
        pid = data.get('pid')
        gpu_id = data.get('gpu_id')
        notify_emails = data.get('notify_emails', [])
        check_interval = data.get('check_interval', 60)
        timeout = data.get('timeout')  # None 表示无限期

        print(f"[任务创建] 收到请求: server={server_name}, task={task_name}, type={monitor_type}, pid={pid}, gpu_id={gpu_id}, emails={notify_emails}")

        # 验证必要参数
        if not all([server_name, task_name]):
            return jsonify({'success': False, 'error': '缺少服务器和任务名称'}), 400

        if monitor_type == 'process' and not pid:
            return jsonify({'success': False, 'error': '进程监控需要提供 PID'}), 400

        if monitor_type == 'gpu_idle' and gpu_id is None:
            return jsonify({'success': False, 'error': 'GPU 空闲监控需要提供 GPU ID'}), 400

        # 验证邮件配置（如果用户提供了邮箱）
        if notify_emails and len(notify_emails) > 0:
            from app.services.email_service import EmailService
            smtp_config = EmailService.get_smtp_config()
            print(f"[任务创建] SMTP配置检查: username={smtp_config.get('smtp_username')}, has_password={bool(smtp_config.get('smtp_password'))}")
            if not smtp_config.get('smtp_username') or not smtp_config.get('smtp_password'):
                return jsonify({
                    'success': False,
                    'error': '邮件通知未配置：请先在任务监控页面配置 SMTP 邮件服务'
                }), 400

        task_id = task_monitor.add_task(
            server_name=server_name,
            task_name=task_name,
            pid=pid,
            gpu_id=gpu_id,
            notify_emails=notify_emails,
            check_interval=check_interval,
            timeout=timeout,
            monitor_type=monitor_type
        )

        print(f"[任务创建] 成功创建任务: task_id={task_id}")
        return jsonify({'success': True, 'task_id': task_id})

    except Exception as e:
        import traceback
        print(f"[任务创建错误] {str(e)}")
        print(traceback.format_exc())
        return jsonify({'success': False, 'error': f'创建任务失败: {str(e)}'}), 500


@bp.route('/tasks/<task_id>', methods=['GET'])
def get_task(task_id):
    """获取任务信息"""
    task = task_monitor.get_task(task_id)
    if task:
        return jsonify({'success': True, 'task': task})
    else:
        return jsonify({'success': False, 'error': '任务不存在'}), 404


@bp.route('/tasks/<task_id>', methods=['PUT'])
def update_task(task_id):
    """更新任务配置"""
    data = request.get_json()

    # 提取可更新的字段
    update_data = {}
    if 'notify_emails' in data:
        update_data['notify_emails'] = data['notify_emails']
    if 'timeout' in data:
        update_data['timeout'] = data['timeout']
    if 'task_name' in data:
        update_data['task_name'] = data['task_name']

    success = task_monitor.update_task(task_id, **update_data)

    if success:
        return jsonify({'success': True, 'message': '任务已更新'})
    else:
        return jsonify({'success': False, 'error': '任务不存在'}), 404


@bp.route('/tasks/<task_id>', methods=['DELETE'])
def delete_task(task_id):
    """删除任务"""
    success = task_monitor.remove_task(task_id)
    if success:
        return jsonify({'success': True, 'message': '任务已删除'})
    else:
        return jsonify({'success': False, 'error': '任务不存在'}), 404


# ==================== 邮件服务 API ====================

@bp.route('/email/status', methods=['GET'])
def email_status():
    """检查邮件配置状态"""
    from app.services.email_service import EmailService

    smtp_config = EmailService.get_smtp_config()
    is_configured = bool(smtp_config.get('smtp_username') and smtp_config.get('smtp_password'))

    return jsonify({
        'success': True,
        'configured': is_configured,
        'config': {
            'smtp_server': smtp_config.get('smtp_server', ''),
            'smtp_port': smtp_config.get('smtp_port', 587),
            'smtp_username': smtp_config.get('smtp_username', ''),
            'smtp_from': smtp_config.get('smtp_from', ''),
            'smtp_use_tls': smtp_config.get('smtp_use_tls', True),
            'smtp_use_ssl': smtp_config.get('smtp_use_ssl', False)
        } if is_configured else None
    })


@bp.route('/email/templates', methods=['GET'])
def email_templates():
    """获取常见邮箱服务商配置模板"""
    from app.services.email_service import EmailService

    return jsonify({
        'success': True,
        'templates': EmailService.SMTP_TEMPLATES
    })


@bp.route('/email/config', methods=['POST'])
def save_email_config():
    """保存邮件配置"""
    from app.services.email_service import EmailService

    data = request.get_json()

    # 验证必填字段
    required_fields = ['smtp_server', 'smtp_port', 'smtp_username', 'smtp_password']
    for field in required_fields:
        if not data.get(field):
            return jsonify({
                'success': False,
                'error': f'缺少必填字段: {field}'
            }), 400

    # 保存配置
    config = {
        'smtp_server': data['smtp_server'],
        'smtp_port': int(data['smtp_port']),
        'smtp_username': data['smtp_username'],
        'smtp_password': data['smtp_password'],
        'smtp_from': data.get('smtp_from', data['smtp_username']),
        'smtp_use_tls': data.get('smtp_use_tls', True),
        'smtp_use_ssl': data.get('smtp_use_ssl', False)
    }

    if EmailService.save_smtp_config(config):
        return jsonify({
            'success': True,
            'message': 'SMTP 配置已保存'
        })
    else:
        return jsonify({
            'success': False,
            'error': '保存配置失败'
        }), 500


@bp.route('/email/send', methods=['POST'])
def send_email():
    """发送测试邮件"""
    data = request.get_json()
    to_emails = data.get('to_emails', [])
    subject = data.get('subject', '测试邮件')
    body = data.get('body', '这是一封测试邮件')

    if not to_emails:
        return jsonify({'success': False, 'error': '缺少收件人邮箱'}), 400

    result = email_service.send_email(to_emails, subject, body)
    return jsonify(result)


# ==================== 系统 API ====================

@bp.route('/system/status', methods=['GET'])
def system_status():
    """获取系统状态"""
    return jsonify({
        'success': True,
        'status': 'running',
        'servers_count': len(ssh_pool.get_server_list()),
        'tasks_count': len(task_monitor.list_tasks())
    })


# ==================== 安全验证 API ====================

@bp.route('/auth/verify', methods=['POST'])
def verify_admin_password():
    """验证管理员密码（用于高危操作）"""
    data = request.get_json()
    password = data.get('password', '')

    if password == Config.ADMIN_PASSWORD:
        return jsonify({'success': True, 'message': '验证成功'})
    else:
        return jsonify({'success': False, 'error': '密码错误'}), 401


# ==================== 用户偏好设置 API ====================

@bp.route('/prefs', methods=['GET'])
def get_user_prefs():
    """获取用户偏好设置"""
    prefs = load_user_prefs()
    return jsonify({'success': True, 'prefs': prefs})


@bp.route('/prefs', methods=['POST'])
def update_user_prefs():
    """更新用户偏好设置"""
    data = request.get_json()
    prefs = load_user_prefs()
    prefs.update(data)
    save_user_prefs(prefs)
    return jsonify({'success': True, 'message': '偏好设置已保存'})


# ==================== 端口转发 API ====================

@bp.route('/forwards', methods=['GET'])
def list_forwards():
    """列出所有端口转发"""
    server_name = request.args.get('server_name')
    forwards = port_forward_manager.list_forwards(server_name)
    return jsonify({'success': True, 'forwards': forwards})


@bp.route('/forwards/create', methods=['POST'])
def create_forward():
    """创建端口转发"""
    data = request.get_json()

    server_name = data.get('server_name')
    name = data.get('name')
    remote_port = data.get('remote_port')
    local_port = data.get('local_port')  # 可选
    tool_type = data.get('tool_type', 'custom')

    if not all([server_name, name, remote_port]):
        return jsonify({
            'success': False,
            'error': '缺少必要参数'
        }), 400

    result = port_forward_manager.create_forward(
        server_name=server_name,
        name=name,
        remote_port=int(remote_port),
        local_port=int(local_port) if local_port else None,
        tool_type=tool_type
    )

    return jsonify(result)


@bp.route('/forwards/<forward_id>', methods=['GET'])
def get_forward(forward_id):
    """获取端口转发详情"""
    forward = port_forward_manager.get_forward(forward_id)
    if forward:
        return jsonify({'success': True, 'forward': forward})
    else:
        return jsonify({'success': False, 'error': '转发不存在'}), 404


@bp.route('/forwards/<forward_id>', methods=['DELETE'])
def delete_forward(forward_id):
    """删除端口转发"""
    success = port_forward_manager.delete_forward(forward_id)
    if success:
        return jsonify({'success': True, 'message': '端口转发已删除'})
    else:
        return jsonify({'success': False, 'error': '转发不存在'}), 404


@bp.route('/forwards/<forward_id>/stop', methods=['POST'])
def stop_forward(forward_id):
    """停止端口转发"""
    success = port_forward_manager.stop_forward(forward_id)
    if success:
        return jsonify({'success': True, 'message': '端口转发已停止'})
    else:
        return jsonify({'success': False, 'error': '转发不存在'}), 404


@bp.route('/forwards/tools', methods=['GET'])
def get_tool_suggestions():
    """获取常用工具建议"""
    tools = port_forward_manager.get_tool_suggestions()
    return jsonify({'success': True, 'tools': tools})
