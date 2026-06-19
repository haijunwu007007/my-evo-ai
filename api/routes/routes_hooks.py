"""
AUTO-EVO-AI V0.1 — Hooks拦截器 API
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from modules.hooks import get_hooks

router = APIRouter()


class RuleRequest(BaseModel):
    name: str
    pattern: str
    action: str = "block"
    rule_type: str = "pre_exec"
    description: str = ""


class CheckRequest(BaseModel):
    command: str


class UpdateRuleRequest(BaseModel):
    rule_id: str
    updates: dict


@router.post("/api/v1/hooks/check")
async def hooks_check(req: CheckRequest):
    h = get_hooks()
    result = h.check_pre_exec(req.command)
    return {"success": True, **result}


@router.get("/api/v1/hooks/rules")
async def hooks_rules():
    h = get_hooks()
    return {"success": True, "rules": h.get_rules()}


@router.post("/api/v1/hooks/rules")
async def hooks_add_rule(req: RuleRequest):
    h = get_hooks()
    r = h.add_rule(req.name, req.pattern, req.action, req.rule_type, req.description)
    return {"success": True, "rule": {"id": r.id, "name": r.name, "action": r.action}}


@router.put("/api/v1/hooks/rules")
async def hooks_update_rule(req: UpdateRuleRequest):
    h = get_hooks()
    ok = h.update_rule(req.rule_id, **req.updates)
    return {"success": True, "updated": ok}


@router.delete("/api/v1/hooks/rules/{rule_id}")
async def hooks_delete_rule(rule_id: str):
    h = get_hooks()
    ok = h.delete_rule(rule_id)
    return {"success": True, "deleted": ok}


@router.get("/api/v1/hooks/logs")
async def hooks_logs(limit: int = 200):
    h = get_hooks()
    return {"success": True, "logs": h.get_audit_logs(limit)}


@router.get("/api/v1/hooks/status")
async def hooks_status():
    h = get_hooks()
    return {"success": True, **h.get_status()}
