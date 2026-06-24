"""AUTO-EVO-AI V0.1 — Mercury Skill 系统 API"""
from fastapi import APIRouter, Body
from modules.mercury_skills import (
    register_skill, get_skill, list_skills, execute_skill,
    set_token_budget, get_token_usage, get_status
)
router = APIRouter(prefix="/api/v1/mercury", tags=["mercury"])

@router.get("/status")
def status():
    return get_status()

@router.get("/skills")
def api_list_skills(access_level: str = "user"):
    return {"skills": list_skills(access_level)}

@router.get("/skills/{name}")
def api_get_skill(name: str):
    return get_skill(name)

@router.post("/skills/register")
def api_register(data: dict = Body(...)):
    return register_skill(data.get("name", ""), data.get("description", ""),
                          None, data.get("min_access_level", "user"),
                          data.get("token_cost", 10))

@router.post("/skills/execute")
def api_execute(data: dict = Body(...)):
    return execute_skill(data.get("name", ""), data.get("params"),
                         data.get("access_level", "user"),
                         data.get("token_budget"))

@router.get("/budget/{user_id}")
def api_get_budget(user_id: str):
    return get_token_usage(user_id)

@router.post("/budget/set")
def api_set_budget(data: dict = Body(...)):
    return set_token_budget(data.get("user_id", ""), data.get("budget", 1000))
