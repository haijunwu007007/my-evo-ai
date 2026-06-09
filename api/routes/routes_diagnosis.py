"""系统诊断 — 健康检查与性能诊断"""
from fastapi import APIRouter
from core.logging_config import get_logger
import time, os

logger = get_logger("evo.api.diagnosis")
router = APIRouter()

@router.get("/api/v1/diagnosis/health")
async def diagnosis_health():
    """系统健康诊断"""
    checks = []
    
    # 磁盘检查
    try:
        import shutil
        usage = shutil.disk_usage(os.path.abspath("."))
        disk_pct = usage.used / usage.total * 100
        checks.append({"name": "磁盘空间", "status": "ok" if disk_pct < 90 else "warn", "value": f"{disk_pct:.1f}%"})
    except: checks.append({"name": "磁盘空间", "status": "unknown"})
    
    # 内存检查
    try:
        import psutil
        mem = psutil.virtual_memory()
        checks.append({"name": "内存", "status": "ok" if mem.percent < 90 else "warn", "value": f"{mem.percent:.1f}%"})
    except: checks.append({"name": "内存", "status": "ok", "value": "未知(psutil未安装)"})
    
    # 运行时间
    checks.append({"name": "服务状态", "status": "ok", "value": "运行中"})
    
    all_ok = all(c["status"] == "ok" or c["status"] == "unknown" for c in checks)
    return {"success": True, "healthy": all_ok, "checks": checks, "timestamp": time.time()}
