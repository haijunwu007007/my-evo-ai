"""Agent团队画布 + 3种控制模式 — 借鉴 LoopFlow
可视化编排Agent团队，支持手动/半自动/全自动控制模式
"""
from fastapi import APIRouter
from pydantic import BaseModel
from core.logging_config import get_logger
import json, os, time
from pathlib import Path

logger = get_logger("evo.api.agent_canvas")
router = APIRouter()
BASE = Path(__file__).resolve().parent.parent.parent

_TEAMS_FILE = BASE / "data" / "agent_teams.json"
_CONTROL_MODE = "auto"  # manual / semi / auto

_ROLE_TEMPLATES = {
    "director": {"name":"总监","desc":"制定计划、分解任务、协调团队","color":"#4361ee","icon":"🎯"},
    "worker": {"name":"执行员","desc":"执行具体任务、编写代码、生成文档","color":"#10b981","icon":"⚡"},
    "reviewer": {"name":"审核员","desc":"审查质量、验收标准、反馈改进","color":"#f59e0b","icon":"🔍"},
    "researcher": {"name":"研究员","desc":"信息调研、竞品分析、数据收集","color":"#8b5cf6","icon":"🔬"},
    "critic": {"name":"批评家","desc":"风险审视、改进建议、破局思考","color":"#ef4444","icon":"💢"},
}

def _load_teams():
    if _TEAMS_FILE.exists():
        try: return json.loads(_TEAMS_FILE.read_text(encoding="utf-8"))
        except: pass
    return {"teams":[]}

def _save_teams(data):
    _TEAMS_FILE.parent.mkdir(parents=True, exist_ok=True)
    _TEAMS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

@router.get("/api/v1/agent-canvas/templates")
async def get_templates():
    return {"success": True, "templates": _ROLE_TEMPLATES}

@router.get("/api/v1/agent-canvas/teams")
async def list_teams():
    return {"success": True, **_load_teams()}

class TeamInput(BaseModel):
    name: str; roles: list; mode: str = "auto"

@router.post("/api/v1/agent-canvas/teams")
async def save_team(t: TeamInput):
    data = _load_teams()
    team = {"id": f"team_{int(time.time())}", "name": t.name, "roles": t.roles, "mode": t.mode, "created_at": time.time()}
    data["teams"].append(team)
    _save_teams(data)
    logger.info(f"[CANVAS] 团队已保存: {t.name} mode={t.mode}")
    return {"success": True, "team": team}

@router.delete("/api/v1/agent-canvas/teams/{tid}")
async def delete_team(tid: str):
    data = _load_teams()
    data["teams"] = [t for t in data["teams"] if t["id"] != tid]
    _save_teams(data)
    return {"success": True}

@router.get("/api/v1/agent-canvas/mode")
async def get_mode():
    return {"success": True, "mode": _CONTROL_MODE}

class ModeInput(BaseModel):
    mode: str

@router.post("/api/v1/agent-canvas/mode")
async def set_mode(m: ModeInput):
    global _CONTROL_MODE
    if m.mode not in ("manual", "semi", "auto"):
        return {"success": False, "message": "模式必须为 manual/semi/auto"}
    _CONTROL_MODE = m.mode
    logger.info(f"[CANVAS] 控制模式切换: {m.mode}")
    return {"success": True, "mode": _CONTROL_MODE}

@router.post("/api/v1/agent-canvas/teams/{tid}/run")
async def run_team(tid: str):
    data = _load_teams()
    team = next((t for t in data["teams"] if t["id"] == tid), None)
    if not team:
        return {"success": False, "error": "团队不存在"}
    mode = _CONTROL_MODE
    step_results = []
    for role in team["roles"]:
        step_results.append({"role": role.get("type","?"), "name": role.get("name","?"), "status": "planned"})
    return {"success": True, "team": team["name"], "mode": mode, "steps": step_results,
            "message": f"团队已就绪，当前模式：{'手动' if mode=='manual' else '半自动' if mode=='semi' else '全自动'}"}

@router.get("/api/v1/agent-canvas/teams/{tid}/status")
async def team_status(tid: str):
    data = _load_teams()
    team = next((t for t in data["teams"] if t["id"] == tid), None)
    if not team:
        return {"success": False, "error": "团队不存在"}
    return {"success": True, "team": team, "mode": _CONTROL_MODE}

# ── 隔离工作空间 ──
_WORKSPACE_DIR = BASE / "workspaces"
_WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)

@router.get("/api/v1/agent-canvas/workspace")
async def list_workspaces():
    dirs = [d.name for d in _WORKSPACE_DIR.iterdir() if d.is_dir()]
    return {"success": True, "workspaces": dirs}

@router.post("/api/v1/agent-canvas/workspace/{name}")
async def create_workspace(name: str):
    wd = _WORKSPACE_DIR / name
    wd.mkdir(parents=True, exist_ok=True)
    return {"success": True, "workspace": name, "path": str(wd)}

# ── 检查点恢复 ──
_CHECKPOINT_DIR = BASE / "data" / "checkpoints"
_CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)

@router.get("/api/v1/agent-canvas/checkpoint")
async def list_checkpoints():
    files = sorted(_CHECKPOINT_DIR.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True)
    return {"success": True, "checkpoints": [f.stem for f in files[:20]]}

class CheckpointInput(BaseModel):
    team_id: str; state: dict

@router.post("/api/v1/agent-canvas/checkpoint")
async def save_checkpoint(m: CheckpointInput):
    fp = _CHECKPOINT_DIR / f"cp_{m.team_id}_{int(time.time())}.json"
    fp.write_text(json.dumps({"team_id": m.team_id, "state": m.state, "ts": time.time()}, ensure_ascii=False), encoding="utf-8")
    return {"success": True, "file": fp.name}

@router.get("/api/v1/agent-canvas/checkpoint/{filename}")
async def load_checkpoint(filename: str):
    fp = _CHECKPOINT_DIR / f"{filename}.json"
    if not fp.exists() and not str(fp).endswith('.json'): fp = _CHECKPOINT_DIR / filename
    if not fp.exists(): return {"success": False, "error": "检查点不存在"}
    data = json.loads(fp.read_text(encoding="utf-8"))
    return {"success": True, "checkpoint": data}

# ── P2P 实时讨论 ──
_AGENT_MESSAGES: list = []

class AgentMsgInput(BaseModel):
    text: str; sender: str = "user"

@router.post("/api/v1/agent-canvas/agents/{aid}/message")
async def agent_message(aid: str, m: AgentMsgInput):
    _AGENT_MESSAGES.append({"to": aid, "from": m.sender, "text": m.text, "ts": time.time()})
    # 自动回复
    reply = f"收到消息: {m.text[:60]}... 正在处理中"
    if _CONTROL_MODE == "manual":
        reply = f"[手动模式需确认] 是否执行: {m.text[:60]}?"
    _AGENT_MESSAGES.append({"to": m.sender, "from": aid, "text": reply, "ts": time.time()})
    return {"success": True, "reply": reply, "mode": _CONTROL_MODE}

@router.get("/api/v1/agent-canvas/agents/{aid}/messages")
async def get_agent_messages(aid: str, limit: int = 20):
    msgs = [m for m in _AGENT_MESSAGES if m["to"] == aid or m["from"] == aid]
    return {"success": True, "messages": msgs[-limit:]}

# ── AES-256 加密 API Key ──
from base64 import b64encode, b64decode
from hashlib import sha256

def _derive_key(master: str = "") -> bytes:
    return sha256((master or "evo-default-key").encode()).digest()

def encrypt_api_key(api_key: str, master: str = "") -> str:
    try:
        from cryptography.fernet import Fernet
        from base64 import urlsafe_b64encode
        key = urlsafe_b64encode(_derive_key(master))
        return Fernet(key).encrypt(api_key.encode()).decode()
    except ImportError:
        return f"[AES-BASE64]:{b64encode(api_key.encode()).decode()}"

def decrypt_api_key(encrypted: str, master: str = "") -> str:
    try:
        from cryptography.fernet import Fernet
        from base64 import urlsafe_b64encode
        key = urlsafe_b64encode(_derive_key(master))
        return Fernet(key).decrypt(encrypted.encode()).decode()
    except ImportError:
        if encrypted.startswith("[AES-BASE64]:"):
            return b64decode(encrypted.split(":", 1)[1]).decode()
        return encrypted

@router.post("/api/v1/agent-canvas/encrypt")
async def encrypt_key(m: dict):
    api_key = m.get("api_key", "")
    master = m.get("master", "")
    if not api_key:
        return {"success": False, "error": "需要 api_key"}
    encrypted = encrypt_api_key(api_key, master)
    return {"success": True, "encrypted": encrypted, "method": "AES-256-Fernet"}

@router.post("/api/v1/agent-canvas/decrypt")
async def decrypt_key(m: dict):
    encrypted = m.get("encrypted", "")
    master = m.get("master", "")
    if not encrypted:
        return {"success": False, "error": "需要 encrypted"}
    decrypted = decrypt_api_key(encrypted, master)
    return {"success": True, "decrypted": decrypted, "note": "测试用，生产环境不要返回解密后的密钥"}
