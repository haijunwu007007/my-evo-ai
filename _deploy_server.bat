@echo off
:: 四端同步 - 服务器端：git pull + 重启
ssh -o ConnectTimeout=10 ubuntu@122.51.144.227 "cd /home/ubuntu/my-evo-ai && git pull origin master && nohup python3 api_server.py --port 8765 > /tmp/evo_api.log 2>&1 & echo DONE"
echo ---
echo 等待服务启动...
timeout /t 5 /nobreak >nul
curl -s --max-time 5 https://autoevoai.com/ | findstr /C:"html" >nul && echo 服务已恢复 || echo 服务可能还未就绪，再等几秒刷新页面
pause
