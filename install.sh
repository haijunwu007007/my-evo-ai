#!/bin/bash
# AUTO-EVO-AI V0.1 — 一键安装脚本
# 用法: curl -s https://autoevoai.com/install.sh | bash
# 或: wget -qO- https://autoevoai.com/install.sh | bash

set -e
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}╔══════════════════════════════════════╗${NC}"
echo -e "${GREEN}║     AUTO-EVO-AI V0.1 一键安装       ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════╝${NC}"
echo ""

# 检查 Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ 未检测到 Docker${NC}"
    echo "请先安装 Docker:"
    echo "  Linux:   curl -fsSL https://get.docker.com | bash"
    echo "  macOS:   https://docs.docker.com/desktop/install/mac/"
    echo "  Windows: https://docs.docker.com/desktop/install/windows/"
    exit 1
fi

echo -e "${GREEN}✅ Docker 已安装${NC}"

# 检查 docker compose
if docker compose version &>/dev/null; then
    DC="docker compose"
elif docker-compose --version &>/dev/null; then
    DC="docker-compose"
else
    echo -e "${RED}❌ 未检测到 docker-compose${NC}"
    echo "请安装: pip install docker-compose 或 docker compose plugin"
    exit 1
fi
echo -e "${GREEN}✅ $($DC version)${NC}"

# 询问 API Key
echo ""
echo -e "${YELLOW}▶ 配置选项${NC}"
echo "================================"
read -p "输入 OpenAI API Key（留空跳过，后续可在页面配置）: " api_key
echo ""

# 创建目录
INSTALL_DIR="$HOME/evo"
mkdir -p "$INSTALL_DIR/data"
mkdir -p "$INSTALL_DIR/config"
cd "$INSTALL_DIR"

# 下载 docker-compose.yml
echo -e "${YELLOW}📥 下载配置文件...${NC}"
curl -s -O https://autoevoai.com/install/docker-compose.yml || \
    cat > docker-compose.yml << 'DOCKEREOF'
version: '3.8'
services:
  evo-api:
    image: ghcr.io/haijunwu007007/auto-evo-ai:latest
    container_name: evo-api
    ports:
      - "8765:8765"
    volumes:
      - ./data:/app/data
      - ./config:/app/config
    environment:
      - TZ=Asia/Shanghai
      - OPENAI_API_KEY=${OPENAI_API_KEY:-}
    restart: unless-stopped
DOCKEREOF

# 启动
echo -e "${YELLOW}🚀 启动 AUTO-EVO-AI...${NC}"
if [ -n "$api_key" ]; then
    export OPENAI_API_KEY="$api_key"
fi

$DC up -d

# 等待启动
echo -e "${YELLOW}⏳ 等待服务启动...${NC}"
for i in $(seq 1 15); do
    if curl -s http://localhost:8765/api/v1/status > /dev/null 2>&1; then
        echo -e "${GREEN}✅ 服务已启动${NC}"
        break
    fi
    sleep 2
done

echo ""
echo -e "${GREEN}╔══════════════════════════════════════╗${NC}"
echo -e "${GREEN}║         安装完成！                    ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════╝${NC}"
echo ""
echo -e "  访问: ${GREEN}http://localhost:8765${NC}"
echo -e "  目录: ${YELLOW}$INSTALL_DIR${NC}"
echo ""
echo -e "  管理命令:"
echo -e "    查看日志:  ${YELLOW}$DC logs -f${NC}"
echo -e "    重启:      ${YELLOW}$DC restart${NC}"
echo -e "    停止:      ${YELLOW}$DC stop${NC}"
echo -e "    升级:      ${YELLOW}$DC pull && $DC up -d${NC}"
echo ""
