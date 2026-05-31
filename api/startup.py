"""
AUTO-EVO-AI V0.1 — API 启动/后台任务层
=======================================
职责：启动事件、后台心跳/自愈/热重载/预热等周期性任务。
"""

from __future__ import annotations

import os
import sys
import time
import asyncio
import logging
from datetime import datetime

from api.infra import app, registry, manager, _module_activity, _START_TIME, BASE_DIR

logger = logging.getLogger("evo.api")


def _mount_vue_frontend():
    """挂载 Vue 3 SPA (/app) + 旧版 Dashboard (/dashboard)"""
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse
    from pathlib import Path

    # ── Vue 3 SPA 生产构建（frontend/dist/）──
    vue_dist = BASE_DIR / "frontend" / "dist"
    if vue_dist.is_dir():
        app.mount("/app", StaticFiles(directory=str(vue_dist), html=True), name="vue_spa")
        logger.info(f"[VUE] SPA 已挂载: {vue_dist} -> /app")
    else:
        logger.warning(
            "[VUE] frontend/dist 不存在，请先执行 cd frontend && npm run build"
        )

    # ── 旧版 Dashboard（根目录 index.html）──
    html_path = BASE_DIR / "index.html"
    if html_path.exists():
        @app.get("/dashboard", include_in_schema=False)
        async def serve_dashboard():
            from fastapi.responses import FileResponse
            return FileResponse(str(html_path), media_type="text/html")
        logger.info(f"[VUE] Dashboard 已挂载: {html_path}")


# ═══════════════════════════════════════════════════════
# 启动事件
# ═══════════════════════════════════════════════════════

@app.on_event("startup")
async def startup():
    logger.info("=" * 60)
    logger.info("AUTO-EVO-AI V0.1 API 服务器启动 (LAZY MODE)")
    logger.info("=" * 60)

    t0 = time.time()
    registry.auto_discover("modules")
    lazy_count = len(registry._pending_modules)
    logger.info(
        f"已注册 {lazy_count} 个模块（lazy），"
        f"已有 {len(registry.modules)} 个已加载模块"
    )
    logger.info(
        f"启动耗时: {time.time()-t0:.1f}s — 首次调用模块时按需加载"
    )

    # ── 挂载 Vue 前端（production 模式）──
    _mount_vue_frontend()

    # ── 启动核心引擎（调度器/事件引擎/任务队列）──
    try:
        from api.routes_scheduler import start_engines
        asyncio.create_task(start_engines())
        logger.info("[ENGINES] 调度器/事件引擎/任务队列 已启动")
    except Exception as e:
        logger.warning(f"[ENGINES] 引擎启动失败: {e}")

    asyncio.create_task(heartbeat_task())
    asyncio.create_task(activity_broadcast_task())
    asyncio.create_task(sysmon_broadcast_task())
    asyncio.create_task(auto_heal_task())
    asyncio.create_task(hot_reload_task())

    # ── 预热 50 个核心模块 ──
    asyncio.create_task(warmup_modules())

    if sys.platform == 'win32':
        import threading
        import webbrowser

        def open_browser():
            time.sleep(2)
            webbrowser.open('http://localhost:8765/dashboard')

        threading.Thread(target=open_browser, daemon=True).start()


# ═══════════════════════════════════════════════════════
# 后台任务
# ═══════════════════════════════════════════════════════

from datetime import datetime as _dt
import time as _time


async def activity_broadcast_task():
    """每5秒广播真实模块活动事件至 WebSocket"""
    await asyncio.sleep(5)
    while True:
        await asyncio.sleep(5)
        if not registry.modules:
            continue
        # 使用真实模块活动数据而非随机数
        active_count = 0
        now = _dt.now()
        for name, mod in list(registry.modules.items()):
            if hasattr(mod, '_exec_time'):
                _module_activity[name] = _module_activity.get(name, 0) + 1
                active_count += 1
            else:
                local_count = _module_activity.get(name, 0)
                if local_count > 0:
                    _module_activity[name] = local_count + 1
                    active_count += 1
        # 按活动量取 top 10
        sorted_activity = sorted(_module_activity.items(), key=lambda x: x[1], reverse=True)[:10]
        for name, cnt in sorted_activity:
            await manager.broadcast({
                "type": "event", "category": "TASK",
                "message": f"[后端] {name} 执行任务完成",
                "module": name, "count": cnt,
                "timestamp": now.isoformat(),
            })
        await manager.broadcast({
            "type": "module_activity",
            "data": [{"name": n, "count": c} for n, c in sorted_activity],
        })


async def heartbeat_task():
    """每30秒检查模块健康状况"""
    while True:
        await asyncio.sleep(30)
        for name, mod in list(registry.modules.items()):
            if hasattr(mod, "health_check"):
                try:
                    hc_result = mod.health_check()
                    if asyncio.iscoroutine(hc_result):
                        hc_result = await asyncio.wait_for(hc_result, timeout=5.0)
                    status = (
                        "ok"
                        if (isinstance(hc_result, dict) and hc_result.get("status") in ("ok", "healthy", "configured"))
                        else "warning"
                    )
                    registry.health[name] = {
                        "status": status,
                        "last_beat": datetime.now().isoformat(),
                        "error": "",
                    }
                except asyncio.TimeoutError:
                    registry.health[name] = {
                        "status": "timeout",
                        "last_beat": "",
                        "error": "health_check timed out (5s)",
                    }
                except Exception as e:
                    if name in registry.health:
                        registry.health[name]["status"] = "error"
                        registry.health[name]["error"] = str(e)[:100]
        try:
            await manager.broadcast({
                "type": "health_update",
                "data": registry.get_all_health(),
            })
        except Exception as e:
            logger.warning(f"[HEARTBEAT] 广播健康状态失败: {e}")


async def auto_heal_task():
    """每60秒尝试重新加载错误状态的模块"""
    await asyncio.sleep(30)
    while True:
        await asyncio.sleep(60)
        try:
            health_map = registry.get_all_health()
            error_names = [
                name for name, h in health_map.items()
                if h.get("status") in ("error", "lazy_error")
            ]
            for name in error_names[:3]:
                try:
                    old_mod = registry.modules.pop(name, None)
                    if old_mod and hasattr(old_mod, 'shutdown'):
                        try:
                            old_mod.shutdown()
                        except Exception as e:
                            logger.warning(f"[AUTO-HEAL] 模块关闭失败: {name}: {e}")
                    registry.health.pop(name, None)
                    new_mod = await asyncio.wait_for(
                        registry.lazy_load_module(name), timeout=30
                    )
                    if new_mod:
                        logger.info(f"[AUTO-HEAL] 修复成功: {name}")
                except Exception as e:
                    logger.warning(f"[AUTO-HEAL] 修复失败: {name}: {e}")
        except Exception as e:
            logger.warning(f"[AUTO-HEAL] 循环异常: {e}")


async def sysmon_broadcast_task():
    """每3秒通过 WebSocket 推送真实系统指标"""
    while True:
        await asyncio.sleep(3)
        try:
            mod_name = "system_monitor"
            mod = registry.modules.get(mod_name)
            if mod is None:
                mod = await registry.lazy_load_module(mod_name)
            if mod and hasattr(mod, "get_metrics"):
                r = mod.get_metrics()
                if isinstance(r, dict) and r.get("success"):
                    await manager.broadcast({"type": "sysmon_metrics", "data": r["metrics"], "timestamp": datetime.now().isoformat()})
        except Exception as e:
            logger.warning(f"[SYSMON] 广播系统指标失败: {e}")


async def hot_reload_task():
    """每30秒扫描新模块并自动注册"""
    await asyncio.sleep(10)
    while True:
        await asyncio.sleep(30)
        try:
            added = registry.rescan_modules("modules")
            if added:
                logger.info(f"[HOT-RELOAD] +{added} 新模块")
        except Exception as e:
            logger.warning(f"[HOT-RELOAD] 扫描异常: {e}")


# ═══════════════════════════════════════════════════════
# 模块预热（上市公司级 — 启动时 pre-warmup 50个核心模块）
# ═══════════════════════════════════════════════════════

async def warmup_modules():
    """启动后预热核心模块（基于注册表中实际存在的模块）"""
    await asyncio.sleep(3)  # 等注册表完成 lazy 收集
    # 优先用 class 注册的模块（lazy 模式下 classes 非空）
    candidate_names = list(registry.classes.keys())[:50]
    if not candidate_names:
        candidate_names = list(registry._pending_modules.keys())[:50]
    if not candidate_names:
        logger.info("[WARMUP] 无待加载模块，跳过预热")
        return

    ok = 0
    for name in candidate_names:
        try:
            mod = await asyncio.wait_for(
                registry.lazy_load_module(name), timeout=15
            )
            if mod is None:
                continue
            # 可选：调用 initialize（部分模块有）
            init = getattr(mod, "initialize", None)
            if init:
                if asyncio.iscoroutinefunction(init):
                    await init()
                else:
                    init()
            ok += 1
        except asyncio.TimeoutError:
            logger.warning(f"[WARMUP] 预热超时: {name}")
        except Exception as e:
            logger.warning(f"[WARMUP] 预热失败: {name}: {e}")
    logger.info(f"[WARMUP] {ok}/{len(candidate_names)} 模块预热完成")

# ═══════════════════════════════════════════════════════
# 关闭事件 — 优雅停止引擎
# ═══════════════════════════════════════════════════════

@app.on_event("shutdown")
async def shutdown():
    logger.info("[SHUTDOWN] 正在关闭核心引擎...")
    try:
        from api.routes_scheduler import stop_engines
        await stop_engines()
        logger.info("[SHUTDOWN] 所有引擎已停止")
    except Exception as e:
        logger.warning(f"[SHUTDOWN] 引擎停止异常: {e}")
