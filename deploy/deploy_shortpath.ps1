# 获取短路径
$keyPath = "$env:USERPROFILE\.ssh\Myevoaikey_"
$shortPath = (New-Object -ComObject Scripting.FileSystemObject).GetFile($keyPath).ShortPath
Write-Host "Key: $shortPath"

# 传 .env
Write-Host "=== SCP .env ==="
scp -i $shortPath "D:\AUTO-EVO-AI-V0.1\.env.prod" ubuntu@122.51.144.227:~/my-evo-ai/.env

# git pull
Write-Host "=== GIT PULL ==="
ssh -i $shortPath -o StrictHostKeyChecking=no ubuntu@122.51.144.227 "cd ~/my-evo-ai && git pull origin master"

# install deps
Write-Host "=== PIP INSTALL ==="
ssh -i $shortPath -o StrictHostKeyChecking=no ubuntu@122.51.144.227 "cd ~/my-evo-ai && pip3 install -r requirements.txt --quiet 2>/dev/null || true"

# restart
Write-Host "=== RESTART ==="
ssh -i $shortPath -o StrictHostKeyChecking=no ubuntu@122.51.144.227 "pkill -f 'uvicorn api_server' 2>/dev/null; sleep 2; nohup python3 -m uvicorn api_server:app --host 0.0.0.0 --port 8765 > ~/evo.log 2>&1 & sleep 5"

# verify
Write-Host "=== VERIFY ==="
curl -s http://122.51.144.227:8765/api/v1/status
