# AUTO-EVO-AI V0.1 — Docker 镜像
# 构建: docker build -t auto-evo-ai:v0.1 .
# 运行: docker run -d -p 8765:8765 --name evo auto-evo-ai:v0.1

FROM python:3.13-slim AS builder

WORKDIR /app

# 系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# 复制项目文件
COPY . .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt 2>/dev/null || \
    pip install --no-cache-dir fastapi uvicorn jinja2 python-multipart aiofiles httpx pyyaml prometheus-client

# ========== 运行时镜像 ==========
FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

COPY --from=builder /app /app

# 服务端口
EXPOSE 8765

# 健康检查
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -sf http://localhost:8765/ || exit 1

# 启动
CMD ["uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "8765"]
