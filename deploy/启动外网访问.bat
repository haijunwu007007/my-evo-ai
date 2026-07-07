@echo off
chcp 65001 >nul
title AUTO-EVO-AI V0.1 — 外网启动
cd /d "%~dp0"

echo ============================================
echo   AUTO-EVO-AI V0.1 — 启动外网访问
echo ============================================
echo.

:: 检测 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Python，请先安装 Python 3.9+
    pause
    exit /b
)

:: 启动 API 服务（如果没运行）
echo [1/2] 启动 API 服务...
start /B python api_server.py > server.log 2>&1
timeout /t 5 /nobreak >nul

:: 检查/安装 cloudflared
echo [2/2] 检查 Cloudflare Tunnel...
winget list Cloudflare.cloudflared >nul 2>&1
if errorlevel 1 (
    echo 首次使用，正在安装 cloudflared（50KB，1-2秒）...
    winget install -e --id Cloudflare.cloudflared --silent >nul 2>&1
    if errorlevel 1 (
        echo [警告] 安装失败，请手动安装：
        echo   winget install Cloudflare.cloudflared
    ) else (
        echo ✅ cloudflared 安装成功
    )
)

:: 打开 Cloudflare Tunnel 窗口
echo.
echo ╔═══════════════════════════════════════════════════╗
echo ║  正在启动外网隧道...                               ║
echo ║  等待 5-30 秒出现 "https://xxxx.trycloudflare.com" ║
echo ║  复制那个地址 → 粘贴到浏览器打开的页面 → 生成二维码  ║
echo ╚═══════════════════════════════════════════════════╝
echo.
start "cloudflared" cmd /k "cloudflared tunnel --url http://127.0.0.1:8765"

:: 打开 QR 页面
echo 正在打开扫码页面...
start http://127.0.0.1:8765/api/qr

echo.
echo ✅ 操作完成！
echo.
echo 📱 等 cloudflared 窗口出现 https://xxx.trycloudflare.com 地址后，
echo    复制地址 → 粘贴到浏览器页面的输入框 → 点击"生成外网二维码"
echo.
echo ❌ 关闭：按任意键退出（隧道会同时关闭）
echo ============================================
pause >nul
