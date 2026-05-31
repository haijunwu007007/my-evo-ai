"""
AUTO-EVO-AI V0.1 — 性能分析模块
=================================
使用 pyinstrument 进行函数级 CPU 热点分析。
支持三种模式：
  1. 请求头触发: X-Profile: true 的请求自动记录火焰图
  2. 间隔采样: /api/profile/start + /api/profile/stop 手动控制
  3. /api/profile/status 查看最近记录
"""

from __future__ import annotations

import os, time, json, threading
from pathlib import Path
from typing import Optional
from collections import deque
from fastapi import Request, APIRouter
from fastapi.responses import JSONResponse

try:
    import pyinstrument
    HAS_PYINSTRUMENT = True
except ImportError:
    HAS_PYINSTRUMENT = False


# ── 全局状态 ──
_profile_enabled = os.environ.get("EVO_PROFILE_ENABLED", "false").lower() in ("1", "true", "yes")
_profile_records: deque = deque(maxlen=50)  # 最多保留 50 条记录
_profiler_instance: pyinstrument.Profiler | None = None
_sampling_active = False


def get_latest_profiles(limit: int = 10) -> list[dict]:
    """获取最近 N 条 profile 记录。"""
    records = list(_profile_records)
    records.reverse()
    return records[:limit]


def record_profile(path: str, elapsed_ms: float, flame_output: str):
    """记录一次 profile 结果。"""
    _profile_records.append({
        "path": path,
        "elapsed_ms": round(elapsed_ms, 2),
        "timestamp": time.time(),
        "flame": flame_output[:5000],  # 截断过大输出
    })


# ═══════════════════════════════════════════════════════
# Profiler 中间件（请求头触发）
# ═══════════════════════════════════════════════════════

async def profiling_middleware_dispatch(request: Request, call_next):
    """可挂载到 app.middleware("http") 的 profiling 中间件。

    触发条件（任一即可）:
      - 请求头 X-Profile: true
      - 查询参数 ?profile=1
      - EVO_PROFILE_ENABLED=true 且路径以 /api/ 开头
    """
    if not HAS_PYINSTRUMENT:
        return await call_next(request)

    path = request.url.path

    # 避免 profile 端点自循环
    if path.startswith("/api/profile"):
        return await call_next(request)

    # 判断是否需要 profiling
    should_profile = (
        request.headers.get("X-Profile", "").lower() == "true"
        or request.query_params.get("profile", "") == "1"
        or (_profile_enabled and path.startswith("/api"))
    )

    if not should_profile:
        return await call_next(request)

    # ── 执行 profiling ──
    profiler = pyinstrument.Profiler()
    profiler.start()
    t0 = time.time()
    try:
        response = await call_next(request)
    finally:
        elapsed = (time.time() - t0) * 1000
        profiler.stop()
        flame = profiler.output_text(unicode=True, show_all=True)
        record_profile(path, elapsed, flame)
        # 只在头触发时打印到日志
        if request.headers.get("X-Profile", "").lower() == "true":
            print(f"[PROFILER] {path} — {elapsed:.1f}ms\n{flame[:2000]}\n{'='*60}")

    return response


# ═══════════════════════════════════════════════════════
# Profile 管理端点
# ═══════════════════════════════════════════════════════

router = APIRouter(prefix="/api/profile", tags=["profile"])


@router.get("/status")
async def profile_status():
    """查看 Profiler 状态和最近记录。"""
    return {
        "enabled": _profile_enabled,
        "available": HAS_PYINSTRUMENT,
        "sampling_active": _sampling_active,
        "records_count": len(_profile_records),
        "records": get_latest_profiles(10),
    }


@router.post("/enable")
async def profile_enable():
    """全局启用 Profiler（所有 /api 请求记录火焰图）。"""
    global _profile_enabled
    _profile_enabled = True
    return {"success": True, "message": "Profiler 已全局启用"}


@router.post("/disable")
async def profile_disable():
    """全局禁用 Profiler。"""
    global _profile_enabled
    _profile_enabled = False
    return {"success": True, "message": "Profiler 已禁用"}


@router.post("/start")
async def profile_start():
    """开始持续采样（直到调用 stop）。"""
    global _profiler_instance, _sampling_active
    if not HAS_PYINSTRUMENT:
        return JSONResponse(status_code=400, content={"error": "pyinstrument 未安装"})
    if _sampling_active:
        return {"success": True, "message": "已在采样中"}
    _profiler_instance = pyinstrument.Profiler()
    _profiler_instance.start()
    _sampling_active = True
    return {"success": True, "message": "持续采样已开始"}


@router.post("/stop")
async def profile_stop():
    """停止持续采样并返回火焰图结果。"""
    global _profiler_instance, _sampling_active
    if not _sampling_active or _profiler_instance is None:
        return JSONResponse(status_code=400, content={"error": "未在采样中"})
    try:
        _profiler_instance.stop()
        text_output = _profiler_instance.output_text(unicode=True, show_all=True)
        html_output = _profiler_instance.output_html()
        
        # 保存 HTML 火焰图到文件
        html_path = Path("_profile_output.html")
        html_path.write_text(html_output, encoding="utf-8")
        
        result = {
            "success": True,
            "message": "采样完成",
            "flame_text": text_output,
            "html_report": str(html_path.absolute()),
        }
        record_profile("/api/profile/stop", 0, text_output)
        return result
    finally:
        _profiler_instance = None
        _sampling_active = False


@router.get("/report")
async def profile_report():
    """获取最近一条火焰图报告（文本格式）。"""
    records = get_latest_profiles(1)
    if not records:
        return {"success": True, "data": None, "message": "暂无 profile 记录"}
    return {
        "success": True,
        "data": records[0],
        "hint": "使用 X-Profile: true 请求头触发单次 profiling",
    }


@router.get("/export")
async def profile_export():
    """导出所有 profile 记录为 JSON。"""
    return {
        "success": True,
        "count": len(_profile_records),
        "records": list(_profile_records),
    }
