# AUTO-EVO-AI 云服务器一键部署脚本
# 用法: PowerShell 右键"以管理员身份运行"

$IP = "122.51.144.227"
$USER = "ubuntu"
$KEY = "$env:USERPROFILE\.ssh\Myevoaikey_"

Write-Host "=== AUTO-EVO-AI 云部署 ===" -ForegroundColor Cyan
Write-Host "目标: $USER@$IP" -ForegroundColor Yellow

Write-Host "`n⚠ 前置条件：" -ForegroundColor Yellow
Write-Host "  1. 腾讯云安全组必须放行 TCP 8765 端口！" -ForegroundColor Yellow
Write-Host "     登录 https://console.cloud.tencent.com/cvm/securitygroup" -ForegroundColor Yellow
Write-Host "     入站规则 → 添加: TCP:8765, 来源:0.0.0.0/0, 允许" -ForegroundColor Yellow
Write-Host "  2. 确保 .env 文件中已配置至少一个 LLM API Key (OPENAI_API_KEY / ZHIPU_API_KEY / DEEPSEEK_API_KEY)" -ForegroundColor Yellow
Write-Host "     否则系统启动后全部模块处于待加载状态，AI 聊天不可用" -ForegroundColor Yellow
Write-Host ""

# 检查 .env 是否存在
if (-not (Test-Path "..\.env")) {
    Write-Host "⚠ .env 文件不存在！自动从 .env.prod 创建..." -ForegroundColor Yellow
    Copy-Item "..\.env.prod" "..\.env"
    Write-Host "  已创建 .env，请填写 API Key 后重新运行本脚本" -ForegroundColor Red
    exit 1
}

# 部署命令（SSH 远程执行）
$commands = @(
    "sudo apt update && sudo apt install -y python3-pip git",
    "rm -rf my-evo-ai-old 2>/dev/null; mv my-evo-ai my-evo-ai-old 2>/dev/null; git clone https://github.com/haijunwu007007/my-evo-ai",
    "cd my-evo-ai && pip install -r requirements.txt 2>&1 | tail -5",
    "sudo ufw allow 8765/tcp 2>/dev/null",
    # ⚡ 关键：复制 .env 到服务器
    'echo "# AUTO-EVO-AI .env (自动部署)" > ~/my-evo-ai/.env'
)

# 传输 .env 文件
Write-Host "→ 传输 .env 配置文件..." -ForegroundColor Green
scp -i "$KEY" "..\.env" "${USER}@${IP}:~/my-evo-ai/.env" 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✅ .env 已传输" -ForegroundColor Green
} else {
    Write-Host "  ⚠ .env 传输失败，需手动在服务器上配置" -ForegroundColor Red
}

$commands += @(
    "pkill -f 'uvicorn api_server' 2>/dev/null; sleep 1",
    "cd my-evo-ai && nohup python3 -m uvicorn api_server:app --host 0.0.0.0 --port 8765 > ~/evo.log 2>&1 &",
    "sleep 5 && curl -s http://localhost:8765/api/v1/status"
)

foreach ($cmd in $commands) {
    Write-Host "→ $cmd" -ForegroundColor Green
    ssh -i "$KEY" -o StrictHostKeyChecking=no "$USER@$IP" "$cmd" 2>&1 | Write-Host
}

Write-Host "`n=== 部署完成 ===" -ForegroundColor Cyan
Write-Host "访问: http://$IP`:8765" -ForegroundColor Yellow
Write-Host "验证: curl http://$IP`:8765/api/v1/status" -ForegroundColor Yellow
