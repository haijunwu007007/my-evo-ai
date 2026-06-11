#!/bin/bash
# AUTO-EVO-AI 全量修复部署脚本
# 用法: bash deploy/deploy_full_fix.sh
set -e

SSH_KEY="${SSH_KEY:-$HOME/.ssh/Myevoaikey_}"
SERVER="${SERVER:-ubuntu@122.51.144.227}"
REMOTE_DIR="${REMOTE_DIR:-~/my-evo-ai}"

echo "=== 🚀 AUTO-EVO-AI 全量修复部署 ==="

# 1. SSH 执行全量修复
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$SERVER" bash << 'EOF'
set -e
cd ~/my-evo-ai

echo "📦 步骤1: 配置 LLM API Key"
# 检查 .env 是否已有 Key
if grep -qE '^ZHIPU_API_KEY=.+' .env 2>/dev/null || grep -qE '^OPENAI_API_KEY=.+' .env 2>/dev/null || grep -qE '^DEEPSEEK_API_KEY=.+' .env 2>/dev/null; then
    echo "  ✅ LLM API Key 已存在"
else
    # 从系统环境变量导入（如果有）
    for k in ZHIPU_API_KEY OPENAI_API_KEY DEEPSEEK_API_KEY ANTHROPIC_API_KEY GEMINI_API_KEY; do
        if [ -n "${!k}" ]; then
            echo "$k=${!k}" >> .env
            echo "  ✅ 已写入 $k"
        fi
    done
    # 如果还是没有，给提示
    if ! grep -qE '^[A-Z_]+_API_KEY=.+' .env 2>/dev/null; then
        echo "  ⚠️ 未检测到 LLM API Key 环境变量"
        echo "  📝 请手动编辑 .env 文件设置至少一个 API Key"
    fi
fi

echo "📦 步骤2: 创建 python -> python3 软链接"
if ! command -v python &>/dev/null && command -v python3 &>/dev/null; then
    sudo ln -sf "$(which python3)" /usr/local/bin/python
    echo "  ✅ 已创建 python -> python3 软链接"
fi

echo "📦 步骤3: 安装/修复 httpx 版本"
pip3 install httpx==0.27.2 httpcore==1.0.7 2>/dev/null
echo "  ✅ httpx 版本已固定"

echo "📦 步骤4: 安装系统依赖"
pip3 install -r requirements.txt 2>/dev/null || true

echo "📦 步骤5: 重启 API 服务"
pkill -f 'uvicorn api_server' 2>/dev/null || true
sleep 2

# 加载 .env 中的 API Key
set -a; source .env 2>/dev/null; set +a

nohup python3 -m uvicorn api_server:app --host 0.0.0.0 --port 8765 > ~/evo.log 2>&1 &
sleep 5

echo ""
echo "=== 📋 部署后验证 ==="
python3 -c "
import httpx, httpcore
print(f'httpx: {httpx.__version__}')
print(f'httpcore: {httpcore.__version__}')
"
echo "---"
curl -s http://localhost:8765/api/v1/status 2>/dev/null | python3 -c "import sys; d=__import__('json').loads(sys.stdin.read()); print(f'✅ API: {d.get(\"version\",\"?\")} | 模块: {d.get(\"modules\",\"?\")}')" 2>/dev/null || echo "⏳ API 启动中..."
EOF

echo ""
echo "=== ✅ 部署完成 ==="
echo "访问: http://122.51.144.227:8765"
echo "验证: curl http://122.51.144.227:8765/api/v1/status"
