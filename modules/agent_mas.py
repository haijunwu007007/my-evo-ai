"""
AUTO-EVO-AI V0.1 — MAS多智能体系统
Grade: A (生产级) | Category: AI智能体
职责：多智能体注册与发现、Agent角色分配、协作编排、消息总线、共识协议
"""

__module_meta__ = {
    "id": "agent-mas",
    "name": "Agent Mas",
    "version": "V0.1",
    "group": "agent",
    "inputs": [
        {"name": "coalition_id", "type": "string", "required": True, "description": ""},
        {"name": "agent_ids", "type": "string", "required": True, "description": ""},
        {"name": "task_type", "type": "string", "required": True, "description": ""},
        {"name": "task_counts", "type": "string", "required": True, "description": ""},
        {"name": "coalition_id", "type": "string", "required": True, "description": ""},
        {"name": "success_rate", "type": "string", "required": True, "description": ""},
    ],
    "outputs": [
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
    ],
    "triggers": [{"type": "event", "config": {"on": "agent_mas.task.request"}}],
    "depends_on": [],
    "tags": ["manager", "multi-agent", "agent"],
    "grade": "A",
    "description": "AUTO-EVO-AI V0.1 — MAS多智能体系统 Grade: A (生产级) | Category: AI智能体",
}

import os
import asyncio
import time
import logging
from typing import Any, Dict, List, Optional, Set
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field

try:
    from modules._base.enterprise_module import EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin
    from modules._base.tracing import trace_operation
    from modules._base.metrics import metrics_collector
    from _base.audit import AuditLogger
except ImportError:
    import sys

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _base.enterprise_module import EnterpriseModule
    from modules._base.enterprise_module import CircuitBreakerMixin, RateLimiterMixin
    from _base.tracing import trace_operation
    from _base.metrics import metrics_collector
    from _base.audit import AuditLogger

logger = logging.getLogger("agent_mas")

class AgentRole(Enum):
    LEADER = "leader"
    WORKER = "worker"
    OBSERVER = "observer"
    COORDINATOR = "coordinator"
    EXECUTOR = "executor"

class AgentStatus(Enum):
    IDLE = "idle"
    BUSY = "busy"
    OFFLINE = "offline"
    ERROR = "error"

@dataclass
class AgentNode:
    """Agent节点"""

    agent_id: str
    name: str
    role: AgentRole
    capabilities: List[str] = field(default_factory=list)
    status: AgentStatus = AgentStatus.IDLE
    current_task: str = ""
    tasks_completed: int = 0
    registered_at: float = field(default_factory=time.time)
    last_heartbeat: float = field(default_factory=time.time)

@dataclass
class TaskAssignment:
    """任务分配"""

    assignment_id: str
    task_id: str
    agent_id: str
    status: str = "assigned"
    assigned_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None

class CoalitionOptimizer:
    """多Agent联盟优化器 - 动态分组、负载均衡、协作策略"""

    def __init__(self):
        self._coalitions: Dict[str, List[str]] = {}
        self._agent_capacities: Dict[str, float] = {}
        self._assignment_history: List[Dict] = []

    def form_coalition(self, coalition_id: str, agent_ids: List[str], task_type: str) -> Dict:
        """组建Agent联盟"""
        self._coalitions[coalition_id] = agent_ids
        for aid in agent_ids:
            self._agent_capacities.setdefault(aid, 1.0)
        entry = {"coalition_id": coalition_id, "agents": agent_ids, "task_type": task_type, "timestamp": time.time()}
        self._assignment_history.append(entry)
        return {"coalition_id": coalition_id, "size": len(agent_ids), "task_type": task_type}

    def balance_load(self, task_counts: Dict[str, int]) -> Dict:
        """负载均衡：建议任务重新分配"""
        agents = sorted(task_counts.items(), key=lambda x: x[1], reverse=True)
        if len(agents) < 2:
            return {"balanced": True, "suggestions": []}
        suggestions = []
        avg = sum(c for _, c in agents) / len(agents)
        for aid, count in agents:
            if count > avg * 1.5:
                suggestions.append({"from": aid, " redistribute": count - int(avg)})
        return {"balanced": len(suggestions) == 0, "avg_load": round(avg, 1), "suggestions": suggestions}

    def evaluate_coalition(self, coalition_id: str, success_rate: float) -> Dict:
        """评估联盟效能"""
        agents = self._coalitions.get(coalition_id, [])
        score = success_rate * min(len(agents) / 5.0, 1.0)
        return {
            "coalition_id": coalition_id,
            "agents": len(agents),
            "success_rate": success_rate,
            "score": round(score, 3),
        }

    def dissolve_coalition(self, coalition_id: str) -> Dict:
        """解散联盟"""
        agents = self._coalitions.pop(coalition_id, None)
        return {"dissolved": agents is not None, "released_agents": agents or []}

    def find_best_agent(self, task_type: str, agent_skills: Dict[str, List[str]]) -> str:
        """根据任务类型找最匹配的Agent"""
        best, best_score = None, 0
        for aid, skills in agent_skills.items():
            score = sum(1 for s in skills if s in task_type.lower())
            if score > best_score:
                best_score = score
                best = aid
        return best or ""

    def detect_conflict(self, agent_id: str, active_coalitions: List[str]) -> Dict:
        """检测Agent是否在多个冲突联盟中"""
        memberships = [cid for cid in active_coalitions if agent_id in self._coalitions.get(cid, [])]
        return {
            "agent": agent_id,
            "memberships": len(memberships),
            "conflict": len(memberships) > 1,
            "coalitions": memberships,
        }

    def get_summary(self) -> Dict:
        """获取优化器摘要"""
        total_agents = set()
        for agents in self._coalitions.values():
            total_agents.update(agents)
        return {
            "active_coalitions": len(self._coalitions),
            "total_agents": len(total_agents),
            "assignments_made": len(self._assignment_history),
            "avg_coalition_size": round(
                sum(len(a) for a in self._coalitions.values()) / max(len(self._coalitions), 1), 1
            ),
        }

class AgentMASManager(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """多智能体系统管理器"""

    MODULE_ID = "agent_mas"
    MODULE_NAME = "MAS多智能体系统"
    VERSION = "V0.1"
    MODULE_LEVEL = "A"

    def __init__(self, config: Optional[Dict[str, Any]] = None):

        super().__init__(config)
        self.module_level = self.MODULE_LEVEL
        self._audit = None
        self._metrics = metrics_collector
        self._agents: Dict[str, AgentNode] = {}
        self._assignments: Dict[str, TaskAssignment] = {}
        self._task_queue: List[Dict[str, Any]] = []
        self._agent_counter: int = 0
        self._assign_counter: int = 0

    def initialize(self) -> None:
        try:
            pass
            # super().initialize() removed for sync compatibility
            if self._audit:
                self._audit.log("mas_initialized", {})
            self.stats.success_count += 1
            logger.info("MAS多智能体系统初始化完成")
        except Exception as e:
            logger.error(f"MAS初始化失败: {e}")
            self.stats.error_count += 1
            raise

    async def execute(self, action: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        _ = self.trace("execute")
        metrics_collector.counter("agent_mas_ops_total", labels={"action": action})
        self.audit("execute", f"action={action}")
        params = params or {}
        start = time.time()
        ok = False
        err = None
        try:
            if action == "register_agent":
                name = params.get("name", "")
                role = params.get("role", "worker")
                capabilities = params.get("capabilities", [])
                if not name:
                    return {"success": False, "error": "Missing: name"}
                agent = self._register_agent(name, role, capabilities)
                ok = True
                return {
                    "success": True,
                    "result": {"agent_id": agent.agent_id, "name": agent.name, "role": agent.role.value},
                }

            elif action == "unregister_agent":
                agent_id = params.get("agent_id", "")
                if not agent_id:
                    return {"success": False, "error": "Missing: agent_id"}
                result = self._unregister_agent(agent_id)
                ok = "error" not in result
                return {"success": ok, "result": result}

            elif action == "heartbeat":
                agent_id = params.get("agent_id", "")
                status = params.get("status", "idle")
                if not agent_id:
                    return {"success": False, "error": "Missing: agent_id"}
                result = self._heartbeat(agent_id, status)
                ok = "error" not in result
                return {"success": ok, "result": result}

            elif action == "submit_task":
                task = params.get("task", {})
                required_capabilities = params.get("required_capabilities", [])
                if not task:
                    return {"success": False, "error": "Missing: task"}
                result = self._submit_task(task, required_capabilities)
                ok = "error" not in result
                return {"success": ok, "result": result}

            elif action == "complete_assignment":
                assignment_id = params.get("assignment_id", "")
                result_data = params.get("result", {})
                if not assignment_id:
                    return {"success": False, "error": "Missing: assignment_id"}
                result = self._complete_assignment(assignment_id, result_data)
                ok = "error" not in result
                return {"success": ok, "result": result}

            elif action == "list_agents":
                role = params.get("role", "")
                agents = self._agents.values()
                if role:
                    agents = [a for a in agents if a.role.value == role]
                return {
                    "success": True,
                    "result": [
                        {
                            "agent_id": a.agent_id,
                            "name": a.name,
                            "role": a.role.value,
                            "status": a.status.value,
                            "capabilities": a.capabilities,
                            "tasks_completed": a.tasks_completed,
                        }
                        for a in agents
                    ],
                }

            elif action == "get_stats":
                role_counts = {}
                status_counts = {}
                for a in self._agents.values():
                    role_counts[a.role.value] = role_counts.get(a.role.value, 0) + 1
                    status_counts[a.status.value] = status_counts.get(a.status.value, 0) + 1
                return {
                    "success": True,
                    "result": {
                        "total_agents": len(self._agents),
                        "pending_tasks": len(self._task_queue),
                        "active_assignments": len(self._assignments),
                        "by_role": role_counts,
                        "by_status": status_counts,
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
        online = sum(1 for a in self._agents.values() if a.status != AgentStatus.OFFLINE)
        idle = sum(1 for a in self._agents.values() if a.status == AgentStatus.IDLE)
        return {
            "status": "healthy" if (online > 0 or len(self._agents) == 0) else "degraded",
            "module_id": self.module_id,
            "module_level": self.module_level,
            "agents": {"total": len(self._agents), "online": online, "idle": idle},
            "pending_tasks": len(self._task_queue),
            "active_assignments": len(self._assignments),
        }

    def shutdown(self) -> None:
        self._agents.clear()
        self._assignments.clear()
        self._task_queue.clear()
        # super().shutdown() removed for sync compatibility

    def _register_agent(self, name: str, role: str, capabilities: List[str]) -> AgentNode:
        self._agent_counter += 1
        try:
            r = AgentRole(role)
        except ValueError:
            r = AgentRole.WORKER
        agent = AgentNode(agent_id=f"agent_{self._agent_counter}", name=name, role=r, capabilities=capabilities)
        self._agents[agent.agent_id] = agent
        if self._audit:
            self._audit.log("agent_registered", {"agent_id": agent.agent_id, "name": name, "role": r.value})
        self.stats.success_count += 1
        return agent

    def _unregister_agent(self, agent_id: str) -> Dict:
        agent = self._agents.get(agent_id)
        if not agent:
            return {"error": "Agent not found"}
        agent.status = AgentStatus.OFFLINE
        if self._audit:
            self._audit.log("agent_unregistered", {"agent_id": agent_id})
        self.stats.success_count += 1
        return {"agent_id": agent_id, "status": "offline"}

    def _heartbeat(self, agent_id: str, status: str) -> Dict:
        agent = self._agents.get(agent_id)
        if not agent:
            return {"error": "Agent not found"}
        try:
            s = AgentStatus(status)
        except ValueError:
            s = AgentStatus.IDLE
        agent.status = s
        agent.last_heartbeat = time.time()
        return {"agent_id": agent_id, "status": s.value}

    def _submit_task(self, task: Dict, required_caps: List[str]) -> Dict:
        """提交任务，自动分配给空闲agent"""
        # 找匹配的空闲agent
        best_agent = None
        best_score = -1
        for agent in self._agents.values():
            if agent.status != AgentStatus.IDLE:
                continue
            if required_caps:
                matched = sum(1 for c in required_caps if c in agent.capabilities)
                score = matched / len(required_caps)
            else:
                score = 0.5
            if score > best_score:
                best_score = score
                best_agent = agent

        if best_agent is None:
            self._task_queue.append({"task": task, "required_capabilities": required_caps, "submitted_at": time.time()})
            return {
                "queued": True,
                "queue_position": len(self._task_queue),
                "message": "No available agent, task queued",
            }

        self._assign_counter += 1
        assignment = TaskAssignment(
            assignment_id=f"assign_{self._assign_counter}",
            task_id=task.get("task_id", f"task_{self._assign_counter}"),
            agent_id=best_agent.agent_id,
        )
        best_agent.status = AgentStatus.BUSY
        best_agent.current_task = assignment.task_id
        self._assignments[assignment.assignment_id] = assignment
        if self._audit:
            self._audit.log(
                "task_assigned",
                {
                    "assignment_id": assignment.assignment_id,
                    "agent_id": best_agent.agent_id,
                    "task_id": assignment.task_id,
                },
            )
        self.stats.success_count += 1
        return {
            "assigned": True,
            "assignment_id": assignment.assignment_id,
            "agent_id": best_agent.agent_id,
            "agent_name": best_agent.name,
        }

    def _complete_assignment(self, assignment_id: str, result_data: Dict) -> Dict:
        assignment = self._assignments.get(assignment_id)
        if not assignment:
            return {"error": "Assignment not found"}
        assignment.status = "completed"
        assignment.completed_at = time.time()
        agent = self._agents.get(assignment.agent_id)
        if agent:
            agent.status = AgentStatus.IDLE
            agent.current_task = ""
            agent.tasks_completed += 1
        # 处理排队的任务
        if self._task_queue and agent and agent.status == AgentStatus.IDLE:
            queued = self._task_queue.pop(0)
            self._submit_task(queued["task"], queued.get("required_capabilities", []))
        if self._audit:
            self._audit.log("assignment_completed", {"assignment_id": assignment_id})
        self.stats.success_count += 1
        return {
            "assignment_id": assignment_id,
            "status": "completed",
            "agent_tasks": agent.tasks_completed if agent else 0,
        }

    def _cancel_assignment(self, assignment_id: str, reason: str) -> Dict:
        """取消任务分配"""
        assignment = self._assignments.get(assignment_id)
        if not assignment or assignment.status != "pending":
            return {"error": "not_found_or_not_cancelable"}
        assignment.status = "cancelled"
        agent = self._agents.get(assignment.agent_id)
        if agent:
            agent.status = AgentStatus.IDLE
            agent.current_task = ""
        if self._audit:
            self._audit.log("assignment_cancelled", {"assignment_id": assignment_id, "reason": reason})
        return {"cancelled": True, "assignment_id": assignment_id}

    def _get_agent_utilization(self) -> Dict:
        """获取所有Agent利用率"""
        utils = []
        for agent in self._agents.values():
            total_time = max(agent.tasks_completed + agent.failed_tasks, 1)
            utilization = round(agent.tasks_completed / total_time * 100, 1)
            utils.append(
                {
                    "agent_id": agent.agent_id,
                    "name": agent.name,
                    "role": agent.role,
                    "tasks_done": agent.tasks_completed,
                    "tasks_failed": agent.failed_tasks,
                    "utilization": utilization,
                    "status": agent.status.value,
                }
            )
        return {"agents": utils, "avg_utilization": round(sum(a["utilization"] for a in utils) / max(len(utils), 1), 1)}

    def _reassign_task(self, assignment_id: str, new_agent_id: str) -> Dict:
        """将任务重新分配给另一个Agent"""
        assignment = self._assignments.get(assignment_id)
        if not assignment:
            return {"error": "not_found"}
        old_agent = self._agents.get(assignment.agent_id)
        new_agent = self._agents.get(new_agent_id)
        if not new_agent:
            return {"error": "new_agent_not_found"}
        if old_agent:
            old_agent.status = AgentStatus.IDLE
            old_agent.current_task = ""
        assignment.agent_id = new_agent_id
        new_agent.status = AgentStatus.BUSY
        new_agent.current_task = assignment.task_type
        if self._audit:
            self._audit.log(
                "task_reassigned",
                {"assignment_id": assignment_id, "from": getattr(old_agent, "agent_id", ""), "to": new_agent_id},
            )
        return {"reassigned": True, "assignment_id": assignment_id, "new_agent": new_agent_id}

    def _get_queue_status(self) -> Dict:
        """获取任务队列状态"""
        return {
            "queue_length": len(self._task_queue),
            "pending_assignments": sum(1 for a in self._assignments.values() if a.status == "pending"),
            "total_agents": len(self._agents),
            "idle_agents": sum(1 for a in self._agents.values() if a.status == AgentStatus.IDLE),
        }

    def _get_capability_map(self) -> Dict:
        """获取系统能力分布图"""
        cap_map: Dict[str, List[str]] = {}
        for agent in self._agents.values():
            for cap in agent.capabilities:
                cap_map.setdefault(cap, []).append(agent.agent_id)
        return {
            "capabilities": len(cap_map),
            "top_capabilities": sorted(cap_map.items(), key=lambda x: len(x[1]), reverse=True)[:10],
            "coverage": {k: len(v) for k, v in cap_map.items()},
        }

    def _expel_agent(self, agent_id: str, reason: str) -> Dict:
        """驱逐不健康Agent"""
        agent = self._agents.pop(agent_id, None)
        if not agent:
            return {"error": "agent_not_found"}
        # 释放该Agent的所有任务
        released = []
        for aid, a in self._assignments.items():
            if a.agent_id == agent_id and a.status == "pending":
                a.status = "failed"
                released.append(aid)
        if self._audit:
            self._audit.log("agent_expelled", {"agent_id": agent_id, "reason": reason, "released_tasks": len(released)})
        return {"expelled": True, "agent_id": agent_id, "released_tasks": released}

    def _batch_register(self, agents: List[Dict]) -> Dict:
        """批量注册Agent"""
        registered, failed = [], []
        for a in agents:
            try:
                node = self._register_agent(a.get("name", ""), a.get("role", ""), a.get("capabilities", []))
                registered.append(node.agent_id)
            except Exception as e:
                failed.append({"name": a.get("name", ""), "error": str(e)[:100]})
        return {"registered": len(registered), "failed": len(failed), "agent_ids": registered}

    def analyze_team_synergy(self) -> Dict[str, Any]:
        """分析团队协同效能：Agent间协作频率、冲突检测、角色覆盖度"""
        agents = self._agents if hasattr(self, "_agents") else {}
        tasks = self._tasks if hasattr(self, "_tasks") else {}
        if not agents:
            return {"total_agents": 0}
        role_coverage: Dict[str, int] = {}
        for aid, agent in agents.items():
            role = agent.get("role", "worker") if isinstance(agent, dict) else "worker"
            role_coverage[role] = role_coverage.get(role, 0) + 1
        completed = sum(1 for t in tasks.values() if isinstance(t, dict) and t.get("status") == "completed")
        pending = sum(1 for t in tasks.values() if isinstance(t, dict) and t.get("status") == "pending")
        total = max(len(tasks), 1)
        return {
            "total_agents": len(agents),
            "role_distribution": role_coverage,
            "tasks_completed": completed,
            "tasks_pending": pending,
            "completion_rate": round(completed / total, 3),
        }

    def get_task_assignment_summary(self) -> Dict[str, Any]:
        """任务分配摘要：各Agent任务负载、超时统计、优先级分布"""
        tasks = self._tasks if hasattr(self, "_tasks") else {}
        agents = self._agents if hasattr(self, "_agents") else {}
        if not tasks:
            return {"total_tasks": 0}
        agent_load: Dict[str, int] = {}
        priority_dist: Dict[str, int] = {}
        overdue = 0
        now = time.time()
        for tid, task in tasks.items():
            if not isinstance(task, dict):
                continue
            assignee = task.get("assignee", "unassigned")
            agent_load[assignee] = agent_load.get(assignee, 0) + 1
            priority_dist[task.get("priority", "normal")] = priority_dist.get(task.get("priority", "normal"), 0) + 1
            deadline = task.get("deadline", 0)
            if deadline and deadline < now and task.get("status") != "completed":
                overdue += 1
        return {
            "total_tasks": len(tasks),
            "agent_workload": agent_load,
            "priority_distribution": priority_dist,
            "overdue_tasks": overdue,
            "total_agents": len(agents),
        }

module_class = AgentMASManager
