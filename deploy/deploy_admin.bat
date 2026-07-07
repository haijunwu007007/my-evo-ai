@echo off
echo Uploading admin.html to server...
scp "D:\AUTO-EVO-AI-V0.1\frontend\admin.html" ubuntu@122.51.144.227:/home/ubuntu/my-evo-ai/frontend/admin.html
if %errorlevel% neq 0 (
    echo Upload failed. Make sure SSH keys are set up.
    pause
    exit /b 1
)
echo Upload OK, restarting service...
ssh ubuntu@122.51.144.227 "sudo systemctl restart evo-api"
if %errorlevel% equ 0 (
    echo Service restarted. Done!
) else (
    echo Restart may have failed, try manually.
)
pause
