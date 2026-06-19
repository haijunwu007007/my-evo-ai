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
    return {"status": "ok", "channels": _get().get_channels()}

@router.post("/api/v1/channel/register")
async def register_channel(name: str, channel_type: str, config: str = "{}"):
    import json
    return _get().register(name, channel_type, json.loads(config))

@router.post("/api/v1/channel/send")
async def send_message(channel: str, content: str):
    return _get().send(channel, content)

@router.get("/api/v1/channel/history")
async def get_history(channel: str = "", limit: int = 20):
    return {"messages": _get().get_history(channel, limit)}
