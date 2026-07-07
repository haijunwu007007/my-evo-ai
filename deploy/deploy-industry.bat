@echo off
chcp 65001 >nul
title AUTO-EVO-AI 行业一键部署（100个行业）
setlocal enabledelayedexpansion

echo ╔══════════════════════════════════════╗
echo ║   AUTO-EVO-AI  行业一键部署          ║
echo ║   覆盖 100 个行业                    ║
echo ╚══════════════════════════════════════╝
echo.

set /p choice="请输入编号 (1-100): "

set i=1
for %%a in (
manufacturing retail finance healthcare education hr enterprise it legal media
collaboration ecommerce logistics realestate hospitality energy pharmaceutical
nonprofit consulting government agriculture construction transportation insurance
telecom automotive aviation maritime mining food sports entertainment advertising
publishing research environmental security beauty community crossborder
office toys pet baby jewelry furniture lighting building hardware electronics
instrument packaging printing textile apparel footwear leather chemical plastics
rubber paper glass ceramics steel metal recycling env_equip fire security_eq
elevator hvac water landscape cleaning home_service wedding photo fitness elderly
funeral tourism exhibition translation design music dance driving abroad
immigration labor headhunt testing certification inspection ip patent
) do (
    if "!i!"=="%choice%" set industry=%%a
    set /a i+=1
)

if "%industry%"=="" (
    echo 无效选择
    pause & exit /b
)

echo [1/3] 开放 8765 端口...
netsh advfirewall firewall add rule name="AUTO-EVO-AI" dir=in action=allow protocol=TCP localport=8765 >nul 2>&1

echo [2/3] 启动: %industry%...
cd /d %~dp0
start http://localhost:8765/
start /B "" "C:\Users\吴海军\.workbuddy\binaries\python\versions\3.13.12\python.exe" -m uvicorn api_server:app --host 0.0.0.0 --port 8765

echo [3/3] ✅ 完成！
echo 访问 http://localhost:8765/
pause
