@echo off
chcp 65001 >nul
echo === AUTO-EVO-AI 一键部署 ===
echo.
echo 目标: ubuntu@122.51.144.227
echo.
echo ⚠ 请使用 SSH 密钥认证部署，或设置 EVO_SSH_PASS 环境变量
echo.

setlocal enabledelayedexpansion

if "%EVO_SSH_PASS%"=="" (
    echo [错误] 请先设置 EVO_SSH_PASS 环境变量
    echo   用法: set EVO_SSH_PASS=your_password ^&^& deploy_all.bat
    pause
    exit /b 1
)

echo [1/4] 上传前端文件...
echo %EVO_SSH_PASS% | scp D:\AUTO-EVO-AI-V0.1\frontend\chat.html ubuntu@122.51.144.227:/home/ubuntu/my-evo-ai/frontend/chat.html
echo %EVO_SSH_PASS% | scp D:\AUTO-EVO-AI-V0.1\frontend\chat_engine.js ubuntu@122.51.144.227:/home/ubuntu/my-evo-ai/frontend/chat_engine.js
echo %EVO_SSH_PASS% | scp D:\AUTO-EVO-AI-V0.1\frontend\chat_engine_deployed.js ubuntu@122.51.144.227:/home/ubuntu/my-evo-ai/frontend/chat_engine_deployed.js
echo %EVO_SSH_PASS% | scp D:\AUTO-EVO-AI-V0.1\frontend\billion-os.html ubuntu@122.51.144.227:/home/ubuntu/my-evo-ai/frontend/billion-os.html
echo [1/4] 完成

echo [2/4] 上传API文件...
echo %EVO_SSH_PASS% | scp D:\AUTO-EVO-AI-V0.1\api_server.py ubuntu@122.51.144.227:/home/ubuntu/my-evo-ai/api_server.py
echo %EVO_SSH_PASS% | scp -r D:\AUTO-EVO-AI-V0.1\api\routes\routes_evo_v2.py ubuntu@122.51.144.227:/home/ubuntu/my-evo-ai/api/routes/routes_evo_v2.py
echo %EVO_SSH_PASS% | scp -r D:\AUTO-EVO-AI-V0.1\api\routes\routes_query.py ubuntu@122.51.144.227:/home/ubuntu/my-evo-ai/api/routes/routes_query.py
echo %EVO_SSH_PASS% | scp -r D:\AUTO-EVO-AI-V0.1\api\routes\routes_raven.py ubuntu@122.51.144.227:/home/ubuntu/my-evo-ai/api/routes/routes_raven.py
echo %EVO_SSH_PASS% | scp -r D:\AUTO-EVO-AI-V0.1\api\routes\routes_chat_storage.py ubuntu@122.51.144.227:/home/ubuntu/my-evo-ai/api/routes/routes_chat_storage.py
echo %EVO_SSH_PASS% | scp -r D:\AUTO-EVO-AI-V0.1\api\agents\yoyo_evolve.py ubuntu@122.51.144.227:/home/ubuntu/my-evo-ai/api/agents/yoyo_evolve.py
echo %EVO_SSH_PASS% | scp -r D:\AUTO-EVO-AI-V0.1\api\agents\agent_raven.py ubuntu@122.51.144.227:/home/ubuntu/my-evo-ai/api/agents/agent_raven.py
echo [2/4] 完成

echo [3/4] 重启服务...
ssh ubuntu@122.51.144.227 "cd /home/ubuntu/my-evo-ai && pkill -f api_server 2>/dev/null; sleep 2; nohup python3 api_server.py --port 8765 > /tmp/evo_api.log 2>&1 &"
echo [3/4] 完成

echo [4/4] 验证...
timeout /t 5 /nobreak >nul
ssh ubuntu@122.51.144.227 "curl -s -o /dev/null -w '首页: %%{http_code}\n' http://127.0.0.1:8765/ && curl -s -o /dev/null -w 'billion: %%{http_code}\n' http://127.0.0.1:8765/billion-os.html && curl -s -o /dev/null -w '自进化: %%{http_code}\n' http://127.0.0.1:8765/api/v1/evo/status"

echo.
echo === 部署完成! ===
pause
