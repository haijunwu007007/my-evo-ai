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

        # Dashboard（旧版）— 放在 catch-all 之前
        html_path = BASE_DIR / "index.html"
        if html_path.exists():
            @app.get("/dashboard", include_in_schema=False)
            async def serve_dashboard():
                from fastapi.responses import Response
                import os
                content = open(str(html_path), "rb").read()
                return Response(content=content, media_type="text/html",
                    headers={"Cache-Control": "no-cache, no-store, must-revalidate", "Pragma": "no-cache", "Expires": "0"})
            logger.info(f"[VUE] Dashboard 已挂载: {html_path}")

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

        # 非 API/App 路径兜底 → 聊天界面
        @app.get("/{path:path}", include_in_schema=False)
        async def _spa_catchall(path: str):
            if path.startswith("api/") or path.startswith("app/"):
                return JSONResponse(status_code=404, content={"error": "not_found"})
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
    """快速预热核心模块（优化版：数量减半、超时缩短、可跳过）"""
    fast = os.environ.get("EVO_FAST_START", "").lower() in ("1", "true", "yes")
    if fast:
        logger.info("[WARMUP] 快速模式，跳过预热")
        return

    await asyncio.sleep(0.5)  # 等 API 先就绪
    candidate_names = list(registry.classes.keys())[:20]
    if not candidate_names:
        candidate_names = list(registry._pending_modules.keys())[:20]
    if not candidate_names:
        logger.info("[WARMUP] 无待加载模块，跳过预热")
        return

    ok = 0
    start = 0
    for i, name in enumerate(candidate_names):
        if i >= 12:  # 最多预热 12 个
            break
        try:
            await asyncio.sleep(0)  # 不阻塞事件循环
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
            pass
    if ok:
        logger.info(f"[WARMUP] {ok}/{len(candidate_names)} 模块预热完成 ({time.time()-start:.1f}s)" if start else f"[WARMUP] {ok} 模块预热完成")


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
    await asyncio.sleep(15)
    while True:
        await asyncio.sleep(60)
        try:
            for name, health in registry.get_all_health().items():
                if health.get("status") in ("error", "timeout"):
                    logger.info(f"[AUTO-HEAL] 尝试恢复: {name}")
                    registry.modules.pop(name, None)
                    await registry.lazy_load_module(name)
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
