"""AUTO-EVO-AI V0.1 — 监控/指标路由（从 api_server.py 抽离）

Prometheus 指标 + 健康检查。
共享状态从 api.infra 导入，与 api_server.py 同源。
"""
import time
from fastapi import APIRouter
from fastapi.responses import Response

router = APIRouter(tags=["metrics"])

# 从共享基础设施导入状态
from api.infra import (
    _START_TIME, _request_counter, _request_errors, _request_latency_ms,
    _cache_hits, _api_cache, manager,
)


@router.get("/api/v1/health")
async def health_check():
    """系统健康检查端点"""
    return {"status": "ok", "timestamp": time.time()}


@router.get("/metrics", include_in_schema=False)
@router.get("/api/v1/metrics", include_in_schema=False)
async def prometheus_metrics():
    """Prometheus 指标导出"""
    now = time.time()
    uptime = now - _START_TIME
    from api.infra import BUILD_TAG, registry
    lines: list = [f"# {BUILD_TAG} Prometheus Metrics Export"]

    # 模块级 Prometheus 指标
    try:
        from modules._prometheus import get_prometheus_text
        pt = get_prometheus_text()
        if pt.strip():
            lines.append("")
            lines.append("# -- modules._prometheus --")
            lines.append(pt)
    except Exception:
        pass

    health = registry.get_all_health()
    ok_count = sum(1 for h in health.values() if h.get("status") in ("ok", "healthy", "configured", "module_only"))
    err_count = sum(1 for h in health.values() if h.get("status") in ("error", "lazy_error", "timeout"))
    lazy_count = sum(1 for h in health.values() if h.get("status") in ("pending_lazy",))

    lines.append(f"evo_system_uptime_seconds {uptime:.0f}")
    lines.append(f"evo_modules_total {len(health)}")
    lines.append(f"evo_modules_healthy {ok_count}")
    lines.append(f"evo_modules_error {err_count}")
    stub_count = registry.get_stub_count()
    lines.append(f"evo_modules_lazy_pending {lazy_count}")
    lines.append(f"evo_modules_stub {stub_count}")

    for path, count in sorted(_request_counter.items()):
        lines.append(f'evo_http_requests_total{{endpoint="{path}"}} {count}')
    for path, count in sorted(_request_errors.items()):
        lines.append(f'evo_http_errors_total{{endpoint="{path}"}} {count}')
    for path, avg in sorted(_request_latency_ms.items()):
        lines.append(f'evo_http_request_duration_ms{{endpoint="{path}"}} {avg:.1f}')

    lines.append(f"evo_ws_connections_active {len(manager.active)}")
    lines.append(f"evo_cache_hits_total {_cache_hits}")
    lines.append(f"evo_cache_entries {len(_api_cache)}")

    # 引擎指标
    try:
        from api.routes.routes_scheduler import HAS_SCHEDULER, HAS_EVENTS, HAS_PIPELINE, HAS_QUEUE
        lines.append(f'evo_engine_active{{engine="scheduler"}} {1 if HAS_SCHEDULER else 0}')
        lines.append(f'evo_engine_active{{engine="events"}} {1 if HAS_EVENTS else 0}')
        lines.append(f'evo_engine_active{{engine="pipeline"}} {1 if HAS_PIPELINE else 0}')
        lines.append(f'evo_engine_active{{engine="queue"}} {1 if HAS_QUEUE else 0}')
    except Exception:
        pass

    text = "\n".join(lines)
    return Response(content=text, media_type="text/plain; version=0.0.4; charset=utf-8")
