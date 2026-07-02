#!/bin/bash
# AUTO-EVO-AI 一键部署（GitHub 拉取 + 重启）
# 在服务器上执行: bash /home/ubuntu/my-evo-ai/deploy/deploy_github_pull.sh

set -e
cd /home/ubuntu/my-evo-ai

echo "=== 1. 设置ghproxy代理 ==="
git config --global url."https://ghproxy.net/https://github.com/".insteadOf "https://github.com/"

echo "=== 2. 拉取最新代码 ==="
git pull origin master
if [ $? -eq 0 ]; then
    echo "拉取成功!"
else
    echo "直接拉取失败，尝试ghproxy..."
    git pull https://ghproxy.net/https://github.com/haijunwu007007/my-evo-ai.git master
fi

echo "=== 3. 重启服务 ==="
pkill -f api_server 2>/dev/null || true
sleep 2
cd /home/ubuntu/my-evo-ai
nohup python3 api_server.py --port 8765 > /tmp/evo_api.log 2>&1 &

echo "=== 4. 等待启动 ==="
sleep 5
curl -s -o /dev/null -w "首页: %{http_code}\n" http://127.0.0.1:8765/
curl -s -o /dev/null -w "billion: %{http_code}\n" http://127.0.0.1:8765/billion-os.html
curl -s -o /dev/null -w "自进化: %{http_code}\n" http://127.0.0.1:8765/api/v1/evo/status

echo "=== 部署完成! ==="
