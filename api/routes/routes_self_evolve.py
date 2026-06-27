# -*- coding: utf-8 -*-
from fastapi import APIRouter
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__),"..",".."))
from modules.self_evolve import SelfEvolveLearner

router = APIRouter(tags=["self-evolve"])
_learner = None

def _get():
    global _learner
    if _learner is None: _learner = SelfEvolveLearner()
    return _learner

@router.get("/api/v1/self-evolve/status")
async def get_status():
    l = _get()
    return {"status": "ok", **l.get_stats(), "active_strategies": 3}

@router.post("/api/v1/self-evolve/record")
async def record_task(agent: str, task_type: str, prompt: str, result: str, duration: float = 0):
    tid = _get().record(agent, task_type, prompt, result, duration)
    return {"task_id": tid}

@router.post("/api/v1/self-evolve/score")
async def score_task(task_id: int, score: float, feedback: str = ""):
    _get().score(task_id, score, feedback)
    return {"success": True}
