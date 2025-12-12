import re
from typing import Dict, List, Optional
from .ssh_manager import ssh_pool
from app.utils.logger import get_logger

logger = get_logger(__name__)


class GPUMonitor:
    """GPU 监控服务"""

    @staticmethod
    def parse_nvidia_smi(output: str) -> List[Dict]:
        """
        解析 nvidia-smi 输出

        返回格式: [
            {
                'id': 0,
                'name': 'NVIDIA GeForce RTX 3090',
                'temperature': 45,
                'utilization': 0,
                'memory_used': 512,
                'memory_total': 24576,
                'memory_percent': 2.1,
                'processes': []
            },
            ...
        ]
        """
        gpus = []

        try:
            # 使用 nvidia-smi --query-gpu 获取结构化数据
            # 格式: index, name, temperature.gpu, utilization.gpu, memory.used, memory.total
            lines = output.strip().split('\n')

            for line in lines:
                if not line.strip():
                    continue

                parts = [p.strip() for p in line.split(',')]
                if len(parts) >= 6:
                    try:
                        memory_used = int(parts[4].split()[0])  # 去掉 MiB
                        memory_total = int(parts[5].split()[0])
                        memory_percent = (memory_used / memory_total * 100) if memory_total > 0 else 0

                        gpu = {
                            'id': int(parts[0]),
                            'name': parts[1],
                            'temperature': int(parts[2]),
                            'utilization': int(parts[3].replace('%', '').strip()),
                            'memory_used': memory_used,
                            'memory_total': memory_total,
                            'memory_percent': round(memory_percent, 1),
                            'processes': []
                        }
                        gpus.append(gpu)
                    except (ValueError, IndexError) as e:
                        continue

        except Exception as e:
            logger.error(f"解析 nvidia-smi 输出失败: {e}")

        return gpus

    @staticmethod
    def get_gpu_info(server_name: str) -> Dict:
        """
        获取服务器 GPU 信息

        返回格式: {
            'success': bool,
            'gpus': List[Dict],
            'error': str
        }
        """
        # 执行 nvidia-smi 命令
        command = (
            "nvidia-smi "
            "--query-gpu=index,name,temperature.gpu,utilization.gpu,memory.used,memory.total "
            "--format=csv,noheader,nounits"
        )

        result = ssh_pool.execute_command(server_name, command, timeout=10)

        if not result['success']:
            return {
                'success': False,
                'gpus': [],
                'error': result['stderr'] or '无法获取 GPU 信息'
            }

        gpus = GPUMonitor.parse_nvidia_smi(result['stdout'])

        return {
            'success': True,
            'gpus': gpus,
            'error': ''
        }

    @staticmethod
    def get_gpu_processes(server_name: str, gpu_id: Optional[int] = None) -> Dict:
        """
        获取 GPU 进程信息

        返回格式: {
            'success': bool,
            'processes': List[Dict],
            'error': str
        }
        """
        # 构建命令
        if gpu_id is not None:
            command = f"nvidia-smi pmon -c 1 -i {gpu_id}"
        else:
            command = "nvidia-smi pmon -c 1"

        result = ssh_pool.execute_command(server_name, command, timeout=10)

        if not result['success']:
            return {
                'success': False,
                'processes': [],
                'error': result['stderr'] or '无法获取进程信息'
            }

        # 解析进程信息
        processes = []
        lines = result['stdout'].strip().split('\n')

        for line in lines[2:]:  # 跳过表头
            if not line.strip() or line.startswith('#'):
                continue

            parts = line.split()
            if len(parts) >= 7:
                try:
                    processes.append({
                        'gpu_id': int(parts[0]),
                        'pid': int(parts[1]),
                        'type': parts[2],
                        'sm': int(parts[3]) if parts[3] != '-' else 0,
                        'mem': int(parts[4]) if parts[4] != '-' else 0,
                        'enc': int(parts[5]) if parts[5] != '-' else 0,
                        'dec': int(parts[6]) if parts[6] != '-' else 0,
                    })
                except (ValueError, IndexError):
                    continue

        return {
            'success': True,
            'processes': processes,
            'error': ''
        }


# 全局 GPU 监控实例
gpu_monitor = GPUMonitor()
