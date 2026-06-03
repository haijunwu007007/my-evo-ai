Start-Sleep -Seconds 20
# Kill kailoader if it occupies port 8765
Get-Process -Name kailoader -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 2
Set-Location "D:\AUTO-EVO-AI-V0.1"
$env:EVO_FAST_START = "1"
Start-Process -NoNewWindow -FilePath "C:\Users\吴海军\.workbuddy\binaries\python\versions\3.13.12\python.exe" -ArgumentList "-m uvicorn api_server:app --host 0.0.0.0 --port 8765"
