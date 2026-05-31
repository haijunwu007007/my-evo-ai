"""
AUTO-EVO-AI V0.1 — WebSocket 实时推送引擎 (WebSocket Engine)
============================================================
上市公司级实时通信:
- FastAPI WebSocket原生集成
- 多频道/房间隔离 (module/pipeline/system/events/task)
- 消息类型: 日志流/进度/状态/事件/告警
- 历史消息缓冲 (可回溯最近N条)
- 心跳检测 + 自动清理断连
- 消息广播 + 定向推送
- 认证Token校验
- 速率限制
"""

from __future__ import annotations

import os
import json
import time
import asyncio
import hashlib
from core.logging_config import get_logger
import secrets
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from datetime import datetime
from dataclasses import dataclass, field, asdict
from enum import Enum
from collections import defaultdict

from fastapi import WebSocket, WebSocketDisconnect, Query
import asyncio

logger = get_logger("evo.ws")


# ═══════════════════════════════════════════════════════════
# 消息类型
# ═══════════════════════════════════════════════════════════

class MessageType(str, Enum):
    # 系统消息
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    HEARTBEAT = "heartbeat"
    ERROR = "error"
    # 日志
    LOG = "log"
    LOG_STREAM = "log_stream"
    # 进度
    PROGRESS = "progress"
    # 状态
    STATUS = "status"
    # 事件
    EVENT = "event"
    # 告警
    ALERT = "alert"
    # 任务
    TASK_UPDATE = "task_update"
    # 模块
    MODULE_OUTPUT = "module_output"
    # 管线
    PIPELINE_STEP = "pipeline_step"
    PIPELINE_RESULT = "pipeline_result"
    # 通知
    NOTIFICATION = "notification"


# ═══════════════════════════════════════════════════════════
# WebSocket消息结构
# ═══════════════════════════════════════════════════════════

@dataclass
class WSMessage:
    """WebSocket消息"""
    type: str = "log"
    channel: str = "system"
    data: dict = field(default_factory=dict)
    timestamp: str = ""
    msg_id: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()
        if not self.msg_id:
            self.msg_id = secrets.token_hex(6)

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)

    @classmethod
    def from_dict(cls, d: dict) -> WSMessage:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ═══════════════════════════════════════════════════════════
# 连接管理
# ═══════════════════════════════════════════════════════════

@dataclass
class WSClient:
    """WebSocket客户端连接"""
    ws: WebSocket = field(repr=False)
    client_id: str = ""
    rooms: set[str] = field(default_factory=set)
    connected_at: str = ""
    last_heartbeat: float = 0.0
    auth_token: str = ""
    ip: str = ""
    user_agent: str = ""

    def __post_init__(self):
        if not self.client_id:
            self.client_id = secrets.token_hex(8)
        if not self.connected_at:
            self.connected_at = datetime.now().isoformat()
        self.last_heartbeat = time.time()


# ═══════════════════════════════════════════════════════════
# WebSocket引擎
# ═══════════════════════════════════════════════════════════

class WSEngine:
    """
    WebSocket实时推送引擎
    """

    # 预定义频道
    CHANNELS = {
        "system": "系统消息 (状态/健康/启动/关闭)",
        "module": "模块执行 (输出/进度/结果)",
        "pipeline": "管线执行 (步骤进度/结果)",
        "events": "事件流 (所有系统事件)",
        "tasks": "任务队列 (状态更新/完成通知)",
        "logs": "日志流 (实时日志)",
        "alerts": "告警 (错误/异常/阈值)",
    }

    def __init__(self, auth_token: str = "", heartbeat_interval: int = 30,
                 history_size: int = 100):
        self._auth_token = auth_token  # 空=不需要认证
        self._heartbeat_interval = heartbeat_interval
        self._history_size = history_size

        # 连接管理
        self._clients: dict[str, WSClient] = {}          # client_id → WSClient
        self._room_clients: dict[str, set[str]] = defaultdict(set)  # room → {client_ids}
        self._lock = asyncio.Lock()

        # 历史缓冲
        self._history: dict[str, list[dict]] = defaultdict(list)  # channel → [messages]
        self._all_history: list[dict] = []               # 全局历史

        # 统计
        self._total_messages = 0
        self._total_connections = 0

        logger.info("[WS] 初始化 | heartbeat=%ds, history=%d", heartbeat_interval, history_size)

    @property
    def client_count(self) -> int:
        return len(self._clients)

    @property
    def total_messages(self) -> int:
        return self._total_messages

    @property
    def total_connections(self) -> int:
        return self._total_connections

    # ─── 连接管理 ───

    async def connect(self, websocket: WebSocket, token: str = "",
                      rooms: list[str] | None = None, client_ip: str = "",
                      user_agent: str = "") -> WSClient:
        """接受WebSocket连接"""
        # 认证
        if self._auth_token and token != self._auth_token:
            await websocket.close(code=4001, reason="认证失败")
            raise ValueError("认证失败")

        await websocket.accept()
        client = WSClient(
            ws=websocket, auth_token=token, ip=client_ip,
            user_agent=user_agent or "unknown"
        )

        async with self._lock:
            self._clients[client.client_id] = client
            self._total_connections += 1

        # 加入默认房间和指定房间
        default_rooms = {"system"}
        if rooms:
            default_rooms.update(rooms)
        for room in default_rooms:
            await self.join_room(client.client_id, room)

        # 发送连接确认
        await self._send_to_client(client, WSMessage(
            type=MessageType.CONNECTED, channel="system",
            data={"client_id": client.client_id, "rooms": list(default_rooms),
                  "server_time": datetime.now().isoformat()}
        ))

        # 发送频道历史
        for room in default_rooms:
            history = self._history.get(room, [])
            if history:
                await self._send_to_client(client, WSMessage(
                    type=MessageType.STATUS, channel=room,
                    data={"type": "history", "count": len(history), "messages": history[-20:]}
                ))

        logger.info("[WS] 连接: %s (%s) rooms=%s", client.client_id[:8], client_ip, list(default_rooms))
        return client

    async def disconnect(self, client_id: str):
        """断开连接"""
        async with self._lock:
            client = self._clients.pop(client_id, None)
            if client:
                for room in list(client.rooms):
                    self._room_clients[room].discard(client_id)
        if client:
            logger.info("[WS] 断开: %s", client_id[:8])

    # ─── 房间管理 ───

    async def join_room(self, client_id: str, room: str):
        """加入房间"""
        async with self._lock:
            self._room_clients[room].add(client_id)
            if client_id in self._clients:
                self._clients[client_id].rooms.add(room)

    async def leave_room(self, client_id: str, room: str):
        """离开房间"""
        async with self._lock:
            self._room_clients[room].discard(client_id)
            if client_id in self._clients:
                self._clients[client_id].rooms.discard(room)

    def get_room_members(self, room: str) -> int:
        return len(self._room_clients.get(room, set()))

    # ─── 消息发送 ───

    async def broadcast(self, message: WSMessage):
        """广播到所有连接"""
        data = message.to_json()
        dead_clients = []
        async with self._lock:
            for cid, client in self._clients.items():
                try:
                    await client.ws.send_text(data)
                except Exception:
                    dead_clients.append(cid)
        for cid in dead_clients:
            await self.disconnect(cid)
        self._record_message(message)

    async def broadcast_to_room(self, room: str, message: WSMessage):
        """广播到指定房间"""
        data = message.to_json()
        dead_clients = []
        client_ids = self._room_clients.get(room, set())
        async with self._lock:
            for cid in client_ids:
                client = self._clients.get(cid)
                if client:
                    try:
                        await client.ws.send_text(data)
                    except Exception:
                        dead_clients.append(cid)
        for cid in dead_clients:
            await self.disconnect(cid)
        self._record_message(message, room)

    async def send_to_client(self, client_id: str, message: WSMessage):
        """发送给指定客户端"""
        client = self._clients.get(client_id)
        if client:
            try:
                await self._send_to_client(client, message)
            except Exception:
                await self.disconnect(client_id)

    async def _send_to_client(self, client: WSClient, message: WSMessage):
        await client.ws.send_text(message.to_json())

    def _record_message(self, message: WSMessage, room: str = None):
        """记录消息到历史"""
        d = asdict(message)
        self._all_history.append(d)
        if len(self._all_history) > self._history_size:
            self._all_history = self._all_history[-self._history_size:]
        if room:
            self._history[room].append(d)
            if len(self._history[room]) > self._history_size:
                self._history[room] = self._history[room][-self._history_size:]
        self._total_messages += 1

    # ─── 快捷方法 ───

    async def send_log(self, channel: str = "logs", level: str = "info",
                       message: str = "", source: str = "", **extra):
        """发送日志"""
        await self.broadcast_to_room(channel, WSMessage(
            type=MessageType.LOG, channel=channel,
            data={"level": level, "message": message, "source": source, **extra}
        ))

    async def send_progress(self, channel: str, progress: float,
                            total: float = 100, label: str = ""):
        """发送进度"""
        await self.broadcast_to_room(channel, WSMessage(
            type=MessageType.PROGRESS, channel=channel,
            data={"progress": round(progress, 1), "total": total, "label": label,
                  "percent": round(progress / total * 100, 1) if total else 0}
        ))

    async def send_status(self, channel: str = "system", **data):
        """发送状态"""
        await self.broadcast_to_room(channel, WSMessage(
            type=MessageType.STATUS, channel=channel, data=data
        ))

    async def send_alert(self, level: str = "warning", title: str = "",
                         message: str = "", source: str = ""):
        """发送告警"""
        await self.broadcast_to_room("alerts", WSMessage(
            type=MessageType.ALERT, channel="alerts",
            data={"level": level, "title": title, "message": message, "source": source}
        ))

    async def send_notification(self, title: str, message: str,
                                notification_type: str = "info"):
        """发送通知"""
        await self.broadcast(WSMessage(
            type=MessageType.NOTIFICATION, channel="system",
            data={"title": title, "message": message, "type": notification_type}
        ))

    async def send_event(self, event_type: str, source: str = "",
                         data: dict = None, priority: int = 5):
        """转发事件"""
        await self.broadcast_to_room("events", WSMessage(
            type=MessageType.EVENT, channel="events",
            data={"event_type": event_type, "source": source,
                  "payload": data or {}, "priority": priority}
        ))

    # ─── 心跳检测 ───

    async def heartbeat_checker(self):
        """定期检查心跳, 清理死连接"""
        while True:
            await asyncio.sleep(self._heartbeat_interval)
            now = time.time()
            dead = []
            async with self._lock:
                for cid, client in self._clients.items():
                    if now - client.last_heartbeat > self._heartbeat_interval * 2:
                        dead.append(cid)
            for cid in dead:
                logger.info("[WS] 心跳超时断开: %s", cid[:8])
                await self.disconnect(cid)

    # ─── 统计 ───

    def stats(self) -> dict:
        room_stats = {}
        for room, cids in self._room_clients.items():
            room_stats[room] = len(cids)
        return {
            "connected_clients": len(self._clients),
            "total_connections": self._total_connections,
            "total_messages": self._total_messages,
            "rooms": room_stats,
            "history_size": len(self._all_history)
        }

    def get_history(self, channel: str | None = None, limit: int = 50) -> list[dict]:
        """获取历史消息"""
        if channel:
            return self._history.get(channel, [])[-limit:]
        return self._all_history[-limit:]


# ─── WebSocket端点处理器 ───

async def ws_endpoint_handler(websocket: WebSocket, engine: WSEngine,
                              token: str = "", rooms: str = ""):
    """FastAPI WebSocket端点处理函数"""
    client = await engine.connect(
        websocket,
        token=token,
        rooms=[r.strip() for r in rooms.split(",") if r.strip()] if rooms else None,
        client_ip=websocket.client.host if websocket.client else "",
        user_agent=websocket.headers.get("user-agent", "")
    )

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
                msg_type = msg.get("type", "")

                if msg_type == "heartbeat":
                    client.last_heartbeat = time.time()
                    await engine.send_to_client(client.client_id, WSMessage(
                        type=MessageType.HEARTBEAT, channel="system",
                        data={"ts": datetime.now().isoformat()}
                    ))

                elif msg_type == "join":
                    room = msg.get("room", "")
                    if room:
                        await engine.join_room(client.client_id, room)

                elif msg_type == "leave":
                    room = msg.get("room", "")
                    if room:
                        await engine.leave_room(client.client_id, room)

                elif msg_type == "ping":
                    await engine.send_to_client(client.client_id, WSMessage(
                        type="pong", channel="system"
                    ))

            except json.JSONDecodeError:
                await engine.send_to_client(client.client_id, WSMessage(
                    type=MessageType.ERROR, channel="system",
                    data={"message": "无效的JSON"}
                ))

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error("[WS] 客户端异常: %s", e)
    finally:
        await engine.disconnect(client.client_id)


# ─── 全局单例 ───

_engine: WSEngine | None = None

def get_ws_engine() -> WSEngine:
    global _engine
    if _engine is None:
        _engine = WSEngine()
    return _engine
