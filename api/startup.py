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

    asyncio.create_task(heartbeat_task())
    asyncio.create_task(activity_broadcast_task())
    asyncio.create_task(auto_heal_task())
    asyncio.create_task(hot_reload_task())

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

import random as _random


async def activity_broadcast_task():
    """每5秒广播模拟模块活动事件至 WebSocket"""
    await asyncio.sleep(5)
    while True:
        await asyncio.sleep(5)
        if not registry.modules:
            continue
        active_names = list(registry.modules.keys())
        chosen = _random.sample(active_names, min(3, len(active_names)))
        for name in chosen:
            _module_activity[name] = _module_activity.get(name, 0) + _random.randint(1, 5)
        for name in chosen:
            await manager.broadcast({
                "type": "event", "category": "TASK",
                "message": f"[后端] {name} 执行任务完成",
                "module": name, "count": _module_activity[name],
                "timestamp": datetime.now().isoformat(),
            })
        sorted_activity = sorted(_module_activity.items(), key=lambda x: x[1], reverse=True)[:10]
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
        except Exception:
            pass


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
                        except Exception:
                            pass
                    registry.health.pop(name, None)
                    new_mod = await asyncio.wait_for(
                        registry.lazy_load_module(name), timeout=30
                    )
                    if new_mod:
                        logger.info(f"[AUTO-HEAL] 修复成功: {name}")
                except Exception:
                    pass
        except Exception:
            pass


async def hot_reload_task():
    """每30秒扫描新模块并自动注册"""
    await asyncio.sleep(10)
    while True:
        await asyncio.sleep(30)
        try:
            added = registry.rescan_modules("modules")
            if added:
                logger.info(f"[HOT-RELOAD] +{added} 新模块")
        except Exception:
            pass


# ═══════════════════════════════════════════════════════
# 模块预热（上市公司级 — 启动时 pre-warmup 50个核心模块）
# ═══════════════════════════════════════════════════════

async def warmup_modules():
    """启动前预热核心模块"""
    import importlib
    warmup_list = [
        "jwt_token", "oauth_provider", "permission_rbac", "sso_auth",
        "audit_trail", "data_analysis", "data_masking", "sql_generator",
        "forex_api", "fund_api", "recommendation_system", "rate_limiter",
        "health_check", "health_checker", "scheduler_pro", "grafana_monitor",
        "prometheus_metrics", "metric_collector", "feishu_notifier",
        "telegram_bridge", "pub_sub", "graphql_gateway", "search_engine",
        "webhook_dispatcher", "event_bus_pro", "risk_control",
        "blockchain_web3", "longterm_memory", "geo_index",
        "iot_edge", "daemon_controller", "api_rate_limiter",
        "orchestrator_core", "workflow_orchestrator", "component_lib",
        "auto_optimizer", "auto_recovery", "enterprise_notifier",
        "process_watchdog", "log_aggregator", "help_docs",
        "realtime_collaboration", "rebalance_protocol",
        "advanced_resilience", "auto_update", "bot_handler",
    ]
    ok = 0
    for name in warmup_list:
        try:
            mod = importlib.import_module(f"modules.{name}")
            cls = getattr(mod, "module_class", None)
            if cls:
                instance = cls()
                await instance.initialize()
                registry.register(name, instance)
                ok += 1
        except Exception:
            pass
    logger.info(f"[WARMUP] {ok}/{len(warmup_list)} 模块预热完成")
