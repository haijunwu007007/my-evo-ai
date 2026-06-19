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
from core.logging_config import get_logger
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI
from api.infra import app, registry, manager, _module_activity, _START_TIME, BASE_DIR

logger = get_logger("evo.api")


def _mount_vue_frontend():
    """挂载 Vue 3 SPA (/app) + 旧版 Dashboard (/dashboard)"""
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse, JSONResponse
    from pathlib import Path

    vue_dist = BASE_DIR / "frontend" / "dist"
    if vue_dist.is_dir():
        def _nocache(resp: FileResponse) -> FileResponse:
            resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            resp.headers["Pragma"] = "no-cache"
            resp.headers["Expires"] = "0"
            return resp

        @app.get("/app", include_in_schema=False)
        async def _spa_root():
            idx = vue_dist / "index.html"
            return _nocache(FileResponse(str(idx), media_type="text/html")) if idx.exists() else JSONResponse(status_code=404, content={"error":"SPA not built"})

        @app.get("/app/{spa_path:path}", include_in_schema=False)
        async def _spa_handler(spa_path: str):
            target = vue_dist / spa_path
            if target.is_file():
                return _nocache(FileResponse(str(target)))
            idx = vue_dist / "index.html"
            if idx.exists():
                return _nocache(FileResponse(str(idx), media_type="text/html"))
            return JSONResponse(status_code=404, content={"error": "SPA not built"})

        # 前端静态文件（i18n.js 等）
        frontend_dir = BASE_DIR / "frontend"
        js_path = frontend_dir / "i18n.js"
        if js_path.exists():
            @app.get("/i18n.js", include_in_schema=False)
            async def _serve_i18n():
                return FileResponse(str(js_path), media_type="application/javascript")
            logger.info(f"[STATIC] i18n.js 已挂载")

        # 根路径 → 简易聊天界面（普通用户入口）
        chat_html = frontend_dir / "chat.html"
        if chat_html.exists():
            @app.get("/", include_in_schema=False)
            async def _chat_root():
                return _nocache(FileResponse(str(chat_html), media_type="text/html"))
            logger.info(f"[CHAT] 聊天界面已挂载: /")

        # 商业版管理后台
        _admin_html = BASE_DIR / "frontend" / "admin.html"
        if _admin_html.exists():
            @app.get("/admin", include_in_schema=False)
            async def serve_admin():
                return FileResponse(str(_admin_html), media_type="text/html")
            logger.info(f"[ADMIN] 管理后台已挂载: {_admin_html}")

        # Workflow 画布 — 从 routes_new_features 模块获取内联 HTML
        try:
            from api.routes.routes_new_features import _WORKFLOW_HTML
            @app.get("/workflow", include_in_schema=False)
            async def serve_workflow():
                from fastapi.responses import HTMLResponse
                return HTMLResponse(_WORKFLOW_HTML)
            logger.info("[WORKFLOW] 可视化画布已挂载: /workflow")
        except ImportError:
            logger.warning("[WORKFLOW] 未找到 workflow HTML (routes_new_features 未加载)")

        # 非 API/App 路径兜底 + 特定文件覆盖
        _OVERRIDE = {
            "enterprise.html": "enterprise.html",
            "company.html": "company.html",
            "deploy.html": "deploy.html",
            "capabilities": "capabilities.html",
            "oss-distiller": "oss-distiller.html",
            "codebase": "codebase.html",
            "self-evolve": "self_evolve.html",
            "permission": "permission.html",
            "memory": "memory.html",
            "multi-agent": "multi_agent.html",
            "desktop": "desktop.html",
            "rbac": "rbac.html",
            "channel": "channel.html",
            "deploy": "deploy.html",
            "canvas": "canvas.html",
            "workflow": "workflow.html",
            "automations": "automations.html",
        }

        @app.get("/{path:path}", include_in_schema=False)
        async def _spa_catchall(path: str):
            if path.startswith("api/") or path.startswith("app/"):
                return JSONResponse(status_code=404, content={"error": "not_found"})
            # 检查覆盖文件
            if path in _OVERRIDE:
                fp = BASE_DIR / "frontend" / _OVERRIDE[path]
                if fp.exists():
                    return FileResponse(str(fp))
            # 兜底返回聊天界面
            if chat_html.exists():
                resp = FileResponse(str(chat_html), media_type="text/html")
                resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
                resp.headers["Pragma"] = "no-cache"
                resp.headers["Expires"] = "0"
                return resp
            return JSONResponse(status_code=404, content={"error": "chat.html not found"})
        logger.info(f"[VUE] SPA 已挂载: {vue_dist} -> /app /*")
    else:
        logger.warning("[VUE] frontend/dist 不存在，请先执行 cd frontend && npm run build")


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
    # 环境变量检查
    _env_checks = [
        ("ZHIPU_API_KEY", "智谱 GLM-4 (LLM 对话)"),
        ("OPENAI_API_KEY", "OpenAI (备用 LLM)"),
        ("STABILITY_API_KEY", "Stability AI (图片生成)"),
        ("SMTP_HOST", "邮件发送"),
        ("ALIPAY_APP_ID", "支付宝支付"),
    ]
    for _env_name, _env_desc in _env_checks:
        if os.environ.get(_env_name):
            logger.info(f"  [OK] {_env_desc} — 已配置")
        else:
            logger.info(f"  [WAIT] {_env_desc} — 未配置（不影响核心功能）")

    # 清理 builtins 兼容层（仅清理 modules._base.compat 注入的）
    try:
        from modules._base.compat import cleanup_compat
        cleanup_compat()
        logger.info("[COMPAT] builtins 兼容层已清理")
    except Exception:
        pass

    # 初始化可观测性
    try:
        from core.telemetry import init_telemetry
        init_telemetry()
    except Exception:
        pass

    t0 = time.time()
    registry.auto_discover("modules")
    lazy_count = len(registry._pending_modules)
    logger.info(
        f"已注册 {lazy_count} 个模块（lazy），"
        f"已有 {len(registry.modules)} 个已加载模块"
    )
    # 预热前10个核心模块（让modules_loaded>0，非懒加载）
    _eager_names = list(registry._pending_modules.keys())[:10]
    if _eager_names:
        logger.info(f"[EAGER] 预热加载前 {len(_eager_names)} 个核心模块...")
        for _nm in _eager_names:
            try:
                import importlib as _il
                _m = _il.import_module(f"modules.{_nm}")
                if _m:
                    registry.modules[_nm] = _m
                    registry._pending_modules.pop(_nm, None)
            except Exception:
                pass
        logger.info(f"[EAGER] 已加载 {len(registry.modules)} 个模块")
    logger.info(f"启动耗时: {time.time()-t0:.1f}s — 部分模块已预热，其余按需加载")

    # 挂载前端
    _mount_vue_frontend()

    # 启动核心引擎
    try:
        from api.routes.routes_scheduler import start_engines
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

    # 扫描外部 MCP 服务器（异步，不阻塞启动）
    try:
        from api.routes.routes_mcp import scan_external_mcp_servers as _mcp_scan
        asyncio.create_task(_mcp_scan())
    except Exception as _e:
        logger.warning(f"[MCP] 外部扫描启动异常: {_e}")

    # 重新初始化技能（MCP 桥接需等 MCP 扫描完成后）
    try:
        from api.routes.routes_skills import init_skills as _reinit_skills
        asyncio.create_task(asyncio.to_thread(_reinit_skills))
    except Exception as _e:
        logger.warning(f"[SKILL] 重初始化异常: {_e}")

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
        from api.routes.routes_scheduler import stop_engines
        await stop_engines()
        logger.info("[SHUTDOWN] 所有引擎已停止")
    except Exception as e:
        logger.warning(f"[SHUTDOWN] 引擎停止异常: {e}")

    # 清理 builtins 兼容层
    try:
        from modules._base.compat import cleanup_compat
        cleanup_compat()
        logger.info("[SHUTDOWN] builtins 兼容层已清理")
    except Exception:
        pass

    # 关闭SQLite连接
    _cleanup_sqlite()
    logger.info("[SHUTDOWN] SQLite 连接已清理")


# ═══════════════════════════════════════════════════════
# 模块预热（上市级 — 启动时预热50个核心模块）
# ═══════════════════════════════════════════════════════

async def warmup_modules():
    """批次预热模块 — 每次尝试50个，失败自动跳过并日志"""
    fast = os.environ.get("EVO_FAST_START", "").lower() in ("1", "true", "yes")
    if fast:
        logger.info("[WARMUP] 快速模式，跳过预热")
        return

    await asyncio.sleep(0.5)
    candidates = list(registry._pending_modules.keys())[:50]
    if not candidates:
        logger.info("[WARMUP] 无待加载模块")
        return

    ok, fail = 0, 0
    for name in candidates:
        try:
            mod = await asyncio.wait_for(registry.lazy_load_module(name), timeout=5)
            if mod is None:
                continue
            init = getattr(mod, "initialize", None)
            if init:
                if asyncio.iscoroutinefunction(init):
                    await init()
                else:
                    init()
            ok += 1
        except (TimeoutError, Exception):
            fail += 1
    logger.info(f"[WARMUP] {ok} 模块预热成功 / {fail} 失败 / {len(candidates)} 尝试")

    # 后台持续加载剩余pending模块
    async def bulk_load_task():
        await asyncio.sleep(5)
        while True:
            remaining = len(registry._pending_modules)
            if remaining == 0:
                await asyncio.sleep(120)
                continue
            batch = list(registry._pending_modules.keys())[:30]
            loaded = 0
            for name in batch:
                try:
                    mod = await asyncio.wait_for(registry.lazy_load_module(name), timeout=5)
                    if mod: loaded += 1
                except:
                    pass
            if loaded:
                logger.info(f"[BULK-LOAD] 后台加载 {loaded}/{len(batch)} 模块 (剩余 {remaining})")
            await asyncio.sleep(30)  # 每30秒加载一批

    asyncio.create_task(bulk_load_task())


# ═══════════════════════════════════════════════════════
# 心跳 & 后台循环任务
# ═══════════════════════════════════════════════════════

async def heartbeat_task():
    await asyncio.sleep(5)
    while True:
        await asyncio.sleep(30)
        try:
            registry.get_all_health()
        except Exception:
            pass


async def activity_broadcast_task():
    await asyncio.sleep(8)
    while True:
        await asyncio.sleep(10)
        try:
            await manager.broadcast({"type": "evt:activity_tick", "timestamp": datetime.now().isoformat()})
        except Exception:
            pass


async def sysmon_broadcast_task():
    await asyncio.sleep(10)
    while True:
        await asyncio.sleep(30)
        try:
            for mod_name in list(registry.modules.keys())[:5]:
                mod = registry.modules.get(mod_name)
                if mod is None:
                    mod = await registry.lazy_load_module(mod_name)
                if mod and hasattr(mod, "get_metrics"):
                    r = mod.get_metrics()
                    if isinstance(r, dict) and r.get("success"):
                        await manager.broadcast({"type": "sysmon_metrics", "data": r["metrics"], "timestamp": datetime.now().isoformat()})
        except Exception as e:
            logger.warning(f"[SYSMON] 广播系统指标失败: {e}")


async def auto_heal_task():
    """修复出错模块 + 持续尝试 pending 模块"""
    await asyncio.sleep(15)
    while True:
        await asyncio.sleep(60)
        try:
            # 修复出错的模块
            all_health = registry.get_all_health()
            for name, health in all_health.items():
                if health.get("status") in ("error", "timeout"):
                    logger.info(f"[AUTO-HEAL] 尝试恢复: {name}")
                    registry.modules.pop(name, None)
                    await registry.lazy_load_module(name)
            # 尝试加载 pending 模块（每次最多10个）
            pending = [n for n in registry._pending_modules.keys() if n not in all_health or all_health[n].get("status") != "ok"]
            for name in pending[:10]:
                try:
                    await asyncio.wait_for(registry.lazy_load_module(name), timeout=5)
                except:
                    pass
        except Exception:
            pass


async def hot_reload_task():
    await asyncio.sleep(10)
    while True:
        await asyncio.sleep(30)
        try:
            added = registry.rescan_modules("modules")
            if added:
                logger.info(f"[HOT-RELOAD] +{added} 新模块")
        except Exception as e:
            logger.warning(f"[HOT-RELOAD] 扫描异常: {e}")


# 挂载 lifespan 到 app
app.router.lifespan_context = lifespan
