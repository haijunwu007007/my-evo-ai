<#
.SYNOPSIS
AUTO-EVO-AI V0.1 一键启动脚本
#>

Write-Host "╔══════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║     AUTO-EVO-AI V0.1  一键启动          ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# 1. 防火墙规则（首次运行需要管理员权限）
$fwRule = netsh advfirewall firewall show rule name="AUTO-EVO-AI-API" 2>$null
if (-not $fwRule) {
    Write-Host "[防火墙] 添加 8765 端口入站规则..." -ForegroundColor Yellow
    netsh advfirewall firewall add rule name="AUTO-EVO-AI-API" dir=in action=allow protocol=TCP localport=8765
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[防火墙] ✅ 已开放 8765 端口" -ForegroundColor Green
    } else {
        Write-Host "[防火墙] ⚠️ 需要管理员权限，请右键以管理员身份运行" -ForegroundColor Red
    }
} else {
    Write-Host "[防火墙] ✅ 8765 端口已开放" -ForegroundColor Green
}

# 2. 获取本机 IP
$ips = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notmatch "Loopback|Virtual|Bluetooth" -and $_.PrefixOrigin -ne "WellKnown" }).IPAddress
Write-Host ""

# 3. 启动 API 服务器
$pyPath = "C:\Users\吴海军\.workbuddy\binaries\python\versions\3.13.12\python.exe"
$serverLog = "server.log"

Write-Host "[服务] 正在启动 API 服务器..." -ForegroundColor Yellow
$proc = Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -match "8765" }
if ($proc) {
    Write-Host "[服务] ⚠️ 已有服务运行中，PID: $($proc.Id)" -ForegroundColor Yellow
} else {
    $p = Start-Process -NoNewWindow -FilePath $pyPath -ArgumentList "-m uvicorn api_server:app --host 0.0.0.0 --port 8765" -PassThru
    Start-Sleep -Seconds 15
    Write-Host "[服务] ✅ 服务已启动 (PID: $($p.Id))" -ForegroundColor Green
}

# 4. 显示访问地址
Write-Host ""
Write-Host "╔══════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║         访问方式                         ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""
Write-Host "  📍 本机访问:" -ForegroundColor White
Write-Host "     http://localhost:8765/app/login" -ForegroundColor Green
Write-Host "     http://127.0.0.1:8765/app/login" -ForegroundColor Green
Write-Host ""
Write-Host "  📱 手机/局域网访问（同一 WiFi）:" -ForegroundColor White
foreach ($ip in $ips) {
    Write-Host "     http://$($ip):8765/app/login" -ForegroundColor Green
}
Write-Host ""
Write-Host "  🌐 外网访问（需安装 Tailscale）:" -ForegroundColor White
Write-Host "     http://<tailscale-ip>:8765/app/login" -ForegroundColor Green
Write-Host ""
Write-Host "  📖 API 文档:" -ForegroundColor White
Write-Host "     http://localhost:8765/scalar" -ForegroundColor Green
Write-Host ""
Write-Host "  🔑 管理员 Key (日志输出前8位):" -ForegroundColor White
Write-Host "     查看 server.log 中 [SECURITY] 行" -ForegroundColor Yellow
Write-Host ""
Write-Host "按任意键打开浏览器，或 Ctrl+C 退出" -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
Start-Process "http://localhost:8765/app/login"
