"""工具代理桥接路由 — 合并17个<1KB的轻量路由文件

包含：Gitea/Hoppscotch/Nextcloud/Superset/Stirling-PDF/OpenClaw/Metabase/
      HomeAssistant/Vaultwarden/Plane/NextChat + WS/v2/Company/Workflows/GiteaSync/Hub
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from fastapi.responses import FileResponse, RedirectResponse
from pathlib import Path
import urllib.request, json, os, asyncio
from api.infra import registry
from api._response import ok, fail
from api.agent_tools import exec_tool, list_tools
from core.logging_config import get_logger

logger = get_logger("evo.routes_tool_proxies")
router = APIRouter()

# ── 静态页面 ──
ROOT = Path(__file__).resolve().parent.parent.parent

# ── 外部服务基础地址映射 ──
_HOSTS = {
    "gitea": os.environ.get("GITEA_URL", "http://localhost:3000"),
    "hoppscotch": os.environ.get("HOPSCOTCH_URL", "http://localhost:3010"),
    "nextcloud": os.environ.get("NEXTCLOUD_URL", "http://localhost:8080"),
    "superset": os.environ.get("SUPERSET_URL", "http://localhost:8088"),
    "stirling_pdf": os.environ.get("STIRLING_PDF_URL", "http://127.0.0.1:8081"),
    "openclaw": os.environ.get("OPENCLAW_URL", "http://127.0.0.1:3002"),
    "metabase": os.environ.get("METABASE_URL", "http://localhost:3000"),
    "homeassistant": os.environ.get("HOMEASSISTANT_URL", "http://localhost:8123"),
    "vaultwarden": os.environ.get("VAULTWARDEN_URL", "http://localhost:8080"),
    "plane": os.environ.get("PLANE_URL", "http://localhost:8080"),
    "nextchat": os.environ.get("NEXTCHAT_URL", "http://127.0.0.1:3099"),
}

def _check(url: str, timeout: int = 5, path: str = "") -> dict:
    """通用健康检查"""
    try:
        r = urllib.request.urlopen(url + path, timeout=timeout)
        return {"healthy": r.status == 200}
    except Exception as e:
        return {"healthy": False, "error": str(e)[:80]}

# ════════════════════════════════════════════
# Group A — 外部工具状态+健康检查（11个）
# ════════════════════════════════════════════

# ── Gitea (50k⭐) ──
@router.get("/api/v1/tools/gitea")
async def gitea_status():
    return {"name":"Gitea","version":"latest","status":"configured","url":_HOSTS["gitea"],"description":"轻量级自托管 Git 服务 — 代码托管、PR 审查、CI/CD"}

@router.get("/api/v1/tools/gitea/health")
async def gitea_health(): return _check(_HOSTS["gitea"], path="/api/v1/version")

# ── Hoppscotch (66k⭐) ──
@router.get("/api/v1/tools/hoppscotch")
async def hoppscotch_status():
    return {"available":True,"url":_HOSTS["hoppscotch"],"name":"Hoppscotch","description":"开源 API 测试工具 (66k⭐) — Postman替代品"}

@router.get("/api/v1/tools/hoppscotch/health")
async def hoppscotch_health(): return _check(_HOSTS["hoppscotch"], path="/api/health")

# ── Nextcloud (30k⭐) ──
@router.get("/api/v1/tools/nextcloud")
async def nc_status():
    return {"name":"Nextcloud","version":"latest","status":"configured","url":_HOSTS["nextcloud"],"description":"自托管企业网盘 — 文件同步/共享/协作/日历/联系人"}

@router.get("/api/v1/tools/nextcloud/health")
async def nc_health(): return _check(_HOSTS["nextcloud"], path="/status.php")

# ── Apache Superset ──
@router.get("/api/v1/tools/superset")
async def superset_status():
    return {"available":True,"url":_HOSTS["superset"],"name":"Apache Superset","description":"企业级数据可视化平台 — 拖拽式图表、Dashboard、SQL查询"}

@router.get("/api/v1/tools/superset/health")
async def superset_health(): return _check(_HOSTS["superset"], path="/api/v1/health")

# ── Stirling-PDF (76k⭐) ──
@router.get("/api/v1/tools/pdf")
async def pdf_status():
    ok = _check(_HOSTS["stirling_pdf"], path="/api/v1/info")["healthy"]
    return {"success":True,"available":ok,"host":_HOSTS["stirling_pdf"],"name":"Stirling-PDF (76k⭐) PDF工具箱"}

_PDF_OPS = [{"id":"merge","name":"合并PDF"},{"id":"split","name":"拆分PDF"},{"id":"compress","name":"压缩PDF"},{"id":"convert","name":"转PDF"},{"id":"ocr","name":"OCR识别"},{"id":"sign","name":"电子签名"}]

@router.get("/api/v1/tools/pdf/operations")
async def pdf_ops(): return {"success":True,"operations":_PDF_OPS}

# ── OpenClaw (373k⭐) ──
@router.get("/api/v1/tools/openclaw")
async def oc_status():
    ok = _check(_HOSTS["openclaw"])["healthy"] or _check(_HOSTS["openclaw"], path="/")["healthy"]
    return {"success":True,"available":ok,"url":_HOSTS["openclaw"],"name":"OpenClaw (373k⭐) AI助手网关"}

@router.get("/api/v1/tools/openclaw/channels")
async def oc_channels():
    return {"success":True,"available":_check(_HOSTS["openclaw"])["healthy"],"channels":["telegram","discord","whatsapp","slack","web"]}

# ── Metabase (45k⭐) ──
@router.get("/api/v1/tools/metabase")
async def mb_status():
    return {"name":"Metabase","version":"latest","status":"configured","url":_HOSTS["metabase"],"description":"轻量级 BI 分析工具 — SQL查询/可视化图表/Dashboard"}

@router.get("/api/v1/tools/metabase/health")
async def mb_health(): return _check(_HOSTS["metabase"], path="/api/health")

# ── Home Assistant (80k⭐) ──
@router.get("/api/v1/tools/homeassistant")
async def ha_status():
    return {"name":"Home Assistant","version":"latest","status":"configured","url":_HOSTS["homeassistant"],"description":"开源智能家居平台 — IoT设备控制/自动化场景/传感器监控"}

@router.get("/api/v1/tools/homeassistant/health")
async def ha_health(): return _check(_HOSTS["homeassistant"], path="/api/")

# ── Vaultwarden (40k⭐) ──
@router.get("/api/v1/tools/vaultwarden")
async def vw_status():
    return {"name":"Vaultwarden","version":"latest","status":"configured","url":_HOSTS["vaultwarden"],"description":"轻量密码管理器 — Bitwarden兼容/自托管凭证库"}

@router.get("/api/v1/tools/vaultwarden/health")
async def vw_health(): return _check(_HOSTS["vaultwarden"], path="/api/health")

# ── Plane (30k⭐) ──
@router.get("/api/v1/tools/plane")
async def plane_status():
    return {"name":"Plane","version":"latest","status":"configured","url":_HOSTS["plane"],"description":"开源项目管理 — Issue/Kanban/Sprint/文档 (Jira替代)"}

@router.get("/api/v1/tools/plane/health")
async def plane_health(): return _check(_HOSTS["plane"], path="/api/v1/health")

# ── ChatGPT-Next-Web ──
@router.get("/api/v1/tools/nextchat")
async def nextchat_status():
    ok = _check(_HOSTS["nextchat"])["healthy"]
    return {"success":True,"available":ok,"url":_HOSTS["nextchat"]}

@router.get("/nextchat", include_in_schema=False)
async def nextchat_redirect(): return RedirectResponse(url=_HOSTS["nextchat"])

# ════════════════════════════════════════════
# Group B — 功能性路由（6个）
# ════════════════════════════════════════════

# ── WebSocket 工具输出 ──
_ws_connections = {}

@router.websocket("/ws/tool")
async def websocket_tool(ws: WebSocket):
    await ws.accept()
    cid = id(ws)
    _ws_connections[cid] = ws
    try:
        while True:
            msg = json.loads(await ws.receive_text())
            name, args = msg.get("tool",""), msg.get("args",{})
            await ws.send_json({"type":"start","tool":name})
            result = exec_tool(name, args)
            await ws.send_json({"type":"result","tool":name,"data":result.get("data","")})
            await ws.send_json({"type":"done"})
    except WebSocketDisconnect:
        pass
    finally:
        _ws_connections.pop(cid, None)

# ── v2 路由已集中到 routes_v2.py，此处不再重复 ──

# ── 虚拟公司 API ──
from api.hub.company import get_status as _co_status, assign_task as _co_task, execute_tasks as _co_exec, get_stats as _co_stats

@router.get("/api/v1/company/status")
async def co_status(): return {"success":True,**_co_status()}

@router.get("/api/v1/company/stats")
async def co_stats(): return {"success":True,**_co_stats()}

@router.post("/api/v1/company/task")
async def co_task(data:dict):
    return await _co_task(data.get("department",""), data.get("task",""))

@router.post("/api/v1/company/execute")
async def co_exec(data:dict={}):
    return await _co_exec(data.get("department",""))

# ── 工作流编排 ──
from modules.workflow_orchestrator import run_workflow as _wf_run, list_workflows as _wf_list, get_executions as _wf_execs

@router.get("/api/v1/workflows")
async def wf_list(): return {"success":True,"workflows":_wf_list()}

@router.post("/api/v1/workflow/run/{workflow_id}")
async def wf_run(workflow_id:str):
    return await _wf_run(workflow_id)

@router.get("/api/v1/workflow/executions")
async def wf_execs(): return {"success":True,"executions":_wf_execs()}

# ── Gitea Issue 同步 ──
from modules.gitea_issue_sync import sync_to_coordinator as _gs_sync, get_sync_status as _gs_status

@router.get("/api/v1/gitea-sync/status")
async def gs_status(): return await _gs_status()

@router.post("/api/v1/gitea-sync/sync")
async def gs_sync(owner: str = Query(""), repo: str = Query("")):
    return await _gs_sync(owner, repo)

# ── 注册函数（兼容原各文件的 _register） ──
async def _register():
    registry.modules["routes_tool_proxies"] = __import__("api.routes.routes_tool_proxies", fromlist=["routes_tool_proxies"])
