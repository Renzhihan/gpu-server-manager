@echo off
chcp 65001 >nul
echo ========================================
echo   GPU 服务器管理系统 - Windows 启动器
echo ========================================
echo.

:: 检查并创建config目录
if not exist "config" (
    echo [信息] 创建 config 目录...
    mkdir config
)

:: 首次运行时复制示例配置文件
if not exist "config\servers.yaml" (
    echo [提示] 首次运行检测到，正在创建配置文件...
    if exist "config\servers.yaml.example" (
        copy config\servers.yaml.example config\servers.yaml
        echo.
        echo ============================================
        echo   配置文件已创建: config\servers.yaml
        echo ============================================
        echo.
        echo 请按以下步骤操作：
        echo 1. 使用记事本打开 config\servers.yaml
        echo 2. 按照示例修改服务器 IP、用户名、密码
        echo 3. 保存文件后重新运行本脚本
        echo.
        pause
        exit /b 0
    ) else (
        echo [错误] 未找到 config\servers.yaml.example 示例文件！
        pause
        exit /b 1
    )
)

:: 检查.env文件
if not exist ".env" (
    if exist ".env.example" (
        echo [提示] 复制环境变量配置文件...
        copy .env.example .env
    )
)

:: 启动应用
echo [信息] 正在启动 GPU 服务器管理系统...
echo [信息] 浏览器访问: http://localhost:5000
echo [信息] 管理员密码: admin
echo.
GPU-Server-Manager.exe

pause
