"""
全局常量配置
集中管理所有魔法数字和配置常量
"""

# ==================== 超时配置 (秒) ====================

class Timeout:
    """超时时间常量"""
    # SSH 连接
    SSH_CONNECT = 10
    SSH_BANNER = 10
    SSH_AUTH = 10

    # 命令执行
    COMMAND_DEFAULT = 30
    COMMAND_SHORT = 10
    COMMAND_MEDIUM = 15
    COMMAND_LONG = 60
    COMMAND_VERY_LONG = 120
    COMMAND_DOCKER_PULL = 300

    # 任务监控
    TASK_CHECK_INTERVAL = 60
    TASK_TIMEOUT_DEFAULT = 86400  # 24 小时

    # 其他
    PORT_FORWARD_KEEPALIVE = 60


# ==================== 缓冲区大小 ====================

class BufferSize:
    """缓冲区大小常量"""
    SSH_CHANNEL = 4096
    FILE_READ = 8192
    LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT = 10
    APP_LOG_BACKUP_COUNT = 5


# ==================== 端口范围 ====================

class PortRange:
    """端口范围常量"""
    SSH_DEFAULT = 22
    FORWARD_START = 16006
    FORWARD_MAX = 20000

    # 常用工具默认端口
    TENSORBOARD = 6006
    MLFLOW = 5000
    JUPYTER = 8888
    WANDB = 8080
    VISDOM = 8097


# ==================== 限制配置 ====================

class Limit:
    """各种限制常量"""
    # GPU 监控
    GPU_HISTORY_LENGTH = 100

    # 日志
    DOCKER_LOG_TAIL = 100

    # 速率限制
    API_RATE_LIMIT_DEFAULT = 60  # 每分钟请求数
    API_RATE_LIMIT_STRICT = 10   # 严格限制
    API_RATE_LIMIT_WINDOW = 60   # 窗口时间（秒）

    # 登录保护
    LOGIN_MAX_ATTEMPTS = 5
    LOGIN_WINDOW_SECONDS = 300  # 5 分钟
    LOGIN_BASE_LOCKOUT = 60  # 首次锁定 1 分钟
    LOGIN_MAX_LOCKOUT = 3600  # 最长锁定 1 小时
    LOGIN_LOCKOUT_MULTIPLIER = 2.0


# ==================== 路径安全 ====================

class PathSecurity:
    """路径安全配置"""
    # 禁止访问的路径前缀
    FORBIDDEN_PATHS = [
        '/etc/shadow',
        '/etc/passwd',
        '/etc/sudoers',
        '/root/.ssh',
        '/proc',
        '/sys',
    ]

    # 允许的根目录（白名单模式，可选）
    # ALLOWED_ROOTS = ['/home', '/data', '/tmp']

    # 危险的路径模式
    DANGEROUS_PATTERNS = [
        '..',  # 路径遍历
        '~',   # 用户目录展开
    ]


# ==================== 命令安全 ====================

class CommandSecurity:
    """命令安全配置"""
    # 禁止的命令模式（用于只读操作检查）
    DANGEROUS_COMMANDS = [
        'rm ', 'rm\t',
        'mv ', 'mv\t',
        'cp ', 'cp\t',
        'dd ',
        'mkfs',
        'fdisk',
        'parted',
        '> ', '>>',
        'sudo',
        'su ',
        'chmod',
        'chown',
        'kill',
        'pkill',
        'killall',
        'reboot',
        'shutdown',
        'init ',
        'systemctl',
    ]

    # Docker 操作允许列表
    DOCKER_ACTIONS = ['start', 'stop', 'restart', 'rm']


# ==================== 用户名验证 ====================

class UserValidation:
    """用户名验证规则"""
    # Linux 用户名规则：字母开头，只能包含小写字母、数字、下划线、连字符
    USERNAME_PATTERN = r'^[a-z_][a-z0-9_-]*$'
    USERNAME_MIN_LENGTH = 1
    USERNAME_MAX_LENGTH = 32

    # 系统保留用户名
    RESERVED_USERNAMES = [
        'root', 'admin', 'administrator', 'daemon', 'bin', 'sys', 'sync',
        'games', 'man', 'lp', 'mail', 'news', 'uucp', 'proxy', 'www-data',
        'backup', 'list', 'irc', 'gnats', 'nobody', 'systemd-network',
        'systemd-resolve', 'syslog', 'messagebus', 'uuidd', 'dnsmasq',
        'usbmux', 'rtkit', 'cups-pk-helper', 'dnsmasq-dhcp', 'sshd',
        'polkitd', 'colord', 'pulse', 'gdm', 'sssd', 'chrony', 'postgres',
        'mysql', 'redis', 'mongodb', 'nginx', 'apache', 'git', 'docker',
    ]


# ==================== 审计事件类型 ====================

class AuditEvent:
    """审计事件类型"""
    # 认证相关
    LOGIN_SUCCESS = 'LOGIN_SUCCESS'
    LOGIN_FAILED = 'LOGIN_FAILED'
    LOGOUT = 'LOGOUT'
    ACCOUNT_LOCKED = 'ACCOUNT_LOCKED'
    BLOCKED_LOGIN_ATTEMPT = 'BLOCKED_LOGIN_ATTEMPT'

    # 服务器操作
    SERVER_ADD = 'SERVER_ADD'
    SERVER_DELETE = 'SERVER_DELETE'
    SERVER_MODIFY = 'SERVER_MODIFY'
    SERVER_CONNECT = 'SERVER_CONNECT'

    # 用户管理
    USER_CREATE = 'USER_CREATE'
    USER_DELETE = 'USER_DELETE'
    USER_PASSWORD_CHANGE = 'USER_PASSWORD_CHANGE'

    # 文件操作
    FILE_LIST = 'FILE_LIST'
    FILE_DOWNLOAD = 'FILE_DOWNLOAD'
    FILE_DELETE = 'FILE_DELETE'
    DIRECTORY_CREATE = 'DIRECTORY_CREATE'

    # Docker 操作
    DOCKER_CONTAINER_START = 'DOCKER_CONTAINER_START'
    DOCKER_CONTAINER_STOP = 'DOCKER_CONTAINER_STOP'
    DOCKER_CONTAINER_REMOVE = 'DOCKER_CONTAINER_REMOVE'
    DOCKER_IMAGE_PULL = 'DOCKER_IMAGE_PULL'

    # 端口转发
    PORT_FORWARD_CREATE = 'PORT_FORWARD_CREATE'
    PORT_FORWARD_STOP = 'PORT_FORWARD_STOP'
    PORT_FORWARD_DELETE = 'PORT_FORWARD_DELETE'

    # 任务监控
    TASK_CREATE = 'TASK_CREATE'
    TASK_DELETE = 'TASK_DELETE'

    # 安全事件
    SECURITY_VIOLATION = 'SECURITY_VIOLATION'
    RATE_LIMIT_EXCEEDED = 'RATE_LIMIT_EXCEEDED'
    PATH_TRAVERSAL_ATTEMPT = 'PATH_TRAVERSAL_ATTEMPT'
    COMMAND_INJECTION_ATTEMPT = 'COMMAND_INJECTION_ATTEMPT'


# ==================== HTTP 状态码 ====================

class HttpStatus:
    """常用 HTTP 状态码"""
    OK = 200
    CREATED = 201
    NO_CONTENT = 204
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    CONFLICT = 409
    TOO_MANY_REQUESTS = 429
    INTERNAL_ERROR = 500
    BAD_GATEWAY = 502
    SERVICE_UNAVAILABLE = 503


# ==================== 应用信息 ====================

class AppInfo:
    """应用信息"""
    VERSION = '1.0.11'
    NAME = 'GPU Server Manager'
