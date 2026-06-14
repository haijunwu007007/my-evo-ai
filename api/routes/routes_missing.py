"""补充缺失的API端点：dashboard/data / enterprise / services / gateway/templates / rag/search / notify/providers / modules/stats / v2/modules"""
from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from typing import Optional
import httpx, json, time
from pathlib import Path
from core.logging_config import get_logger

logger = get_logger("evo.api.missing")
router = APIRouter()

@router.get("/api/v1/notify/providers")
async def notify_providers():
    return {"success": True, "providers": [], "count": 0, "note": "通知提供商管理功能待实现"}

@router.get("/api/v1/modules/stats")
async def modules_stats():
    mod_dir = Path(__file__).parent.parent.parent / "modules"
    files = list(mod_dir.glob("*.py")) if mod_dir.exists() else []
    sizes = [f.stat().st_size for f in files if f.name != "__init__.py"]
    return {
        "success": True, "total_files": len(files),
        "total_size_kb": round(sum(sizes)/1024, 1),
        "avg_size_kb": round(sum(sizes)/len(sizes)/1024, 1) if sizes else 0,
        "note": "模块文件系统统计"
    }

@router.get("/api/v2/modules")
async def modules_v2():
    return {"success": True, "version": "v2", "modules": [], "count": 0, "note": "v2 API 暂未开放"}

@router.get("/api/v1/dashboard/data")
async def dashboard_data():
    """仪表盘聚合数据"""
    data = {"success": True, "timestamp": time.time()}
    try:
        async with httpx.AsyncClient(timeout=5) as c:
            r = await c.get("http://127.0.0.1:8765/api/v1/status")
            if r.status_code == 200:
                s = r.json()
                data["status"] = s.get("status", "running")
                data["version"] = s.get("version", "V0.1")
                data["modules"] = s.get("modules_files", 0)
                data["system"] = s.get("system", "AUTO-EVO-AI")
    except Exception:
        data["status"] = "unknown"

    try:
        async with httpx.AsyncClient(timeout=5) as c:
            r = await c.get("http://127.0.0.1:8765/api/v1/version")
            if r.status_code == 200:
                v = r.json()
                data["api_version"] = v.get("version", "")
                data["build"] = v.get("build", "")
    except Exception:
        pass

    try:
        async with httpx.AsyncClient(timeout=5) as c:
            r = await c.get("http://127.0.0.1:8765/api/v1/health")
            if r.status_code == 200:
                data["health"] = r.json()
    except Exception:
        pass

    try:
        async with httpx.AsyncClient(timeout=8) as c:
            r = await c.get("http://127.0.0.1:8765/api/v1/modules")
            if r.status_code == 200:
                m = r.json()
                modules = m.get("modules", [])
                cat_count = {}
                for mo in modules:
                    cat = mo.get("category", "其他")
                    cat_count[cat] = cat_count.get(cat, 0) + 1
                data["module_count"] = len(modules)
                data["module_categories"] = cat_count
    except Exception:
        pass

    try:
        async with httpx.AsyncClient(timeout=8) as c:
            r = await c.get("http://127.0.0.1:8765/api/v1/skills")
            if r.status_code == 200:
                skills = r.json()
                data["skill_count"] = len(skills.get("skills", skills.get("data", [])))
    except Exception:
        pass

    return data

@router.get("/api/v1/enterprise")
async def enterprise_status():
    return {"success": True, "status": "available",
        "features": {"tenant_management": False,"sso": False,"audit_log": False,"rbac": False,"api_key_management": True,"rate_limiting": True},
        "note": "企业功能开发中，请联系管理员获取完整版本"}

@router.get("/api/v1/services")
async def services_list():
    services = []
    endpoints = [
        ("API服务", "/api/v1/health", "运行中"),("智能聊天", "/api/v1/smart", "运行中"),
        ("Agent引擎", "/api/v1/agent/run", "运行中"),("技能系统", "/api/v1/skills", "运行中"),
        ("模块系统", "/api/v1/modules", "运行中"),("MCP集成", "/api/v1/mcp/servers", "运行中"),
        ("A2A通信", "/api/v1/a2a/agents", "运行中"),("RAG知识库", "/api/v1/rag/documents", "运行中"),
        ("工作流", "/api/v1/workflows", "运行中"),("定时任务", "/api/v1/scheduler/tasks", "运行中"),
        ("连接器", "/api/v1/connectors", "运行中"),("Gateway网关", "/api/v1/gateway/health", "运行中"),
    ]
    for name, ep, status in endpoints:
        try:
            async with httpx.AsyncClient(timeout=3) as c:
                r = await c.get(f"http://127.0.0.1:8765{ep}")
                services.append({"name": name, "endpoint": ep, "status": "healthy" if r.status_code == 200 else "error", "code": r.status_code})
        except Exception:
            services.append({"name": name, "endpoint": ep, "status": "unreachable", "code": 0})
    return {"success": True, "services": services, "count": len(services)}

@router.get("/api/v1/gateway/templates")
async def gateway_templates():
    try:
        async with httpx.AsyncClient(timeout=5) as c:
            r = await c.get("http://127.0.0.1:8765/api/v1/gateway/health")
            if r.status_code != 200:
                return {"success": True, "templates": [], "note": "Gateway服务未完全启动"}
    except Exception:
        return {"success": True, "templates": [], "note": "Gateway服务未启动"}
    db_path = Path(__file__).parent.parent.parent / "connectors" / "integrations_db.json"
    if db_path.exists():
        try:
            db = json.loads(db_path.read_text(encoding="utf-8"))
            templates = [{"slug": k, "name": v.get("name", k), "category": v.get("category", "其他"),
                          "auth_type": v.get("auth_type", "oauth2"), "description": v.get("description", "")[:200]}
                         for k, v in db.items()]
            return {"success": True, "templates": templates, "count": len(templates)}
        except Exception:
            pass
    return {"success": True, "templates": [], "note": "暂无集成模板"}

@router.get("/api/v1/rag/search")
async def rag_search(q: str = Query("", description="搜索关键词")):
    if not q:
        return {"success": True, "results": [], "note": "请提供搜索关键词 ?q=xxx"}
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(f"http://127.0.0.1:8765/api/v1/rag/search?q={q}")
            if r.status_code == 200:
                return r.json()
    except Exception:
        pass
    return {"success": True, "results": [], "note": f"搜索 '{q}' 未找到结果，可尝试其他关键词"}
