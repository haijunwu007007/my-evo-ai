#!/bin/bash
# AUTO-EVO-AI 服务器部署脚本
# 用法: bash deploy_server.sh
# 适用: 腾讯云 122.51.144.227 (Ubuntu)

set -e

echo "=========================================="
echo "  AUTO-EVO-AI 服务器部署脚本"
echo "  时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="

cd ~/my-evo-ai

# 1. 拉取最新代码
echo ""
echo "[1/5] 拉取最新代码..."
git pull origin master 2>&1 || git fetch origin master && git reset --hard origin/master

# 2. 安装依赖
echo ""
echo "[2/5] 安装办公套件 + 音频转录依赖..."
source venv/bin/activate 2>/dev/null || python3 -m venv venv && source venv/bin/activate
pip install --upgrade pip -q
pip install python-docx python-pptx PyPDF2 pdfplumber openpyxl -q
pip install SpeechRecognition pydub imageio-ffmpeg -q
echo "  依赖安装完成"

# 3. 检查文件完整性
echo ""
echo "[3/5] 检查新模块文件..."
FILES=(
  "modules/docx_processor.py"
  "modules/pdf_toolkit.py"
  "modules/ppt_generator.py"
  "modules/excel_pro.py"
  "api/routes/routes_docs.py"
  "api/routes/routes_audio.py"
  "api/routes/routes_static.py"
  "frontend/docs.html"
  "frontend/admin.html"
)
MISSING=0
for f in "${FILES[@]}"; do
  if [ -f "$f" ]; then
    echo "  ✅ $f"
  else
    echo "  ❌ $f (缺失)"
    MISSING=$((MISSING+1))
  fi
done
if [ $MISSING -gt 0 ]; then
  echo "  警告: $MISSING 个文件缺失，请先 git pull"
fi

# 4. 检查注册状态
echo ""
echo "[4/5] 检查模块注册状态..."
# 先确保服务在运行
if curl -s http://localhost:8765/api/v1/modules > /dev/null 2>&1; then
  TOTAL=$(curl -s http://localhost:8765/api/v1/modules | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d.get('modules',d.get('data',[]))))" 2>/dev/null || echo "未知")
  echo "  当前注册模块数: $TOTAL"
  echo "  (预期: 原模块数+4)"
else
  echo "  ⚠️ API服务未运行，请先启动: bash start.sh"
fi

# 5. 重启服务
echo ""
echo "[5/5] 重启服务..."
# 查找并杀掉旧进程
OLD_PID=$(pgrep -f "uvicorn.*8765" 2>/dev/null || echo "")
if [ -n "$OLD_PID" ]; then
  echo "  停止旧进程 (PID: $OLD_PID)..."
  kill $OLD_PID 2>/dev/null
  sleep 2
fi

# 启动新进程
echo "  启动服务..."
nohup bash start.sh > /dev/null 2>&1 &
sleep 3

# 验证
if curl -s http://localhost:8765/api/v1/health > /dev/null 2>&1; then
  echo "  ✅ 服务已启动 (端口 8765)"
  echo "  📍 http://localhost:8765/"
  echo "  📍 http://localhost:8765/office (办公套件)"
else
  echo "  ⚠️ 服务启动中，请稍后检查..."
fi

echo ""
echo "=========================================="
echo "  部署完成!"
echo "  办公套件: http://localhost:8765/office"
echo "  管理后台: http://localhost:8765/admin"
echo "=========================================="
