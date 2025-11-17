@echo off
chcp 65001 >nul
echo ========================================
echo   GPU 服务器管理系统 - Windows 启动器
echo ========================================
echo.

:: 检查是否存在配置文件
if not exist "config\servers.yaml" (
    echo [错误] 未找到 config\servers.yaml 配置文件！
    echo 请先配置服务器信息。
    pause
    exit /b 1
)

if not exist ".env" (
    echo [提示] 未找到 .env 文件，复制默认配置...
    copy .env.example .env
    echo 请编辑 .env 文件配置邮件服务等信息。
)

:: 启动应用
echo [信息] 正在启动 GPU 服务器管理系统...
echo.
GPU-Server-Manager.exe

pause
