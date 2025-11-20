# -*- mode: python ; coding: utf-8 -*-
# PyInstaller 配置文件 - Windows EXE 打包

import os
import sys

block_cipher = None

# 项目根目录
root_dir = os.path.abspath('.')

# 需要包含的数据文件
import os

datas = [
    ('app/templates', 'app/templates'),
    ('config/servers.yaml.example', 'config'),  # 仅打包示例配置,用户可在外部修改
    ('config/settings.py', 'config'),
]

# 只添加存在的文件/目录
if os.path.exists('app/static'):
    datas.append(('app/static', 'app/static'))
if os.path.exists('.env.example'):
    datas.append(('.env.example', '.'))
if os.path.exists('README.md'):
    datas.append(('README.md', '.'))

# 需要包含的二进制文件
binaries = []

# 隐藏导入（PyInstaller可能检测不到的模块）
hiddenimports = [
    'flask',
    'flask_cors',
    'flask_socketio',
    'paramiko',
    'yaml',
    'dotenv',
    'psutil',
    'apscheduler',
    'engineio',
    'socketio',
    # SocketIO 异步驱动 (PyInstaller 必需)
    'engineio.async_drivers.threading',
    'engineio.async_drivers.eventlet',
    'engineio.async_threading',
    'engineio.async_eventlet',
    'app.routes.main',
    'app.routes.api',
    'app.routes.terminal_events',
    'app.services.ssh_manager',
    'app.services.gpu_monitor',
    'app.services.docker_manager',
    'app.services.user_manager',
    'app.services.file_manager',
    'app.services.email_service',
    'app.services.task_monitor',
    'app.services.port_forward',
    'app.services.terminal_manager',
    'config.settings',
]

a = Analysis(
    ['run.py'],
    pathex=[root_dir],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='GPU-Server-Manager',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # 保留控制台窗口以显示日志
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='app/static/icon.ico' if os.path.exists('app/static/icon.ico') else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='GPU-Server-Manager',
)
