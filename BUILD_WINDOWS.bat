@echo off
chcp 65001 >nul
echo ========================================
echo   GPU 服务器管理系统 - Windows 打包脚本
echo ========================================
echo.

:: 检查Python
echo [1/6] 检查Python环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到Python！
    echo 请先安装Python 3.11或更高版本
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)
python --version
echo.

:: 安装依赖
echo [2/6] 安装项目依赖...
pip install -r requirements.txt
if errorlevel 1 (
    echo [错误] 依赖安装失败！
    pause
    exit /b 1
)
echo.

:: 安装PyInstaller
echo [3/6] 安装PyInstaller...
pip install pyinstaller
if errorlevel 1 (
    echo [错误] PyInstaller安装失败！
    pause
    exit /b 1
)
echo.

:: 清理旧的打包文件
echo [4/6] 清理旧的打包文件...
if exist "dist" rmdir /s /q dist
if exist "build" rmdir /s /q build
echo.

:: 执行打包
echo [5/6] 开始打包（这可能需要几分钟）...
pyinstaller build_windows.spec
if errorlevel 1 (
    echo [错误] 打包失败！
    pause
    exit /b 1
)
echo.

:: 复制额外文件
echo [6/6] 复制额外文件...
copy START_WINDOWS.bat dist\GPU-Server-Manager\
copy README.md dist\GPU-Server-Manager\
copy WINDOWS_BUILD.md dist\GPU-Server-Manager\
copy AUTH_AND_WINDOWS.md dist\GPU-Server-Manager\
copy .env.example dist\GPU-Server-Manager\
echo.

:: 创建压缩包（如果有PowerShell）
echo [可选] 创建压缩包...
powershell -Command "Compress-Archive -Path 'dist\GPU-Server-Manager\*' -DestinationPath 'GPU-Server-Manager-Windows.zip' -Force"
if errorlevel 1 (
    echo [提示] 压缩包创建失败，但exe已生成
)
echo.

echo ========================================
echo   打包完成！
echo ========================================
echo.
echo 打包文件位置: dist\GPU-Server-Manager\
echo 主程序: dist\GPU-Server-Manager\GPU-Server-Manager.exe
echo.
if exist "GPU-Server-Manager-Windows.zip" (
    echo 压缩包: GPU-Server-Manager-Windows.zip
    echo.
)
echo 可以将整个 dist\GPU-Server-Manager 文件夹
echo 复制到其他Windows电脑使用（无需Python环境）
echo.
pause
