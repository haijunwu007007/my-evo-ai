# 远程部署
$k = "$env:USERPROFILE\.ssh\Myevoaikey_"
$h = "ubuntu@122.51.144.227"

# 传 .env
scp -i "$k" D:\AUTO-EVO-AI-V0.1\.env.prod "${h}:~/my-evo-ai/.env" 2>$null

# 远程执行
ssh -i "$k" -o StrictHostKeyChecking=no $h "
  cd ~/my-evo-ai &&
  git pull origin master &&
  pip3 install -r requirements.txt --quiet 2>/dev/null &&
  pkill -f 'uvicorn api_server' 2>/dev/null; sleep 2 &&
  nohup python3 -m uvicorn api_server:app --host 0.0.0.0 --port 8765 > ~/evo.log 2>&1 &
  sleep 6
"

Write-Host "=== 部署完成 ==="

# 验证
$r = curl -s --max-time 5 "http://122.51.144.227:8765/api/v1/status"
Write-Host "STATUS: $r"

$r2 = curl -s --max-time 10 -X POST "http://122.51.144.227:8765/api/v1/chat" -H "Content-Type: application/json" -d '{"message":"你好","session_id":"v"}'
Write-Host "CHAT: $r2"

$r3 = curl -s --max-time 15 -X POST "http://122.51.144.227:8765/api/v1/agent/run" -H "Content-Type: application/json" -d '{"task":"简单测试","use_tools":false}'
Write-Host "AGENT: $r3"

Write-Host "=== Done ==="
