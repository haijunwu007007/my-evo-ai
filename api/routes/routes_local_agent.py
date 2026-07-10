"""本地桌面代理 — WebSocket 中继"""
import json, asyncio, logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger("evo.local_agent")
router = APIRouter(tags=["local_agent"])

# 已连接的本地代理
_agents: dict[str, WebSocket] = {}

@router.websocket("/ws/agent")
async def agent_ws(ws: WebSocket):
    """本地代理连接到此 WebSocket"""
    await ws.accept()
    agent_id = f"agent_{id(ws)}"
    _agents[agent_id] = ws
    logger.info(f"[AGENT] 本地代理已连接: {agent_id}")
    try:
        while True:
            data = await ws.receive_text()
            msg = json.loads(data)
            if msg.get("type") == "result":
                # 代理返回执行结果
                logger.info(f"[AGENT] 收到结果: agent={agent_id}, result={str(msg.get('data',''))[:100]}")
    except WebSocketDisconnect as _e:
        logger.warning(f"error: {_e}")
    finally:
        _agents.pop(agent_id, None)
        logger.info(f"[AGENT] 代理断开: {agent_id}")

@router.post("/api/v1/agent/local/exec")
async def exec_local(action: str = "", **params):
    """通过 WebSocket 向本地代理发送命令"""
    if not _agents:
        return {"success": False, "error": "没有已连接的本地代理。请在电脑上运行: python local_agent.py"}
    # 发给第一个可用的代理
    agent_id, ws = next(iter(_agents.items()))
    # 发送命令
    await ws.send_text(json.dumps({"action": action, "params": params}))
    # 等待结果（简化：直接返回已发送，结果通过 WS 异步接收）
    return {"success": True, "agent": agent_id, "command": action, "status": "sent"}

@router.get("/api/v1/agent/local/status")
async def agent_status():
    return {"success": True, "connected": len(_agents), "agents": list(_agents.keys()) if _agents else []}
