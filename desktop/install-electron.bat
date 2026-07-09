@echo off
chcp 65001 >nul
echo ============================================
echo AUTO-EVO-AI 桌面客户端安装
echo ============================================
echo.
echo 步骤1: 安装 Electron 依赖...
cd /d "%~dp0"
call npm install
if %ERRORLEVEL% NEQ 0 (
    echo ❌ npm install 失败
    pause
    exit /b 1
)
echo ✅ 依赖安装完成
echo.
echo 步骤2: 启动桌面客户端...
echo 提示: 确保 API 服务已启动 (python api_server.py)
echo.
call npm start
pause
