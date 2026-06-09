"""🌐 对外服务化 — 公开API+限流+嵌入脚本+用量"""
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional
from core.logging_config import get_logger
import json, time, sqlite3, hashlib
from pathlib import Path

logger = get_logger("evo.api.public")
router = APIRouter()

BASE_DIR = Path(__file__).resolve().parent.parent.parent
_PUB_DB = BASE_DIR / "core" / "adaptive_engine.db"

def _init_pub():
    conn = sqlite3.connect(str(_PUB_DB))
    conn.execute("CREATE TABLE IF NOT EXISTS api_keys (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, key TEXT UNIQUE, owner TEXT, created_at REAL, active INTEGER DEFAULT 1)")
    conn.execute("CREATE TABLE IF NOT EXISTS api_usage (id INTEGER PRIMARY KEY AUTOINCREMENT, key TEXT, endpoint TEXT, called_at REAL)")
    conn.commit(); conn.close()
_init_pub()

# 创建公开API Key
@router.post("/api/v1/public/key/create")
async def create_api_key(name: str = "default", owner: str = "admin"):
    conn = sqlite3.connect(str(_PUB_DB))
    key = f"evo_pub_{hashlib.sha256(f'{name}:{time.time()}:{owner}'.encode()).hexdigest()[:16]}"
    conn.execute("INSERT INTO api_keys (name, key, owner, created_at) VALUES (?,?,?,?)", (name, key, owner, time.time()))
    conn.commit(); conn.close()
    return {"success": True, "api_key": key, "name": name}

# 公开API网关（带限流&用量记录）
@router.post("/api/v1/public/smart")
async def public_smart(request: Request, message: str = "", api_key: str = ""):
    if not api_key:
        raise HTTPException(401, "需要提供 api_key")
    conn = sqlite3.connect(str(_PUB_DB))
    row = conn.execute("SELECT active FROM api_keys WHERE key=?", (api_key,)).fetchone()
    if not row or not row[0]:
        conn.close()
        raise HTTPException(403, "API Key 无效或已禁用")
    # 检查限流（每分钟最多30次）
    minute_ago = time.time() - 60
    count = conn.execute("SELECT COUNT(*) FROM api_usage WHERE key=? AND called_at>?", (api_key, minute_ago)).fetchone()[0]
    if count >= 30:
        conn.close()
        raise HTTPException(429, "请求太频繁，每分钟最多30次")
    conn.execute("INSERT INTO api_usage (key, endpoint, called_at) VALUES (?,?,?)", (api_key, "smart", time.time()))
    conn.commit(); conn.close()
    
    import httpx
    async with httpx.AsyncClient(timeout=60) as c:
        r = await c.post("http://127.0.0.1:8765/api/v1/smart", json={"message": message, "lang": "zh-CN"})
        return r.json()

# 用量查询
@router.get("/api/v1/public/usage")
async def public_usage(api_key: str = ""):
    conn = sqlite3.connect(str(_PUB_DB))
    if api_key:
        rows = conn.execute("SELECT endpoint, COUNT(*) as cnt FROM api_usage WHERE key=? GROUP BY endpoint", (api_key,)).fetchall()
    else:
        rows = conn.execute("SELECT key, endpoint, COUNT(*) as cnt FROM api_usage GROUP BY key, endpoint").fetchall()
    conn.close()
    return {"success": True, "usage": [{"key": r[0], "endpoint": r[1], "count": r[2]} for r in rows]}

# 嵌入聊天脚本
EMBED_HTML = """<!-- AUTO-EVO-AI 嵌入聊天 -->
<div id="evo-ai-chat" style="position:fixed;bottom:20px;right:20px;z-index:99999">
  <div id="evo-chat-btn" onclick="toggleEvoChat()" style="width:56px;height:56px;border-radius:50%;background:#4361ee;color:#fff;display:flex;align-items:center;justify-content:center;cursor:pointer;box-shadow:0 4px 12px rgba(0,0,0,.3);font-size:24px">🤖</div>
  <div id="evo-chat-box" style="display:none;position:absolute;bottom:70px;right:0;width:360px;height:480px;background:#1a1a2e;border-radius:12px;border:1px solid #2d3561;overflow:hidden;box-shadow:0 8px 32px rgba(0,0,0,.5)">
    <div style="background:#4361ee;padding:12px;text-align:center;font-size:14px;font-weight:600">AUTO-EVO-AI</div>
    <div id="evo-chat-msgs" style="height:360px;overflow-y:auto;padding:12px;font-size:13px;color:#e0e0e0"></div>
    <div style="display:flex;padding:8px;gap:8px;border-top:1px solid #2d3561">
      <input id="evo-chat-input" placeholder="输入..." style="flex:1;padding:8px;border-radius:6px;border:1px solid #2d3561;background:#0f0f1a;color:#e0e0e0;font-size:13px">
      <button onclick="sendEvoChat()" style="padding:8px 16px;border:none;border-radius:6px;background:#4361ee;color:#fff;cursor:pointer">发送</button>
    </div>
  </div>
</div>
<script>
function toggleEvoChat(){var b=document.getElementById('evo-chat-box');b.style.display=b.style.display==='none'?'block':'none'}
function sendEvoChat(){var i=document.getElementById('evo-chat-input');var t=i.value.trim();if(!t)return;i.value='';var m=document.getElementById('evo-chat-msgs');m.innerHTML+='<div style="text-align:right;margin:4px 0">'+t+'</div>';fetch('http://localhost:8765/api/v1/public/smart?message='+encodeURIComponent(t)+'&api_key='+localStorage.getItem('evo_pub_key')||'').then(function(r){return r.json()}).then(function(d){m.innerHTML+='<div style="text-align:left;margin:4px 0;color:#8892b0">'+(d.result||d.detail||'...')+'</div>';m.scrollTop=m.scrollHeight})}
document.getElementById('evo-chat-input').addEventListener('keydown',function(e){if(e.key==='Enter')sendEvoChat()});
</script>"""

@router.get("/api/v1/public/embed.js", response_class=HTMLResponse)
async def embed_script():
    return HTMLResponse(content=EMBED_HTML, media_type="application/javascript")
