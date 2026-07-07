@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 正在推送到 GitHub...
git config http.version HTTP/1.1
git push origin master
if %errorlevel% equ 0 (
    echo ✅ 推送成功
) else (
    echo ❌ 推送失败，可能是网络问题
    echo 试试开梯子后再运行本脚本
)
pause
