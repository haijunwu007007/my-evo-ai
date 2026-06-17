"""AUTO-EVO-AI V0.1 — 工作流 API 路由"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

router = APIRouter(prefix="/api/v1/workflow", tags=["workflow"])

from api.workflow.engine import get_engine
from api.workflow.executor import tool_executor, create_and_run
from api.workflow.planner import create_planner_prompt, parse_steps
from api.workflow.autonomous import get_agent

engine = get_engine()
engine._tool_executor = tool_executor

class StepDef(BaseModel):
    id: str = ""
    tool: str
    args: dict = {}
    depends_on: List[str] = []
    max_retries: int = 2
    timeout: int = 120
    label: str = ""

class CreateWorkflow(BaseModel):
    name: str
    steps: List[StepDef]
    description: str = ""
    owner: str = "user"

class RunGoal(BaseModel):
    goal: str
    max_steps: int = 10
    context: str = ""

@router.post("/create")
async def create(req: CreateWorkflow):
    steps = [s.model_dump() for s in req.steps]
    wf = engine.create(req.name, steps, req.description, req.owner)
    return {"ok": True, "wf_id": wf.wf_id}

@router.post("/{wf_id}/execute")
async def execute(wf_id: str):
    return engine.execute(wf_id)

@router.get("/{wf_id}")
async def get(wf_id: str):
    wf = engine.get(wf_id)
    if not wf:
        raise HTTPException(404)
    return wf.to_dict()

@router.get("")
async def list_all(owner: str = ""):
    ws = engine.list(owner)
    return {"ok": True, "workflows": [w.to_dict() for w in ws]}

@router.post("/plan")
async def plan(req: RunGoal):
    agent = get_agent()
    result = agent.plan(req.goal, req.context)
    return result

@router.post("/run-goal")
async def run_goal(req: RunGoal):
    agent = get_agent()
    result = agent.run(req.goal, req.max_steps)
    return result
