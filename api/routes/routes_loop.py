"""LOOP 工程引擎 — 自主循环：发现→规划→执行→验证→迭代
Loop Engineering 范式: 设计 loop 来驱动 agent，而不是手动 prompt
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
import json, time, hashlib, sqlite3, threading, asyncio, os
from pathlib import Path
from datetime import datetime

router = APIRouter(prefix="/api/v1/loop", tags=["loop"])

_LOOP_DB = Path(__file__).resolve().parent.parent.parent / "data" / "loop_engine.db"
_LOOP_DB.parent.mkdir(exist_ok=True)
_local = threading.local()

def _db():
    if not hasattr(_local, 'conn') or _local.conn is None:
        _local.conn = sqlite3.connect(str(_LOOP_DB))
        _local.conn.row_factory = sqlite3.Row
        _local.conn.execute("PRAGMA journal_mode=WAL")
        _local.conn.executescript("""
            CREATE TABLE IF NOT EXISTS loops (
                id TEXT PRIMARY KEY, name TEXT, goal TEXT, state TEXT DEFAULT 'created',
                phase TEXT DEFAULT 'discovery', iteration INTEGER DEFAULT 0, max_iterations INTEGER DEFAULT 5,
                config TEXT DEFAULT '{}', result TEXT, created_at REAL, updated_at REAL
            );
            CREATE TABLE IF NOT EXISTS loop_steps (
                id TEXT PRIMARY KEY, loop_id TEXT, phase TEXT, action TEXT,
                input TEXT, output TEXT, status TEXT DEFAULT 'pending',
                started_at REAL, completed_at REAL, duration_ms REAL
            );
        """)
        _local.conn.commit()
    return _local.conn

class LoopRequest(BaseModel):
    name: str
    goal: str
    max_iterations: int = 5
    config: dict = {}

@router.get("/status")
async def status():
    conn = _db()
    active = conn.execute("SELECT COUNT(*) FROM loops WHERE state='running'").fetchone()[0]
    total = conn.execute("SELECT COUNT(*) FROM loops").fetchone()[0]
    return {"success": True, "active_loops": active, "total_loops": total, "engine": "active"}

@router.post("/create")
async def create_loop(req: LoopRequest):
    """创建新循环"""
    conn = _db()
    lid = hashlib.md5((req.name + str(time.time())).encode()).hexdigest()[:12]
    now = time.time()
    conn.execute(
        "INSERT INTO loops(id,name,goal,state,phase,iteration,max_iterations,config,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
        (lid, req.name, req.goal, 'created', 'discovery', 0, req.max_iterations, json.dumps(req.config), now, now)
    )
    conn.commit()
    return {"success": True, "id": lid, "message": "循环已创建"}

@router.post("/run/{lid}")
async def run_loop(lid: str):
    """执行循环：发现→规划→执行→验证→迭代"""
    conn = _db()
    loop = conn.execute("SELECT * FROM loops WHERE id = ?", (lid,)).fetchone()
    if not loop:
        return {"success": False, "error": "循环不存在"}

    conn.execute("UPDATE loops SET state='running', updated_at=? WHERE id=?", (time.time(), lid))
    conn.commit()

    async def _run():
        llm_key = os.environ.get("ZHIPU_API_KEY", "")
        max_iter = loop["max_iterations"]
        goal = loop["goal"]

        for iteration in range(max_iter):
            phases = ["discovery", "planning", "execution", "verification"]
            for phase in phases:
                prompt_map = {
                    "discovery": f"分析目标「{goal}」第{iteration+1}轮，发现需要的信息和依赖",
                    "planning": f"基于发现，制定第{iteration+1}轮执行计划",
                    "execution": f"执行第{iteration+1}轮计划中的步骤",
                    "verification": f"验证第{iteration+1}轮执行结果，是否达成目标？返回 success/fail 和改进建议",
                }
                prompt = prompt_map[phase]
                step_id = hashlib.md5((lid + phase + str(time.time())).encode()).hexdigest()[:12]
                start = time.time()

                # 使用 LLM
                import subprocess
                payload = json.dumps({"model": "GLM-4-Flash", "messages": [
                    {"role": "system", "content": "你是LOOP循环引擎的核心Agent，分析并执行任务。"},
                    {"role": "user", "content": prompt}
                ], "max_tokens": 2048})
                cmd = ['curl', '-s', '-X', 'POST',
                       'https://open.bigmodel.cn/api/paas/v4/chat/completions',
                       '-H', f'Authorization: Bearer {llm_key}',
                       '-H', 'Content-Type: application/json',
                       '-d', payload, '--connect-timeout', '15', '--max-time', '30']
                try:
                    r = subprocess.run(cmd, capture_output=True, timeout=35)
                    out = r.stdout.decode('utf-8', errors='replace')
                    data = json.loads(out) if out else {}
                    output = data.get("choices",[{}])[0].get("message",{}).get("content","(空)")
                except Exception as e:
                    output = f"LLM调用失败: {str(e)[:100]}"

                duration = (time.time() - start) * 1000
                conn.execute(
                    "INSERT INTO loop_steps(id,loop_id,phase,action,input,output,status,started_at,completed_at,duration_ms) VALUES(?,?,?,?,?,?,?,?,?,?)",
                    (step_id, lid, phase, prompt, prompt, output, 'completed', start, time.time(), duration)
                )
                conn.execute("UPDATE loops SET phase=?, iteration=?, updated_at=? WHERE id=?",
                             (phase, iteration, time.time(), lid))
                conn.commit()

            # 一轮结束后检查是否完成
            iters = iteration + 1
            if iters >= max_iter:
                break

        conn.execute("UPDATE loops SET state='completed', phase='done', result=?, updated_at=? WHERE id=?",
                     (f"完成 {max_iter} 轮循环", time.time(), lid))
        conn.commit()

    asyncio.create_task(_run())
    return {"success": True, "message": "循环已启动，异步执行中"}

@router.get("/list")
async def list_loops():
    conn = _db()
    rows = conn.execute("SELECT id,name,goal,state,phase,iteration,max_iterations,created_at FROM loops ORDER BY created_at DESC").fetchall()
    return {"success": True, "loops": [dict(r) for r in rows]}

@router.get("/steps/{lid}")
async def get_steps(lid: str):
    conn = _db()
    steps = conn.execute("SELECT phase,action,output,status,duration_ms,completed_at FROM loop_steps WHERE loop_id=? ORDER BY started_at", (lid,)).fetchall()
    return {"success": True, "steps": [dict(s) for s in steps]}
