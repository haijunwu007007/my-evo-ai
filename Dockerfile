# ═══════════════════════════════════════════════════════
# AUTO-EVO-AI V0.1 — Production Dockerfile (~200MB)
# ═══════════════════════════════════════════════════════

# ── Stage 1: Python Dependencies ──
FROM python:3.11-slim AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt && \
    find /root/.local -name "*.pyc" -delete && \
    find /root/.local -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

# ── Stage 2: Runtime ──
FROM python:3.11-alpine
WORKDIR /app

# ca-certificates 仅用于 HTTPS healthcheck
RUN apk add --no-cache ca-certificates && \
    rm -rf /var/cache/apk/*

COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

COPY api_server.py config.yaml .env.example ./
COPY api/ api/
COPY core/ core/
COPY modules/ modules/

ENV \
    PYTHONIOENCODING=utf-8 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    APP_VERSION=0.1.0

EXPOSE 8765
CMD ["python", "api_server.py"]
