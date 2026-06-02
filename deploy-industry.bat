@echo off
chcp 65001 >nul
title AUTO-EVO-AI 行业一键部署（40个行业）
setlocal enabledelayedexpansion

echo ╔══════════════════════════════════════╗
echo ║   AUTO-EVO-AI  行业一键部署          ║
echo ║   覆盖 40 个行业                     ║
echo ╚══════════════════════════════════════╝
echo.

set industry=
set /p choice="请输入编号 (1-40): "

set i=1
for %%a in (
manufacturing retail finance healthcare education hr enterprise it legal media
collaboration ecommerce logistics realestate hospitality energy pharmaceutical
nonprofit consulting government agriculture construction transportation insurance
telecom automotive aviation maritime mining food sports entertainment advertising
publishing research environmental security beauty community crossborder
) do (
    if "!i!"=="%choice%" set industry=%%a
    set /a i+=1
)

if "%industry%"=="" (
    echo 无效选择，请重新输入
    pause
    exit /b
)

echo.
echo [1/3] 开放 8765 端口...
netsh advfirewall firewall add rule name="AUTO-EVO-AI" dir=in action=allow protocol=TCP localport=8765 >nul 2>&1

echo [2/3] 启动行业服务: !industry!...
cd /d %~dp0
start http://localhost:8765/
start /B "" "C:\Users\吴海军\.workbuddy\binaries\python\versions\3.13.12\python.exe" -m uvicorn api_server:app --host 0.0.0.0 --port 8765

echo.
echo [3/3] ✅ 完成！
echo.
echo 打开浏览器访问：http://localhost:8765/
echo.
pause
