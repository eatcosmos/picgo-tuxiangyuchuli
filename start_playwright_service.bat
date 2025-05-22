@echo off
chcp 65001 >nul
title Playwright Chrome Service
echo 正在启动Playwright Chrome服务...

:: 检查端口9222是否已被占用
netstat -ano | findstr :9222 >nul
if %errorlevel% equ 0 (
    echo 端口9222已被占用，可能服务已经在运行
    echo 请检查任务管理器或使用以下命令查看:
    echo netstat -ano ^| findstr :9222
    pause
    exit /b
)

:: 启动服务
start /min cmd /c "python playwright_server.py"
echo.
echo 服务已在后台启动!
echo 您可以关闭此窗口，服务将继续在后台运行。
echo.
echo 要查看服务是否正常运行，请访问: http://localhost:9222/json/version
echo 要停止服务，请在任务管理器中结束相关的Python进程
echo.
pause 