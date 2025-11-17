import threading
import time
from typing import Dict, List, Optional
from datetime import datetime
from .ssh_manager import ssh_pool
from .email_service import email_service


class TaskMonitor:
    """任务监控服务"""

    def __init__(self):
        self.tasks = {}  # {task_id: task_info}
        self.task_counter = 0
        self.lock = threading.Lock()
        self.monitor_thread = None
        self.running = False

    def add_task(
        self,
        server_name: str,
        task_name: str,
        pid: int = None,
        notify_emails: List[str] = None,
        check_interval: int = 60,
        timeout: int = None,
        monitor_type: str = 'process',
        gpu_id: int = None
    ) -> str:
        """
        添加任务监控

        参数:
            server_name: 服务器名称
            task_name: 任务名称
            pid: 进程 ID (monitor_type='process' 时必需)
            notify_emails: 通知邮箱列表
            check_interval: 检查间隔（秒）
            timeout: 超时时间（秒，None表示无限期）
            monitor_type: 监控类型 ('process' 或 'gpu_idle')
            gpu_id: GPU ID (monitor_type='gpu_idle' 时必需)

        返回: task_id
        """
        with self.lock:
            self.task_counter += 1
            task_id = f"task_{self.task_counter}_{int(time.time())}"

            self.tasks[task_id] = {
                'task_id': task_id,
                'server_name': server_name,
                'task_name': task_name,
                'monitor_type': monitor_type,
                'pid': pid,
                'gpu_id': gpu_id,
                'notify_emails': notify_emails or [],
                'check_interval': check_interval,
                'timeout': timeout,
                'status': 'running',
                'created_at': datetime.now().isoformat(),
                'completed_at': None,
                'last_check': None,
                'gpu_was_busy': False  # 用于GPU空闲监听：记录是否检测到过非空闲状态
            }

            # 启动监控线程（如果尚未启动）
            if not self.running:
                self.start_monitoring()

            return task_id

    def remove_task(self, task_id: str) -> bool:
        """移除任务监控"""
        with self.lock:
            if task_id in self.tasks:
                del self.tasks[task_id]
                return True
            return False

    def update_task(self, task_id: str, **kwargs) -> bool:
        """更新任务配置"""
        with self.lock:
            if task_id not in self.tasks:
                return False

            task = self.tasks[task_id]
            # 只允许更新某些字段
            allowed_fields = ['notify_emails', 'timeout', 'task_name']
            for field in allowed_fields:
                if field in kwargs:
                    task[field] = kwargs[field]

            return True

    def get_task(self, task_id: str) -> Optional[Dict]:
        """获取任务信息"""
        with self.lock:
            return self.tasks.get(task_id)

    def list_tasks(self, server_name: Optional[str] = None) -> List[Dict]:
        """列出所有任务"""
        with self.lock:
            if server_name:
                return [
                    task for task in self.tasks.values()
                    if task['server_name'] == server_name
                ]
            return list(self.tasks.values())

    def _check_task_status(self, task_id: str) -> bool:
        """
        检查任务状态

        返回: True 表示任务仍在运行，False 表示任务已结束/触发
        """
        task = self.tasks.get(task_id)
        if not task:
            return False

        server_name = task['server_name']
        monitor_type = task.get('monitor_type', 'process')

        task['last_check'] = datetime.now().isoformat()

        # 进程监控模式
        if monitor_type == 'process':
            return self._check_process_task(task)
        # GPU空闲监控模式
        elif monitor_type == 'gpu_idle':
            return self._check_gpu_idle_task(task)

        return True

    def _check_process_task(self, task: Dict) -> bool:
        """检查进程监控任务"""
        server_name = task['server_name']
        pid = task['pid']

        # 检查进程是否存在
        command = f"ps -p {pid} -o pid="
        result = ssh_pool.execute_command(server_name, command, timeout=10)

        # 进程不存在，任务完成
        if not result['success'] or not result['stdout'].strip():
            task['status'] = 'completed'
            task['completed_at'] = datetime.now().isoformat()

            # 发送邮件通知
            if task['notify_emails']:
                email_service.send_task_completion_notification(
                    to_emails=task['notify_emails'],
                    task_name=task['task_name'],
                    server_name=server_name,
                    status='success',
                    details=f"进程 PID: {pid} 已结束\n完成时间: {task['completed_at']}"
                )

            return False

        # 检查是否超时（如果设置了超时）
        if task.get('timeout'):
            created_at = datetime.fromisoformat(task['created_at'])
            elapsed = (datetime.now() - created_at).total_seconds()

            if elapsed > task['timeout']:
                task['status'] = 'timeout'
                task['completed_at'] = datetime.now().isoformat()

                # 发送超时通知
                if task['notify_emails']:
                    email_service.send_task_completion_notification(
                        to_emails=task['notify_emails'],
                        task_name=task['task_name'],
                        server_name=server_name,
                        status='timeout',
                        details=f"任务 PID: {pid}\n超时时间: {task['timeout']}秒\n已运行: {int(elapsed)}秒"
                    )

                return False

        return True

    def _check_gpu_idle_task(self, task: Dict) -> bool:
        """检查GPU空闲监控任务"""
        server_name = task['server_name']
        gpu_id = task['gpu_id']

        # 检查指定GPU的显存使用情况
        # 方法1: 检查该GPU上是否有进程
        process_cmd = f"nvidia-smi pmon -c 1 -i {gpu_id} 2>/dev/null | awk 'NR>2 && $2 != \"-\" {{print $2}}'"
        process_result = ssh_pool.execute_command(server_name, process_cmd, timeout=10)

        has_processes = process_result['success'] and process_result['stdout'].strip()

        # 方法2: 检查显存使用
        memory_cmd = f"nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits -i {gpu_id}"
        memory_result = ssh_pool.execute_command(server_name, memory_cmd, timeout=10)

        memory_used = 0
        if memory_result['success']:
            try:
                memory_used = int(memory_result['stdout'].strip())
            except:
                pass

        # GPU空闲条件：无进程 且 显存使用为0MB
        is_idle = not has_processes and memory_used == 0

        # 如果GPU非空闲，标记已检测到忙碌状态
        if not is_idle:
            task['gpu_was_busy'] = True
            return True

        # 如果GPU空闲，但之前未检测到忙碌状态，继续等待
        if not task.get('gpu_was_busy', False):
            return True

        # GPU已从忙碌变为空闲，发送通知
        task['status'] = 'completed'
        task['completed_at'] = datetime.now().isoformat()

        # 发送邮件通知
        if task['notify_emails']:
            email_service.send_task_completion_notification(
                to_emails=task['notify_emails'],
                task_name=task['task_name'],
                server_name=server_name,
                status='success',
                details=f"GPU {gpu_id} 已空闲\n显存使用: {memory_used} MB\n完成时间: {task['completed_at']}"
            )

        return False

    def _monitor_loop(self):
        """监控循环"""
        while self.running:
            try:
                with self.lock:
                    task_ids = list(self.tasks.keys())

                for task_id in task_ids:
                    task = self.tasks.get(task_id)
                    if task and task['status'] == 'running':
                        if not self._check_task_status(task_id):
                            print(f"任务 {task_id} 已完成")

                time.sleep(5)  # 每 5 秒检查一次

            except Exception as e:
                print(f"任务监控循环错误: {e}")
                time.sleep(5)

    def start_monitoring(self):
        """启动任务监控"""
        if not self.running:
            self.running = True
            self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.monitor_thread.start()
            print("任务监控已启动")

    def stop_monitoring(self):
        """停止任务监控"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
            print("任务监控已停止")


# 全局任务监控实例
task_monitor = TaskMonitor()
