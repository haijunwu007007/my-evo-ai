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
import atexit
import logging
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI
from api.infra import app, registry, manager, _module_activity, _START_TIME, BASE_DIR

logger = logging.getLogger("evo.api")

_cleanup_tasks: list = []

def _cleanup_sqlite():
    """清理引擎模块中的SQLite连接（防止ResourceWarning）"""
    import sqlite3, gc
    for obj in gc.get_objects():
        if isinstance(obj, sqlite3.Connection):
            try:
                obj.close()
            except Exception:
                pass

@asynccontextmanager
async def lifespan(app: FastAPI):
    """替代 @app.on_event('startup') 和 @app.on_event('shutdown')"""
    # ═══════════ STARTUP ═══════════
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
    logger.info(f"启动耗时: {time.time()-t0:.1f}s — 首次调用模块时按需加载")

    # 挂载前端
    _mount_vue_frontend()

    # 启动核心引擎
    try:
        from api.routes_scheduler import start_engines
        asyncio.create_task(start_engines())
        logger.info("[ENGINES] 调度器/事件引擎/任务队列 已启动")
    except Exception as e:
        logger.warning(f"[ENGINES] 引擎启动失败: {e}")

    # 后台任务
    asyncio.create_task(heartbeat_task())
    asyncio.create_task(activity_broadcast_task())
    asyncio.create_task(sysmon_broadcast_task())
    asyncio.create_task(auto_heal_task())
    asyncio.create_task(hot_reload_task())
    asyncio.create_task(warmup_modules())

    if sys.platform == 'win32':
        import threading
        import webbrowser
        def open_browser():
            time.sleep(2)
            webbrowser.open('http://localhost:8765/dashboard')
        threading.Thread(target=open_browser, daemon=True).start()

    yield  # 应用在此处运行

    # ═══════════ SHUTDOWN ═══════════
    logger.info("[SHUTDOWN] 正在关闭核心引擎...")
    try:
        from api.routes_scheduler import stop_engines
        await stop_engines()
        logger.info("[SHUTDOWN] 所有引擎已停止")
    except Exception as e:
        logger.warning(f"[SHUTDOWN] 引擎停止异常: {e}")

    # 关闭SQLite连接
    _cleanup_sqlite()
    logger.info("[SHUTDOWN] SQLite 连接已清理")

# 挂载 lifespan 到 app
import starlette.routing
app.router.lifespan_context = lifespan
