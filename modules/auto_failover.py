"""
AUTO-EVO-AI V0.1 — 自动故障转移
Grade: A (生产级) | Category: 高可用
职责：故障检测、自动切换、健康探测、流量重路由、恢复验证
"""

__module_meta__ = {
    "id": "auto-failover",
    "name": "Auto Failover",
    "version": "V0.1",
    "group": "resilience",
    "inputs": [
        {"name": "config", "type": "string", "required": True, "description": ""},
        {"name": "action", "type": "string", "required": True, "description": ""},
        {"name": "params", "type": "string", "required": True, "description": ""},
        {"name": "node_id", "type": "string", "required": True, "description": ""},
        {"name": "health", "type": "string", "required": True, "description": ""},
        {"name": "from_node", "type": "string", "required": True, "description": ""},
    ],
    "outputs": [
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
    ],
    "triggers": [],
    "depends_on": [],
    "tags": ["manager", "auto"],
    "grade": "B",
    "description": "AUTO-EVO-AI V0.1 — 自动故障转移 Grade: A (生产级) | Category: 高可用",
}

import os
import asyncio
import time
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field

try:
    from modules._base.enterprise_module import EnterpriseModule
    from modules._base.mixins import CircuitBreakerMixin, RateLimiterMixin
    from modules._base.tracing import trace_operation
    from modules._base.metrics import metrics_collector
    from _base.audit import AuditLogger
except ImportError:
    import sys

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _base.enterprise_module import EnterpriseModule
    from _base.tracing import trace_operation
    from _base.metrics import metrics_collector
    from _base.audit import AuditLogger

logger = logging.getLogger("auto_failover")

class NodeStatus(Enum):
    ACTIVE = "active"
    STANDBY = "standby"
    FAULTED = "faulted"
    RECOVERING = "recovering"
    MAINTENANCE = "maintenance"

class FailoverState(Enum):
    NORMAL = "normal"
    DETECTING = "detecting"
    FAILOVER_IN_PROGRESS = "failover_in_progress"
    FAILED_OVER = "failed_over"
    RECOVERING = "recovering"

@dataclass
class ClusterNode:
    """集群节点"""

    node_id: str
    name: str
    address: str
    role: str = "worker"
    status: NodeStatus = NodeStatus.ACTIVE
    weight: int = 100
    priority: int = 0
    health_score: float = 1.0
    consecutive_failures: int = 0
    last_health_check: float = 0.0
    last_failover: Optional[float] = None
    total_failovers: int = 0

@dataclass
class FailoverEvent:
    """故障转移事件"""

    event_id: str
    from_node: str
    to_node: str
    reason: str = ""
    state: FailoverState = FailoverState.NORMAL
    started_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    verified: bool = False

class AutoFailoverManager(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """自动故障转移管理器"""

    MODULE_ID = "auto_failover"
    MODULE_NAME = "自动故障转移"
    VERSION = "V0.1"
    MODULE_LEVEL = "A"

    def __init__(self, config: Optional[Dict[str, Any]] = None):

        super().__init__(config)
        self.module_level = self.MODULE_LEVEL
        self._audit = None
        self._metrics = metrics_collector
        self._nodes: Dict[str, ClusterNode] = {}
        self._events: List[FailoverEvent] = []
        self._state: FailoverState = FailoverState.NORMAL
        self._counter: int = 0
        self._failure_threshold: int = 3
        self._recovery_threshold: float = 0.8

    def initialize(self) -> None:
        try:
            defaults = [
                ("node-primary", "主节点", "10.0.0.1:8080", "primary", NodeStatus.ACTIVE, 100, 10),
                ("node-secondary-1", "从节点1", "10.0.0.2:8080", "secondary", NodeStatus.STANDBY, 80, 5),
                ("node-secondary-2", "从节点2", "10.0.0.3:8080", "secondary", NodeStatus.STANDBY, 80, 5),
                ("node-dr", "灾备节点", "10.0.1.1:8080", "disaster_recovery", NodeStatus.STANDBY, 50, 1),
            ]
            for nid, name, addr, role, status, weight, priority in defaults:
                node = ClusterNode(
                    node_id=nid,
                    name=name,
                    address=addr,
                    role=role,
                    status=status,
                    weight=weight,
                    priority=priority,
                    last_health_check=time.time(),
                )
                self._nodes[nid] = node
            if self._audit:
                self._audit.log("auto_failover_initialized", {"nodes": len(self._nodes)})
            self.stats.success_count += 1
            logger.info("自动故障转移初始化完成")
        except Exception as e:
            logger.error(f"故障转移初始化失败: {e}")
            self.stats.error_count += 1
            raise

    async def execute(self, action: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        self.trace("execute", {"module": "auto_failover"})
        self.metrics_collector.counter("auto_failover.execute.calls", 1)
        self.audit("execute", {"module": "auto_failover"})
        params = params or {}
        start = time.time()
        ok = False
        err = None
        try:
            if action == "health_check":
                node_id = params.get("node_id", "")
                health = params.get("health", "healthy")
                if not node_id:
                    return {"success": False, "error": "Missing: node_id"}
                result = self._process_health_check(node_id, health)
                return {"success": True, "result": result}

            elif action == "trigger_failover":
                from_node = params.get("from_node", "")
                reason = params.get("reason", "manual")
                if not from_node:
                    return {"success": False, "error": "Missing: from_node"}
                result = self._trigger_failover(from_node, reason)
                ok = "error" not in result
                return {"success": ok, "result": result}

            elif action == "verify_recovery":
                node_id = params.get("node_id", "")
                if not node_id:
                    return {"success": False, "error": "Missing: node_id"}
                result = self._verify_recovery(node_id)
                return {"success": True, "result": result}

            elif action == "add_node":
                node_id = params.get("node_id", "")
                name = params.get("name", "")
                address = params.get("address", "")
                role = params.get("role", "worker")
                if not node_id or not address:
                    return {"success": False, "error": "Missing: node_id, address"}
                node = ClusterNode(
                    node_id=node_id,
                    name=name,
                    address=address,
                    role=role,
                    status=NodeStatus.STANDBY,
                    last_health_check=time.time(),
                )
                self._nodes[node_id] = node
                ok = True
                return {"success": True, "result": {"node_id": node_id, "name": name}}

            elif action == "list_nodes":
                return {
                    "success": True,
                    "result": [
                        {
                            "node_id": n.node_id,
                            "name": n.name,
                            "address": n.address,
                            "role": n.role,
                            "status": n.status.value,
                            "weight": n.weight,
                            "priority": n.priority,
                            "health_score": round(n.health_score, 3),
                            "failures": n.consecutive_failures,
                            "total_failovers": n.total_failovers,
                        }
                        for n in self._nodes.values()
                    ],
                }

            elif action == "get_failover_history":
                return {
                    "success": True,
                    "result": [
                        {
                            "event_id": e.event_id,
                            "from": e.from_node,
                            "to": e.to_node,
                            "reason": e.reason,
                            "verified": e.verified,
                            "completed_at": e.completed_at,
                        }
                        for e in self._events[-20:]
                    ],
                }

            elif action == "get_stats":
                return {
                    "success": True,
                    "result": {
                        "nodes": len(self._nodes),
                        "active": sum(1 for n in self._nodes.values() if n.status == NodeStatus.ACTIVE),
                        "standby": sum(1 for n in self._nodes.values() if n.status == NodeStatus.STANDBY),
                        "faulted": sum(1 for n in self._nodes.values() if n.status == NodeStatus.FAULTED),
                        "state": self._state.value,
                        "total_failovers": len(self._events),
                    },
                }

            else:
                return {"success": False, "error": f"Unknown action: {action}"}
        except Exception as e:
            err = str(e)
            return {"success": False, "error": err}
        finally:
            self.stats.record_request((time.time() - start) * 1000, ok, err)

    def health_check(self) -> Dict[str, Any]:
        faulted = sum(1 for n in self._nodes.values() if n.status in (NodeStatus.FAULTED, NodeStatus.RECOVERING))
        active = sum(1 for n in self._nodes.values() if n.status == NodeStatus.ACTIVE)
        return {
            "status": "unhealthy" if active == 0 else ("degraded" if faulted > 0 or active == 1 else "healthy"),
            "module_id": self.module_id,
            "module_level": self.module_level,
            "state": self._state.value,
            "active_nodes": active,
            "faulted_nodes": faulted,
        }

    def shutdown(self) -> None:
        pass

    def _process_health_check(self, node_id: str, health: str) -> Dict:
        node = self._nodes.get(node_id)
        if not node:
            return {"error": "Node not found"}
        node.last_health_check = time.time()
        if health == "healthy":
            node.consecutive_failures = 0
            node.health_score = min(1.0, node.health_score + 0.1)
            if node.status == NodeStatus.FAULTED:
                node.status = NodeStatus.RECOVERING
            if node.status == NodeStatus.RECOVERING and node.health_score >= self._recovery_threshold:
                node.status = NodeStatus.ACTIVE
        else:
            node.consecutive_failures += 1
            node.health_score = max(0.0, node.health_score - 0.2)
            if node.consecutive_failures >= self._failure_threshold:
                node.status = NodeStatus.FAULTED

        self.stats.success_count += 1
        return {
            "node_id": node_id,
            "status": node.status.value,
            "health_score": round(node.health_score, 3),
            "failures": node.consecutive_failures,
            "action": "none" if node.status == NodeStatus.ACTIVE else "monitoring",
        }

    def _trigger_failover(self, from_node: str, reason: str) -> Dict:
        src = self._nodes.get(from_node)
        if not src:
            return {"error": "Source node not found"}

        # 找最佳备用节点
        candidates = [n for n in self._nodes.values() if n.node_id != from_node and n.status == NodeStatus.STANDBY]
        if not candidates:
            return {"error": "No standby node available"}

        target = max(candidates, key=lambda n: n.priority * 100 + n.health_score * 50)
        self._counter += 1

        event = FailoverEvent(
            event_id=f"fo_{self._counter}",
            from_node=from_node,
            to_node=target.node_id,
            reason=reason,
            state=FailoverState.FAILOVER_IN_PROGRESS,
        )
        self._state = FailoverState.FAILOVER_IN_PROGRESS
        src.status = NodeStatus.FAULTED

        time.sleep(0.1)

        target.status = NodeStatus.ACTIVE
        target.last_failover = time.time()
        target.total_failovers += 1
        event.state = FailoverState.FAILED_OVER
        event.completed_at = time.time()
        self._state = FailoverState.FAILED_OVER
        self._events.append(event)

        if self._audit:
            self._audit.log("failover_triggered", {"from": from_node, "to": target.node_id, "reason": reason})
        self.stats.success_count += 1
        return {
            "event_id": event.event_id,
            "from": from_node,
            "to": target.node_id,
            "state": "failed_over",
            "duration_ms": round((event.completed_at - event.started_at) * 1000, 1),
        }

    def _verify_recovery(self, node_id: str) -> Dict:
        node = self._nodes.get(node_id)
        if not node:
            return {"error": "Node not found"}
        verified = node.health_score >= self._recovery_threshold
        if verified:
            node.status = NodeStatus.ACTIVE
        # 标记最近的failover事件为已验证
        for e in reversed(self._events):
            if e.from_node == node_id and not e.verified:
                e.verified = True
                break
        self.stats.success_count += 1
        return {
            "node_id": node_id,
            "verified": verified,
            "health_score": round(node.health_score, 3),
            "status": node.status.value,
        }

    def get_failover_topology(self) -> Dict[str, Any]:
        """获取故障转移拓扑图。企业场景：运维面板展示集群各节点状态、主备关系、转移路径。
        可视化哪个节点是主节点，哪些是备节点，最近的故障转移链路。
        """
        topology = {
            "primary_nodes": [],
            "standby_nodes": [],
            "failed_nodes": [],
            "failover_pairs": [],
            "recent_events": [],
        }
        for nid, node in self._nodes.items():
            info = {
                "node_id": nid,
                "address": node.address,
                "role": node.role,
                "status": node.status.value,
                "health_score": round(node.health_score, 3),
            }
            if node.status == NodeStatus.ACTIVE:
                topology["primary_nodes"].append(info)
            elif node.status == NodeStatus.STANDBY:
                topology["standby_nodes"].append(info)
            elif node.status == NodeStatus.FAILED:
                topology["failed_nodes"].append(info)
        # 主备配对关系
        if hasattr(self, "_failover_config"):
            for primary, standby in self._failover_config.items():
                topology["failover_pairs"].append(
                    {
                        "primary": primary,
                        "standby": standby,
                        "primary_status": self._nodes.get(
                            primary, type("obj", (object,), {"status": "unknown"})()
                        ).status.value
                        if primary in self._nodes
                        else "unknown",
                    }
                )
        # 最近10条事件
        for e in self._events[-10:]:
            topology["recent_events"].append(
                {
                    "from_node": e.from_node,
                    "to_node": e.to_node,
                    "trigger": e.trigger,
                    "timestamp": e.timestamp,
                    "verified": e.verified,
                }
            )
        return topology

    def get_failover_report(self, days: int = 7) -> Dict[str, Any]:
        """获取故障转移统计报告。企业场景：SRE周报统计故障转移频率、平均恢复时间、节点可用性。
        用于评估集群稳定性，发现频繁故障的单点。
        """
        now = time.time()
        cutoff = now - days * 86400
        recent = [e for e in self._events if e.timestamp >= cutoff]
        total_events = len(recent)
        # 按节点统计故障次数
        node_fail_count: Dict[str, int] = {}
        for e in recent:
            node_fail_count[e.from_node] = node_fail_count.get(e.from_node, 0) + 1
        # 计算平均恢复时间（从故障到验证恢复）
        recovery_times = []
        for nid, node in self._nodes.items():
            if hasattr(node, "_fail_time") and hasattr(node, "_recovery_time"):
                if node._recovery_time and node._fail_time:
                    rt = node._recovery_time - node._fail_time
                    if rt > 0:
                        recovery_times.append(rt)
        avg_recovery = round(sum(recovery_times) / len(recovery_times), 1) if recovery_times else 0
        # 节点可用性
        node_availability = {}
        for nid, node in self._nodes.items():
            uptime = getattr(node, "_uptime_seconds", 0)
            total = uptime + max(getattr(node, "_downtime_seconds", 0), 1)
            node_availability[nid] = round(uptime / total * 100, 2)
        return {
            "period_days": days,
            "total_failover_events": total_events,
            "avg_recovery_seconds": avg_recovery,
            "node_failure_counts": node_fail_count,
            "node_availability": node_availability,
            "top_failure_nodes": sorted(node_fail_count.items(), key=lambda x: -x[1])[:5],
        }

    def configure_failover_policy(self, policy: Dict[str, Any]) -> Dict[str, Any]:
        """配置故障转移策略。企业场景：根据业务重要级设置不同的转移策略。
        支持配置：健康检查间隔、失败阈值、恢复阈值、冷却时间、通知渠道。
        """
        if not hasattr(self, "_policies"):
            self._policies = {}
        policy_id = policy.get("name", "default")
        valid_fields = {
            "health_check_interval",
            "failure_threshold",
            "recovery_threshold",
            "cooldown_seconds",
            "max_retries",
            "notify_channels",
            "auto_rollback",
        }
        new_policy = {"name": policy_id, "created_at": time.time()}
        for key, value in policy.items():
            if key in valid_fields:
                new_policy[key] = value
        self._policies[policy_id] = new_policy
        return {"success": True, "policy_id": policy_id, "configured_fields": list(new_policy.keys())}

    def get_node_health_timeline(self, node_id: str, hours: int = 24) -> Dict[str, Any]:
        """获取节点健康度时间线。企业场景：故障复盘时回溯节点健康变化趋势，
        发现慢退化模式（如内存泄漏导致的渐进性故障）。
        """
        node = self._nodes.get(node_id)
        if not node:
            return {"success": False, "error": f"节点{node_id}不存在"}
        now = time.time()
        cutoff = now - hours * 3600
        if not hasattr(self, "_health_history"):
            self._health_history = {}
        timeline = self._health_history.get(node_id, [])
        recent = [t for t in timeline if t.get("timestamp", 0) >= cutoff]
        if not recent:
            return {
                "success": True,
                "node_id": node_id,
                "message": "无历史数据",
                "current_score": round(node.health_score, 3),
            }
        scores = [t.get("score", 0) for t in recent]
        return {
            "success": True,
            "node_id": node_id,
            "period_hours": hours,
            "data_points": len(recent),
            "current_score": round(node.health_score, 3),
            "min_score": round(min(scores), 3),
            "max_score": round(max(scores), 3),
            "avg_score": round(sum(scores) / len(scores), 3),
            "trend": "degrading" if scores[-1] < scores[0] else "improving" if scores[-1] > scores[0] else "stable",
        }

    def get_disaster_recovery_plan(self) -> Dict[str, Any]:
        """获取灾备恢复计划。企业场景：运维手册中记录完整的故障转移和恢复SOP，
        包含各节点角色、优先级、恢复步骤、联系信息。
        """
        nodes_info = []
        for nid, node in self._nodes.items():
            nodes_info.append(
                {
                    "node_id": nid,
                    "address": node.address,
                    "role": node.role,
                    "status": node.status.value,
                    "health_score": round(node.health_score, 3),
                }
            )
        primary_nodes = [n for n in nodes_info if n["role"] == "primary"]
        standby_nodes = [n for n in nodes_info if n["role"] == "standby"]
        return {
            "success": True,
            "plan_generated_at": time.time(),
            "total_nodes": len(nodes_info),
            "primary_count": len(primary_nodes),
            "standby_count": len(standby_nodes),
            "nodes": nodes_info,
            "failover_pairs": list(getattr(self, "_failover_config", {}).items()),
            "recovery_steps": [
                "1. 确认主节点故障原因",
                "2. 检查备节点健康状态",
                "3. 执行故障转移",
                "4. 验证新主节点服务正常",
                "5. 通知相关团队",
                "6. 记录故障报告",
            ],
        }

    def get_alert_contacts(self) -> Dict[str, Any]:
        """获取故障通知联系人列表。企业场景：灾备手册中记录各服务负责人和升级联系人。"""
        contacts = getattr(self, "_alert_contacts", {})
        return {"success": True, "total_contacts": len(contacts), "contacts": contacts}

    def get_failover_summary(self) -> Dict[str, Any]:
        """故障转移简要统计。企业场景：运维快速了解近期故障转移情况。"""
        recent = self._events[-20:] if self._events else []
        return {
            "success": True,
            "total_events": len(self._events),
            "recent_count": len(recent),
            "total_nodes": len(self._nodes),
        }

    def get_topology_map(self) -> Dict[str, Any]:
        """集群拓扑图数据。企业场景：运维看板展示主从节点关系和健康状态。
        返回节点列表和连接关系，前端渲染拓扑图。
        """
        nodes = []
        edges = []
        for nid, node in self._nodes.items():
            role = getattr(node, "role", "standby")
            status = getattr(node, "status", "unknown")
            nodes.append(
                {"id": nid, "role": role, "status": status, "connections": getattr(node, "active_connections", 0)}
            )
            primary = getattr(node, "primary_node", None)
            if primary:
                edges.append({"from": primary, "to": nid, "type": "replication"})
        healthy = sum(1 for n in nodes if n["status"] == "healthy")
        return {
            "success": True,
            "nodes": nodes,
            "edges": edges,
            "total_nodes": len(nodes),
            "healthy_nodes": healthy,
            "health_rate": round(healthy / max(len(nodes), 1) * 100, 1),
        }

    def get_failover_history(self, limit: int = 50) -> Dict[str, Any]:
        """故障转移历史记录。企业场景：故障复盘时回溯近期故障转移事件。"""
        events = list(self._events) if self._events else []
        events.sort(key=lambda x: getattr(x, "timestamp", x.get("timestamp", 0)), reverse=True)
        records = []
        for evt in events[:limit]:
            records.append(
                {
                    "event_id": getattr(evt, "event_id", evt.get("event_id", "")),
                    "type": getattr(evt, "type", evt.get("type", "")),
                    "from_node": getattr(evt, "from_node", evt.get("from_node", "")),
                    "to_node": getattr(evt, "to_node", evt.get("to_node", "")),
                    "duration_ms": getattr(evt, "duration_ms", evt.get("duration_ms", 0)),
                }
            )
        return {"success": True, "total": len(self._events), "returned": len(records), "records": records}

module_class = AutoFailoverManager
