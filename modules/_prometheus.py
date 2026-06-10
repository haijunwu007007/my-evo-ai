"""
AUTO-EVO-AI V0.1 — Prometheus 指标注册器
供 EnterpriseModule 子类装饰器使用，统一暴露 metrics。
"""
import logging, time, os
from collections import defaultdict
from typing import Dict

logger = logging.getLogger("evo.prometheus")

_metrics: dict[str, dict] = defaultdict(lambda: {"count": 0, "errors": 0, "total_ms": 0})
_registered = set()

def increment(module_id: str, method: str = "execute", duration_ms: float = 0, error: bool = False):
    key = f"{module_id}.{method}"
    m = _metrics[key]
    m["count"] += 1
    m["total_ms"] += duration_ms
    if error:
        m["errors"] += 1
    m["last_ts"] = time.time()
    _registered.add(module_id)

def get_metrics() -> dict:
    now = time.time()
    rows = []
    for key, m in sorted(_metrics.items()):
        avg_ms = round(m["total_ms"] / m["count"], 1) if m["count"] > 0 else 0
        rows.append({
            "metric": key,
            "count": m["count"],
            "errors": m["errors"],
            "avg_ms": avg_ms,
            "last_secs_ago": int(now - m.get("last_ts", now)),
        })
    return {"metrics": rows, "registered_modules": len(_registered)}

def get_prometheus_text() -> str:
    lines = ["# HELP evo_module_total Module execution count", "# TYPE evo_module_total counter"]
    now = time.time()
    for key, m in sorted(_metrics.items()):
        lines.append(f'evo_module_total{{metric="{key}"}} {m["count"]}')
        lines.append(f'evo_module_errors{{metric="{key}"}} {m["errors"]}')
        avg = round(m["total_ms"] / m["count"], 1) if m["count"] > 0 else 0
        lines.append(f'evo_module_avg_ms{{metric="{key}"}} {avg}')
    lines.append(f"evo_modules_active_called {len(_registered)}")
    return "\n".join(lines) + "\n"
