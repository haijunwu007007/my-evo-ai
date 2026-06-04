@echo off
chcp 65001 >nul
echo === AUTO-EVO-AI 云部署 ===
echo 目标: ubuntu@122.51.144.227
echo 密钥: %USERPROFILE%\.ssh\Myevoaikey_
echo.
echo 正在连接服务器部署...
ssh -i "%USERPROFILE%\.ssh\Myevoaikey_" -o StrictHostKeyChecking=no ubuntu@122.51.144.227 "sudo apt update && sudo apt install -y python3-pip git && git clone https://github.com/haijunwu007007/my-evo-ai && cd my-evo-ai && pip install -r requirements.lock && nohup python3 -m uvicorn api_server:app --host 0.0.0.0 --port 8765 > ~/evo.log 2>&1 &"
echo.
echo === 部署完成 ===
echo 访问 http://122.51.144.227:8765
pause
