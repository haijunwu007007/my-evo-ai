#!/bin/bash
# AUTO-EVO-AI V0.1 云服务器一键部署脚本
# 适用于: Ubuntu 22.04 / Debian 11+ (腾讯云/阿里云/华为云)
# 用法: curl -fsSL https://raw.githubusercontent.com/haijunwu007007/my-evo-ai/master/deploy.sh | bash
#
# ⚠ 前置条件：云服务商安全组必须放行 TCP 8765 端口
#   腾讯云: https://console.cloud.tencent.com/cvm/securitygroup
#   阿里云: https://ecs.console.aliyun.com/securityGroup
#   入站规则: TCP:8765, 来源:0.0.0.0/0, 允许

set -e
echo "=========================================="
echo "  AUTO-EVO-AI V0.1 云服务器一键部署"
echo "=========================================="
echo ""
echo "⚠ 重要：请先在云控制台安全组放行 TCP 8765 端口！"
echo "  否则外网无法访问！"
echo ""

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

# 4. 防火墙（OS 层面 + 提示云安全组）
echo "[4/5] 配置防火墙..."
ufw allow 8765/tcp > /dev/null 2>&1 || echo "ufw not available, skip"
echo "  ✅ OS 防火墙已放行 8765"
echo "  ⚠ 请确认云控制台安全组也放行了 TCP 8765！"

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
echo "  如外网无法访问，请检查云安全组："
echo "    腾讯云: https://console.cloud.tencent.com/cvm/securitygroup"
echo "    阿里云: https://ecs.console.aliyun.com/securityGroup"
echo ""
echo "  首次访问会自动进入设置向导"
echo "=========================================="
