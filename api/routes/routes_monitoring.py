# -*- coding: utf-8 -*-
"""P3 监控告警系统 — 服务健康+资源使用+自动告警"""
from fastapi import APIRouter
import os, subprocess, time, json, sqlite3, threading
from pathlib import Path

router = APIRouter(prefix="/api/v1/monitor", tags=["monitor"])
BASE = Path(__file__).resolve().parent.parent.parent
DB = BASE / "data" / "monitor.db"

def _init_db():
    conn = sqlite3.connect(str(DB))
    conn.execute("CREATE TABLE IF NOT EXISTS alerts (id INTEGER PRIMARY KEY AUTOINCREMENT, type TEXT, message TEXT, severity TEXT, time REAL)")
    conn.execute("CREATE TABLE IF NOT EXISTS checks (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, status TEXT, detail TEXT, time REAL)")
    conn.commit()
    return conn

_init_db()

def _check_port(port, timeout=3):
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect(("localhost", port))
        s.close()
        return True
    except: return False

def _check_cmd(cmd):
    try: r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10); return r.returncode == 0
    except: return False

@router.get("/health/full")
def full_health():
    """全量健康检查 — 所有服务"""
    checks = {
        "evo": _check_port(8765),
        "hk_worker": _check_port(18766),
        "docker": _check_cmd("docker ps"),
        "nginx": _check_cmd("nginx -t"),
        "systemd": _check_cmd("systemctl is-active evo.service"),
    }
    all_ok = all(checks.values())
    return {"success": True, "status": "healthy" if all_ok else "degraded", "checks": checks}

@router.get("/resources")
def resources():
    """系统资源监控"""
    data = {"cpu": "", "memory": "", "disk": "", "docker": 0}
    try:
        r = subprocess.run("top -bn1 | head -5", shell=True, capture_output=True, text=True, timeout=5)
        data["cpu"] = r.stdout[:200]
        r = subprocess.run("free -m", shell=True, capture_output=True, text=True, timeout=5)
        data["memory"] = r.stdout[:200]
        r = subprocess.run("df -h /", shell=True, capture_output=True, text=True, timeout=5)
        data["disk"] = r.stdout[:200]
        r = subprocess.run("docker ps -q | wc -l", shell=True, capture_output=True, text=True, timeout=5)
        data["docker"] = int(r.stdout.strip() or 0)
    except: pass
    return {"success": True, "data": data}

@router.get("/alerts")
def get_alerts():
    """告警记录"""
    conn = _init_db()
    cur = conn.execute("SELECT * FROM alerts ORDER BY time DESC LIMIT 50")
    alerts = [{"id": r[0], "type": r[1], "message": r[2], "severity": r[3], "time": r[4]} for r in cur.fetchall()]
    conn.close()
    return {"success": True, "alerts": alerts}

@router.post("/alerts/check")
def check_and_alert():
    """运行检查并记录告警"""
    h = full_health()
    alerts = []
    for service, ok in h["checks"].items():
        if not ok:
            msg = f"{service} 不可用"
            conn = _init_db()
            conn.execute("INSERT INTO alerts (type, message, severity, time) VALUES (?,?,?,?)",
                        (service, msg, "critical", time.time()))
            conn.commit()
            conn.close()
            alerts.append({"type": service, "message": msg})
    h["alerts"] = alerts
    return h

# SSE 实时推送
@router.get("/events")
async def sse_events():
    """SSE 实时事件流"""
    from fastapi.responses import StreamingResponse
    import asyncio
    async def event_stream():
        while True:
            h = full_health()
            yield f"data: {json.dumps(h)}\n\n"
            await asyncio.sleep(5)
    return StreamingResponse(event_stream(), media_type="text/event-stream")

@router.get("/metrics")
def prometheus_metrics():
    """Prometheus 格式指标"""
    h = full_health()
    lines = ["# HELP evo_service Service health status"]
    for name, ok in h["checks"].items():
        lines.append(f'evo_service{{name="{name}"}} {1 if ok else 0}')
    return {"success": True, "metrics": "\n".join(lines)}
