# ═══════════════════════════════════════════════════════
# AUTO-EVO-AI V0.1 — Production Dockerfile (优化版~350MB)
# ═══════════════════════════════════════════════════════

# ── Stage 1: Builder ──
FROM python:3.11-slim AS builder

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt && \
    find /root/.local -name "*.pyc" -delete && \
    find /root/.local -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

# ── Stage 2: Runtime ──
FROM python:3.11-slim

ARG BUILD_VERSION=0.1.0
ARG BUILD_DATE
LABEL \
    name="AUTO-EVO-AI" \
    version="${BUILD_VERSION}" \
    description="上市公司级 AI 自动化系统 — 515模块" \
    org.opencontainers.image.created="${BUILD_DATE}" \
    org.opencontainers.image.version="${BUILD_VERSION}"

WORKDIR /app

# 仅安装运行必需工具，清理 apt 缓存
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# 复用 builder 层的 Python 依赖
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# 只复制运行必需的文件
COPY api_server.py .
COPY config.yaml .
COPY .env.example .
COPY api/ api/
COPY core/ core/
COPY modules/ modules/
# 前端构建产物（可选），跳过 dev 依赖

ENV \
    PYTHONIOENCODING=utf-8 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    APP_VERSION="${BUILD_VERSION:-0.1.0}"

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -sf http://127.0.0.1:8765/api/status || exit 1

EXPOSE 8765
CMD ["python", "api_server.py"]
