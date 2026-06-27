# -*- coding: utf-8 -*-
from fastapi import APIRouter
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__),"..",".."))
from modules.channel_agent import ChannelAgent

router = APIRouter(tags=["channel"])
_ch = None
def _get():
    global _ch
    if _ch is None: _ch = ChannelAgent()
    return _ch

@router.get("/api/v1/channel/status")
async def get_status():
    try:
        return {"success": True, "channels": _get().get_channels()}
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.post("/api/v1/channel/register")
async def register_channel(name: str, channel_type: str, config: str = "{}"):
    import json
    try:
        return {"success": True, "result": _get().register(name, channel_type, json.loads(config))}
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.post("/api/v1/channel/send")
async def send_message(channel: str, content: str):
    try:
        return {"success": True, "result": _get().send(channel, content)}
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.get("/api/v1/channel/history")
async def get_history(channel: str = "", limit: int = 20):
    try:
        return {"success": True, "messages": _get().get_history(channel, limit)}
    except Exception as e:
        return {"success": False, "error": str(e)}
