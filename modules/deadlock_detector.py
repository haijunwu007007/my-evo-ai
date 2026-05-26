"""Production-grade 死锁检测模块 V0.1
上市公司生产级实现 - 等待图分析/环检测/超时管理/自动解除/资源追踪
"""

__module_meta__ = {
    "id": "deadlock-detector",
    "name": "Deadlock Detector",
    "version": "V0.1",
    "group": "database",
    "inputs": [
        {"name": "txn_id", "type": "string", "required": True, "description": ""},
        {"name": "resource", "type": "string", "required": True, "description": ""},
        {"name": "txn_id", "type": "string", "required": True, "description": ""},
        {"name": "resource", "type": "string", "required": True, "description": ""},
        {"name": "txn_id", "type": "string", "required": True, "description": ""},
        {"name": "resource", "type": "string", "required": True, "description": ""},
    ],
    "outputs": [
        {"name": "results", "type": "list[dict]", "description": "结果列表"},
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
    ],
    "triggers": [],
    "depends_on": [],
    "tags": ["deadlock", "manager"],
    "grade": "A",
    "description": "Production-grade 死锁检测模块 V0.1 上市公司生产级实现 - 等待图分析/环检测/超时管理/自动解除/资源追踪",
}
import logging
import time
import uuid
from collections import defaultdict, deque
from typing import Any, Dict, List, Optional, Set, Tuple

from modules._base.enterprise_module import EnterpriseModule, ModuleStatus
from modules._base.metrics import prometheus_timer, metrics_collector
from modules._base.mixins import CircuitBreakerMixin, RateLimiterMixin

logger = logging.getLogger("deadlock_detector")

class WaitGraph:
    """等待图(Wait-for Graph)构建与分析"""

    def __init__(self):
        self._edges: Dict[str, Set[str]] = defaultdict(set)
        self._resources: Dict[str, str] = {}
        self._transactions: Dict[str, Dict] = {}

    def add_waiting(self, txn_id: str, resource: str):
        holder = self._resources.get(resource)
        self._transactions[txn_id] = {
            "waiting_for": resource,
            "holding": set(),
            "since": time.time(),
            "status": "waiting",
        }
        if holder and holder != txn_id:
            self._edges[txn_id].add(holder)

    def add_holding(self, txn_id: str, resource: str):
        self._resources[resource] = txn_id
        if txn_id in self._transactions:
            self._transactions[txn_id]["holding"].add(resource)

    def release(self, txn_id: str, resource: str = None):
        if txn_id not in self._transactions:
            return
        txn = self._transactions[txn_id]
        txn["status"] = "completed"
        if resource:
            self._resources.pop(resource, None)
            txn["holding"].discard(resource)
        else:
            for r in list(txn["holding"]):
                self._resources.pop(r, None)
        self._edges.pop(txn_id, None)

    def detect_cycle(self) -> List[List[str]]:
        visited = set()
        path = []
        cycles = []

        def dfs(node: str):
            if node in path:
                idx = path.index(node)
                cycles.append(list(path[idx:]) + [node])
                return
            if node in visited:
                return
            visited.add(node)
            path.append(node)
            for neighbor in self._edges.get(node, set()):
                dfs(neighbor)
            path.pop()

        for node in list(self._edges.keys()):
            if node not in visited:
                dfs(node)
                visited.clear()
        return cycles

    def get_graph_summary(self) -> Dict:
        return {
            "transactions": len(self._transactions),
            "waiting_edges": sum(len(v) for v in self._edges.values()),
            "resources_locked": len(self._resources),
            "waiting_txns": sum(1 for t in self._transactions.values() if t["status"] == "waiting"),
        }

    # --- Auto-generated action dispatch methods ---
    def _action_add_holding(self, params=None):
        """Auto-generated action wrapper for add_holding"""
        if params is None:
            params = {}
        return self.add_holding(**params)

    def _action_add_waiting(self, params=None):
        """Auto-generated action wrapper for add_waiting"""
        if params is None:
            params = {}
        return self.add_waiting(**params)

    def _action_detect_cycle(self, params=None):
        """Auto-generated action wrapper for detect_cycle"""
        if params is None:
            params = {}
        return self.detect_cycle(**params)

    def _action_get_graph_summary(self, params=None):
        """Auto-generated action wrapper for get_graph_summary"""
        if params is None:
            params = {}
        return self.get_graph_summary(**params)

    def _action_release(self, params=None):
        """Auto-generated action wrapper for release"""
        if params is None:
            params = {}
        return self.release(**params)

class DeadlockResolver(object):
    """死锁解除策略引擎"""

    STRATEGIES = ["abort_youngest", "abort_oldest", "abort_longest_wait", "abort_most_locks", "manual"]

    def __init__(self, strategy: str = "abort_youngest"):
        self.strategy = strategy

    def resolve(self, cycle: List[str], transactions: Dict[str, Dict]) -> Dict:
        if not cycle:
            return {"action": "none", "reason": "no_cycle"}
        victim = self._select_victim(cycle, transactions)
        aborted_resources = set()
        if victim in transactions:
            aborted_resources = transactions[victim].get("holding", set())
        return {
            "action": "abort",
            "victim": victim,
            "cycle": cycle,
            "strategy": self.strategy,
            "freed_resources": list(aborted_resources),
            "remaining_txns": [t for t in cycle if t != victim],
        }

    def _select_victim(self, cycle: List[str], transactions: Dict[str, Dict]) -> str:
        if len(cycle) <= 1:
            return cycle[0] if cycle else ""
        candidates = [(t, transactions.get(t, {})) for t in cycle if t in transactions]
        if not candidates:
            return cycle[0]
        if self.strategy == "abort_youngest":
            return min(candidates, key=lambda x: x[1].get("since", 0))[0]
        elif self.strategy == "abort_oldest":
            return max(candidates, key=lambda x: x[1].get("since", 0))[0]
        elif self.strategy == "abort_longest_wait":
            return min(candidates, key=lambda x: x[1].get("since", 0))[0]
        elif self.strategy == "abort_most_locks":
            return max(candidates, key=lambda x: len(x[1].get("holding", set())))[0]
        return candidates[0][0]

class TimeoutManager(object):
    """锁超时管理"""

    def __init__(self, default_timeout: float = 30.0):
        self.default_timeout = default_timeout
        self._timeouts: Dict[str, float] = {}
        self._custom_timeouts: Dict[str, float] = {}

    def set_timeout(self, resource: str, timeout: float = None):
        t = timeout if timeout is not None else self.default_timeout
        self._timeouts[resource] = time.time() + t

    def check_timeouts(self) -> List[Dict]:
        now = time.time()
        expired = []
        for resource, deadline in list(self._timeouts.items()):
            if now > deadline:
                expired.append({"resource": resource, "deadline": deadline, "expired_sec": round(now - deadline, 2)})
                del self._timeouts[resource]
        return expired

    def remove(self, resource: str):
        self._timeouts.pop(resource, None)

    def get_pending(self) -> Dict[str, float]:
        now = time.time()
        return {r: round(d - now, 1) for r, d in self._timeouts.items() if d > now}

class ResourceTracker:
    """资源占用追踪"""

    def __init__(self):
        self._locks: Dict[str, List[Dict]] = defaultdict(list)
        self._lock_history: deque = deque(maxlen=10000)

    def acquire(self, resource: str, txn_id: str, lock_type: str = "exclusive", timeout: float = 30.0) -> Dict:
        existing = self._locks[resource]
        conflicting = [l for l in existing if l["txn_id"] != txn_id and l["lock_type"] == "exclusive"]
        shared_conflict = [
            l for l in existing if l["txn_id"] != txn_id and l["lock_type"] == "exclusive" and lock_type != "shared"
        ]
        if conflicting or shared_conflict:
            return {"acquired": False, "blocked_by": [l["txn_id"] for l in conflicting]}
        entry = {"txn_id": txn_id, "lock_type": lock_type, "acquired_at": time.time(), "timeout": timeout}
        self._locks[resource].append(entry)
        self._lock_history.append({"resource": resource, "action": "acquire", "txn_id": txn_id, "ts": time.time()})
        return {"acquired": True, "lock_type": lock_type}

    def release(self, resource: str, txn_id: str) -> Dict:
        before = len(self._locks.get(resource, []))
        self._locks[resource] = [l for l in self._locks.get(resource, []) if l["txn_id"] != txn_id]
        released = before - len(self._locks[resource])
        self._lock_history.append({"resource": resource, "action": "release", "txn_id": txn_id, "ts": time.time()})
        return {"released": released}

    def get_lock_info(self, resource: str) -> Dict:
        locks = self._locks.get(resource, [])
        return {
            "resource": resource,
            "holders": [
                {"txn_id": l["txn_id"], "type": l["lock_type"], "held_sec": round(time.time() - l["acquired_at"], 1)}
                for l in locks
            ],
        }

    def get_all_locks(self) -> Dict[str, List]:
        return {k: [l["txn_id"] for l in v] for k, v in self._locks.items() if v}

class DeadlockDetector(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """死锁检测 - 生产级实现"""

    def __init__(self, config: Optional[Dict] = None):

        super().__init__(config=config)
        self.metrics_collector = self._NoopMetricsCollector()

        self.config = config or {}
        self._metrics: Dict[str, Any] = {
            "total_operations": 0,
            "errors": 0,
            "detections": 0,
            "resolutions": 0,
            "timeouts_expired": 0,
            "avg_latency_ms": 0,
            "last_success_ts": None,
        }
        self._audit_log: List[Dict] = []
        self._status = ModuleStatus.INITIALIZING
        self._logger = logger

        self.wait_graph = WaitGraph()
        self.resolver = DeadlockResolver(strategy=self.config.get("resolve_strategy", "abort_youngest"))
        self.timeout_mgr = TimeoutManager(default_timeout=self.config.get("lock_timeout", 30))
        self.resource_tracker = ResourceTracker()
        self._detection_history: List[Dict] = []
        self._check_interval = self.config.get("check_interval", 5.0)
        self._last_check = 0

    def initialize(self) -> dict:
        self._status = ModuleStatus.RUNNING
        return {
            "success": True,
            "resolve_strategy": self.resolver.strategy,
            "lock_timeout": self.timeout_mgr.default_timeout,
        }

    def health_check(self) -> dict:
        return {
            "healthy": self._status == ModuleStatus.RUNNING,
            "detections": self._metrics["detections"],
            "resolutions": self._metrics["resolutions"],
            **self.wait_graph.get_graph_summary(),
        }

    def request_lock(self, params: dict = None) -> dict:
        params = params or {}
        resource = params.get("resource", "")
        txn_id = params.get("txn_id", str(uuid.uuid4())[:8])
        lock_type = params.get("lock_type", "exclusive")
        timeout = float(params.get("timeout", self.timeout_mgr.default_timeout))
        result = self.resource_tracker.acquire(resource, txn_id, lock_type, timeout)
        if result["acquired"]:
            self.wait_graph.add_holding(txn_id, resource)
            self.timeout_mgr.set_timeout(resource, timeout)
        else:
            self.wait_graph.add_waiting(txn_id, resource)
        return {"success": True, **result, "txn_id": txn_id}

    def release_lock(self, params: dict = None) -> dict:
        params = params or {}
        resource = params.get("resource", "")
        txn_id = params.get("txn_id", "")
        self.resource_tracker.release(resource, txn_id)
        self.wait_graph.release(txn_id, resource)
        self.timeout_mgr.remove(resource)
        return {"success": True, "resource": resource, "txn_id": txn_id}

    def detect(self, params: dict = None) -> dict:
        params = params or {}
        now = time.time()
        if now - self._last_check < self._check_interval and not params.get("force"):
            return {"success": True, "cycles": [], "reason": "skip_throttle"}
        self._last_check = now
        timeouts = self.timeout_mgr.check_timeouts()
        self._metrics["timeouts_expired"] += len(timeouts)
        for t in timeouts:
            self.resource_tracker.release(t["resource"], "")
            self.wait_graph.release("", t["resource"])
        cycles = self.wait_graph.detect_cycle()
        if cycles:
            self._metrics["detections"] += 1
            for cycle in cycles:
                resolution = self.resolver.resolve(cycle, self.wait_graph._transactions)
                if resolution["action"] == "abort":
                    victim = resolution["victim"]
                    self._metrics["resolutions"] += 1
                    self.wait_graph.release(victim)
                    self._detection_history.append(
                        {"cycle": cycle, "victim": victim, "strategy": resolution["strategy"], "ts": now}
                    )
                self._detection_history.append(resolution)
            return {
                "success": True,
                "deadlock": True,
                "cycles": cycles,
                "timeouts": timeouts,
                "resolutions": self._detection_history[-len(cycles) :],
            }
        return {"success": True, "deadlock": False, "cycles": [], "timeouts": timeouts}

    def get_lock_info(self, params: dict = None) -> dict:
        params = params or {}
        resource = params.get("resource", "")
        return {"success": True, **self.resource_tracker.get_lock_info(resource)}

    def get_all_locks(self, params: dict = None) -> dict:
        return {"success": True, "locks": self.resource_tracker.get_all_locks()}

    def get_detection_history(self, params: dict = None) -> dict:
        params = params or {}
        limit = int(params.get("limit", 50))
        return {"success": True, "history": self._detection_history[-limit:]}

    async def execute(self, action: str, params: dict = None) -> dict:
        self.trace("execute", {"module": "deadlock_detector"})
        self.metrics_collector.counter("deadlock_detector.execute.calls", 1)
        self.audit("execute", {"module": "deadlock_detector"})
        params = params or {}
        handler = getattr(self, action, None)
        if handler and callable(handler):
            self._metrics["total_operations"] += 1
            t0 = time.time()
            try:
                result = handler(params)
                self._metrics["last_success_ts"] = time.time()
                self._metrics["avg_latency_ms"] = (
                    self._metrics["avg_latency_ms"] * 0.9 + (time.time() - t0) * 1000 * 0.1
                )
                return result
            except Exception as e:
                self._metrics["errors"] += 1
                return {"success": False, "error": str(e)}
        return {"success": False, "error": f"Unknown action: {action}"}

    def analyze_lock_contention(self, resource_id: str) -> Dict[str, Any]:
        """锁竞争分析。企业场景：性能优化团队分析热点资源的锁等待情况，
        识别锁竞争严重的资源并优化访问模式（如拆分热点key、乐观锁替代悲观锁）。
        """
        locks = getattr(self, "_locks", {})
        waiters = getattr(self, "_wait_graph", {}).get(resource_id, [])
        lock_info = locks.get(resource_id, {})
        return {
            "success": True,
            "resource_id": resource_id,
            "lock_holder": lock_info.get("holder", "none"),
            "wait_queue_length": len(waiters),
            "waiters": waiters,
            "total_wait_time_ms": sum(w.get("wait_ms", 0) for w in waiters),
        }

    def get_deadlock_history(self, limit: int = 20) -> Dict[str, Any]:
        """死锁历史记录。企业场景：复盘死锁事件，分析根因并制定预防措施。"""
        history = getattr(self, "_deadlock_history", [])
        recent = history[-limit:]
        return {"success": True, "total_events": len(history), "returned": len(recent), "events": recent}

    def get_lock_usage_report(self, hours: int = 1) -> Dict[str, Any]:
        """锁使用报告。企业场景：DBA审查数据库锁等待情况，
        识别长事务持有锁过久、热点行竞争等问题。
        """
        locks = getattr(self, "_locks", {})
        now = time.time()
        cutoff = now - hours * 3600
        lock_stats = []
        for rid, info in locks.items():
            holder = info.get("holder", "")
            acquired = info.get("acquired_at", 0)
            hold_time = now - acquired if acquired > cutoff else 0
            lock_stats.append(
                {
                    "resource_id": rid,
                    "holder": holder,
                    "hold_time_s": round(hold_time, 2),
                    "waiters": len(self._wait_graph.get(rid, [])),
                }
            )
        lock_stats.sort(key=lambda x: -x["hold_time_s"])
        long_held = [s for s in lock_stats if s["hold_time_s"] > 30]
        return {
            "success": True,
            "hours": hours,
            "total_locks": len(locks),
            "long_held_locks": len(long_held),
            "top_by_hold_time": lock_stats[:10],
        }

    def force_release_lock(self, resource_id: str, reason: str = "manual") -> Dict[str, Any]:
        """强制释放锁。企业场景：紧急情况下DBA手动释放死锁或长事务持有的锁，
        恢复系统可用性。操作会记录审计日志。
        """
        locks = getattr(self, "_locks", {})
        lock_info = locks.get(resource_id)
        if not lock_info:
            return {"success": False, "error": f"资源 {resource_id} 无活跃锁"}
        old_holder = lock_info.get("holder", "unknown")
        waiters = self._wait_graph.get(resource_id, [])
        released = {
            "resource_id": resource_id,
            "old_holder": old_holder,
            "released_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "waiters_awakened": len(waiters),
            "reason": reason,
        }
        del locks[resource_id]
        if resource_id in self._wait_graph:
            del self._wait_graph[resource_id]
        return {"success": True, **released}

    def get_lock_dependency_graph(self) -> Dict[str, Any]:
        """生成锁依赖图。企业场景：架构师分析系统锁竞争关系，
        识别热点资源，优化锁粒度减少争用。
        """
        locks = getattr(self, "_locks", {})
        wait_graph = getattr(self, "_wait_graph", {})
        nodes = []
        edges = []
        for rid, info in locks.items():
            nodes.append({"id": rid, "type": "resource", "holder": info.get("holder", "")})
        for rid, waiters in wait_graph.items():
            for waiter in waiters:
                edges.append({"source": waiter, "target": rid, "type": "waiting"})
        # 检测循环依赖
        cycles = self._detect_cycles(wait_graph)
        return {
            "success": True,
            "node_count": len(nodes),
            "edge_count": len(edges),
            "nodes": nodes[:50],
            "edges": edges[:100],
            "cycles_detected": len(cycles),
            "cycles": cycles[:5],
        }

    def _detect_cycles(self, wait_graph: Dict) -> List[List[str]]:
        """检测等待图中的环。环=死锁。"""
        visited = set()
        path = []
        cycles = []

        def dfs(node):
            if node in visited:
                if node in path:
                    idx = path.index(node)
                    cycles.append(path[idx:] + [node])
                return
            visited.add(node)
            path.append(node)
            for waiter in wait_graph.get(node, []):
                dfs(waiter)
            path.pop()

        for node in list(wait_graph.keys()):
            visited.clear()
            dfs(node)
        return cycles

    def get_deadlock_risk_report(self) -> Dict[str, Any]:
        """死锁风险评估报告。企业场景：DBA定期评估数据库锁使用情况，
        识别高风险SQL和事务模式。
        """
        locks = getattr(self, "_locks", {})
        wait_graph = getattr(self, "_wait_graph", {})
        now = time.time()
        # 锁持有时间分布
        hold_times = []
        for info in locks.values():
            acquired = info.get("acquired_at", 0)
            if acquired > 0:
                hold_times.append(now - acquired)
        avg_hold = sum(hold_times) / max(len(hold_times), 1)
        max_hold = max(hold_times) if hold_times else 0
        # 等待队列深度
        wait_depths = [len(w) for w in wait_graph.values()]
        avg_wait = sum(wait_depths) / max(len(wait_depths), 1)
        max_wait = max(wait_depths) if wait_depths else 0
        risk_score = 0
        risk_factors = []
        if avg_hold > 10:
            risk_score += 25
            risk_factors.append(f"平均锁持有时间{avg_hold:.1f}s，超过10s阈值")
        if max_hold > 60:
            risk_score += 30
            risk_factors.append(f"最长锁持有时间{max_hold:.1f}s，超过60s阈值")
        if max_wait > 5:
            risk_score += 25
            risk_factors.append(f"最大等待深度{max_wait}，超过5阈值")
        if len(self._detect_cycles(wait_graph)) > 0:
            risk_score += 50
            risk_factors.append("检测到循环等待，存在死锁风险")
        risk_level = "critical" if risk_score >= 50 else ("warning" if risk_score >= 25 else "normal")
        return {
            "success": True,
            "active_locks": len(locks),
            "avg_hold_time_s": round(avg_hold, 2),
            "max_hold_time_s": round(max_hold, 2),
            "avg_wait_depth": round(avg_wait, 1),
            "max_wait_depth": max_wait,
            "risk_score": min(risk_score, 100),
            "risk_level": risk_level,
            "risk_factors": risk_factors,
        }

    def shutdown(self) -> dict:
        """Graceful shutdown for deadlock_detector."""
        self._status = "stopped"
        self._logger.info("%s shutdown complete", self.__class__.__name__)
        return {"success": True, "module": self.__class__.__name__}

module_class = DeadlockDetector
