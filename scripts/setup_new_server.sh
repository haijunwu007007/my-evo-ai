#!/bin/bash
# AUTO-EVO-AI 新服务器一键安装脚本
# 用法: bash scripts/setup_new_server.sh

set -e

echo "===== AUTO-EVO-AI 新服务器环境安装 ====="
echo ""

# 1. 系统依赖
echo "[1/8] 安装系统依赖..."
sudo apt-get update -qq
sudo apt-get install -y -qq python3-pip python3-venv nodejs npm docker.io docker-compose fzf btop ffmpeg nginx 2>/dev/null

# 2. Python 环境
echo "[2/8] 安装 Python 依赖..."
pip3 install --quiet aichat goose-ai thefuck pipx 2>/dev/null

# 3. OfficeCLI
echo "[3/8] 安装 OfficeCLI..."
curl -fsSL https://github.com/iOfficeAI/OfficeCLI/releases/latest/download/officecli-linux-x64 -o /tmp/officecli
chmod +x /tmp/officecli
sudo mv /tmp/officecli /usr/local/bin/officecli
officecli --version

# 4. n8n CLI
echo "[4/8] 安装 n8n CLI..."
sudo npm install -g n8n 2>/dev/null

# 5. Docker 服务启动
echo "[5/8] 启动 Docker..."
sudo systemctl enable docker 2>/dev/null
sudo systemctl start docker 2>/dev/null

# 6. Python 项目依赖
echo "[6/8] 安装项目依赖..."
if [ -f requirements.txt ]; then
    pip3 install -r requirements.txt --quiet
fi

# 7. Evo 服务注册
echo "[7/8] 注册 Evo 系统服务..."
sudo tee /etc/systemd/system/evo.service > /dev/null <<'EOF'
[Unit]
Description=AUTO-EVO-AI Service
After=network.target docker.service

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/my-evo-ai
ExecStart=/usr/bin/python3 api/startup.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload
sudo systemctl enable evo.service

# 8. 验证
echo "[8/8] 验证安装..."
echo "--- CLI工具 ---"
for t in aichat officecli thefuck fzf btop ffmpeg pipx docker n8n; do
    which $t 2>/dev/null && echo "  ✅ $t" || echo "  ❌ $t"
done

echo ""
echo "===== 安装完成 ====="
echo "启动服务: sudo systemctl start evo.service"
echo "查看日志: journalctl -u evo.service -f"
