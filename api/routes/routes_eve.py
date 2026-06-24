"""EVE Agent 架构学习 API"""
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger("routes_eve")
router = APIRouter(prefix="/api/v1/eve", tags=["eve"])

class StepReq(BaseModel): action: str; params: dict = {}
class ApprovalReq(BaseModel): agent: str; action: str; reason: str
class ApprovalRsp(BaseModel): req_id: str; approve: bool; note: str = ""
class SandboxReq(BaseModel): code: str

@router.get("/status")
def eve_status():
    from modules.eve_learn import module_class
    return module_class().get_status()

@router.get("/concept/{concept}")
def eve_concept(concept: str = "overview"):
    from modules.eve_learn import get_eve_concept
    return get_eve_concept(concept)

@router.get("/agents")
def eve_agents():
    from modules.eve_learn import list_agents
    return {"success": True, "agents": list_agents(),
            "note": "EVE 风格：状态持久化到文件系统"}

@router.post("/agent/create")
def eve_create(name: str):
    from modules.eve_learn import create_agent
    return create_agent(name)

@router.delete("/agent/{agent_id}")
def eve_delete(agent_id: str):
    from modules.eve_learn import delete_agent
    return delete_agent(agent_id)

@router.post("/agent/{agent_id}/step")
def eve_step(agent_id: str, req: StepReq):
    from modules.eve_learn import execute_step
    return execute_step(agent_id, req.action, req.params)

@router.post("/sandbox/check")
def eve_sandbox(req: SandboxReq):
    from modules.eve_learn import sandbox_check
    return sandbox_check(req.code)

@router.post("/approval/create")
def eve_approval(req: ApprovalReq):
    from modules.eve_learn import approval_create
    return approval_create(req.agent, req.action, req.reason)

@router.post("/approval/respond")
def eve_approval_respond(req: ApprovalRsp):
    from modules.eve_learn import approval_respond
    return approval_respond(req.req_id, req.approve, req.note)
