#!/bin/bash
# AUTO-EVO-AI 部署脚本
# 用法: bash deploy/deploy.sh

set -e
echo "=== AUTO-EVO-AI 部署 ==="

# 检查环境
PYTHON=$(which python3 || which python)
if [ -z "$PYTHON" ]; then echo "❌ 需要 Python 3.13+"; exit 1; fi
echo "✅ Python: $($PYTHON --version)"

# 安装依赖
pip install -r requirements.txt 2>/dev/null || true

# 配置环境变量
if [ ! -f ".env" ]; then
    cp .env.example .env 2>/dev/null || cat > .env <<EOF
ZHIPU_API_KEY=
OPENAI_API_KEY=
EVO_ADMIN_KEY=change-me
PORT=8765
HOST=0.0.0.0
EOF
    echo "✅ .env 已创建，请配置 API Key"
fi

# 启动
echo "🚀 启动服务..."
$PYTHON -m uvicorn api_server:app --host ${HOST:-0.0.0.0} --port ${PORT:-8765}
