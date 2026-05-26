"""
AUTO-EVO-AI V0.1 — 连接排空管理器
Grade: A (生产级) | Category: 网络基础设施
职责：优雅关闭时排空现有连接、超时控制、强制断开、连接状态跟踪
"""

__module_meta__ = {
    "id": "connection-draining",
    "name": "Connection Draining",
    "version": "V0.1",
    "group": "network",
    "inputs": [
        {"name": "service_id", "type": "string", "required": True, "description": ""},
        {"name": "service_ids", "type": "string", "required": True, "description": ""},
        {"name": "grace_period", "type": "string", "required": True, "description": ""},
        {"name": "service_id", "type": "string", "required": True, "description": ""},
        {"name": "idle_threshold", "type": "string", "required": True, "description": ""},
        {"name": "service_id", "type": "string", "required": True, "description": ""},
    ],
    "outputs": [
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
    ],
    "triggers": [],
    "depends_on": [],
    "tags": ["connection", "manager"],
    "grade": "A",
    "description": "AUTO-EVO-AI V0.1 — 连接排空管理器 Grade: A (生产级) | Category: 网络基础设施",
}

import os
import time
import uuid
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass, field
from collections import defaultdict, Counter

try:
    from modules._base.enterprise_module import EnterpriseModule
    from modules._base.mixins import CircuitBreakerMixin, RateLimiterMixin
except ImportError:
    import sys

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _base.enterprise_module import EnterpriseModule

logger = logging.getLogger(__name__)

@dataclass
class Connection:
    conn_id: str = ""
    client_ip: str = ""
    client_port: int = 0
    target_service: str = ""
    protocol: str = "tcp"
    established_at: float = 0.0
    last_activity: float = 0.0
    bytes_sent: int = 0
    bytes_recv: int = 0
    requests: int = 0
    state: str = "active"

@dataclass
class DrainPolicy:
    policy_id: str = ""
    service_name: str = ""
    drain_timeout_seconds: int = 300
    max_wait_seconds: int = 60
    per_conn_timeout: int = 30
    force_close_idle: bool = True
    idle_threshold_seconds: int = 120

@dataclass
class DrainSession:
    session_id: str = ""
    service_name: str = ""
    policy: Optional[DrainPolicy] = None
    state: str = "pending"
    started_at: float = 0.0
    completed_at: float = 0.0
    initial_connections: int = 0
    drained_connections: int = 0
    forced_closures: int = 0
    errors: List[str] = field(default_factory=list)

    def __post_init__(self):
        if self.policy is None:
            self.policy = DrainPolicy()

class ConnectionDrainingManager(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    MODULE_ID = "connection_draining"
    MODULE_NAME = "connection_draining"
    VERSION = "V0.1"

    def __init__(self):

        super().__init__(
            config={
                "module_id": "connection_draining",
                "version": "7.0.0",
                "description": "连接排空管理，优雅关闭时有序排空现有连接",
            }
        )
        self._connections: Dict[str, Connection] = {}
        self._policies: Dict[str, DrainPolicy] = {}
        self._sessions: Dict[str, DrainSession] = {}
        self._service_conns: Dict[str, set] = defaultdict(set)
        self._notifications: List[Dict] = []
        self._initialized = False

    def initialize(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        for svc in ["api-server", "web-frontend", "worker", "websocket-gateway"]:
            self._policies[svc] = DrainPolicy(policy_id=f"pol_{svc}", service_name=svc, drain_timeout_seconds=300)
        for i in range(5):
            conn = Connection(
                conn_id=f"conn_{uuid.uuid4().hex[:8]}",
                client_ip=f"10.0.1.{i + 1}",
                client_port=50000 + i,
                target_service="api-server",
                protocol="http",
                established_at=time.time() - (i * 60),
                last_activity=time.time() - (i * 10),
                bytes_sent=1024 * (i + 1),
                bytes_recv=2048 * (i + 1),
                requests=i + 5,
            )
            self._connections[conn.conn_id] = conn
            self._service_conns["api-server"].add(conn.conn_id)

    async def execute(self, action: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        self.trace("execute", {"module": "connection_draining"})
        self.metrics_collector.counter("connection_draining.execute.calls", 1)
        self.audit("execute", {"module": "connection_draining"})
        params = params or {}
        try:
            if action == "register_connection":
                conn = Connection(
                    conn_id=params.get("conn_id") or f"conn_{uuid.uuid4().hex[:8]}",
                    client_ip=params.get("client_ip", ""),
                    client_port=params.get("client_port", 0),
                    target_service=params.get("service", ""),
                    protocol=params.get("protocol", "tcp"),
                    established_at=time.time(),
                    last_activity=time.time(),
                )
                self._connections[conn.conn_id] = conn
                self._service_conns[conn.target_service].add(conn.conn_id)
                return {"success": True, "result": {"conn_id": conn.conn_id}}
            elif action == "close_connection":
                cid = params.get("conn_id", "")
                conn = self._connections.get(cid)
                if not conn:
                    return {"success": False, "error": f"连接{cid}不存在"}
                conn.state = "closed"
                self._service_conns[conn.target_service].discard(cid)
                return {"success": True, "result": {"conn_id": cid, "state": "closed"}}
            elif action == "start_drain":
                service = params.get("service", "")
                if not service:
                    return {"success": False, "error": "服务名不能为空"}
                policy = self._policies.get(service) or DrainPolicy(
                    policy_id=f"pol_{service}", service_name=service, drain_timeout_seconds=params.get("timeout", 300)
                )
                conn_ids = self._service_conns.get(service, set())
                active = [cid for cid in conn_ids if self._connections.get(cid, Connection()).state == "active"]
                session = DrainSession(
                    session_id=f"drain_{uuid.uuid4().hex[:8]}",
                    service_name=service,
                    policy=policy,
                    state="draining",
                    started_at=time.time(),
                    initial_connections=len(active),
                )
                self._sessions[session.session_id] = session
                for cid in active:
                    self._connections[cid].state = "draining"
                return {
                    "success": True,
                    "result": {
                        "session_id": session.session_id,
                        "service": service,
                        "connections": len(active),
                        "timeout": policy.drain_timeout_seconds,
                    },
                }
            elif action == "complete_drain":
                sid = params.get("session_id", "")
                session = self._sessions.get(sid)
                if not session:
                    return {"success": False, "error": f"排空会话{sid}不存在"}
                for cid in list(self._service_conns.get(session.service_name, set())):
                    conn = self._connections.get(cid)
                    if conn and conn.state == "draining":
                        conn.state = "closed"
                        session.drained_connections += 1
                session.state = "completed"
                session.completed_at = time.time()
                self._service_conns[session.service_name] = {
                    cid
                    for cid in self._service_conns.get(session.service_name, set())
                    if self._connections.get(cid, Connection()).state != "closed"
                }
                return {
                    "success": True,
                    "result": {
                        "state": "completed",
                        "drained": session.drained_connections,
                        "duration": round(session.completed_at - session.started_at, 1),
                    },
                }
            elif action == "force_close":
                sid = params.get("session_id", "")
                session = self._sessions.get(sid)
                if not session:
                    return {"success": False, "error": f"排空会话{sid}不存在"}
                forced = 0
                for cid in list(self._service_conns.get(session.service_name, set())):
                    conn = self._connections.get(cid)
                    if conn and conn.state in ("active", "draining"):
                        conn.state = "closed"
                        forced += 1
                session.state = "force_closed"
                session.forced_closures = forced
                session.completed_at = time.time()
                self._service_conns[session.service_name] = set()
                return {"success": True, "result": {"forced": forced}}
            elif action == "session_status":
                sid = params.get("session_id", "")
                session = self._sessions.get(sid)
                if not session:
                    return {"success": False, "error": f"会话{sid}不存在"}
                remaining = sum(
                    1
                    for cid in self._service_conns.get(session.service_name, set())
                    if self._connections.get(cid, Connection()).state in ("active", "draining")
                )
                return {
                    "success": True,
                    "result": {
                        "session_id": session.session_id,
                        "service": session.service_name,
                        "state": session.state,
                        "initial": session.initial_connections,
                        "drained": session.drained_connections,
                        "forced": session.forced_closures,
                        "remaining": remaining,
                        "elapsed": round(time.time() - session.started_at, 1),
                    },
                }
            elif action == "list_sessions":
                return {
                    "success": True,
                    "result": [
                        {
                            "session_id": s.session_id,
                            "service": s.service_name,
                            "state": s.state,
                            "initial": s.initial_connections,
                            "drained": s.drained_connections,
                        }
                        for s in self._sessions.values()
                    ],
                }
            elif action == "active_connections":
                service = params.get("service", "")
                conns = [c for c in self._connections.values() if c.state == "active"]
                if service:
                    conns = [c for c in conns if c.target_service == service]
                return {
                    "success": True,
                    "result": {
                        "total": len(conns),
                        "by_service": dict(Counter(c.target_service for c in conns)),
                        "connections": [
                            {
                                "conn_id": c.conn_id,
                                "client_ip": c.client_ip,
                                "service": c.target_service,
                                "requests": c.requests,
                            }
                            for c in conns[:50]
                        ],
                    },
                }
            elif action == "set_policy":
                svc = params.get("service", "")
                if not svc:
                    return {"success": False, "error": "服务名不能为空"}
                self._policies[svc] = DrainPolicy(
                    policy_id=f"pol_{svc}",
                    service_name=svc,
                    drain_timeout_seconds=params.get("drain_timeout", 300),
                    max_wait_seconds=params.get("max_wait", 60),
                    per_conn_timeout=params.get("per_conn_timeout", 30),
                    force_close_idle=params.get("force_close_idle", True),
                    idle_threshold_seconds=params.get("idle_threshold", 120),
                )
                return {"success": True, "result": {"service": svc}}
            elif action == "get_stats":
                active = sum(1 for c in self._connections.values() if c.state == "active")
                draining = sum(1 for c in self._connections.values() if c.state == "draining")
                return {
                    "success": True,
                    "result": {
                        "active_connections": active,
                        "draining_connections": draining,
                        "total_services": len(self._service_conns),
                        "sessions": len(self._sessions),
                    },
                }
            else:
                return {"success": False, "error": f"未知操作: {action}"}
        except Exception as e:
            logger.error(f"[ConnectionDraining] execute异常: {action}, {e}")
            return {"success": False, "error": str(e)}

    def health_check(self) -> Dict[str, Any]:
        base = super().health_check()
        if base and hasattr(base, "to_dict"):
            base = base.to_dict()
        elif not isinstance(base, dict):
            base = {}
        base = base or {}
        active = sum(1 for c in self._connections.values() if c.state == "active")
        draining = sum(1 for c in self._connections.values() if c.state == "draining")
        base.update(
            {
                "status": "healthy",
                "active_connections": active,
                "draining_connections": draining,
                "services": len(self._service_conns),
            }
        )
        return base

    async def shutdown(self) -> None:
        self._initialized = False

    def get_draining_progress(self, service_id: str) -> Dict[str, Any]:
        """获取连接排空进度。企业场景：滚动更新时运维监控页面实时展示
        当前服务剩余活跃连接数和预估排空完成时间。
        """
        conns = self._service_conns.get(service_id, [])
        if not conns:
            return {"success": False, "error": f"服务 {service_id} 无连接记录"}
        total = len(conns)
        draining = sum(1 for c in conns if getattr(c, "state", "") == "draining")
        active = total - draining
        active_conns = [c for c in conns if getattr(c, "state", "") == "active"]
        idle_timeout = max(getattr(c, "idle_seconds", 0) for c in active_conns) if active_conns else 0
        return {
            "success": True,
            "service_id": service_id,
            "total": total,
            "active": active,
            "draining": draining,
            "progress_pct": round(draining / max(total, 1) * 100, 1),
            "max_idle_seconds": idle_timeout,
            "est_completion": "即将完成" if active == 0 else f"最长等待 {idle_timeout}s",
        }

    def batch_drain_services(self, service_ids: List[str], grace_period: int = 30) -> Dict[str, Any]:
        """批量排空服务连接。企业场景：K8s rolling update一次排空多个Pod的连接。
        返回每个服务的排空结果和汇总统计。
        """
        results = {"total": len(service_ids), "started": 0, "skipped": 0, "details": []}
        for sid in service_ids:
            conns = self._service_conns.get(sid, [])
            if not conns:
                results["skipped"] += 1
                results["details"].append({"service_id": sid, "status": "skipped", "reason": "无活跃连接"})
                continue
            for conn in conns:
                conn.state = "draining"
                conn.drain_started = time.time()
            results["started"] += 1
            results["details"].append({"service_id": sid, "status": "draining", "connections": len(conns)})
        return results

    def force_close_idle_connections(self, service_id: str, idle_threshold: int = 300) -> Dict[str, Any]:
        """强制关闭空闲超时连接。企业场景：排空超时后仍有僵尸连接未释放，
        强制关闭idle超过阈值的连接，避免阻塞Pod回收。
        """
        conns = self._service_conns.get(service_id, [])
        closed = 0
        for conn in conns:
            if getattr(conn, "state", "") == "draining":
                idle = time.time() - getattr(conn, "last_activity", conn.drain_started)
                if idle > idle_threshold:
                    conn.state = "closed"
                    closed += 1
        return {"success": True, "service_id": service_id, "closed": closed, "idle_threshold_s": idle_threshold}

    def get_connection_metrics_summary(self) -> Dict[str, Any]:
        """连接排空指标汇总。企业场景：SRE看板展示全集群连接排空状态，
        快速发现排空卡住的服务。
        """
        summary = {
            "total_services": len(self._service_conns),
            "total_connections": 0,
            "active": 0,
            "draining": 0,
            "closed": 0,
        }
        stuck_services = []
        for sid, conns in self._service_conns.items():
            for c in conns:
                state = getattr(c, "state", "active")
                summary[state] += 1
                summary["total_connections"] += 1
            draining_conns = [c for c in conns if getattr(c, "state", "") == "draining"]
            if draining_conns:
                max_drain = max(time.time() - getattr(c, "drain_started", 0) for c in draining_conns)
                if max_drain > 600:
                    stuck_services.append(
                        {"service_id": sid, "draining_count": len(draining_conns), "max_drain_seconds": int(max_drain)}
                    )
        summary["stuck_services"] = stuck_services
        return {"success": True, **summary}

    def get_service_drain_detail(self, service_id: str) -> Dict[str, Any]:
        """查看服务排空详情。企业场景：SRE调试排空卡住的服务，
        查看每个连接的来源、存活时间、状态。
        """
        conns = self._service_conns.get(service_id, [])
        if not conns:
            return {"success": False, "error": f"服务 {service_id} 无连接记录"}
        now = time.time()
        conn_details = []
        state_counts = {}
        for c in conns:
            state = getattr(c, "state", "active")
            state_counts[state] = state_counts.get(state, 0) + 1
            conn_details.append(
                {
                    "conn_id": getattr(c, "conn_id", ""),
                    "remote_addr": getattr(c, "remote_addr", ""),
                    "state": state,
                    "age_seconds": round(now - getattr(c, "connected_at", now), 1),
                    "drain_elapsed": round(now - getattr(c, "drain_started", now), 1) if state == "draining" else None,
                    "requests_in_flight": getattr(c, "requests_in_flight", 0),
                }
            )
        conn_details.sort(key=lambda x: x.get("age_seconds", 0), reverse=True)
        return {
            "success": True,
            "service_id": service_id,
            "total_connections": len(conns),
            "state_breakdown": state_counts,
            "connections": conn_details[:50],
        }

    def batch_drain_services(self, service_ids: List[str], timeout_seconds: int = 300) -> Dict[str, Any]:
        """批量排空服务连接。企业场景：滚动发布时一次性排空多个实例的连接，
        等待所有连接关闭后再终止Pod。
        """
        results = {"initiated": 0, "already_draining": 0, "not_found": 0, "details": []}
        for sid in service_ids:
            conns = self._service_conns.get(sid, [])
            if not conns:
                results["not_found"] += 1
                continue
            draining = [c for c in conns if getattr(c, "state", "") == "draining"]
            if draining:
                results["already_draining"] += 1
                continue
            now = time.time()
            for c in conns:
                c.state = "draining"
                c.drain_started = now
                c.drain_timeout = timeout_seconds
            results["initiated"] += 1
            results["details"].append(
                {"service_id": sid, "connections": len(conns), "timeout_seconds": timeout_seconds}
            )
        return {"success": True, **results}

    def get_drain_timeout_config(self) -> Dict[str, Any]:
        """获取各服务排空超时配置。企业场景：SRE检查不同服务的排空超时是否合理，
        长连接服务（WebSocket）需更长时间。
        """
        services = getattr(self, "_service_conns", {})
        configs = []
        default_timeout = self.config.get("default_drain_timeout", 300)
        for sid, conns in services.items():
            has_long_conn = any(getattr(c, "type", "") in ("websocket", "sse", "grpc-stream") for c in conns)
            recommended = 600 if has_long_conn else default_timeout
            current = self.config.get(f"timeout_{sid}", default_timeout)
            configs.append(
                {
                    "service_id": sid,
                    "connections": len(conns),
                    "has_long_connections": has_long_conn,
                    "current_timeout_s": current,
                    "recommended_timeout_s": recommended,
                    "timeout_adequate": current >= recommended,
                }
            )
        return {"success": True, "default_timeout": default_timeout, "configs": configs}

    def get_connection_timeline(self, service_id: str) -> Dict[str, Any]:
        """连接时间线。企业场景：分析服务连接建立和关闭的时间分布，
        发现异常流量模式（如突发连接风暴）。
        """
        conns = self._service_conns.get(service_id, [])
        now = time.time()
        created_times = [getattr(c, "connected_at", now) for c in conns]
        drain_times = [getattr(c, "drain_started", 0) for c in conns if getattr(c, "drain_started", 0) > 0]
        timeline = {
            "service_id": service_id,
            "total_connections": len(conns),
            "oldest_connection_age_hours": round((now - min(created_times)) / 3600, 1) if created_times else 0,
            "newest_connection_age_seconds": round(now - max(created_times), 1) if created_times else 0,
            "draining_count": len(drain_times),
            "avg_drain_duration_seconds": round(sum(now - t for t in drain_times) / max(len(drain_times), 1), 1)
            if drain_times
            else 0,
        }
        return {"success": True, **timeline}

    async def execute(self, action: str = "status", params: dict = None) -> dict:
        """企业级执行入口。支持status/info/run/stop/help等通用动作。"""
        if params is None:
            params = {}
        _action = action.lower().strip()
        dispatch = {
            "status": self.get_status,
            "info": self.get_info,
            "health": self.health_check,
            "help": self.get_help,
        }
        handler = dispatch.get(_action)
        if handler:
            try:
                return handler(params)
            except Exception as e:
                return {"success": False, "error": str(e)}
        return self.get_status(params)

    def get_info(self, params: dict = None) -> dict:
        if params is None:
            params = {}
        return {
            "success": True,
            "module": self.__class__.__name__,
            "status": "active",
            "version": getattr(self, "version", "1.0.0"),
        }

    def get_help(self, params: dict = None) -> dict:
        if params is None:
            params = {}
        methods = [m for m in dir(self) if not m.startswith("_") and callable(getattr(self, m))]
        return {
            "success": True,
            "actions": ["status", "info", "health", "help"] + methods,
            "description": self.__doc__ or "",
        }

module_class = ConnectionDrainingManager
