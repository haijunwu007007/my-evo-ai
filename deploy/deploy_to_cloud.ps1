# AUTO-EVO-AI 云服务器一键部署脚本
# 用法: PowerShell 右键"以管理员身份运行"

$IP = "122.51.144.227"
$USER = "ubuntu"
$KEY = "$env:USERPROFILE\.ssh\Myevoaikey_"

Write-Host "=== AUTO-EVO-AI 云部署 ===" -ForegroundColor Cyan
Write-Host "目标: $USER@$IP" -ForegroundColor Yellow

# 部署命令（SSH 远程执行）
$commands = @(
    "sudo apt update",
    "sudo apt install -y python3-pip git",
    "git clone https://github.com/haijunwu007007/my-evo-ai",
    "cd my-evo-ai && pip install -r requirements.lock",
    "cd my-evo-ai && nohup python3 -m uvicorn api_server:app --host 0.0.0.0 --port 8765 > ~/evo.log 2>&1 &",
    "sleep 3 && curl -s http://localhost:8765/api/v1/status | head -c 200"
)

foreach ($cmd in $commands) {
    Write-Host "→ $cmd" -ForegroundColor Green
    ssh -i "$KEY" -o StrictHostKeyChecking=no "$USER@$IP" "$cmd" 2>&1 | Write-Host
}

Write-Host "=== 部署完成 ===" -ForegroundColor Cyan
Write-Host "访问: http://$IP:8765" -ForegroundColor Yellow
