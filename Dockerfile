# ═══════════════════════════════════════════════════════
# AUTO-EVO-AI V0.1 — Production Dockerfile (535模块)
# ═══════════════════════════════════════════════════════

# ── Stage 1: Builder (install dependencies) ──
FROM python:3.11-slim AS builder

WORKDIR /build
COPY requirements-core.txt .
RUN pip install --no-cache-dir --user -r requirements-core.txt

# ── Stage 2: Runtime (minimal image) ──
FROM python:3.11-slim

# Build args for metadata
ARG BUILD_VERSION
ARG BUILD_DATE
LABEL \
    name="AUTO-EVO-AI" \
    version="${BUILD_VERSION}" \
    description="上市公司级 AI 自动化系统 — 571模块" \
    org.opencontainers.image.created="${BUILD_DATE}" \
    org.opencontainers.image.version="${BUILD_VERSION}"

WORKDIR /app

# Install runtime system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates netcat-openbsd && \
    rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy application code (excludes ignored by .dockerignore)
COPY api/ api/
COPY modules/ modules/
COPY core/ core/
COPY config.yaml .
COPY api_server.py .

# Runtime environment
ENV \
    PYTHONIOENCODING=utf-8 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    APP_VERSION="${BUILD_VERSION:-0.1.0}"

# Health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -sf http://127.0.0.1:8765/api/health || exit 1

EXPOSE 8765

CMD ["python", "api_server.py"]
