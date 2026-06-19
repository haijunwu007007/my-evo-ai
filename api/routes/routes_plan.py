"""
AUTO-EVO-AI V0.1 — 计划模式 API
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from modules.plan_mode import get_planner

router = APIRouter()


class PlanCreateRequest(BaseModel):
    title: str = "未命名计划"
    description: str = ""
    plan_type: str = "architecture"
    content: str = ""
    files: list[str] = []
    steps: list[dict] = []


class PlanFeedback(BaseModel):
    feedback: str = ""


@router.post("/api/v1/plan/activate")
async def plan_activate():
    p = get_planner()
    p.activate()
    return {"success": True, "active": True, "message": "计划模式已开启"}


@router.post("/api/v1/plan/deactivate")
async def plan_deactivate():
    p = get_planner()
    p.deactivate()
    return {"success": True, "active": False, "message": "计划模式已关闭"}


@router.post("/api/v1/plan/create")
async def plan_create(req: PlanCreateRequest):
    p = get_planner()
    r = p.create_plan(req.title, req.description, req.plan_type,
                      req.content, req.files, req.steps)
    return {"success": True, "plan": {
        "id": r.id, "title": r.title, "status": r.status,
        "created_at": r.created_at, "plan_type": r.plan_type,
    }}


@router.post("/api/v1/plan/approve")
async def plan_approve(fb: PlanFeedback = PlanFeedback()):
    p = get_planner()
    r = p.approve(fb.feedback)
    if not r:
        raise HTTPException(400, "没有待审批的计划")
    return {"success": True, "plan": {"id": r.id, "status": r.status, "approved_at": r.approved_at}}


@router.post("/api/v1/plan/reject")
async def plan_reject(fb: PlanFeedback = PlanFeedback()):
    p = get_planner()
    r = p.reject(fb.feedback)
    if not r:
        raise HTTPException(400, "没有待审批的计划")
    return {"success": True, "plan": {"id": r.id, "status": r.status, "feedback": r.feedback}}


@router.get("/api/v1/plan/status")
async def plan_status():
    p = get_planner()
    return {"success": True, **p.get_status()}


@router.get("/api/v1/plan/history")
async def plan_history(limit: int = 50):
    p = get_planner()
    return {"success": True, "plans": p.get_history(limit)}
