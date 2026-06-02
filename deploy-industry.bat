@echo off
chcp 65001 >nul
title AUTO-EVO-AI 行业一键部署

echo ╔══════════════════════════════════════╗
echo ║   AUTO-EVO-AI  行业一键部署          ║
echo ╚══════════════════════════════════════╝
echo.

:menu
echo 请选择要部署的行业（输入编号）：
echo.
echo  1.  🏭 制造业       2.  🏪 零售业
echo  3.  🏦 金融业       4.  🏥 医疗业
echo  5.  🎓 教育业       6.  👥 人力资源
echo  7.  🏢 企业服务     8.  💻 IT科技
echo  9.  ⚖️ 法务         10. 🎬 媒体
echo 11.  👥 团队协作     12. 🛒 电子商务
echo 13.  📦 物流仓储     14. 🏠 房地产
echo 15.  🏨 酒店餐饮     16. ⚡ 能源
echo 17.  💊 医药         18. 💚 非营利
echo 19.  📋 咨询         20. 🏛️ 公共服务
echo.
set /p choice="请输入编号 (1-20): "

if "%choice%"=="1"  set industry=manufacturing
if "%choice%"=="2"  set industry=retail
if "%choice%"=="3"  set industry=finance
if "%choice%"=="4"  set industry=healthcare
if "%choice%"=="5"  set industry=education
if "%choice%"=="6"  set industry=hr
if "%choice%"=="7"  set industry=enterprise
if "%choice%"=="8"  set industry=it
if "%choice%"=="9"  set industry=legal
if "%choice%"=="10" set industry=media
if "%choice%"=="11" set industry=collaboration
if "%choice%"=="12" set industry=ecommerce
if "%choice%"=="13" set industry=logistics
if "%choice%"=="14" set industry=realestate
if "%choice%"=="15" set industry=hospitality
if "%choice%"=="16" set industry=energy
if "%choice%"=="17" set industry=pharmaceutical
if "%choice%"=="18" set industry=nonprofit
if "%choice%"=="19" set industry=consulting
if "%choice%"=="20" set industry=government

if "%industry%"=="" (
    echo 无效选择，请重新输入
    goto menu
)

echo.
echo [1/3] 开放 8765 端口...
netsh advfirewall firewall add rule name="AUTO-EVO-AI" dir=in action=allow protocol=TCP localport=8765 >nul 2>&1

echo [2/3] 启动行业服务: %industry%...
cd /d %~dp0
C:\Users\吴海军\.workbuddy\binaries\python\versions\3.13.12\python.exe -m uvicorn api_server:app --host 0.0.0.0 --port 8765
start http://localhost:8765/

echo [3/3] 完成！
echo.
echo 打开 http://localhost:8765/ 开始使用
echo.
pause
