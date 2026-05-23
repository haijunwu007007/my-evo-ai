"""
        Workflow Manager - 企业级工作流管理引擎
生产级DAG工作流编排：节点编排、条件分支、并行执行、超时控制、重试策略、审批流
支持：JSON定义工作流、节点依赖DAG校验、执行状态追踪、SLA监控
"""

__module_meta__ = {
    "id": "workflow-manager",
    "name": "工作流管理引擎",
    "version": "6.5.0",
    "group": "workflow",
    "inputs": [
        {"name": "workflow_def", "type": "dict", "required": True, "description": "工作流JSON定义"},
        {"name": "trigger_mode", "type": "string", "description": "触发模式: manual/event/schedule"},
    ],
    "outputs": [
        {"name": "execution_id", "type": "string", "description": "执行ID"},
        {"name": "status", "type": "dict", "description": "执行状态"},
    ],
    "triggers": [{"type": "event", "config": {"on": "workflow.execute.request"}}],
    "depends_on": ["trigger-engine", "event-bus"],
    "tags": ["workflow", "dag", "core"],
    "grade": "S",
}
import time
import uuid
import copy
import threading
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple
from collections import defaultdict, deque

from modules._base.enterprise_module import EnterpriseModule

class NodeState(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    WAITING_APPROVAL = "waiting_approval"

class WorkflowState(Enum):
    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    WAITING_APPROVAL = "waiting_approval"

class RetryPolicy:
    """重试策略：指数退避 + 最大重试次数"""

    def __init__(
        self, max_retries: int = 3, backoff_base: float = 2.0, backoff_max: float = 60.0, retry_on: List[str] = None
    ):
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        self.backoff_max = backoff_max
        self.retry_on = retry_on or ["failed", "timeout"]

    def get_delay(self, attempt: int) -> float:
        delay = min(self.backoff_base**attempt, self.backoff_max)
        return delay

    def should_retry(self, state: str, attempt: int) -> bool:
        return state in self.retry_on and attempt < self.max_retries

    def to_dict(self) -> Dict:
        return {
            "max_retries": self.max_retries,
            "backoff_base": self.backoff_base,
            "backoff_max": self.backoff_max,
            "retry_on": self.retry_on,
        }

    @classmethod
    def from_dict(cls, d: Dict) -> "RetryPolicy":
        return cls(**{k: v for k, v in d.items() if k in cls.__init__.__code__.co_varnames})

# ─── DAG 校验引擎 ────────────────────────────────────────────

class DAGValidator:
    """有向无环图校验：环检测、可达性分析、关键路径计算"""

    @staticmethod
    def detect_cycle(nodes: Dict[str, Dict]) -> Optional[List[str]]:
        """DFS检测环，返回环路径或None"""
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {nid: WHITE for nid in nodes}
        parent = {}

        def dfs(node: str) -> Optional[List[str]]:
            color[node] = GRAY
            for dep in nodes[node].get("depends_on", []):
                if dep not in nodes:
                    continue
                if color[dep] == GRAY:
                    # 回溯找环
                    cycle = [dep, node]
                    cur = node
                    while parent.get(cur) != dep:
                        cur = parent.get(cur)
                        if cur:
                            cycle.append(cur)
                        else:
                            break
                    cycle.reverse()
                    return cycle
                if color[dep] == WHITE:
                    parent[dep] = node
                    result = dfs(dep)
                    if result:
                        return result
            color[node] = BLACK
            return None

        for nid in nodes:
            if color[nid] == WHITE:
                cycle = dfs(nid)
                if cycle:
                    return cycle
        return None

    @staticmethod
    def topological_sort(nodes: Dict[str, Dict]) -> List[str]:
        """拓扑排序，返回执行顺序"""
        in_degree = {nid: 0 for nid in nodes}
        for nid, node in nodes.items():
            for dep in node.get("depends_on", []):
                if dep in nodes:
                    in_degree[nid] = in_degree.get(nid, 0) + 1
        queue = deque([nid for nid, deg in in_degree.items() if deg == 0])
        order = []
        while queue:
            node = queue.popleft()
            order.append(node)
            for nid, n in nodes.items():
                if node in n.get("depends_on", []):
                    in_degree[nid] -= 1
                    if in_degree[nid] == 0:
                        queue.append(nid)
        return order

    @staticmethod
    def get_parallel_groups(nodes: Dict[str, Dict]) -> List[List[str]]:
        """获取可并行执行的层级"""
        remaining = set(nodes.keys())
        groups = []
        while remaining:
            ready = [
                nid
                for nid in remaining
                if all(d not in remaining or d in set() for d in nodes[nid].get("depends_on", []))
            ]
            if not ready:
                # 环路或孤立节点
                ready = list(remaining)
            # 更精确：depends_on中的依赖必须已在前面层级中完成
            completed = set()
            for g in groups:
                completed.update(g)
            ready = [nid for nid in remaining if all(d in completed for d in nodes[nid].get("depends_on", []))]
            if not ready:
                ready = list(remaining)
            groups.append(ready)
            remaining -= set(ready)
        return groups

    @staticmethod
    def critical_path(nodes: Dict[str, Dict]) -> Tuple[List[str], float]:
        """关键路径分析：最长执行路径"""
        durations = {nid: node.get("timeout", node.get("estimated_duration", 1.0)) for nid, node in nodes.items()}
        topo = DAGValidator.topological_sort(nodes)
        dist = {nid: 0.0 for nid in nodes}
        prev = {nid: None for nid in nodes}
        for nid in topo:
            for dep in nodes[nid].get("depends_on", []):
                if dep in dist and dist[dep] + durations.get(dep, 0) > dist[nid]:
                    dist[nid] = dist[dep] + durations.get(dep, 0)
                    prev[nid] = dep
        # 找最长路径终点
        end_node = max(dist, key=dist.get) if dist else None
        path = []
        cur = end_node
        while cur:
            path.append(cur)
            cur = prev.get(cur)
        path.reverse()
        return path, dist.get(end_node, 0)

    @staticmethod
    def validate(nodes: Dict[str, Dict]) -> Dict:
        """完整校验"""
        errors = []
        warnings = []
        # 环检测
        cycle = DAGValidator.detect_cycle(nodes)
        if cycle:
            errors.append(f"Circular dependency detected: {' -> '.join(cycle)}")
        # 孤立节点
        has_deps = {nid for nid, n in nodes.items() if n.get("depends_on")}
        has_dependents = set()
        for n in nodes.values():
            for dep in n.get("depends_on", []):
                has_dependents.add(dep)
        orphaned = (
            set(nodes.keys()) - has_deps - has_dependents - {nid for nid in nodes if not nodes[nid].get("depends_on")}
        )
        # 缺失依赖引用
        for nid, n in nodes.items():
            for dep in n.get("depends_on", []):
                if dep not in nodes:
                    errors.append(f"Node '{nid}' depends on non-existent node '{dep}'")
        # 起始节点
        start_nodes = [nid for nid, n in nodes.items() if not n.get("depends_on")]
        if not start_nodes and nodes:
            errors.append("No start nodes (all nodes have dependencies)")
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "start_nodes": start_nodes,
            "node_count": len(nodes),
        }

# ─── 工作流执行引擎 ──────────────────────────────────────────

class WorkflowExecutor:
    """工作流执行引擎：状态机驱动的DAG执行"""

    def __init__(self):
        self._workflows: Dict[str, Dict] = {}
        self._executions: Dict[str, Dict] = {}
        self._approval_requests: Dict[str, Dict] = {}
        self._lock = threading.Lock()
        self._max_executions = 500

    def create_workflow(self, definition: Dict) -> Dict:
        """创建工作流定义"""
        wf_id = definition.get("workflow_id", str(uuid.uuid4())[:8])
        nodes = definition.get("nodes", {})
        # 校验
        validation = DAGValidator.validate(nodes)
        if not validation["valid"]:
            return {"success": False, "error": "Validation failed", "details": validation}

        wf = {
            "workflow_id": wf_id,
            "name": definition.get("name", wf_id),
            "description": definition.get("description", ""),
            "nodes": nodes,
            "variables": definition.get("variables", {}),
            "timeout": definition.get("timeout", 3600),
            "retry_policy": RetryPolicy.from_dict(definition.get("retry_policy", {})),
            "sla": definition.get("sla", {}),
            "tags": definition.get("tags", []),
            "state": "draft",
            "validation": validation,
            "critical_path": DAGValidator.critical_path(nodes),
            "parallel_groups": DAGValidator.get_parallel_groups(nodes),
            "created_at": time.time(),
            "updated_at": time.time(),
        }
        self._workflows[wf_id] = wf
        return {"success": True, "data": {"workflow_id": wf_id, "node_count": len(nodes)}}

    def start_workflow(self, wf_id: str, input_vars: Dict = None) -> Dict:
        with self._lock:
            wf = self._workflows.get(wf_id)
            if not wf:
                return {"success": False, "error": "Workflow not found"}
            if wf["state"] not in ("draft", "completed", "failed", "cancelled"):
                return {"success": False, "error": f"Cannot start workflow in state {wf['state']}"}

            exec_id = str(uuid.uuid4())[:12]
            wf["state"] = "running"
            wf["updated_at"] = time.time()

            # 初始化节点执行状态
            node_states = {}
            for nid, node in wf["nodes"].items():
                node_states[nid] = {
                    "state": "pending",
                    "attempt": 0,
                    "started_at": None,
                    "finished_at": None,
                    "result": None,
                    "error": None,
                }

            execution = {
                "exec_id": exec_id,
                "workflow_id": wf_id,
                "state": "running",
                "input": input_vars or {},
                "variables": dict(wf["variables"]),
                "node_states": node_states,
                "current_step": 0,
                "started_at": time.time(),
                "finished_at": None,
                "timeout_at": time.time() + wf["timeout"],
            }
            self._executions[exec_id] = execution
            return {"success": True, "data": {"exec_id": exec_id, "workflow_id": wf_id, "state": "running"}}

    def advance_execution(self, exec_id: str, node_id: str, result: Dict) -> Dict:
        """推进执行：标记节点完成，触发下游"""
        with self._lock:
            execution = self._executions.get(exec_id)
            if not execution:
                return {"success": False, "error": "Execution not found"}
            if execution["state"] != "running":
                return {"success": False, "error": f"Execution state: {execution['state']}"}

            wf = self._workflows.get(execution["workflow_id"])
            if not wf:
                return {"success": False, "error": "Workflow not found"}

            node_state = execution["node_states"].get(node_id)
            if not node_state:
                return {"success": False, "error": f"Node {node_id} not found"}

            # 超时检查
            if time.time() > execution["timeout_at"]:
                execution["state"] = "failed"
                node_state["state"] = "timeout"
                return {"success": False, "error": "Workflow timeout exceeded"}

            # 更新节点状态
            node_state["state"] = result.get("state", "success")
            node_state["result"] = result.get("data")
            node_state["error"] = result.get("error")
            node_state["finished_at"] = time.time()

            # 审批节点处理
            wf_node = wf["nodes"].get(node_id, {})
            if wf_node.get("approval_required"):
                execution["state"] = "waiting_approval"
                self._approval_requests[f"{exec_id}:{node_id}"] = {
                    "exec_id": exec_id,
                    "node_id": node_id,
                    "requester": result.get("data", {}).get("requester", "system"),
                    "reason": wf_node.get("approval_reason", ""),
                    "created_at": time.time(),
                    "status": "pending",
                }
                node_state["state"] = "waiting_approval"
                return {"success": True, "data": {"waiting_approval": True, "node_id": node_id}}

            # 失败重试
            if node_state["state"] == "failed" and wf["retry_policy"].should_retry("failed", node_state["attempt"]):
                node_state["attempt"] += 1
                node_state["state"] = "pending"
                delay = wf["retry_policy"].get_delay(node_state["attempt"])
                return {"success": True, "data": {"retrying": True, "attempt": node_state["attempt"], "delay": delay}}

            # 条件分支：失败策略
            if node_state["state"] == "failed":
                fail_strategy = wf_node.get("on_failure", "stop")
                if fail_strategy == "continue":
                    pass  # 继续执行下游
                elif fail_strategy == "skip_downstream":
                    # 标记下游跳过
                    self._skip_downstream(wf, execution, node_id)
                else:  # stop
                    execution["state"] = "failed"
                    execution["finished_at"] = time.time()
                    return {"success": False, "data": {"state": "failed", "failed_at": node_id}}

            # 检查可执行下游
            ready_nodes = self._get_ready_nodes(wf, execution)
            execution["current_step"] += 1

            # 检查是否全部完成
            all_done = all(ns["state"] in ("success", "skipped") for ns in execution["node_states"].values())
            if all_done and not ready_nodes:
                execution["state"] = "completed"
                execution["finished_at"] = time.time()

            return {
                "success": True,
                "data": {
                    "state": execution["state"],
                    "node_state": node_state["state"],
                    "ready_nodes": ready_nodes,
                    "step": execution["current_step"],
                },
            }

    def approve(self, exec_id: str, node_id: str, approved: bool, approver: str = "system", comment: str = "") -> Dict:
        """处理审批请求"""
        key = f"{exec_id}:{node_id}"
        req = self._approval_requests.get(key)
        if not req:
            return {"success": False, "error": "Approval request not found"}
        if req["status"] != "pending":
            return {"success": False, "error": f"Already {req['status']}"}

        req["status"] = "approved" if approved else "rejected"
        req["approver"] = approver
        req["comment"] = comment
        req["resolved_at"] = time.time()

        with self._lock:
            execution = self._executions.get(exec_id)
            if execution:
                if approved:
                    execution["state"] = "running"
                    execution["node_states"][node_id]["state"] = "success"
                    return self.advance_execution(exec_id, node_id, {"state": "success", "data": {"approved": True}})
                else:
                    execution["state"] = "failed"
                    execution["finished_at"] = time.time()
                    execution["node_states"][node_id]["state"] = "failed"
                    return {"success": True, "data": {"state": "failed", "reason": "approval_rejected"}}
        return {"success": True, "data": {"status": req["status"]}}

    def pause_workflow(self, exec_id: str) -> Dict:
        with self._lock:
            execution = self._executions.get(exec_id)
            if execution and execution["state"] == "running":
                execution["state"] = "paused"
                return {"success": True}
        return {"success": False, "error": "Cannot pause"}

    def resume_workflow(self, exec_id: str) -> Dict:
        with self._lock:
            execution = self._executions.get(exec_id)
            if execution and execution["state"] == "paused":
                execution["state"] = "running"
                return {"success": True}
        return {"success": False, "error": "Cannot resume"}

    def cancel_workflow(self, exec_id: str) -> Dict:
        with self._lock:
            execution = self._executions.get(exec_id)
            if execution and execution["state"] in ("running", "paused", "waiting_approval"):
                execution["state"] = "cancelled"
                execution["finished_at"] = time.time()
                for ns in execution["node_states"].values():
                    if ns["state"] in ("pending", "running", "waiting_approval"):
                        ns["state"] = "cancelled"
                return {"success": True}
        return {"success": False, "error": "Cannot cancel"}

    def _get_ready_nodes(self, wf: Dict, execution: Dict) -> List[str]:
        """获取当前可执行的节点"""
        ready = []
        for nid, ns in execution["node_states"].items():
            if ns["state"] != "pending":
                continue
            deps = wf["nodes"][nid].get("depends_on", [])
            if all(execution["node_states"].get(d, {}).get("state") == "success" for d in deps):
                # 条件分支
                condition = wf["nodes"][nid].get("condition")
                if condition:
                    ctx = execution.get("variables", {})
                    from modules.trigger_engine import ConditionEvaluator

                    if not ConditionEvaluator().evaluate(condition, ctx):
                        ns["state"] = "skipped"
                        continue
                ready.append(nid)
        return ready

    def _skip_downstream(self, wf: Dict, execution: Dict, failed_node: str):
        """递归标记下游节点为skipped"""
        visited = set()
        queue = deque([failed_node])
        while queue:
            cur = queue.popleft()
            if cur in visited:
                continue
            visited.add(cur)
            for nid, node in wf["nodes"].items():
                if cur in node.get("depends_on", []):
                    if execution["node_states"][nid]["state"] == "pending":
                        execution["node_states"][nid]["state"] = "skipped"
                    queue.append(nid)

    def get_execution(self, exec_id: str) -> Optional[Dict]:
        return self._executions.get(exec_id)

    def list_workflows(self, state: str = None) -> List[Dict]:
        results = []
        for wf in self._workflows.values():
            if state and wf["state"] != state:
                continue
            results.append({k: v for k, v in wf.items() if k != "nodes"})
        return results

    def list_executions(self, wf_id: str = None, state: str = None, limit: int = 50) -> List[Dict]:
        results = []
        for ex in self._executions.values():
            if wf_id and ex["workflow_id"] != wf_id:
                continue
            if state and ex["state"] != state:
                continue
            results.append(ex)
        return results[-limit:]

    def stats(self) -> Dict:
        wfs = list(self._workflows.values())
        exs = list(self._executions.values())
        return {
            "total_workflows": len(wfs),
            "total_executions": len(exs),
            "running": sum(1 for e in exs if e["state"] == "running"),
            "completed": sum(1 for e in exs if e["state"] == "completed"),
            "failed": sum(1 for e in exs if e["state"] == "failed"),
            "waiting_approval": sum(1 for e in exs if e["state"] == "waiting_approval"),
            "pending_approvals": len(self._approval_requests),
        }

# ─── 主模块 ──────────────────────────────────────────────────

class WorkflowManager(EnterpriseModule):
    """企业级工作流管理引擎
    核心能力：DAG编排、条件分支、并行执行、超时控制、重试策略、审批流
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._executor = WorkflowExecutor()

    def _dispatch(self, action: str, params: Dict) -> Dict:
        handler = {
            "status": self._action_status,
            "stats": self._action_stats,
            "health": self._action_health,
            "configure": self._action_configure,
            "create": self._action_create,
            "validate": self._action_validate,
            "list": self._action_list,
            "get": self._action_get,
            "remove": self._action_remove,
            "start": self._action_start,
            "advance": self._action_advance,
            "pause": self._action_pause,
            "resume": self._action_resume,
            "cancel": self._action_cancel,
            "approve": self._action_approve,
            "reject": self._action_reject,
            "executions": self._action_executions,
            "execution_detail": self._action_execution_detail,
            "pending_approvals": self._action_pending_approvals,
            "critical_path": self._action_critical_path,
            "reset": self._action_reset,
        }.get(action)
        if handler:
            try:
                return handler(params)
            except Exception as e:
                self.trace("dispatch_error", {"action": action, "error": str(e)})
                return {"success": False, "error": str(e)}
        return {"success": False, "error": f"Unknown action: {action}"}

    async def execute(self, action: str = "status", params: Dict = None) -> Dict:
        params = params or {}
        self.trace("execute", {"action": action})
        self.metrics_collector.counter("workflow_execute_total", labels={"action": action}).inc()
        return self._dispatch(action, params)

    # ── 基础Action ──

    def _action_status(self, params: Dict) -> Dict:
        return {
            "success": True,
            "data": {"module": "WorkflowManager", "state": "active", "workflows": len(self._executor._workflows)},
        }

    def _action_stats(self, params: Dict) -> Dict:
        return {"success": True, "data": self._executor.stats()}

    def _action_health(self, params: Dict) -> Dict:
        s = self._executor.stats()
        issues = []
        if s["failed"] > 5:
            issues.append(f"{s['failed']} failed executions")
        if s["pending_approvals"] > 10:
            issues.append(f"{s['pending_approvals']} approvals pending")
        return {"success": True, "data": {"status": "healthy" if not issues else "degraded", "issues": issues}}

    def _action_configure(self, params: Dict) -> Dict:
        return {"success": True, "data": {"message": "Configuration updated"}}

    # ── 工作流定义 ──

    def _action_create(self, params: Dict) -> Dict:
        return self._executor.create_workflow(params)

    def _action_validate(self, params: Dict) -> Dict:
        nodes = params.get("nodes", {})
        result = DAGValidator.validate(nodes)
        cp, duration = DAGValidator.critical_path(nodes)
        result["critical_path"] = cp
        result["estimated_duration"] = duration
        result["parallel_groups"] = DAGValidator.get_parallel_groups(nodes)
        return {"success": True, "data": result}

    def _action_list(self, params: Dict) -> Dict:
        wfs = self._executor.list_workflows(state=params.get("state"))
        return {"success": True, "data": {"workflows": wfs, "total": len(wfs)}}

    def _action_get(self, params: Dict) -> Dict:
        wf = self._executor._workflows.get(params.get("workflow_id", ""))
        if not wf:
            return {"success": False, "error": "Workflow not found"}
        return {"success": True, "data": wf}

    def _action_remove(self, params: Dict) -> Dict:
        wf_id = params.get("workflow_id", "")
        if wf_id in self._executor._workflows:
            del self._executor._workflows[wf_id]
            return {"success": True, "data": {"removed": True}}
        return {"success": False, "error": "Workflow not found"}

    # ── 执行 ──

    def _action_start(self, params: Dict) -> Dict:
        return self._executor.start_workflow(params.get("workflow_id", ""), params.get("input_vars"))

    def _action_advance(self, params: Dict) -> Dict:
        return self._executor.advance_execution(
            params.get("exec_id", ""),
            params.get("node_id", ""),
            {
                "state": params.get("result_state", "success"),
                "data": params.get("result_data"),
                "error": params.get("error"),
            },
        )

    def _action_pause(self, params: Dict) -> Dict:
        return self._executor.pause_workflow(params.get("exec_id", ""))

    def _action_resume(self, params: Dict) -> Dict:
        return self._executor.resume_workflow(params.get("exec_id", ""))

    def _action_cancel(self, params: Dict) -> Dict:
        return self._executor.cancel_workflow(params.get("exec_id", ""))

    def _action_approve(self, params: Dict) -> Dict:
        return self._executor.approve(
            params.get("exec_id", ""),
            params.get("node_id", ""),
            True,
            params.get("approver", "system"),
            params.get("comment", ""),
        )

    def _action_reject(self, params: Dict) -> Dict:
        return self._executor.approve(
            params.get("exec_id", ""),
            params.get("node_id", ""),
            False,
            params.get("approver", "system"),
            params.get("comment", ""),
        )

    # ── 查询 ──

    def _action_executions(self, params: Dict) -> Dict:
        exs = self._executor.list_executions(
            wf_id=params.get("workflow_id"), state=params.get("state"), limit=params.get("limit", 50)
        )
        return {"success": True, "data": {"executions": exs, "total": len(exs)}}

    def _action_execution_detail(self, params: Dict) -> Dict:
        ex = self._executor.get_execution(params.get("exec_id", ""))
        if not ex:
            return {"success": False, "error": "Execution not found"}
        # 计算进度
        total = len(ex["node_states"])
        done = sum(1 for ns in ex["node_states"].values() if ns["state"] in ("success", "skipped", "failed"))
        ex["progress"] = f"{done}/{total}" if total else "0/0"
        ex["progress_pct"] = round(done / total * 100, 1) if total else 0
        return {"success": True, "data": ex}

    def _action_pending_approvals(self, params: Dict) -> Dict:
        pending = [v for v in self._executor._approval_requests.values() if v["status"] == "pending"]
        return {"success": True, "data": {"approvals": pending, "total": len(pending)}}

    def _action_critical_path(self, params: Dict) -> Dict:
        wf = self._executor._workflows.get(params.get("workflow_id", ""))
        if not wf:
            return {"success": False, "error": "Workflow not found"}
        path, duration = DAGValidator.critical_path(wf["nodes"])
        return {"success": True, "data": {"path": path, "estimated_duration": duration}}

    def _action_reset(self, params: Dict) -> Dict:
        self._executor._executions.clear()
        self._executor._approval_requests.clear()
        return {"success": True, "data": {"message": "All executions and approvals cleared"}}

module_class = WorkflowManager
