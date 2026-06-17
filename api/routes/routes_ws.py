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
    except WebSocketDisconnect:
        pass
    finally:
        active_connections.pop(conn_id, None)
