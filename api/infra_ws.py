"""
AUTO-EVO-AI V0.1 — WebSocket 连接管理器
从 infra.py 拆分出
"""
import logging
logger = logging.getLogger("evo.infra_ws")

from __future__ import annotations

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self.active: list = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.active:
            self.active.remove(ws)

    async def broadcast(self, message: dict):
        for ws in self.active[:]:
            try:
                await ws.send_json(message)
            except Exception:
                self.disconnect(ws)


manager = ConnectionManager()
