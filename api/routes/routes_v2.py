"""API v2 路由 — 版本化入口"""
from fastapi import APIRouter
from api._response import ok, fail
from api.agent_tools import exec_tool, list_tools

router = APIRouter(prefix="/api/v2", tags=["v2"])

@router.get("/tools")
async def v2_list_tools():
    return ok({"tools": [{"name": t["name"], "cat": t["category"]} for t in list_tools()]})

@router.post("/tools/exec")
async def v2_exec_tool(name: str, args: dict = {}):
    r = exec_tool(name, args)
    return ok({"tool": name, "result": r.get("data", "")})

@router.get("/status")
async def v2_status():
    from api._multi_worker import WORKERS
    return ok({"version": "v2", "workers": WORKERS, "tools": len(list_tools())})
