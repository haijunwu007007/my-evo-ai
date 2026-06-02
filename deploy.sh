#!/bin/bash
# AUTO-EVO-AI V0.1 云服务器一键部署脚本
# 适用于: Ubuntu 22.04 / Debian 11+
# 用法: curl -fsSL https://raw.githubusercontent.com/haijunwu007007/my-evo-ai/master/deploy.sh | bash

set -e
echo "=========================================="
echo "  AUTO-EVO-AI V0.1 云服务器一键部署"
echo "=========================================="

# 1. 系统依赖
echo "[1/5] 安装系统依赖..."
apt-get update -qq
apt-get install -y -qq python3 python3-pip python3-venv git curl ufw > /dev/null 2>&1

# 2. 下载代码
echo "[2/5] 下载系统代码..."
cd /opt
if [ -d "AUTO-EVO-AI" ]; then
  cd AUTO-EVO-AI && git pull
else
  git clone https://github.com/haijunwu007007/my-evo-ai.git AUTO-EVO-AI
  cd AUTO-EVO-AI
fi

# 3. Python 环境
echo "[3/5] 配置 Python 环境..."
python3 -m venv venv
source venv/bin/activate
pip install -q -r requirements.txt 2>/dev/null || pip install -q fastapi uvicorn jinja2 python-multipart aiofiles httpx pyyaml
pip install -q asyncpg

# 4. 防火墙
echo "[4/5] 配置防火墙..."
ufw allow 8765/tcp > /dev/null 2>&1 || echo "ufw not available, skip"

# 5. 启动服务 (systemd)
echo "[5/5] 注册系统服务..."
cat > /etc/systemd/system/evo-api.service << 'EOF'
[Unit]
Description=AUTO-EVO-AI API Server
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/AUTO-EVO-AI
ExecStart=/opt/AUTO-EVO-AI/venv/bin/python -m uvicorn api_server:app --host 0.0.0.0 --port 8765
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable evo-api
systemctl restart evo-api

# 显示结果
IP=$(curl -s ifconfig.me)
echo ""
echo "=========================================="
echo "  ✅ 部署完成！"
echo "=========================================="
echo ""
echo "  本地访问:  http://localhost:8765/app/login"
echo "  外网访问:  http://$IP:8765/app/login"
echo ""
echo "  首次访问会自动进入设置向导"
echo "=========================================="
