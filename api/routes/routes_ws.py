from core.logging_config import get_logger
logger = get_logger("evo.routes_ws")
"""WebSocket 实时工具输出"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import asyncio, json
from api.agent_tools import exec_tool

router = APIRouter()

active_connections = {}

@router.websocket("/ws/tool")
async def websocket_tool(websocket: WebSocket):
    await websocket.accept()
    conn_id = id(websocket)
    active_connections[conn_id] = websocket
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            name = msg.get("tool", "")
            args = msg.get("args", {})

            await websocket.send_json({"type": "start", "tool": name})
            result = exec_tool(name, args)
            await websocket.send_json({"type": "result", "tool": name, "data": result.get("data", "")})
            await websocket.send_json({"type": "done"})
    except WebSocketDisconnect as _e:
        logger.warning(f"error: {_e}")
    finally:
        active_connections.pop(conn_id, None)

# ── 实时协作聊天 ──
chat_rooms = {}

@router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    await websocket.accept()
    conn_id = id(websocket)
    user_name = "anonymous"
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            if msg.get("type") == "join":
                user_name = msg.get("user", f"user_{conn_id % 10000}")
                chat_rooms[conn_id] = {"ws": websocket, "user": user_name}
                # 广播用户列表
                users = {v["user"]: True for v in chat_rooms.values()}
                for cid, info in chat_rooms.items():
                    try:
                        await info["ws"].send_json({"type": "users", "users": users})
                    except Exception as _e:
                        logger.warning(f"error: {_e}")
            elif msg.get("type") == "message":
                text = msg.get("text", "")
                user = msg.get("user", user_name)
                # 广播给所有连接
                for cid, info in chat_rooms.items():
                    try:
                        await info["ws"].send_json({"type": "message", "user": user, "text": text})
                    except Exception as _e:
                        logger.warning(f"error: {_e}")
    except WebSocketDisconnect as _e:
        logger.warning(f"error: {_e}")
    finally:
        chat_rooms.pop(conn_id, None)
        # 更新用户列表
        users = {v["user"]: True for v in chat_rooms.values()}
        for cid, info in chat_rooms.items():
            try:
                await info["ws"].send_json({"type": "users", "users": users})
            except Exception as _e:
                logger.warning(f"error: {_e}")
