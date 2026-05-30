"""
AUTO-EVO-AI V0.1 — Demeter AI智能体
Grade: A (生产级) | Category: AI智能体
职责：资源管理、配额分配、资源调度、容量规划、成本优化
"""

__module_meta__ = {
    "id": "agent-demeter",
    "name": "Agent Demeter",
    "version": "V0.1",
    "group": "agent",
    "inputs": [
        {"name": "config", "type": "string", "required": True, "description": ""},
        {"name": "action", "type": "string", "required": True, "description": ""},
        {"name": "params", "type": "string", "required": True, "description": ""},
        {"name": "pool_id", "type": "string", "required": True, "description": ""},
        {"name": "rtype", "type": "string", "required": True, "description": ""},
        {"name": "total", "type": "string", "required": True, "description": ""},
    ],
    "outputs": [
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
    ],
    "triggers": [{"type": "event", "config": {"on": "agent_demeter.task.request"}}],
    "depends_on": [],
    "tags": ["engine", "manager", "multi-agent", "agent"],
    "grade": "B",
    "description": "AUTO-EVO-AI V0.1 — Demeter AI智能体 Grade: A (生产级) | Category: AI智能体",
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
    from modules._base.enterprise_module import EnterpriseModulenterpriseModule, CircuitBreakerMixin, RateLimiterMixin
    from modules._base.tracing import trace_operation
    from modules._base.metrics import prometheus_timer, metrics_collector
    from modules._base.audit import AuditLogger
except ImportError:
    import sys

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _base.enterprise_module import EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin
    from _base.tracing import trace_operation
    from _base.metrics import metrics_collector
    from _base.audit import AuditLogger

logger = logging.getLogger("agent_demeter")

class ResourceType(Enum):
    """资源类型"""

    CPU = "cpu"
    MEMORY = "memory"
    DISK = "disk"
    NETWORK = "network"
    GPU = "gpu"
    LICENSE = "license"

@dataclass
class ResourcePool:
    """资源池"""

    pool_id: str
    resource_type: ResourceType
    total: float
    allocated: float = 0.0
    reserved: float = 0.0
    unit: str = ""

    @property
    def available(self) -> float:
        return max(0, self.total - self.allocated - self.reserved)

    @property
    def utilization(self) -> float:
        if self.total == 0:
            return 0
        return round((self.allocated + self.reserved) / self.total, 4)

@dataclass
class Allocation:
    """分配记录"""

    allocation_id: str
    pool_id: str
    consumer: str
    amount: float
    status: str = "active"
    created_at: float = field(default_factory=time.time)

class AgentDemeterManager(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """Demeter智能体管理器 - 资源管理与调度"""

    MODULE_ID = "agent_demeter"
    MODULE_NAME = "Demeter智能体"
    VERSION = "V0.1"
    MODULE_LEVEL = "A"

    def __init__(self, config: Optional[Dict[str, Any]] = None):

        super().__init__(config)
        self.module_level = self.MODULE_LEVEL
        self._audit = None
        self._metrics = metrics_collector
        self._pools: Dict[str, ResourcePool] = {}
        self._allocations: Dict[str, Allocation] = {}
        self._alloc_counter: int = 0

    def initialize(self) -> None:
        """初始化，创建默认资源池"""
        try:
            pass
            # super().initialize() removed for sync compatibility
            # 创建默认资源池
            defaults = [
                ("cpu_pool", ResourceType.CPU, 100, "%"),
                ("mem_pool", ResourceType.MEMORY, 32768, "MB"),
                ("disk_pool", ResourceType.DISK, 1024000, "MB"),
                ("gpu_pool", ResourceType.GPU, 4, "cards"),
            ]
            for pool_id, rtype, total, unit in defaults:
                self._pools[pool_id] = ResourcePool(pool_id=pool_id, resource_type=rtype, total=total, unit=unit)
            if self._audit:
                self._audit.log("demeter_initialized", {"pools": len(self._pools)})
            self.stats.success_count += 1
            logger.info("Demeter智能体初始化完成")
        except Exception as e:
            logger.error(f"Demeter初始化失败: {e}")
            self.stats.error_count += 1
            raise

    async def execute(self, action: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """执行动作"""
        _ = self.trace("execute")
        metrics_collector.counter("agent_demeter_ops_total", labels={"action": action})
        self.audit("execute", f"action={action}")
        params = params or {}
        start_time = time.time()
        success = False
        error_msg = None

        try:
            if action == "allocate":
                pool_id = params.get("pool_id")
                consumer = params.get("consumer")
                amount = params.get("amount")
                if not all([pool_id, consumer, amount is not None]):
                    return {"success": False, "error": "Missing: pool_id, consumer, amount"}
                result = self.allocate(pool_id, consumer, float(amount))
                success = True
                return {"success": True, "result": result}

            elif action == "release":
                alloc_id = params.get("allocation_id")
                if not alloc_id:
                    return {"success": False, "error": "Missing: allocation_id"}
                result = self.release(alloc_id)
                success = True
                return {"success": True, "result": result}

            elif action == "create_pool":
                pool_id = params.get("pool_id")
                rtype = params.get("resource_type", "cpu")
                total = params.get("total", 100)
                unit = params.get("unit", "")
                if not pool_id:
                    return {"success": False, "error": "Missing: pool_id"}
                result = self.create_pool(pool_id, rtype, total, unit)
                success = True
                return {"success": True, "result": result}

            elif action == "pool_status":
                pool_id = params.get("pool_id", "")
                if pool_id:
                    pools = {pool_id: self._pool_info(self._pools.get(pool_id))}
                else:
                    pools = {pid: self._pool_info(p) for pid, p in self._pools.items()}
                return {"success": True, "result": pools}

            elif action == "list_allocations":
                consumer = params.get("consumer", "")
                allocs = self._allocations.values()
                if consumer:
                    allocs = [a for a in allocs if a.consumer == consumer]
                return {
                    "success": True,
                    "result": [
                        {
                            "id": a.allocation_id,
                            "pool": a.pool_id,
                            "consumer": a.consumer,
                            "amount": a.amount,
                            "status": a.status,
                        }
                        for a in allocs
                    ],
                }

            else:
                return {"success": False, "error": f"Unknown action: {action}"}

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Execute error: {e}", exc_info=True)
            return {"success": False, "error": error_msg}
        finally:
            duration_ms = (time.time() - start_time) * 1000
            self.stats.record_request(duration_ms, success, error_msg)

    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        high_util = sum(1 for p in self._pools.values() if p.utilization > 0.9)
        status = "healthy" if high_util == 0 else ("degraded" if high_util <= 2 else "unhealthy")
        return {
            "status": status,
            "module_id": self.module_id,
            "module_level": self.module_level,
            "pools": len(self._pools),
            "allocations": len(self._allocations),
            "high_utilization_pools": high_util,
        }

    def shutdown(self) -> None:
        """优雅关闭，释放所有资源"""
        self._allocations.clear()
        for p in self._pools.values():
            p.allocated = 0
            p.reserved = 0
        # super().shutdown() removed for sync compatibility

    def create_pool(self, pool_id: str, rtype: str, total: float, unit: str = "") -> Dict:
        """创建资源池"""
        try:
            rt = ResourceType(rtype)
        except ValueError:
            rt = ResourceType.CPU
        pool = ResourcePool(pool_id=pool_id, resource_type=rt, total=total, unit=unit)
        self._pools[pool_id] = pool
        if self._audit:
            self._audit.log("pool_created", {"pool_id": pool_id, "type": rtype, "total": total})
        self.stats.success_count += 1
        return {"pool_id": pool_id, "type": rtype, "total": total, "unit": unit}

    def allocate(self, pool_id: str, consumer: str, amount: float) -> Dict:
        """分配资源"""
        pool = self._pools.get(pool_id)
        if not pool:
            return {"error": f"Pool not found: {pool_id}"}
        if pool.available < amount:
            return {"error": "Insufficient resources", "available": pool.available, "requested": amount}

        self._alloc_counter += 1
        alloc_id = f"alloc_{self._alloc_counter}"
        pool.allocated += amount
        alloc = Allocation(allocation_id=alloc_id, pool_id=pool_id, consumer=consumer, amount=amount)
        self._allocations[alloc_id] = alloc

        if self._audit:
            self._audit.log(
                "resource_allocated", {"alloc_id": alloc_id, "pool": pool_id, "consumer": consumer, "amount": amount}
            )
        self.stats.success_count += 1
        return {"allocation_id": alloc_id, "pool_id": pool_id, "amount": amount, "remaining": pool.available}

    def release(self, alloc_id: str) -> Dict:
        """释放资源"""
        alloc = self._allocations.get(alloc_id)
        if not alloc:
            return {"error": f"Allocation not found: {alloc_id}"}
        pool = self._pools.get(alloc.pool_id)
        if pool:
            pool.allocated = max(0, pool.allocated - alloc.amount)
        alloc.status = "released"
        if self._audit:
            self._audit.log("resource_released", {"alloc_id": alloc_id, "pool": alloc.pool_id})
        self.stats.success_count += 1
        return {"allocation_id": alloc_id, "released": alloc.amount, "status": "released"}

    def _pool_info(self, pool: Optional[ResourcePool]) -> Dict:
        if not pool:
            return {"error": "not found"}
        return {
            "pool_id": pool.pool_id,
            "type": pool.resource_type.value,
            "total": pool.total,
            "allocated": pool.allocated,
            "reserved": pool.reserved,
            "available": pool.available,
            "utilization": pool.utilization,
            "unit": pool.unit,
        }

module_class = AgentDemeterManager

class ResourceAllocationEngine(object):
    """资源分配引擎 - 智能调度、负载均衡、容量规划"""

    def __init__(self):
        self._pools: Dict[str, Dict] = {}
        self._allocations: Dict[str, List[Dict]] = {}
        self._utilization_history: Dict[str, List[float]] = {}
        self._reservation_queue: List[Dict] = []
        self._scaling_rules: Dict[str, Dict] = {}

    def create_pool(self, pool_id: str, capacity: float, unit: str = "unit") -> Dict:
        """创建资源池"""
        self._pools[pool_id] = {"capacity": capacity, "allocated": 0.0, "unit": unit}
        self._allocations[pool_id] = []
        self._utilization_history[pool_id] = []
        return {"pool_id": pool_id, "capacity": capacity, "unit": unit}

    def allocate(self, pool_id: str, consumer: str, amount: float, priority: str = "normal") -> Dict:
        """分配资源"""
        pool = self._pools.get(pool_id)
        if not pool:
            return {"error": "pool not found"}
        available = pool["capacity"] - pool["allocated"]
        if available < amount:
            return {"error": "insufficient", "available": available, "requested": amount}
        pool["allocated"] += amount
        alloc_id = f"alloc-{pool_id}-{consumer}-{int(time.time())}"
        alloc = {
            "alloc_id": alloc_id,
            "consumer": consumer,
            "amount": amount,
            "priority": priority,
            "status": "active",
            "created_at": time.time(),
        }
        self._allocations[pool_id].append(alloc)
        self._record_utilization(pool_id)
        return alloc

    def release(self, pool_id: str, alloc_id: str) -> bool:
        """释放资源"""
        allocs = self._allocations.get(pool_id, [])
        for i, a in enumerate(allocs):
            if a["alloc_id"] == alloc_id and a["status"] == "active":
                a["status"] = "released"
                a["released_at"] = time.time()
                pool = self._pools.get(pool_id, {})
                pool["allocated"] = max(0, pool.get("allocated", 0) - a["amount"])
                self._record_utilization(pool_id)
                return True
        return False

    def get_utilization(self, pool_id: str) -> Dict[str, Any]:
        """获取利用率"""
        pool = self._pools.get(pool_id, {})
        cap = pool.get("capacity", 0)
        alloc = pool.get("allocated", 0)
        util = alloc / max(cap, 1e-8)
        return {
            "pool_id": pool_id,
            "capacity": cap,
            "allocated": round(alloc, 4),
            "utilization": round(util, 4),
            "available": round(cap - alloc, 4),
        }

    def suggest_scaling(self, pool_id: str) -> Dict[str, Any]:
        """容量规划建议"""
        history = self._utilization_history.get(pool_id, [])
        if len(history) < 5:
            return {"pool_id": pool_id, "suggestion": "insufficient_data"}
        avg_util = sum(history[-10:]) / len(history[-10:])
        trend = history[-1] - history[-5] if len(history) >= 5 else 0
        suggestion = "scale_up" if avg_util > 0.8 else "scale_down" if avg_util < 0.3 else "maintain"
        return {
            "pool_id": pool_id,
            "avg_utilization": round(avg_util, 4),
            "trend": round(trend, 4),
            "suggestion": suggestion,
        }

    def add_scaling_rule(self, pool_id: str, threshold_high: float, threshold_low: float, action: str) -> None:
        """添加弹性伸缩规则"""
        self._scaling_rules[pool_id] = {"high": threshold_high, "low": threshold_low, "action": action}

    def _record_utilization(self, pool_id: str) -> None:
        pool = self._pools.get(pool_id, {})
        cap = pool.get("capacity", 0)
        alloc = pool.get("allocated", 0)
        util = alloc / max(cap, 1e-8)
        history = self._utilization_history.setdefault(pool_id, [])
        history.append(util)
        if len(history) > 1000:
            self._utilization_history[pool_id] = history[-500:]

    def list_pools(self) -> List[Dict]:
        return [{"pool_id": pid, **self.get_utilization(pid)} for pid in self._pools]

    def get_active_allocations(self, pool_id: str) -> List[Dict]:
        allocs = self._allocations.get(pool_id, [])
        return [a for a in allocs if a["status"] == "active"]

    def force_balance(self, pool_id: str, target_util: float = 0.5) -> Dict:
        """强制均衡"""
        pool = self._pools.get(pool_id)
        if not pool:
            return {"error": "pool not found"}
        current = pool["allocated"] / max(pool["capacity"], 1e-8)
        if abs(current - target_util) < 0.05:
            return {"status": "already_balanced", "utilization": round(current, 4)}
        new_cap = pool["allocated"] / target_util
        pool["capacity"] = new_cap
        return {
            "status": "balanced",
            "old_capacity": round(pool["capacity"], 2),
            "new_capacity": round(new_cap, 2),
            "utilization": round(target_util, 4),
        }

    def reserve(self, pool_id: str, consumer: str, amount: float, duration: float = 0) -> Dict:
        """预约资源"""
        pool = self._pools.get(pool_id, {})
        available = pool.get("capacity", 0) - pool.get("allocated", 0)
        if available < amount:
            return {"error": "insufficient", "available": available}
        reservation = {
            "pool_id": pool_id,
            "consumer": consumer,
            "amount": amount,
            "duration": duration,
            "status": "reserved",
            "created_at": time.time(),
        }
        self._reservation_queue.append(reservation)
        pool["allocated"] = pool.get("allocated", 0) + amount
        return reservation

    def get_reservation_status(self) -> List[Dict]:
        """获取预约状态"""
        return [r for r in self._reservation_queue if r["status"] == "reserved"]

    def cancel_reservation(self, consumer: str, pool_id: str) -> bool:
        """取消预约"""
        for i, r in enumerate(self._reservation_queue):
            if r["consumer"] == consumer and r["pool_id"] == pool_id and r["status"] == "reserved":
                r["status"] = "cancelled"
                pool = self._pools.get(pool_id, {})
                pool["allocated"] = max(0, pool.get("allocated", 0) - r["amount"])
                return True
        return False

    def get_capacity_report(self) -> Dict[str, Any]:
        """容量报告"""
        total_cap = sum(p["capacity"] for p in self._pools.values())
        total_alloc = sum(p["allocated"] for p in self._pools.values())
        total_reservations = len([r for r in self._reservation_queue if r["status"] == "reserved"])
        pool_reports = []
        for pid in self._pools:
            pool_reports.append(self.get_utilization(pid))
        return {
            "total_pools": len(self._pools),
            "total_capacity": round(total_cap, 2),
            "total_allocated": round(total_alloc, 2),
            "total_utilization": round(total_alloc / max(total_cap, 1e-8), 4),
            "active_reservations": total_reservations,
            "pools": pool_reports,
        }

    def set_pool_capacity(self, pool_id: str, new_capacity: float) -> bool:
        """调整池容量"""
        pool = self._pools.get(pool_id)
        if not pool:
            return False
        old_cap = pool["capacity"]
        pool["capacity"] = new_capacity
        if pool["allocated"] > new_capacity:
            pool["allocated"] = new_capacity
        self._record_utilization(pool_id)
        return True

    def get_consumer_usage(self, pool_id: str, consumer: str) -> Dict[str, Any]:
        """获取消费者用量"""
        allocs = self._allocations.get(pool_id, [])
        consumer_allocs = [a for a in allocs if a["consumer"] == consumer]
        active = [a for a in consumer_allocs if a["status"] == "active"]
        return {
            "consumer": consumer,
            "pool_id": pool_id,
            "total_allocations": len(consumer_allocs),
            "active_allocations": len(active),
            "total_amount": sum(a["amount"] for a in active),
        }

    def redistribute(self, source_pool: str, target_pool: str, amount: float) -> Dict:
        """跨池资源调配"""
        src = self._pools.get(source_pool, {})
        tgt = self._pools.get(target_pool, {})
        available = src.get("capacity", 0) - src.get("allocated", 0)
        if available < amount:
            return {"error": "insufficient_source", "available": available, "requested": amount}
        src["capacity"] -= amount
        tgt["capacity"] += amount
        return {"status": "redistributed", "amount": amount, "source": source_pool, "target": target_pool}

    def delete_pool(self, pool_id: str) -> bool:
        """删除资源池"""
        pool = self._pools.get(pool_id)
        if not pool or pool.get("allocated", 0) > 0:
            return False
        del self._pools[pool_id]
        self._allocations.pop(pool_id, None)
        self._utilization_history.pop(pool_id, None)
        self._scaling_rules.pop(pool_id, None)
        return True

    def get_pool_history(self, pool_id: str, points: int = 20) -> List[float]:
        """获取利用率历史"""
        history = self._utilization_history.get(pool_id, [])
        if len(history) <= points:
            return [round(h, 4) for h in history]
        step = len(history) / points
        return [round(history[int(i * step)], 4) for i in range(points)]

    def export_state(self) -> Dict[str, Any]:
        """导出引擎状态"""
        return {
            "pools": dict(self._pools),
            "allocation_count": sum(len(a) for a in self._allocations.values()),
            "reservations": len(self._reservation_queue),
            "scaling_rules": list(self._scaling_rules.keys()),
        }

    def find_idle_pools(self, threshold: float = 0.2) -> List[Dict]:
        """找出空闲资源池"""
        idle = []
        for pid in self._pools:
            util = self.get_utilization(pid)
            if util["utilization"] < threshold:
                idle.append(util)
        return sorted(idle, key=lambda x: x["utilization"])

    def find_hot_pools(self, threshold: float = 0.9) -> List[Dict]:
        """找出热点资源池"""
        hot = []
        for pid in self._pools:
            util = self.get_utilization(pid)
            if util["utilization"] > threshold:
                hot.append(util)
        return sorted(hot, key=lambda x: -x["utilization"])

    def pre_warm_pool(self, pool_id: str, amount: float) -> Dict:
        """预热资源池"""
        pool = self._pools.get(pool_id, {})
        if not pool:
            return {"error": "pool not found"}
        pool["capacity"] += amount
        return {"pool_id": pool_id, "added_capacity": amount, "new_capacity": pool["capacity"]}

    def analyze_allocation_efficiency(self) -> Dict[str, Any]:
        """分析资源分配效率：利用率、碎片率、浪费比例"""
        pools = self._pools if hasattr(self, "_pools") else {}
        if not pools:
            return {"total_pools": 0, "efficiency": {}}
        results = []
        total_capacity = 0
        total_used = 0
        for pid, pool in pools.items():
            cap = pool.get("capacity", 0)
            used = pool.get("allocated", 0)
            total_capacity += cap
            total_used += used
            util = used / cap if cap > 0 else 0
            frag = 1 - util if util < 1 else 0
            grade = "A" if util > 0.8 else "B" if util > 0.6 else "C" if util > 0.4 else "D"
            results.append(
                {
                    "pool_id": pid,
                    "capacity": cap,
                    "allocated": used,
                    "utilization": round(util, 3),
                    "fragmentation": round(frag, 3),
                    "grade": grade,
                }
            )
        overall_util = total_used / total_capacity if total_capacity > 0 else 0
        return {
            "total_pools": len(pools),
            "overall_utilization": round(overall_util, 3),
            "total_capacity": total_capacity,
            "total_allocated": total_used,
            "pools": sorted(results, key=lambda x: x["utilization"]),
        }
