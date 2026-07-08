# AUTO-EVO-AI V0.1 — 多阶段构建 Dockerfile
# 生产级：多阶段构建、非root用户、HEALTHCHECK、标签

# === Stage 1: 构建阶段 ===
FROM python:3.11-slim AS builder

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt && \
    find /root/.local -name "*.pyc" -delete && \
    find /root/.local -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# === Stage 2: 运行阶段 ===
FROM python:3.11-slim

LABEL maintainer="AUTO-EVO-AI Team" \
      version="V0.1" \
      description="AUTO-EVO-AI 智能进化系统" \
      org.opencontainers.image.source="https://github.com/haijunwu007007/my-evo-ai"

# 安装系统依赖（最小集合）
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 从构建阶段复制已安装的包
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# 创建非root用户
RUN groupadd -r evo && useradd -r -g evo -d /app -s /sbin/nologin evo

WORKDIR /app

# 复制源码（排除开发/测试文件）
COPY . .
RUN rm -rf tests/ vue-app/ _archive/ benchmarks/ generated/ output/scaffolds/ \
    .github/ .gitignore .coveragerc fill_stubs.py make_ppt.py

# 创建数据目录并授权
RUN mkdir -p /data /app/logs /app/output/apps && \
    chown -R evo:evo /app /data

# 健康检查
HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -sf http://localhost:8765/api/v1/health || exit 1

EXPOSE 8765
USER evo

# 启动（使用 gunicorn + uvicorn workers 生产模式）
CMD ["python3", "-m", "uvicorn", "api_server:app", \
     "--host", "0.0.0.0", "--port", "8765", \
     "--workers", "4", \
     "--log-level", "info", \
     "--limit-concurrency", "1000"]
