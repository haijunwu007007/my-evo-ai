@echo off
chcp 65001 >nul
echo 正在上传首页文件到公网服务器...
scp -i "%USERPROFILE%\.ssh\Myevoaikey_" -o StrictHostKeyChecking=no "D:\AUTO-EVO-AI-V0.1\frontend\index_deployed.html" ubuntu@122.51.144.227:/home/ubuntu/my-evo-ai/frontend/index_deployed.html
if %ERRORLEVEL% EQU 0 (
    echo ✅ 上传成功！
    echo 正在重启服务...
    ssh -i "%USERPROFILE%\.ssh\Myevoaikey_" -o StrictHostKeyChecking=no ubuntu@122.51.144.227 "pkill -f uvicorn; cd /home/ubuntu/my-evo-ai && nohup python3 -m uvicorn api_server:app --host 0.0.0.0 --port 8765 > ~/evo.log 2>&1 &"
    echo ✅ 服务已重启
) else (
    echo ❌ 上传失败，尝试用密码登录...
    scp "D:\AUTO-EVO-AI-V0.1\frontend\index_deployed.html" ubuntu@122.51.144.227:/home/ubuntu/my-evo-ai/frontend/index_deployed.html
)
pause
