"""
AUTO-EVO-AI V0.1 — 分布式协调服务
Grade: A (生产级) | Category: 分布式基础
职责：分布式锁、Leader选举、分布式Barrier、命名服务、会话管理
"""

__module_meta__ = {
    "id": "coordination",
    "name": "Coordination",
    "version": "V0.1",
    "group": "system",
    "inputs": [
        {"name": "lock_key", "type": "string", "required": True, "description": ""},
        {"name": "service_id", "type": "string", "required": True, "description": ""},
        {"name": "resource", "type": "string", "required": True, "description": ""},
        {"name": "ttl_seconds", "type": "string", "required": True, "description": ""},
        {"name": "owner", "type": "string", "required": True, "description": ""},
        {"name": "group", "type": "string", "required": True, "description": ""},
    ],
    "outputs": [
        {"name": "success", "type": "bool", "description": "是否成功"},
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
    ],
    "triggers": [],
    "depends_on": [],
    "tags": ["coordination", "service", "manager"],
    "grade": "B",
    "description": "AUTO-EVO-AI V0.1 — 分布式协调服务 Grade: A (生产级) | Category: 分布式基础",
}

import os
import time
import uuid
import logging
import hashlib
from typing import Any, Dict, List, Optional, Set
from datetime import datetime
from dataclasses import dataclass, field
from collections import defaultdict
from enum import Enum

try:
    from modules._base.enterprise_module import EnterpriseModule
    from modules._base.mixins import CircuitBreakerMixin, RateLimiterMixin
except ImportError:
    import sys

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _base.enterprise_module import EnterpriseModule

logger = logging.getLogger(__name__)

class LockType(str, Enum):
    EXCLUSIVE = "exclusive"
    SHARED = "shared"
    READ = "shared"
    WRITE = "exclusive"

@dataclass
class DistributedLock:
    lock_key: str = ""
    lock_type: str = "exclusive"
    owner: str = ""
    ttl_seconds: int = 30
    acquired_at: float = 0.0
    expires_at: float = 0.0
    generation: int = 0
    shared_owners: Set[str] = field(default_factory=set)

@dataclass
class ElectionRecord:
    election_id: str = ""
    topic: str = ""
    leader: str = ""
    candidates: List[str] = field(default_factory=list)
    epoch: int = 0
    state: str = "pending"  # pending, elected, expired
    started_at: float = 0.0
    leader_since: float = 0.0

@dataclass
class ServiceNode:
    node_id: str = ""
    name: str = ""
    address: str = ""
    port: int = 0
    metadata: Dict[str, str] = field(default_factory=dict)
    status: str = "up"
    registered_at: float = 0.0
    last_heartbeat: float = 0.0
    ttl_seconds: int = 60

@dataclass
class CoordinationSession:
    session_id: str = ""
    node_id: str = ""
    created_at: float = 0.0
    last_heartbeat: float = 0.0
    timeout_ms: int = 30000
    ephemeral_nodes: List[str] = field(default_factory=list)
    watches: List[str] = field(default_factory=list)
    is_active: bool = True

class CoordinationManager(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    MODULE_ID = "coordination"
    MODULE_NAME = "coordination"
    VERSION = "V0.1"

    def __init__(self):

        super().__init__(
            config={
                "module_id": "coordination",
                "version": "7.0.0",
                "description": "分布式协调服务：锁/选举/命名服务/会话管理",
            }
        )
        self._locks: Dict[str, DistributedLock] = {}
        self._elections: Dict[str, ElectionRecord] = {}
        self._nodes: Dict[str, ServiceNode] = {}
        self._services: Dict[str, List[str]] = defaultdict(list)  # service_name -> node_ids
        self._sessions: Dict[str, CoordinationSession] = {}
        self._barriers: Dict[str, Dict] = {}  # barrier_id -> {required: n, arrived: set, released: bool}
        self._initialized = False

    def initialize(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        # 预设服务节点
        for name, addr, port, meta in [
            ("api-1", "10.0.1.1", 8080, {"version": "7.0", "zone": "east"}),
            ("api-2", "10.0.1.2", 8080, {"version": "7.0", "zone": "east"}),
            ("worker-1", "10.0.2.1", 9090, {"version": "7.0", "zone": "west"}),
            ("worker-2", "10.0.2.2", 9090, {"version": "7.0", "zone": "west"}),
        ]:
            node = ServiceNode(
                node_id=f"node_{uuid.uuid4().hex[:8]}",
                name=name,
                address=addr,
                port=port,
                metadata=meta,
                status="up",
                registered_at=time.time(),
                last_heartbeat=time.time(),
            )
            self._nodes[node.node_id] = node
            svc = name.rsplit("-", 1)[0]
            self._services[svc].append(node.node_id)

    def _check_lock_expiry(self, lock_key: str) -> bool:
        lock = self._locks.get(lock_key)
        if lock and time.time() > lock.expires_at:
            del self._locks[lock_key]
            return True
        return False

    async def execute(self, action: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        self.trace("execute", {"module": "coordination"})
        self.metrics_collector.counter("coordination.execute.calls", 1)
        self.audit("execute", {"module": "coordination"})
        params = params or {}
        try:
            pass
            # === 分布式锁 ===
            if action == "acquire_lock":
                lock_key = params.get("lock_key", "")
                owner = params.get("owner", "default")
                lock_type = params.get("lock_type", "exclusive")
                ttl = params.get("ttl", 30)
                if not lock_key:
                    return {"success": False, "error": "lock_key不能为空"}
                self._check_lock_expiry(lock_key)
                existing = self._locks.get(lock_key)
                if existing and lock_type == "exclusive":
                    return {"success": False, "error": "锁已被占用", "result": {"owner": existing.owner}}
                if existing and existing.lock_type == "exclusive":
                    return {"success": False, "error": "排他锁被占用", "result": {"owner": existing.owner}}
                if lock_type == "shared" and existing:
                    if owner in existing.shared_owners:
                        return {"success": True, "result": {"lock_key": lock_key, "reentrant": True}}
                    existing.shared_owners.add(owner)
                    return {
                        "success": True,
                        "result": {"lock_key": lock_key, "shared_count": len(existing.shared_owners)},
                    }
                lock = DistributedLock(
                    lock_key=lock_key,
                    lock_type=lock_type,
                    owner=owner,
                    ttl_seconds=ttl,
                    acquired_at=time.time(),
                    expires_at=time.time() + ttl,
                    generation=1,
                )
                if lock_type == "shared":
                    lock.shared_owners = {owner}
                self._locks[lock_key] = lock
                return {
                    "success": True,
                    "result": {"lock_key": lock_key, "owner": owner, "lock_type": lock_type, "ttl": ttl},
                }

            elif action == "release_lock":
                lock_key = params.get("lock_key", "")
                owner = params.get("owner", "default")
                lock = self._locks.get(lock_key)
                if not lock:
                    return {"success": False, "error": "锁不存在"}
                if lock.lock_type == "shared":
                    lock.shared_owners.discard(owner)
                    if not lock.shared_owners:
                        del self._locks[lock_key]
                    return {"success": True, "result": {"released": True, "remaining": len(lock.shared_owners)}}
                if lock.owner != owner:
                    return {"success": False, "error": "不是锁的持有者"}
                del self._locks[lock_key]
                return {"success": True, "result": {"released": True}}

            elif action == "list_locks":
                active_locks = {}
                expired_keys = []
                for k, v in self._locks.items():
                    if time.time() > v.expires_at:
                        expired_keys.append(k)
                    else:
                        active_locks[k] = {
                            "owner": v.owner,
                            "type": v.lock_type,
                            "ttl_remaining": round(v.expires_at - time.time(), 1),
                        }
                for k in expired_keys:
                    del self._locks[k]
                return {"success": True, "result": {"total": len(active_locks), "locks": active_locks}}

            # === Leader选举 ===
            elif action == "elect":
                topic = params.get("topic", "default")
                candidate = params.get("candidate", "node-1")
                if topic not in self._elections:
                    self._elections[topic] = ElectionRecord(
                        election_id=f"elec_{uuid.uuid4().hex[:8]}", topic=topic, candidates=[], started_at=time.time()
                    )
                elec = self._elections[topic]
                if candidate not in elec.candidates:
                    elec.candidates.append(candidate)
                elec.leader = elec.candidates[0]  # 简单策略：第一个候选人为leader
                elec.epoch += 1
                elec.state = "elected"
                if not elec.leader_since:
                    elec.leader_since = time.time()
                return {
                    "success": True,
                    "result": {
                        "topic": topic,
                        "leader": elec.leader,
                        "epoch": elec.epoch,
                        "candidates": elec.candidates,
                        "is_leader": elec.leader == candidate,
                    },
                }

            elif action == "get_leader":
                topic = params.get("topic", "default")
                elec = self._elections.get(topic)
                if not elec:
                    return {"success": False, "error": f"选举{topic}不存在"}
                return {
                    "success": True,
                    "result": {
                        "topic": topic,
                        "leader": elec.leader,
                        "epoch": elec.epoch,
                        "state": elec.state,
                        "candidates": elec.candidates,
                    },
                }

            elif action == "resign":
                topic = params.get("topic", "")
                elec = self._elections.get(topic)
                if not elec:
                    return {"success": False, "error": f"选举{topic}不存在"}
                if elec.leader in elec.candidates:
                    elec.candidates.remove(elec.leader)
                elec.leader = elec.candidates[0] if elec.candidates else ""
                elec.epoch += 1
                if not elec.leader:
                    elec.state = "expired"
                return {"success": True, "result": {"new_leader": elec.leader, "epoch": elec.epoch}}

            # === 命名服务 ===
            elif action == "register_node":
                node_id = params.get("node_id") or f"node_{uuid.uuid4().hex[:8]}"
                node = ServiceNode(
                    node_id=node_id,
                    name=params.get("name", ""),
                    address=params.get("address", ""),
                    port=params.get("port", 0),
                    metadata=params.get("metadata", {}),
                    status="up",
                    registered_at=time.time(),
                    last_heartbeat=time.time(),
                    ttl_seconds=params.get("ttl", 60),
                )
                self._nodes[node_id] = node
                svc = params.get("service", "")
                if svc:
                    if node_id not in self._services[svc]:
                        self._services[svc].append(node_id)
                return {"success": True, "result": {"node_id": node_id}}

            elif action == "discover":
                svc = params.get("service", "")
                nodes = []
                if svc:
                    for nid in self._services.get(svc, []):
                        node = self._nodes.get(nid)
                        if node and node.status == "up":
                            nodes.append(
                                {"node_id": nid, "address": node.address, "port": node.port, "metadata": node.metadata}
                            )
                return {"success": True, "result": {"service": svc, "nodes": nodes}}

            elif action == "heartbeat":
                nid = params.get("node_id", "")
                node = self._nodes.get(nid)
                if not node:
                    return {"success": False, "error": f"节点{nid}不存在"}
                node.last_heartbeat = time.time()
                node.status = "up"
                return {"success": True, "result": {"ack": True}}

            # === Barrier ===
            elif action == "create_barrier":
                bid = params.get("barrier_id") or f"barrier_{uuid.uuid4().hex[:8]}"
                self._barriers[bid] = {
                    "required": params.get("required", 2),
                    "arrived": set(),
                    "released": False,
                    "created_at": time.time(),
                }
                return {"success": True, "result": {"barrier_id": bid}}

            elif action == "barrier_enter":
                bid = params.get("barrier_id", "")
                party = params.get("party", "default")
                barrier = self._barriers.get(bid)
                if not barrier:
                    return {"success": False, "error": "Barrier不存在"}
                barrier["arrived"].add(party)
                if len(barrier["arrived"]) >= barrier["required"]:
                    barrier["released"] = True
                    return {"success": True, "result": {"released": True, "parties": len(barrier["arrived"])}}
                return {
                    "success": True,
                    "result": {
                        "released": False,
                        "waiting": barrier["required"] - len(barrier["arrived"]),
                        "arrived": len(barrier["arrived"]),
                    },
                }

            elif action == "get_stats":
                return {
                    "success": True,
                    "result": {
                        "locks": len(self._locks),
                        "elections": len(self._elections),
                        "nodes": len(self._nodes),
                        "services": len(self._services),
                        "barriers": len(self._barriers),
                        "sessions": len(self._sessions),
                    },
                }

            else:
                return {"success": False, "error": f"未知操作: {action}"}
        except Exception as e:
            logger.error(f"[Coordination] execute异常: {action}, {e}")
            return {"success": False, "error": str(e)}

    def health_check(self) -> Dict[str, Any]:
        base = super().health_check()
        if base and hasattr(base, "to_dict"):
            base = base.to_dict()
        elif not isinstance(base, dict):
            base = {}
        base = base or {}
        base.update(
            {
                "status": "healthy",
                "locks": len(self._locks),
                "nodes": len(self._nodes),
                "services": len(self._services),
                "elections": len(self._elections),
            }
        )
        return base

    async def shutdown(self) -> None:
        self._initialized = False

    def get_service_registry(self) -> Dict[str, Any]:
        """服务注册表。企业场景：微服务架构中查看所有已注册服务的状态、地址、版本。
        服务发现的核心数据源，供API Gateway和负载均衡器使用。
        """
        services = getattr(self, "_services", {})
        registry = []
        for svc_id, svc in services.items():
            registry.append(
                {
                    "service_id": svc_id,
                    "name": getattr(svc, "name", svc_id),
                    "address": getattr(svc, "address", ""),
                    "port": getattr(svc, "port", 0),
                    "status": getattr(svc, "status", "unknown"),
                    "version": getattr(svc, "version", ""),
                    "last_heartbeat": getattr(svc, "last_heartbeat", 0),
                }
            )
        healthy = sum(1 for r in registry if r["status"] == "healthy")
        return {
            "success": True,
            "total_services": len(registry),
            "healthy": healthy,
            "unhealthy": len(registry) - healthy,
            "services": registry,
        }

    def get_leader_status(self) -> Dict[str, Any]:
        """Leader选举状态。企业场景：排查主从切换问题，查看当前谁是Leader，
        上次选举时间和选举次数。
        """
        elections = getattr(self, "_elections", {})
        status = []
        for group, election in elections.items():
            status.append(
                {
                    "group": group,
                    "leader": getattr(election, "leader", "unknown"),
                    "term": getattr(election, "term", 0),
                    "last_election": getattr(election, "last_election_time", 0),
                    "election_count": getattr(election, "election_count", 0),
                }
            )
        return {"success": True, "election_groups": len(status), "status": status}

    def deregister_service(self, service_id: str) -> Dict[str, Any]:
        """注销服务。企业场景：服务下线/缩容时从注册中心移除实例，
        避免负载均衡将请求路由到已下线的节点。
        """
        services = getattr(self, "_services", {})
        if service_id not in services:
            return {"success": False, "error": f"服务 {service_id} 未注册"}
        service = services.pop(service_id)
        if self._audit:
            self._audit.log("service_deregistered", {"service_id": service_id})
        return {"success": True, "service_id": service_id, "name": getattr(service, "name", service_id)}

    def acquire_lock(self, resource: str, ttl_seconds: int = 30, owner: str = "default") -> Dict[str, Any]:
        """获取分布式锁。企业场景：定时任务/幂等操作前获取锁，
        防止多实例重复执行。支持TTL自动过期。
        """
        locks = getattr(self, "_locks", {})
        existing = locks.get(resource)
        if existing:
            if existing.get("expires_at", 0) > time.time():
                return {
                    "success": False,
                    "error": "资源已被锁定",
                    "locked_by": existing.get("owner", "?"),
                    "remaining_ttl": round(existing["expires_at"] - time.time(), 1),
                }
            # 锁已过期，自动释放
            del locks[resource]
        locks[resource] = {"owner": owner, "acquired_at": time.time(), "expires_at": time.time() + ttl_seconds}
        return {"success": True, "resource": resource, "owner": owner, "ttl_seconds": ttl_seconds}

    def get_service_registry_snapshot(self) -> Dict[str, Any]:
        """服务注册表快照。企业场景：运维dashboard实时展示集群中所有已注册服务
        及其健康状态，快速发现服务下线或异常。
        """
        services = getattr(self, "_services", {})
        snapshot = []
        now = time.time()
        for svc_id, svc in services.items():
            last_heartbeat = getattr(svc, "last_heartbeat", 0)
            age = now - last_heartbeat if last_heartbeat else 9999
            status = "healthy" if age < 30 else ("warning" if age < 90 else "critical")
            snapshot.append(
                {
                    "service_id": svc_id,
                    "address": getattr(svc, "address", ""),
                    "port": getattr(svc, "port", 0),
                    "status": status,
                    "last_heartbeat_age_s": int(age),
                    "metadata": getattr(svc, "metadata", {}),
                }
            )
        snapshot.sort(key=lambda x: x["last_heartbeat_age_s"])
        healthy = sum(1 for s in snapshot if s["status"] == "healthy")
        return {
            "success": True,
            "total": len(snapshot),
            "healthy": healthy,
            "unhealthy": len(snapshot) - healthy,
            "services": snapshot,
        }

    def run_leader_election(self, group: str, candidate_id: str) -> Dict[str, Any]:
        """执行Leader选举。企业场景：主从架构中选举主节点，基于租约机制
        确保同一时刻只有一个Leader处理写请求。
        """
        locks = getattr(self, "_locks", {})
        lock_key = f"leader:{group}"
        existing = locks.get(lock_key)
        if existing:
            if time.time() < existing.get("expires_at", 0):
                return {
                    "success": False,
                    "is_leader": False,
                    "current_leader": existing.get("owner", "unknown"),
                    "remaining_lease_s": int(existing["expires_at"] - time.time()),
                }
        lease_ttl = 30
        locks[lock_key] = {"owner": candidate_id, "acquired_at": time.time(), "expires_at": time.time() + lease_ttl}
        return {"success": True, "is_leader": True, "leader": candidate_id, "lease_ttl_s": lease_ttl}

    def deregister_service(self, service_id: str) -> Dict[str, Any]:
        """注销服务。企业场景：服务优雅下线时从注册表中移除，
        避免其他服务将请求路由到已下线的实例。
        """
        services = getattr(self, "_services", {})
        if service_id not in services:
            return {"success": False, "error": f"服务 {service_id} 未注册"}
        service = services.pop(service_id)
        return {
            "success": True,
            "service_id": service_id,
            "name": getattr(service, "name", service_id),
            "message": "服务已注销",
        }

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

module_class = CoordinationManager
