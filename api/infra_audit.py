"""审计日志 — 从 infra.py 拆分"""
from __future__ import annotations
from datetime import datetime
from typing import List

_audit_log: list[dict] = []
_MAX_AUDIT = 1000


def _record_audit(method: str, path: str, client_ip: str, status: int, latency_ms: float, error: str = ""):
    entry = {
        "timestamp": datetime.now().isoformat(),
        "method": method, "path": path,
        "client_ip": client_ip, "status": status,
        "latency_ms": round(latency_ms, 1),
        "error": error[:200] if error else "",
    }
    _audit_log.append(entry)
    if len(_audit_log) > _MAX_AUDIT:
        _audit_log.pop(0)
