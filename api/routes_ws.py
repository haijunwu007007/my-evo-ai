"""
AUTO-EVO-AI V0.1 — WebSocket 实时推送路由
========================================
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from api.infra import (app, registry, manager, logger, get_coordinator_v3,
    _module_activity)

router = APIRouter()

# ── 旧版 WebSocket 连接管理器（兼容已有连接）──

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket, token: str = Query(default=""),
                             rooms: str = Query(default="")):
    """WebSocket主端点 - 兼容旧版action协议 + 新版WS引擎"""
    # 如果有rooms参数, 使用新版WS引擎
    if rooms:
        from core.ws_engine import get_ws_engine, ws_endpoint_handler as _ws_handler
        engine = get_ws_engine()
        await _ws_handler(ws, engine, token=token, rooms=rooms)
        return

    # 兼容旧版前端WebSocket协议
    await manager.connect(ws)
    try:
        while True:
            data = await ws.receive_text()
            try:
                msg = __import__('json').loads(data)
                if msg.get("action") == "call":
                    result = registry.call(
                        msg.get("module", ""), msg.get("method", ""),
                        *msg.get("args", []), **msg.get("kwargs", {})
                    )
                    await ws.send_json({"type": "result", "id": msg.get("id"), "data": result})
                elif msg.get("action") == "list_modules":
                    await ws.send_json({"type": "modules", "data": list(registry.modules.keys())})
                elif msg.get("action") == "execute":
                    coord = get_coordinator_v3()
                    if coord:
                        result = await coord.execute(msg.get("task", ""), msg.get("context", {}))
                        await ws.send_json({"type": "execute_result", "id": msg.get("id"), "data": result})
                    else:
                        await ws.send_json({"type": "error", "message": "协调器未初始化", "id": msg.get("id")})
                elif msg.get("action") == "find_modules":
                    coord = get_coordinator_v3()
                    if coord:
                        matches = coord.capability_graph.find_modules_by_task(msg.get("query", ""))
                        await ws.send_json({"type": "find_result", "data": [{"module": m, "score": round(s, 2)} for m, s in matches[:10]]})
                elif msg.get("action") == "coordinator_status":
                    coord = get_coordinator_v3()
                    if coord:
                        await ws.send_json({"type": "coordinator_status", "data": coord.get_status()})
                elif msg.get("action") == "health_update":
                    await ws.send_json({
                        "type": "health_update",
                        "data": registry.get_all_health(),
                        "coordinator": get_coordinator_v3().get_status() if get_coordinator_v3() else None,
                    })
            except Exception as e:
                await ws.send_json({"type": "error", "message": str(e)})
    except WebSocketDisconnect:
        manager.disconnect(ws)


@app.websocket("/ws/{channel}")
async def websocket_channel_endpoint(websocket: WebSocket, channel: str,
                                     token: str = Query(default="")):
    """WebSocket频道端点"""
    from core.ws_engine import get_ws_engine, ws_endpoint_handler as _ws_handler
    engine = get_ws_engine()
    await _ws_handler(websocket, engine, token=token,
                      rooms=f"system,{channel}")


@app.get("/api/v1/ws/stats")
async def ws_stats():
    """WebSocket统计"""
    from core.ws_engine import get_ws_engine
    ws = get_ws_engine()
    return {"success": True, **ws.stats()}


@app.get("/api/v1/ws/channels")
async def ws_channels():
    """可用频道列表"""
    from core.ws_engine import WSEngine
    return {"success": True, "channels": WSEngine.CHANNELS}


@app.get("/api/v1/ws/history")
async def ws_history(channel: str = None, limit: int = 50):
    """消息历史"""
    from core.ws_engine import get_ws_engine
    ws = get_ws_engine()
    history = ws.get_history(channel=channel, limit=limit)
    return {"success": True, "history": history}


@app.post("/api/v1/ws/broadcast")
async def ws_broadcast(body: dict):
    """广播消息 (管理用)"""
    from core.ws_engine import get_ws_engine, WSMessage
    ws = get_ws_engine()
    msg = WSMessage(**body)
    await ws.broadcast(msg)
    return {"success": True, "msg_id": msg.msg_id}


__all__ = ["router"]
