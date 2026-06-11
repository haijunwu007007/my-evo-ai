@echo off
chcp 65001 >nul

echo === AUTO-EVO-AI 云部署 ===
echo 目标: ubuntu@122.51.144.227
echo.

if not exist "..\.env" (
    echo .env not found, copy from .env.prod...
    copy "..\.env.prod" "..\.env"
)

set KEY=%USERPROFILE%\.ssh\Myevoaikey_

echo [1/5] SCP env file...
scp -i "%KEY%" "..\.env" ubuntu@122.51.144.227:~/my-evo-ai/.env

echo [2/5] SSH git pull...
ssh -i "%KEY%" -o StrictHostKeyChecking=no ubuntu@122.51.144.227 "cd my-evo-ai && git pull origin master"

echo [3/5] Install deps...
ssh -i "%KEY%" -o StrictHostKeyChecking=no ubuntu@122.51.144.227 "cd my-evo-ai && pip3 install -r requirements.txt --quiet 2>/dev/null || true"

echo [4/5] Restart service...
ssh -i "%KEY%" -o StrictHostKeyChecking=no ubuntu@122.51.144.227 "pkill -f 'uvicorn api_server' 2>/dev/null; sleep 2; nohup python3 -m uvicorn api_server:app --host 0.0.0.0 --port 8765 > ~/evo.log 2>&1 & sleep 5"

echo [5/5] Verify...
ssh -i "%KEY%" -o StrictHostKeyChecking=no ubuntu@122.51.144.227 "curl -s http://localhost:8765/api/v1/status"

echo.
echo === DONE ===
echo http://122.51.144.227:8765
pause
