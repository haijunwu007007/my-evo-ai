"""Plugin 市场与管理 API

提供 Plugin 的安装/卸载/启停/搜索 API，
以及 Plugin 市场(本地+远程)浏览。
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from core.logging_config import get_logger
from modules._base.plugin_manager import plugin_manager

logger = get_logger("evo.api.plugins")
router = APIRouter()


# ── 数据模型 ──

class PluginInstallRequest(BaseModel):
    plugin_id: str
    source_url: Optional[str] = ""


# ── 全局状态 ──

_PLUGIN_MARKET = [
    # 内置核心 Plugin（预置列表）
    {"id": "llm-gateway",     "name": "LLM 网关",       "desc": "多模型 AI 调用网关",          "version": "V0.1", "author": "EvoAI", "stars": 0},
    {"id": "notify-center",   "name": "通知中心",       "desc": "13 通道消息推送",              "version": "V0.1", "author": "EvoAI", "stars": 0},
    {"id": "scheduler",       "name": "调度引擎",       "desc": "Cron 定时任务调度",            "version": "V0.1", "author": "EvoAI", "stars": 0},
    {"id": "event-engine",    "name": "事件引擎",       "desc": "事件驱动与规则引擎",            "version": "V0.1", "author": "EvoAI", "stars": 0},
    {"id": "webhook-handler", "name": "Webhook 处理",   "desc": "GitHub/通用 Webhook 接收处理",  "version": "V0.1", "author": "EvoAI", "stars": 0},
    {"id": "data-viz",       "name": "数据可视化",     "desc": "Dashboard 图表与数据展示",       "version": "V0.1", "author": "EvoAI", "stars": 0},
]


# ── API 端点 ──

@router.get("/api/v1/plugins")
async def list_plugins(enabled: Optional[bool] = None):
    """列出所有已安装的 Plugin"""
    result = []
    for pid, plugin in plugin_manager.all.items():
        meta = plugin_manager.all_metas.get(pid)
        if enabled is not None and meta and meta.enabled != enabled:
            continue
        result.append({
            "id": pid,
            "name": plugin.plugin_name,
            "version": plugin.plugin_version,
            "enabled": meta.enabled if meta else True,
            "hooks": meta.hooks if meta else [],
            "status": plugin.get_status().get("status", "unknown"),
        })
    return {"success": True, "plugins": result, "total": len(result)}


@router.get("/api/v1/plugins/{plugin_id}")
async def get_plugin(plugin_id: str):
    """获取单个 Plugin 详情"""
    plugin = plugin_manager.get(plugin_id)
    if not plugin:
        raise HTTPException(404, detail=f"Plugin {plugin_id} 未安装")
    meta = plugin_manager.all_metas.get(plugin_id)
    return {
        "success": True,
        "plugin": {
            "id": plugin.plugin_id,
            "name": plugin.plugin_name,
            "version": plugin.plugin_version,
            "status": plugin.get_status(),
            "health": plugin.health_check(),
            "actions": plugin.get_actions(),
            "enabled": meta.enabled if meta else True,
            "hooks": meta.hooks if meta else [],
        }
    }


@router.post("/api/v1/plugins/{plugin_id}/enable")
async def enable_plugin(plugin_id: str):
    """启用 Plugin"""
    ok = plugin_manager.enable(plugin_id)
    if not ok:
        raise HTTPException(404, detail=f"Plugin {plugin_id} 不存在")
    return {"success": True, "plugin_id": plugin_id, "enabled": True}


@router.post("/api/v1/plugins/{plugin_id}/disable")
async def disable_plugin(plugin_id: str):
    """停用 Plugin"""
    ok = plugin_manager.disable(plugin_id)
    if not ok:
        raise HTTPException(404, detail=f"Plugin {plugin_id} 不存在")
    return {"success": True, "plugin_id": plugin_id, "enabled": False}


@router.post("/api/v1/plugins/{plugin_id}/uninstall")
async def uninstall_plugin(plugin_id: str):
    """卸载 Plugin"""
    ok = plugin_manager.unregister(plugin_id)
    if not ok:
        raise HTTPException(404, detail=f"Plugin {plugin_id} 不存在或无法卸载")
    return {"success": True, "plugin_id": plugin_id, "action": "uninstalled"}


@router.post("/api/v1/plugins/install")
async def install_plugin(req: PluginInstallRequest):
    """安装 Plugin（本地扫描或市场下载）"""
    result = plugin_manager.install_from_market(req.plugin_id, req.source_url or "")
    return result


@router.post("/api/v1/plugins/scan")
async def scan_plugins():
    """扫描 modules/ 目录发现新 Plugin"""
    from pathlib import Path
    mod_dir = Path(__file__).parent.parent.parent / "modules"
    count = plugin_manager.scan_directory(str(mod_dir))
    return {"success": True, "discovered": count, "total": plugin_manager.count}


@router.get("/api/v1/plugins/market/available")
async def market_available():
    """获取 Plugin 市场可安装列表"""
    installed = set(plugin_manager.all.keys())
    available = [p for p in _PLUGIN_MARKET if p["id"] not in installed]
    return {"success": True, "plugins": available, "total": len(available)}


@router.get("/api/v1/plugins/hooks")
async def list_hooks():
    """列出所有 Hook 点及已注册的 Plugin"""
    from modules._base.plugin_manager import HOOKS
    hook_info = {}
    for name, hook in HOOKS.items():
        handlers = plugin_manager._hook_handlers.get(name, [])
        hook_info[name] = {
            "description": hook.description,
            "priority": hook.priority,
            "plugins": [{
                "id": pid,
                "name": plugin_manager.all.get(pid, object).__class__.__name__ if pid in plugin_manager.all else pid
            } for pid in handlers],
        }
    return {"success": True, "hooks": hook_info}
