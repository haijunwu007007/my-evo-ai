"""录屏学习系统 — 录制→分析→技能生成→回放
记录人类操作演示，AI 分析生成可复用的自动化技能
"""

from fastapi import APIRouter, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional
import json, time, hashlib, sqlite3, threading, base64, os
from pathlib import Path
from datetime import datetime

router = APIRouter(prefix="/api/v1/learn", tags=["learn"])

_LEARN_DB = Path(__file__).resolve().parent.parent.parent / "data" / "learn_engine.db"
_LEARN_DB.parent.mkdir(exist_ok=True)
_local = threading.local()

def _db():
    if not hasattr(_local, 'conn') or _local.conn is None:
        _local.conn = sqlite3.connect(str(_LEARN_DB))
        _local.conn.row_factory = sqlite3.Row
        _local.conn.execute("PRAGMA journal_mode=WAL")
        _local.conn.executescript("""
            CREATE TABLE IF NOT EXISTS demonstrations (
                id TEXT PRIMARY KEY, name TEXT, description TEXT,
                steps TEXT DEFAULT '[]', skill_code TEXT,
                created_at REAL, updated_at REAL, use_count INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS recordings (
                id TEXT PRIMARY KEY, demo_id TEXT,
                action TEXT, selector TEXT, value TEXT, url TEXT,
                screenshot TEXT, timestamp REAL, order_num INTEGER
            );
        """)
        _local.conn.commit()
    return _local.conn

# ─── Models ───
class RecordAction(BaseModel):
    demo_id: str
    action: str          # click, input, scroll, navigate, screenshot
    selector: str = ""
    value: str = ""
    url: str = ""

class CreateDemoRequest(BaseModel):
    name: str
    description: str = ""

class AnalyzeRequest(BaseModel):
    demo_id: str

@router.get("/status")
async def status():
    conn = _db()
    dc = conn.execute("SELECT COUNT(*) FROM demonstrations").fetchone()[0]
    rc = conn.execute("SELECT COUNT(*) FROM recordings").fetchone()[0]
    return {"success": True, "demonstrations": dc, "recordings": rc, "engine": "ready"}

@router.post("/demo/create")
async def create_demo(req: CreateDemoRequest):
    """创建新的演示录制"""
    conn = _db()
    did = hashlib.md5((req.name + str(time.time())).encode()).hexdigest()[:12]
    now = time.time()
    conn.execute("INSERT INTO demonstrations(id,name,description,created_at,updated_at) VALUES(?,?,?,?,?)",
                 (did, req.name, req.description, now, now))
    conn.commit()
    return {"success": True, "id": did, "message": f"演示 '{req.name}' 已创建"}

@router.post("/record")
async def record_action(req: RecordAction):
    """录制一个操作步骤"""
    conn = _db()
    demo = conn.execute("SELECT * FROM demonstrations WHERE id=?", (req.demo_id,)).fetchone()
    if not demo:
        return {"success": False, "error": "演示不存在"}
    rid = hashlib.md5((req.demo_id + str(time.time())).encode()).hexdigest()[:16]
    max_order = conn.execute("SELECT MAX(order_num) FROM recordings WHERE demo_id=?", (req.demo_id,)).fetchone()[0] or 0
    conn.execute(
        "INSERT INTO recordings(id,demo_id,action,selector,value,url,timestamp,order_num) VALUES(?,?,?,?,?,?,?,?)",
        (rid, req.demo_id, req.action, req.selector, req.value, req.url, time.time(), max_order + 1)
    )
    conn.execute("UPDATE demonstrations SET updated_at=? WHERE id=?", (time.time(), req.demo_id))
    conn.commit()
    return {"success": True, "id": rid, "order": max_order + 1, "message": "步骤已录制"}

@router.post("/analyze/{demo_id}")
async def analyze_demo(demo_id: str):
    """AI 分析录制的操作，生成可复用技能代码"""
    conn = _db()
    recs = conn.execute("SELECT * FROM recordings WHERE demo_id=? ORDER BY order_num", (demo_id,)).fetchall()
    if not recs:
        return {"success": False, "error": "没有录制数据"}

    steps_text = "\n".join([f"{r['order_num']}. {r['action']}({r['selector']}) = '{r['value'][:50]}'" for r in recs])
    prompt = f"""分析以下桌面操作序列，生成一个可复用的自动化 Python 函数：

操作步骤:
{steps_text}

请生成一个函数 `def learned_skill():` 包含完整的操作步骤。
"""

    import subprocess
    llm_key = os.environ.get("ZHIPU_API_KEY", "")
    payload = json.dumps({"model": "GLM-4-Flash", "messages": [
        {"role": "system", "content": "你是一个桌面自动化专家，分析操作演示并生成可重用技能。"},
        {"role": "user", "content": prompt}
    ], "max_tokens": 4096})
    cmd = ['curl', '-s', '-X', 'POST',
           'https://open.bigmodel.cn/api/paas/v4/chat/completions',
           '-H', f'Authorization: Bearer {llm_key}',
           '-H', 'Content-Type: application/json',
           '-d', payload, '--connect-timeout', '15', '--max-time', '60']
    r = subprocess.run(cmd, capture_output=True, timeout=65)
    out = r.stdout.decode('utf-8', errors='replace')
    skill_code = ""
    try:
        data = json.loads(out)
        skill_code = data.get("choices",[{}])[0].get("message",{}).get("content","")
    except:
        skill_code = f"# LLM分析失败\n# 请人工检查\n{out[:200]}"

    conn.execute("UPDATE demonstrations SET skill_code=?, description=? WHERE id=?",
                 (skill_code, f"AI从{len(recs)}步操作自动生成", demo_id))
    conn.commit()
    return {"success": True, "skill_code": skill_code, "steps_count": len(recs)}

@router.get("/demo/{demo_id}")
async def get_demo(demo_id: str):
    conn = _db()
    demo = conn.execute("SELECT * FROM demonstrations WHERE id=?", (demo_id,)).fetchone()
    if not demo:
        return {"success": False, "error": "不存在"}
    recs = conn.execute("SELECT action,selector,value,url,order_num FROM recordings WHERE demo_id=? ORDER BY order_num", (demo_id,)).fetchall()
    return {"success": True, "demo": dict(demo), "recordings": [dict(r) for r in recs]}

@router.get("/list")
async def list_demos():
    conn = _db()
    rows = conn.execute("SELECT id,name,description,created_at,use_count FROM demonstrations ORDER BY created_at DESC").fetchall()
    return {"success": True, "demonstrations": [dict(r) for r in rows]}
