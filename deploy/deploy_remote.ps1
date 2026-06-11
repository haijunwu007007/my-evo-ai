# AUTO-EVO-AI 远程部署脚本
$key = "$env:USERPROFILE\.ssh\Myevoaikey_"
$hostname = "ubuntu@122.51.144.227"

Write-Host "=== 开始远程部署 ==="

# 1. 传输 .env
Write-Host "[1/5] 传输 .env..."
scp -i "$key" D:\AUTO-EVO-AI-V0.1\.env.prod "${hostname}:~/my-evo-ai/.env"

# 2. SSH 执行部署
Write-Host "[2/5] 远程执行部署..."
ssh -i "$key" -o StrictHostKeyChecking=no $hostname @"
cd ~/my-evo-ai
echo '--- git pull ---'
git pull origin master
echo '--- pip install ---'
pip3 install -r requirements.txt --quiet 2>/dev/null || true
echo '--- kill old ---'
pkill -f 'uvicorn api_server' 2>/dev/null || true
sleep 2
echo '--- start service ---'
nohup python3 -m uvicorn api_server:app --host 0.0.0.0 --port 8765 > ~/evo.log 2>&1 &
sleep 5
echo '--- verify ---'
curl -s http://localhost:8765/api/v1/status
"@

Write-Host "[3/5] 验证公网..."
$retry = 0
while ($retry -lt 3) {
    $r = curl -s --max-time 5 "http://122.51.144.227:8765/api/v1/status"
    if ($r -match "success") {
        Write-Host "✅ 服务正常: $r"
        break
    }
    $retry++
    Start-Sleep -Seconds 3
}

Write-Host "[4/5] 验证LLM聊天..."
$r2 = curl -s --max-time 10 -X POST "http://122.51.144.227:8765/api/v1/chat" -H "Content-Type: application/json" -d '{"message":"你好","session_id":"deploy_test"}'
Write-Host "✅ 聊天响应: $r2"

Write-Host "[5/5] 验证Agent引擎..."
$r3 = curl -s --max-time 15 -X POST "http://122.51.144.227:8765/api/v1/agent/run" -H "Content-Type: application/json" -d '{"task":"简单测试","use_tools":false}'
Write-Host "✅ Agent响应: $r3"

Write-Host "=== 部署完成 ==="
