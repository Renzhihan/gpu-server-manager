"""
登录保护服务
实现速率限制和临时账户锁定，防止暴力破解攻击
"""
import time
import threading
from datetime import datetime
from typing import Dict, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class LoginAttempt:
    """登录尝试记录"""
    count: int = 0
    first_attempt: float = 0.0
    last_attempt: float = 0.0
    locked_until: float = 0.0


@dataclass
class LoginProtectionConfig:
    """登录保护配置"""
    # 失败尝试阈值
    max_attempts: int = 5
    # 时间窗口（秒）- 在此时间内达到 max_attempts 次失败则锁定
    window_seconds: int = 300  # 5分钟
    # 锁定时间（秒）- 递增锁定
    base_lockout_seconds: int = 60  # 基础锁定1分钟
    max_lockout_seconds: int = 3600  # 最长锁定1小时
    # 锁定时间递增倍数
    lockout_multiplier: float = 2.0
    # 成功登录后是否重置计数
    reset_on_success: bool = True
    # 清理过期记录的间隔（秒）
    cleanup_interval: int = 3600


class LoginProtectionService:
    """
    登录保护服务

    功能：
    - 基于 IP 的速率限制
    - 递增锁定时间（首次1分钟，后续翻倍）
    - 自动清理过期记录
    - 线程安全
    """

    def __init__(self, config: Optional[LoginProtectionConfig] = None):
        self.config = config or LoginProtectionConfig()
        self._attempts: Dict[str, LoginAttempt] = defaultdict(LoginAttempt)
        self._lock = threading.Lock()
        self._lockout_counts: Dict[str, int] = defaultdict(int)  # 记录锁定次数用于递增

        # 启动定期清理线程
        self._cleanup_thread = threading.Thread(target=self._periodic_cleanup, daemon=True)
        self._cleanup_thread.start()

    def _periodic_cleanup(self):
        """定期清理过期的记录"""
        while True:
            time.sleep(self.config.cleanup_interval)
            self._cleanup_expired()

    def _cleanup_expired(self):
        """清理过期的尝试记录"""
        current_time = time.time()
        with self._lock:
            expired_keys = []
            for ip, attempt in self._attempts.items():
                # 如果记录超过窗口时间且未锁定，则可以清理
                if (current_time - attempt.last_attempt > self.config.window_seconds
                    and attempt.locked_until < current_time):
                    expired_keys.append(ip)

            for key in expired_keys:
                del self._attempts[key]
                if key in self._lockout_counts:
                    del self._lockout_counts[key]

    def check_rate_limit(self, ip: str) -> Tuple[bool, Optional[dict]]:
        """
        检查是否允许登录尝试

        Args:
            ip: 客户端 IP 地址

        Returns:
            (allowed, info):
            - allowed: 是否允许尝试
            - info: 如果被拒绝，包含锁定信息；否则为 None
        """
        current_time = time.time()

        with self._lock:
            attempt = self._attempts[ip]

            # 检查是否处于锁定状态
            if attempt.locked_until > current_time:
                remaining = int(attempt.locked_until - current_time)
                return False, {
                    'locked': True,
                    'remaining_seconds': remaining,
                    'remaining_formatted': self._format_time(remaining),
                    'reason': 'account_locked',
                    'attempts': attempt.count,
                    'message': f'账户已被临时锁定，请在 {self._format_time(remaining)} 后重试'
                }

            # 检查是否在时间窗口内
            if attempt.first_attempt > 0 and current_time - attempt.first_attempt > self.config.window_seconds:
                # 窗口过期，重置计数
                attempt.count = 0
                attempt.first_attempt = 0

            return True, None

    def record_failed_attempt(self, ip: str) -> dict:
        """
        记录登录失败尝试

        Args:
            ip: 客户端 IP 地址

        Returns:
            包含当前状态的字典
        """
        current_time = time.time()

        with self._lock:
            attempt = self._attempts[ip]

            # 更新尝试记录
            if attempt.first_attempt == 0 or current_time - attempt.first_attempt > self.config.window_seconds:
                # 新窗口开始
                attempt.first_attempt = current_time
                attempt.count = 1
            else:
                attempt.count += 1

            attempt.last_attempt = current_time

            # 检查是否需要锁定
            remaining_attempts = self.config.max_attempts - attempt.count

            if attempt.count >= self.config.max_attempts:
                # 计算锁定时间（递增）
                self._lockout_counts[ip] += 1
                lockout_time = min(
                    self.config.base_lockout_seconds * (self.config.lockout_multiplier ** (self._lockout_counts[ip] - 1)),
                    self.config.max_lockout_seconds
                )
                attempt.locked_until = current_time + lockout_time
                attempt.count = 0  # 重置计数

                return {
                    'locked': True,
                    'lockout_seconds': int(lockout_time),
                    'lockout_formatted': self._format_time(int(lockout_time)),
                    'lockout_count': self._lockout_counts[ip],
                    'message': f'登录失败次数过多，账户已被锁定 {self._format_time(int(lockout_time))}'
                }

            return {
                'locked': False,
                'attempts': attempt.count,
                'remaining_attempts': remaining_attempts,
                'window_remaining': int(self.config.window_seconds - (current_time - attempt.first_attempt)),
                'message': f'密码错误，还剩 {remaining_attempts} 次尝试机会'
            }

    def record_successful_login(self, ip: str):
        """
        记录登录成功

        Args:
            ip: 客户端 IP 地址
        """
        if self.config.reset_on_success:
            with self._lock:
                if ip in self._attempts:
                    del self._attempts[ip]
                if ip in self._lockout_counts:
                    del self._lockout_counts[ip]

    def get_status(self, ip: str) -> dict:
        """
        获取指定 IP 的状态

        Args:
            ip: 客户端 IP 地址

        Returns:
            状态信息字典
        """
        current_time = time.time()

        with self._lock:
            if ip not in self._attempts:
                return {
                    'locked': False,
                    'attempts': 0,
                    'remaining_attempts': self.config.max_attempts,
                    'message': '正常'
                }

            attempt = self._attempts[ip]

            if attempt.locked_until > current_time:
                remaining = int(attempt.locked_until - current_time)
                return {
                    'locked': True,
                    'remaining_seconds': remaining,
                    'remaining_formatted': self._format_time(remaining),
                    'lockout_count': self._lockout_counts.get(ip, 0),
                    'message': f'已锁定，{self._format_time(remaining)} 后解锁'
                }

            # 检查窗口是否过期
            if current_time - attempt.first_attempt > self.config.window_seconds:
                return {
                    'locked': False,
                    'attempts': 0,
                    'remaining_attempts': self.config.max_attempts,
                    'message': '正常'
                }

            remaining_attempts = self.config.max_attempts - attempt.count
            return {
                'locked': False,
                'attempts': attempt.count,
                'remaining_attempts': remaining_attempts,
                'window_remaining': int(self.config.window_seconds - (current_time - attempt.first_attempt)),
                'message': f'已尝试 {attempt.count} 次，还剩 {remaining_attempts} 次机会'
            }

    def unlock(self, ip: str) -> bool:
        """
        手动解锁指定 IP（管理员功能）

        Args:
            ip: 客户端 IP 地址

        Returns:
            是否成功解锁
        """
        with self._lock:
            if ip in self._attempts:
                del self._attempts[ip]
            if ip in self._lockout_counts:
                del self._lockout_counts[ip]
            return True

    def get_all_locked(self) -> list:
        """
        获取所有被锁定的 IP（管理员功能）

        Returns:
            被锁定的 IP 列表及其状态
        """
        current_time = time.time()
        locked_list = []

        with self._lock:
            for ip, attempt in self._attempts.items():
                if attempt.locked_until > current_time:
                    locked_list.append({
                        'ip': ip,
                        'remaining_seconds': int(attempt.locked_until - current_time),
                        'remaining_formatted': self._format_time(int(attempt.locked_until - current_time)),
                        'lockout_count': self._lockout_counts.get(ip, 0),
                        'locked_at': datetime.fromtimestamp(
                            attempt.locked_until - self.config.base_lockout_seconds *
                            (self.config.lockout_multiplier ** (self._lockout_counts.get(ip, 1) - 1))
                        ).strftime('%Y-%m-%d %H:%M:%S')
                    })

        return locked_list

    @staticmethod
    def _format_time(seconds: int) -> str:
        """格式化时间显示"""
        if seconds < 60:
            return f'{seconds} 秒'
        elif seconds < 3600:
            minutes = seconds // 60
            secs = seconds % 60
            if secs > 0:
                return f'{minutes} 分 {secs} 秒'
            return f'{minutes} 分钟'
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            if minutes > 0:
                return f'{hours} 小时 {minutes} 分钟'
            return f'{hours} 小时'


# 全局登录保护实例
login_protection = LoginProtectionService()
