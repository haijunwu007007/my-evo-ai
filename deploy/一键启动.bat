@echo off
chcp 65001 >nul
title AUTO-EVO-AI V0.1 一键启动
cd /d "%~dp0"

echo ============================================
echo   AUTO-EVO-AI V0.1 — 一键启动
echo   系统启动中，请稍候...
echo ============================================
echo.

:: 检测 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Python，请先安装 Python 3.9+
    pause
    exit /b
)

:: 启动 API 服务
echo [1/2] 启动 API 服务...
start /B python api_server.py > server.log 2>&1
timeout /t 5 /nobreak >nul

:: 打开浏览器
echo [2/2] 打开扫码即用页面...
start http://127.0.0.1:8765/api/qr

echo.
echo ✅ 系统已启动！
echo.
echo 📱 手机扫屏幕上的二维码即可使用！
echo    （必须连接同一WiFi）
echo.
echo ❌ 关闭：按任意键或直接关掉这个窗口
echo ============================================
pause >nul
taskkill /f /im python.exe >nul 2>&1
