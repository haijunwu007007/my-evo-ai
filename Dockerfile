# ═══════════════════════════════════════════════════════
# AUTO-EVO-AI V0.1 — Production Dockerfile (535模块)
# ═══════════════════════════════════════════════════════

# ── Stage 1: Builder (install dependencies) ──
FROM python:3.11-slim AS builder

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ── Stage 2: Runtime (minimal image) ──
FROM python:3.11-slim

ARG BUILD_VERSION=0.1.0
ARG BUILD_DATE
LABEL \
    name="AUTO-EVO-AI" \
    version="${BUILD_VERSION}" \
    description="上市公司级 AI 自动化系统 — 535模块" \
    org.opencontainers.image.created="${BUILD_DATE}" \
    org.opencontainers.image.version="${BUILD_VERSION}"

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates netcat-openbsd && \
    rm -rf /var/lib/apt/lists/*

COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

COPY api/ api/
COPY modules/ modules/
COPY core/ core/
COPY config.yaml .
COPY api_server.py .
COPY .env.example .
# 前端构建: cd frontend && npm run build（可选，不影响API服务）

ENV \
    PYTHONIOENCODING=utf-8 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    APP_VERSION="${BUILD_VERSION:-0.1.0}"

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -sf http://127.0.0.1:8765/api/status || exit 1

EXPOSE 8765

CMD ["python", "api_server.py"]
