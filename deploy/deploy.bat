@echo off
chcp 65001 >nul

echo === AUTO-EVO-AI 云部署 ===
echo 目标: ubuntu@122.51.144.227
echo 密钥: %%USERPROFILE%%\.ssh\Myevoaikey_
echo.

echo ⚠ 前置条件：
echo   1. 腾讯云安全组必须放行 TCP 8765 端口！
echo      登录 https://console.cloud.tencent.com/cvm/securitygroup
echo      找到本服务器的安全组 → 入站规则 → 添加规则:
echo        TCP:8765, 来源:0.0.0.0/0, 策略:允许
echo   2. 确保项目根目录的 .env 文件中已配置至少一个 LLM API Key
echo      否则系统启动后全部模块处于待加载状态，AI 聊天不可用
echo.

if not exist "..\.env" (
    echo ⚠ .env 文件不存在！从 .env.prod 复制...
    copy "..\.env.prod" "..\.env"
    echo   已创建 .env，请填写 API Key 后重新运行本脚本
    pause
    exit /b 1
)

echo 正在连接服务器部署...
echo.

rem 先手动传输 .env 文件
echo 传输 .env 配置文件...
scp -i "%%USERPROFILE%%\.ssh\Myevoaikey_" "..\.env" ubuntu@122.51.144.227:~/my-evo-ai/.env

rem SSH 执行部署
ssh -i "%%USERPROFILE%%\.ssh\Myevoaikey_" -o StrictHostKeyChecking=no ubuntu@122.51.144.227 ^
    "pkill -f 'uvicorn api_server' 2>/dev/null; " ^
    "cd my-evo-ai && git pull && " ^
    "pip install -r requirements.txt && " ^
    "nohup python3 -m uvicorn api_server:app --host 0.0.0.0 --port 8765 > ~/evo.log 2>&1 & " ^
    "sleep 5 && " ^
    "curl -s http://localhost:8765/api/v1/status | python3 -c \"import sys;print(sys.stdin.read()[:200])\""

echo.
echo === 部署完成 ===
echo 访问 http://122.51.144.227:8765
echo 验证: curl http://122.51.144.227:8765/api/v1/status
pause
