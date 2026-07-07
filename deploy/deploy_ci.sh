#!/bin/bash
# AUTO-EVO-AI CI/CD 一键部署脚本
# 用法: bash deploy_ci.sh [branch]

set -e
BRANCH=${1:-master}
APP_DIR="/home/ubuntu/my-evo-ai"

echo "=== AUTO-EVO-AI CI/CD ==="
echo "Branch: $BRANCH"
echo "Target: $APP_DIR"
echo "Time: $(date)"

# 1. 拉取最新代码
cd "$APP_DIR"
git fetch origin "$BRANCH"
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/"$BRANCH")
if [ "$LOCAL" = "$REMOTE" ]; then
  echo "Already up-to-date ($LOCAL). Restarting service..."
  sudo systemctl restart evo.service
  echo "Done."
  exit 0
fi
git reset --hard origin/"$BRANCH"

# 2. 安装依赖（如果有变更）
if [ -f requirements.txt ]; then
  pip3 install -r requirements.txt -q 2>/dev/null || true
fi

# 3. 重启服务
sudo systemctl restart evo.service
sleep 2

# 4. 健康检查
for i in 1 2 3; do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8765/api/auth/config 2>/dev/null || echo "000")
  if [ "$STATUS" = "200" ]; then
    echo "Health check PASS ($STATUS)"
    exit 0
  fi
  echo "Retry $i/3..."
  sleep 2
done
echo "Health check FAIL. Status: $STATUS"
exit 1
