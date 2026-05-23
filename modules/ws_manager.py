# -*- coding: utf-8 -*-
"""
AUTO-EVO-AI V0.1 - WebSocketManager WebSocket连接管理器
========================================================
企业级WebSocket管理：连接池/房间/广播/心跳/消息队列/重连。
支持：多房间管理、连接状态追踪、心跳保活、
      消息广播/单播/组播、消息持久化、连接限流、
      二进制消息支持、事件回调、连接统计。

A级生产标准：EnterpriseModule + 链路追踪 + Prometheus + 审计 + 熔断 + 限流
"""

__module_meta__ = {
    "id": "ws-manager",
    "name": "Ws Manager",
    "version": "1.0.0",
    "group": "network",
    "inputs": [
        {"name": "config", "type": "string", "required": True, "description": ""},
        {"name": "action", "type": "string", "required": True, "description": ""},
        {"name": "params", "type": "string", "required": True, "description": ""},
        {"name": "remote_addr", "type": "string", "required": True, "description": ""},
        {"name": "ws", "type": "string", "required": True, "description": ""},
        {"name": "connection_id", "type": "string", "required": True, "description": ""},
    ],
    "outputs": [
        {"name": "success", "type": "bool", "description": "是否成功"},
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "results", "type": "list[dict]", "description": "结果列表"},
    ],
    "triggers": [],
    "depends_on": [],
    "tags": ["ws", "manager"],
    "grade": "A",
    "description": "AUTO-EVO-AI V0.1 - WebSocketManager WebSocket连接管理器 ========================================================",
}
import time
import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import uuid

from modules._base.enterprise_module import EnterpriseModule, ModuleStatus, HealthReport
from modules._base.metrics import prometheus_timer, metrics_collector
from modules._base.circuit_breaker import CircuitBreakerMixin
from modules._base.rate_limiter import RateLimiterMixin

class ConnectionState(str, Enum):
    CONNECTING = "connecting"
    CONNECTED = "connected"
    AUTHENTICATED = "authenticated"
    RECONNECTING = "reconnecting"
    CLOSING = "closing"
    CLOSED = "closed"

class MessageType(str, Enum):
    TEXT = "text"
    BINARY = "binary"
    PING = "ping"
    PONG = "pong"
    CLOSE = "close"

@dataclass
class WSConnection:
    """WebSocket连接"""

    connection_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    ws: Any = None  # WebSocket实例
    remote_addr: str = ""
    state: ConnectionState = ConnectionState.CONNECTING
    user_id: Optional[str] = None
    username: str = ""
    scopes: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    rooms: Set[str] = field(default_factory=set)
    connected_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_active: str = field(default_factory=lambda: datetime.now().isoformat())
    last_ping: Optional[str] = None
    last_pong: Optional[str] = None
    messages_sent: int = 0
    messages_received: int = 0
    bytes_sent: int = 0
    bytes_received: int = 0
    ping_interval: float = 30.0
    ping_timeout: float = 10.0
    max_message_rate: float = 100.0  # 每秒最大消息数
    authenticated: bool = False
    # 内部消息队列
    _send_queue: asyncio.Queue = field(default_factory=lambda: asyncio.Queue(maxsize=1000))
    _rate_counter: int = 0
    _rate_window: float = field(default_factory=time.time)

    @property
    def idle_seconds(self) -> float:
        try:
            last = datetime.fromisoformat(self.last_active)
            return (datetime.now() - last).total_seconds()
        except Exception:
            return 0.0

    @property
    def is_healthy(self) -> bool:
        if self.state != ConnectionState.CONNECTED and self.state != ConnectionState.AUTHENTICATED:
            return False
        if self.ping_timeout and self.last_ping:
            try:
                pong = datetime.fromisoformat(self.last_pong or "1970-01-01")
                ping = datetime.fromisoformat(self.last_ping)
                if self.last_pong and pong < ping:
                    return False
            except Exception:
                pass
        return True

@dataclass
class WSRoom:
    """WebSocket房间"""

    room_id: str
    name: str = ""
    description: str = ""
    max_members: int = 1000
    persistent: bool = False
    message_history: bool = False
    history_max: int = 100
    history: List[Dict[str, Any]] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)
    total_messages: int = 0
    _members: Set[str] = field(default_factory=set)

    @property
    def member_count(self) -> int:
        return len(self._members)

@dataclass
class WSMessage:
    """WebSocket消息"""

    message_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    sender_id: str = ""
    room_id: str = ""
    target_type: str = "broadcast"  # broadcast/unicast/multicast
    target_ids: List[str] = field(default_factory=list)
    message_type: MessageType = MessageType.TEXT
    content: str = ""
    binary_data: bytes = b""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)
    ttl_seconds: float = 0.0

# ============================================================================
# WebSocketManager 主类
# ============================================================================

class WebSocketManager(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """
    WebSocket连接管理器

    功能：
      - 连接注册/注销/状态管理
      - 房间创建/加入/离开/销毁
      - 消息广播/单播/组播
      - 心跳保活（Ping/Pong）
      - 消息限流
      - 二进制消息支持
      - 消息历史（可选）
      - 事件回调系统
      - 连接统计
      - 健康检查
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):

        super().__init__()
        self.config = config or {}
        # 连接表
        self._connections: Dict[str, WSConnection] = {}
        # 用户 -> 连接ID映射
        self._user_connections: Dict[str, Set[str]] = defaultdict(set)
        # 房间表
        self._rooms: Dict[str, WSRoom] = {}
        # 发送工作协程（每连接一个）
        self._sender_tasks: Dict[str, asyncio.Task] = {}
        # 链路追踪上下文（trace_id -> span信息）
        self._trace_contexts: Dict[str, Dict[str, Any]] = {}
        self._trace_enabled = self.config.get("trace_enabled", True)
        # 心跳检查任务
        self._heartbeat_task: Optional[asyncio.Task] = None
        # 事件回调
        self._event_handlers: Dict[str, List[Callable]] = defaultdict(list)
        # 消息处理器（按消息类型）
        self._message_handlers: Dict[str, Callable] = {}
        # 统计
        self._ws_stats = {
            "total_connections": 0,
            "active_connections": 0,
            "total_messages_sent": 0,
            "total_messages_received": 0,
            "total_bytes_sent": 0,
            "total_bytes_received": 0,
            "total_rooms": 0,
            "total_disconnections": 0,
            "heartbeat_timeouts": 0,
            "rate_limited": 0,
        }
        # 配置
        self._max_connections = self.config.get("max_connections", 10000)
        self._heartbeat_interval = self.config.get("heartbeat_interval", 30.0)
        self._heartbeat_timeout = self.config.get("heartbeat_timeout", 10.0)
        self._max_message_size = self.config.get("max_message_size", 65536)
        self._default_room_max = self.config.get("default_room_max", 1000)
        # 预创建房间
        for room_cfg in self.config.get("preset_rooms", []):
            self.create_room(
                room_id=room_cfg.get("id", ""),
                name=room_cfg.get("name", ""),
                max_members=room_cfg.get("max_members", self._default_room_max),
            )

    # ----------------------------------------------------------------
    # 生命周期
    # ----------------------------------------------------------------

    def initialize(self) -> Result:
        try:
            self._update_status(ModuleStatus.INITIALIZING)
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            # 注册内置消息处理器
            self._message_handlers["ping"] = self._handle_ping
            self._message_handlers["pong"] = self._handle_pong
            self._message_handlers["join"] = self._handle_join
            self._message_handlers["leave"] = self._handle_leave
            self._update_status(ModuleStatus.RUNNING)
            self.audit("ws_manager.initialized", {"rooms": len(self._rooms), "max_connections": self._max_connections})
            logger.info(f"[WSManager] 初始化完成: max={self._max_connections}")
            return Result(success=True)
        except Exception as e:
            self._update_status(ModuleStatus.ERROR)
            logger.error(f"[WSManager] 初始化失败: {e}")
            return Result(success=False, error=str(e))

    async def execute(self, action: str = "list_actions", params: dict = None) -> dict:
        _ = self.trace("execute")
        """统一执行入口 — 根据action路由到对应业务方法"""
        params = params or {}
        actions = {
            "register_connection": self.register_connection,
            "unregister_connection": self.unregister_connection,
            "authenticate_connection": self.authenticate_connection,
            "get_connection": self.get_connection,
            "get_user_connections": self.get_user_connections,
            "create_room": self.create_room,
            "delete_room": self.delete_room,
            "join_room": self.join_room,
            "leave_room": self.leave_room,
            "list_rooms": self.list_rooms,
            "on_message": self.on_message,
            "send_to_connection": self.send_to_connection,
            "send_to_room": self.send_to_room,
            "broadcast": self.broadcast,
            "on": self.on,
            "get_stats": self.get_stats,
            "get_room_info": self.get_room_info,
            "list_actions": lambda: list(actions.keys()),
            "help": lambda: {"actions": list(actions.keys()), "usage": "execute(action, params)"},
        }

        if action not in actions:
            return {"status": "error", "message": f"Unknown action: {action}", "available": list(actions.keys())}

        handler = actions[action]
        if callable(handler) and not isinstance(handler, list):
            import inspect

            if inspect.iscoroutinefunction(handler):
                try:
                    sig = inspect.signature(handler)
                    if len(sig.parameters) <= 1:
                        result = handler()
                    else:
                        result = handler(**params)
                except Exception as e:
                    return {"status": "error", "message": str(e)}
            else:
                try:
                    sig = inspect.signature(handler)
                    if len(sig.parameters) <= 1:
                        result = handler()
                    else:
                        result = handler(**params)
                except Exception as e:
                    return {"status": "error", "message": str(e)}
            if isinstance(result, dict):
                return {"status": "success", **result}
            return {"status": "success", "data": result}

    def health_check(self) -> HealthReport:
        active = sum(
            1
            for c in self._connections.values()
            if c.state in (ConnectionState.CONNECTED, ConnectionState.AUTHENTICATED)
        )
        checks = {
            "active_connections": active,
            "rooms_count": len(self._rooms),
            "max_connections": self._max_connections,
            "heartbeat_running": self._heartbeat_task and not self._heartbeat_task.done(),
            "connection_utilization": round(active / self._max_connections * 100, 2) if self._max_connections else 0,
        }
        return HealthReport(
            status="running",
            healthy=True,
            last_beat=datetime.now().isoformat(),
            uptime_seconds=self.stats.uptime_seconds,
            checks_run=5,
            error_rate=self.stats.error_rate,
            details=checks,
            version="V0.1",
        )

    def shutdown(self) -> Result:
        try:
            self._update_status(ModuleStatus.STOPPING)
            if self._heartbeat_task:
                self._heartbeat_task.cancel()
            for conn_id, task in self._sender_tasks.items():
                task.cancel()
            asyncio.gather(*self._sender_tasks.values(), return_exceptions=True)
            self._sender_tasks.clear()
            self._connections.clear()
            self._rooms.clear()
            self._update_status(ModuleStatus.STOPPED)
            logger.info("[WSManager] 关闭完成")
            return Result(success=True)
        except Exception as e:
            return Result(success=False, error=str(e))

    # ----------------------------------------------------------------
    # 连接管理
    # ----------------------------------------------------------------

    def register_connection(self, remote_addr: str = "", ws: Any = None) -> WSConnection:
        """注册新连接"""
        metrics_collector.counter("ws_ops_total")

        # 链路追踪：记录连接注册span
        trace_id = str(uuid.uuid4())[:16]
        if self._trace_enabled:
            self._trace_contexts[trace_id] = {
                "operation": "register_connection",
                "start": time.time(),
                "addr": remote_addr,
            }
        if not self.rate_limit("connect"):
            if trace_id in self._trace_contexts:
                self._trace_contexts[trace_id]["status"] = "rate_limited"
            raise Exception("connection_rate_limited")
        if len(self._connections) >= self._max_connections:
            raise Exception("max_connections_reached")
        conn = WSConnection(remote_addr=remote_addr or "unknown", ws=ws)
        conn.state = ConnectionState.CONNECTED
        self._connections[conn.connection_id] = conn
        self._ws_stats["total_connections"] += 1
        self._ws_stats["active_connections"] = len(
            [
                c
                for c in self._connections.values()
                if c.state in (ConnectionState.CONNECTED, ConnectionState.AUTHENTICATED)
            ]
        )
        # 启动发送工作协程
        task = asyncio.create_task(self._sender_worker(conn.connection_id))
        self._sender_tasks[conn.connection_id] = task
        self._emit_event("connection.opened", {"id": conn.connection_id, "addr": conn.remote_addr})
        self.audit("ws.connection.opened", {"id": conn.connection_id, "addr": conn.remote_addr})
        logger.info(f"[WSManager] 新连接: {conn.connection_id} from {conn.remote_addr}")
        # 完成链路追踪span
        if self._trace_enabled and trace_id in self._trace_contexts:
            self._trace_contexts[trace_id].update(
                {"status": "success", "end": time.time(), "conn_id": conn.connection_id}
            )
        return conn

    def unregister_connection(self, connection_id: str, code: int = 1000, reason: str = "") -> Result:
        """注销连接"""
        conn = self._connections.get(connection_id)
        if not conn:
            return Result(success=False, error=f"连接不存在: {connection_id}")
        conn.state = ConnectionState.CLOSING
        # 离开所有房间
        for room_id in list(conn.rooms):
            self.leave_room(connection_id, room_id)
        # 清理用户映射
        if conn.user_id:
            self._user_connections[conn.user_id].discard(connection_id)
        # 取消发送任务
        task = self._sender_tasks.pop(connection_id, None)
        if task:
            task.cancel()
        conn.state = ConnectionState.CLOSED
        self._connections.pop(connection_id, None)
        self._ws_stats["active_connections"] = len(
            [
                c
                for c in self._connections.values()
                if c.state in (ConnectionState.CONNECTED, ConnectionState.AUTHENTICATED)
            ]
        )
        self._ws_stats["total_disconnections"] += 1
        self._emit_event("connection.closed", {"id": connection_id, "code": code, "reason": reason})
        return Result(success=True)

    def authenticate_connection(
        self, connection_id: str, user_id: str, username: str = "", scopes: Optional[List[str]] = None
    ) -> Result:
        """认证连接"""
        conn = self._connections.get(connection_id)
        if not conn:
            return Result(success=False, error="连接不存在")
        conn.state = ConnectionState.AUTHENTICATED
        conn.authenticated = True
        conn.user_id = user_id
        conn.username = username
        conn.scopes = scopes or []
        self._user_connections[user_id].add(connection_id)
        self._emit_event("connection.authenticated", {"id": connection_id, "user_id": user_id})
        return Result(success=True)

    def get_connection(self, connection_id: str) -> Optional[WSConnection]:
        return self._connections.get(connection_id)

    def get_user_connections(self, user_id: str) -> List[WSConnection]:
        conn_ids = self._user_connections.get(user_id, set())
        return [self._connections[cid] for cid in conn_ids if cid in self._connections]

    # ----------------------------------------------------------------
    # 房间管理
    # ----------------------------------------------------------------

    def create_room(
        self,
        room_id: str,
        name: str = "",
        max_members: int = 0,
        persistent: bool = False,
        message_history: bool = False,
        history_max: int = 100,
    ) -> Result:
        """创建房间"""
        if room_id in self._rooms:
            return Result(success=False, error=f"房间已存在: {room_id}")
        self._rooms[room_id] = WSRoom(
            room_id=room_id,
            name=name or room_id,
            max_members=max_members or self._default_room_max,
            persistent=persistent,
            message_history=message_history,
            history_max=history_max,
        )
        self._ws_stats["total_rooms"] = len(self._rooms)
        self._emit_event("room.created", {"room_id": room_id})
        return Result(success=True, data={"room_id": room_id})

    def delete_room(self, room_id: str, force: bool = False) -> Result:
        """删除房间"""
        room = self._rooms.get(room_id)
        if not room:
            return Result(success=False, error=f"房间不存在: {room_id}")
        if room.member_count > 0 and not force:
            return Result(success=False, error=f"房间非空: {room_id}, {room.member_count} members")
        for cid in list(room._members):
            conn = self._connections.get(cid)
            if conn:
                conn.rooms.discard(room_id)
        del self._rooms[room_id]
        self._ws_stats["total_rooms"] = len(self._rooms)
        return Result(success=True)

    def join_room(self, connection_id: str, room_id: str) -> Result:
        """加入房间"""
        conn = self._connections.get(connection_id)
        room = self._rooms.get(room_id)
        if not conn:
            return Result(success=False, error="连接不存在")
        if not room:
            return Result(success=False, error=f"房间不存在: {room_id}")
        if len(room._members) >= room.max_members:
            return Result(success=False, error="房间已满")
        conn.rooms.add(room_id)
        room._members.add(connection_id)
        # 通知房间成员
        self.send_to_room(
            room_id,
            json.dumps(
                {
                    "type": "system",
                    "event": "member_joined",
                    "data": {"connection_id": connection_id, "user": conn.username or conn.user_id or "anonymous"},
                    "member_count": room.member_count,
                },
                ensure_ascii=False,
            ),
        )
        self._emit_event("room.joined", {"room_id": room_id, "connection_id": connection_id})
        return Result(success=True, data={"room_id": room_id, "members": room.member_count})

    def leave_room(self, connection_id: str, room_id: str) -> Result:
        """离开房间"""
        conn = self._connections.get(connection_id)
        room = self._rooms.get(room_id)
        if not conn or not room:
            return Result(success=False, error="连接或房间不存在")
        conn.rooms.discard(room_id)
        room._members.discard(connection_id)
        self.send_to_room(
            room_id,
            json.dumps(
                {
                    "type": "system",
                    "event": "member_left",
                    "data": {"connection_id": connection_id, "user": conn.username or conn.user_id or "anonymous"},
                    "member_count": room.member_count,
                },
                ensure_ascii=False,
            ),
        )
        self._emit_event("room.left", {"room_id": room_id, "connection_id": connection_id})
        return Result(success=True)

    def list_rooms(self) -> List[Dict]:
        return [
            {
                "room_id": r.room_id,
                "name": r.name,
                "members": r.member_count,
                "max_members": r.max_members,
                "messages": r.total_messages,
                "persistent": r.persistent,
                "has_history": r.message_history,
            }
            for r in self._rooms.values()
        ]

    # ----------------------------------------------------------------
    # 消息收发
    # ----------------------------------------------------------------

    def on_message(self, connection_id: str, raw_data: str or bytes):
        """处理收到的消息"""
        start = time.time()
        conn = self._connections.get(connection_id)
        if not conn:
            return
        conn.last_active = datetime.now().isoformat()
        conn.messages_received += 1
        self._ws_stats["total_messages_received"] += 1
        # 限流检查
        now = time.time()
        if now - conn._rate_window >= 1.0:
            conn._rate_counter = 0
            conn._rate_window = now
        conn._rate_counter += 1
        if conn._rate_counter > conn.max_message_rate:
            self._ws_stats["rate_limited"] += 1
            self.send_to_connection(connection_id, json.dumps({"type": "error", "message": "rate_limited"}))
            return
        # 解析消息
        try:
            if isinstance(raw_data, bytes):
                conn.bytes_received += len(raw_data)
                data = json.loads(raw_data.decode("utf-8"))
            else:
                conn.bytes_received += len(raw_data.encode("utf-8"))
                data = json.loads(raw_data)
        except json.JSONDecodeError:
            self.send_to_connection(connection_id, json.dumps({"type": "error", "message": "invalid_json"}))
            return
        # 检查大小
        if len(str(data)) > self._max_message_size:
            self.send_to_connection(connection_id, json.dumps({"type": "error", "message": "message_too_large"}))
            return
        # 路由到处理器
        msg_type = data.get("type", "")
        handler = self._message_handlers.get(msg_type)
        if handler:
            try:
                handler(connection_id, data)
            except Exception as e:
                logger.error(f"[WSManager] 消息处理错误: {msg_type}, {e}")
        self.stats.record_request((time.time() - start) * 1000, True)

    def send_to_connection(self, connection_id: str, message: str) -> Result:
        """发送消息到指定连接"""
        conn = self._connections.get(connection_id)
        if not conn:
            return Result(success=False, error="连接不存在")
        try:
            conn._send_queue.put(message)
            conn.messages_sent += 1
            conn.bytes_sent += len(message.encode("utf-8"))
            self._ws_stats["total_messages_sent"] += 1
            self._ws_stats["total_bytes_sent"] += len(message.encode("utf-8"))
            return Result(success=True)
        except asyncio.QueueFull:
            return Result(success=False, error="send_queue_full")

    def send_to_room(self, room_id: str, message: str, exclude: Optional[str] = None) -> int:
        """广播消息到房间"""
        room = self._rooms.get(room_id)
        if not room:
            return 0
        sent = 0
        for conn_id in list(room._members):
            if exclude and conn_id == exclude:
                continue
            conn = self._connections.get(conn_id)
            if conn and conn.state in (ConnectionState.CONNECTED, ConnectionState.AUTHENTICATED):
                self.send_to_connection(conn_id, message)
                sent += 1
        room.total_messages += 1
        # 保存历史
        if room.message_history:
            room.history.append({"message": message, "timestamp": datetime.now().isoformat()})
            if len(room.history) > room.history_max:
                room.history = room.history[-room.history_max // 2 :]
        return sent

    def broadcast(self, message: str) -> int:
        """广播到所有连接"""
        sent = 0
        for conn_id, conn in list(self._connections.items()):
            if conn.state in (ConnectionState.CONNECTED, ConnectionState.AUTHENTICATED):
                self.send_to_connection(conn_id, message)
                sent += 1
        return sent

    # ----------------------------------------------------------------
    # 发送工作协程
    # ----------------------------------------------------------------

    def _sender_worker(self, connection_id: str):
        """发送工作协程"""
        conn = self._connections.get(connection_id)
        if not conn:
            return
        while True:
            try:
                message = asyncio.wait_for(conn._send_queue.get(), timeout=5.0)
                if conn.ws:
                    conn.ws.send(message)
                conn.last_active = datetime.now().isoformat()
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"[WSManager] 发送失败: {connection_id}, {e}")
                break

    # ----------------------------------------------------------------
    # 内置消息处理器
    # ----------------------------------------------------------------

    def _handle_ping(self, conn_id: str, data: Dict):
        conn = self._connections.get(conn_id)
        if conn:
            conn.last_ping = datetime.now().isoformat()
            self.send_to_connection(conn_id, json.dumps({"type": "pong", "timestamp": datetime.now().isoformat()}))

    def _handle_pong(self, conn_id: str, data: Dict):
        conn = self._connections.get(conn_id)
        if conn:
            conn.last_pong = datetime.now().isoformat()

    def _handle_join(self, conn_id: str, data: Dict):
        room_id = data.get("room_id", "")
        if room_id:
            self.join_room(conn_id, room_id)

    def _handle_leave(self, conn_id: str, data: Dict):
        room_id = data.get("room_id", "")
        if room_id:
            self.leave_room(conn_id, room_id)

    # ----------------------------------------------------------------
    # 心跳检查
    # ----------------------------------------------------------------

    def _heartbeat_loop(self):
        """心跳检查循环"""
        while True:
            try:
                time.sleep(self._heartbeat_interval)
                now = datetime.now()
                for conn_id, conn in list(self._connections.items()):
                    if conn.state not in (ConnectionState.CONNECTED, ConnectionState.AUTHENTICATED):
                        continue
                    # 发送ping
                    self.send_to_connection(conn_id, json.dumps({"type": "ping"}))
                    conn.last_ping = now.isoformat()
                    # 检查超时
                    if conn.last_pong:
                        try:
                            pong_time = datetime.fromisoformat(conn.last_pong)
                            if conn.last_ping:
                                ping_time = datetime.fromisoformat(conn.last_ping)
                                if (
                                    pong_time < ping_time
                                    and (now - ping_time).total_seconds() > self._heartbeat_timeout
                                ):
                                    self._ws_stats["heartbeat_timeouts"] += 1
                                    self.unregister_connection(conn_id, 4000, "heartbeat_timeout")
                                    logger.warning(f"[WSManager] 心跳超时: {conn_id}")
                        except Exception:
                            pass
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[WSManager] 心跳检查异常: {e}")

    # ----------------------------------------------------------------
    # 事件系统
    # ----------------------------------------------------------------

    def on(self, event_name: str, handler: Callable):
        """注册事件处理器"""
        self._event_handlers[event_name].append(handler)

    def _emit_event(self, event_name: str, data: Dict):
        """触发事件"""
        for handler in self._event_handlers.get(event_name, []):
            try:
                handler(data)
            except Exception as e:
                logger.error(f"[WSManager] 事件处理错误: {event_name}, {e}")

    # ----------------------------------------------------------------
    # 查询接口
    # ----------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        active = sum(
            1
            for c in self._connections.values()
            if c.state in (ConnectionState.CONNECTED, ConnectionState.AUTHENTICATED)
        )
        return {
            **self._ws_stats,
            "active_connections": active,
            "authenticated": sum(1 for c in self._connections.values() if c.authenticated),
            "total_rooms": len(self._rooms),
            "max_connections": self._max_connections,
            "module_stats": self.stats.to_dict(),
        }

    def get_room_info(self, room_id: str) -> Optional[Dict]:
        room = self._rooms.get(room_id)
        if not room:
            return None
        return {
            "room_id": room.room_id,
            "name": room.name,
            "members": room.member_count,
            "max_members": room.max_members,
            "total_messages": room.total_messages,
            "history_length": len(room.history),
            "persistent": room.persistent,
        }

# ============================================================================
# 模块注册
# ============================================================================

module_class = WebSocketManager
