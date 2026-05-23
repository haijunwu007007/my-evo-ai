"""
AUTO-EVO-AI V0.1 - Capacity Planner Module (Grade: A Production)
容量规划：资源预测、负载分析、扩缩容建议、成本优化
"""

__module_meta__ = {
    "id": "capacity-planner",
    "name": "Capacity Planner",
    "version": "1.0.0",
    "group": "system",
    "inputs": [
        {"name": "sample", "type": "string", "required": True, "description": ""},
        {"name": "resource", "type": "string", "required": True, "description": ""},
        {"name": "resource", "type": "string", "required": True, "description": ""},
        {"name": "operation", "type": "string", "required": True, "description": ""},
        {"name": "params", "type": "string", "required": True, "description": ""},
        {"name": "p", "type": "string", "required": True, "description": ""},
    ],
    "outputs": [
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "success", "type": "bool", "description": "是否成功"},
        {"name": "result", "type": "dict", "description": "执行结果"},
    ],
    "triggers": [],
    "depends_on": [],
    "tags": ["engine", "manager", "capacity"],
    "grade": "A",
    "description": "AUTO-EVO-AI V0.1 - Capacity Planner Module (Grade: A Production) 容量规划：资源预测、负载分析、扩缩容建议、成本优化",
}

import os
import asyncio
import time
import logging
import uuid
import math
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
from collections import defaultdict

try:
    from modules._base.enterprise_module import EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin
    from modules._base.tracing import trace_operation
    from modules._base.metrics import metrics_collector, prometheus_timer
    from modules._base.audit import AuditLogger
except ImportError:

    class EnterpriseModule:
        def __init__(self):
            self._initialized = False
            self.logger = logging.getLogger(__name__)

        def initialize(self):
            self._initialized = True

        def shutdown(self):
            self._initialized = False

        def health_check(self):
            return {"status": "ok"}

    class CircuitBreakerMixin:
        pass

    class RateLimiterMixin:
        pass

    trace_operation = lambda x: lambda f: f
    prometheus_timer = lambda x: lambda f: f
    metrics_collector = None

    class AuditLogger:
        def log(self, *a, **k):
            pass

logger = logging.getLogger(__name__)

class ResourceType(Enum):
    CPU = "cpu"
    MEMORY = "memory"
    STORAGE = "storage"
    NETWORK = "network"
    GPU = "gpu"
    CONNECTIONS = "connections"

class AlertLevel(Enum):
    NORMAL = "normal"
    WARNING = "warning"
    CRITICAL = "critical"

@dataclass
class ResourcePool:
    pool_id: str
    name: str
    resource_type: ResourceType
    total_capacity: float
    unit: str
    allocated: float = 0
    reserved: float = 0
    cost_per_unit: float = 0

@dataclass
class UsageSample:
    pool_id: str
    timestamp: datetime
    used: float
    requested: float = 0
    rejected: float = 0

@dataclass
class ForecastResult:
    forecast_id: str = field(default_factory=lambda: f"fc_{uuid.uuid4().hex[:8]}")
    pool_id: str = ""
    horizon_days: int = 30
    predicted_peak: float = 0
    predicted_avg: float = 0
    growth_rate: float = 0
    recommended_capacity: float = 0
    recommendation: str = ""
    confidence: float = 0

@dataclass
class ScalePlan:
    plan_id: str = field(default_factory=lambda: f"sp_{uuid.uuid4().hex[:8]}")
    pool_id: str = ""
    action: str = ""  # scale_up, scale_down, maintain
    current_capacity: float = 0
    target_capacity: float = 0
    urgency: str = "normal"  # normal, soon, immediate
    reason: str = ""
    estimated_cost_impact: float = 0
    created_at: datetime = field(default_factory=datetime.now)

class DemandForecastEngine(object):
    """需求预测引擎 - 基于历史数据的容量趋势预测"""

    def __init__(self):
        self._history: List[UsageSample] = []
        self._window_size = 7

    def add_sample(self, sample: object) -> None:
        self._history.append(sample)

    def predict_next(self, resource: str) -> Dict:
        """基于移动平均预测下一周期需求"""
        recent = [s for s in self._history if hasattr(s, "resource_id") and s.resource_id == resource]
        if len(recent) < 2:
            return {"resource": resource, "predicted": 0, "confidence": 0.0}
        values = [s.value for s in recent[-self._window_size :] if hasattr(s, "value")]
        avg = sum(values) / len(values) if values else 0
        variance = sum((v - avg) ** 2 for v in values) / len(values) if values else 0
        return {
            "resource": resource,
            "predicted": round(avg),
            "confidence": round(1.0 - min(variance / max(avg**2, 1), 1.0), 4),
        }

    def detect_anomaly(self, resource: str) -> bool:
        """检测资源使用异常"""
        recent = [s for s in self._history if hasattr(s, "resource_id") and s.resource_id == resource]
        if len(recent) < 3:
            return False
        values = [s.value for s in recent[-10:] if hasattr(s, "value")]
        if not values:
            return False
        avg = sum(values) / len(values)
        return abs(values[-1] - avg) > avg * 2 if avg > 0 else False

class CapacityPlannerManager(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    def __init__(self):
        self._initialized = False

    """容量规划管理器"""

    def __init__(self):

        super().__init__()
        self.module_name = "capacity_planner"
        self.module_id = self.module_name
        self.module_version = "7.0.0"
        self._pools: Dict[str, ResourcePool] = {}
        self._usage_history: Dict[str, List[UsageSample]] = defaultdict(list)
        self._forecasts: Dict[str, ForecastResult] = {}
        self._scale_plans: Dict[str, ScalePlan] = {}
        self._audit = AuditLogger()
        self._forecast_count = 0
        self._setup_default_pools()

    def _setup_default_pools(self):
        defaults = [
            ResourcePool("pool_cpu", "CPU集群", ResourceType.CPU, 256, "cores", 128, 25.6, 0.05),
            ResourcePool("pool_memory", "内存集群", ResourceType.MEMORY, 1024, "GB", 640, 102.4, 0.02),
            ResourcePool("pool_storage", "存储集群", ResourceType.STORAGE, 50000, "GB", 30000, 5000, 0.001),
            ResourcePool("pool_network", "网络带宽", ResourceType.NETWORK, 100, "Gbps", 60, 10, 0.10),
            ResourcePool("pool_conn", "连接池", ResourceType.CONNECTIONS, 100000, "conn", 50000, 10000, 0.0001),
        ]
        for p in defaults:
            self._pools[p.pool_id] = p
        # Seed usage history
        for pool in defaults:
            base = pool.allocated * 0.8
            for i in range(30):
                variation = 1 + 0.1 * math.sin(i * 0.5) + 0.02 * i
                self._usage_history[pool.pool_id].append(
                    UsageSample(pool.pool_id, datetime.now() - timedelta(days=30 - i), base * variation)
                )

    def initialize(self):
        logger.info("capacity_planner initialized")

    async def execute(self, operation: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        _ = self.trace("execute")
        metrics_collector.counter("capacity_planner_ops_total", labels={"action": operation})
        self.audit("execute", f"operation={operation}")
        params = params or {}
        if operation == "add_pool":
            return self._add_pool(params)
        elif operation == "record_usage":
            return self._record_usage(params)
        elif operation == "get_pool_status":
            return self._get_pool_status(params)
        elif operation == "forecast":
            return self._forecast(params)
        elif operation == "generate_plan":
            return self._generate_plan(params)
        elif operation == "get_alerts":
            return self._get_alerts(params)
        elif operation == "get_all_pools":
            return self._get_all_pools(params)
        elif operation == "cost_analysis":
            return self._cost_analysis(params)
        elif operation == "utilization_report":
            return self._utilization_report(params)
        else:
            return {
                "success": False,
                "error": f"unknown op: {operation}",
                "available": [
                    "add_pool",
                    "record_usage",
                    "get_pool_status",
                    "forecast",
                    "generate_plan",
                    "get_alerts",
                    "get_all_pools",
                    "cost_analysis",
                    "utilization_report",
                ],
            }

    def _add_pool(self, p: Dict) -> Dict:
        pool_id = p.get("pool_id")
        name = p.get("name", "")
        resource_type = p.get("resource_type", "cpu")
        capacity = p.get("capacity", 0)
        unit = p.get("unit", "")
        cost = p.get("cost_per_unit", 0)

        if not pool_id or capacity <= 0:
            return {"success": False, "error": "invalid pool_id or capacity"}

        try:
            rt = ResourceType(resource_type)
        except ValueError:
            rt = ResourceType.CPU

        pool = ResourcePool(pool_id, name, rt, capacity, unit, 0, 0, cost)
        self._pools[pool_id] = pool
        return {"success": True, "result": {"pool_id": pool_id, "name": name, "capacity": capacity, "unit": unit}}

    def _record_usage(self, p: Dict) -> Dict:
        pool_id = p.get("pool_id")
        used = p.get("used", 0)
        requested = p.get("requested", 0)
        rejected = p.get("rejected", 0)

        if not pool_id or pool_id not in self._pools:
            return {"success": False, "error": "pool not found"}

        sample = UsageSample(pool_id, datetime.now(), float(used), float(requested), float(rejected))
        self._usage_history[pool_id].append(sample)

        # Update pool allocation
        self._pools[pool_id].allocated = max(self._pools[pool_id].allocated, float(used))

        return {
            "success": True,
            "result": {"pool_id": pool_id, "used": used, "total_samples": len(self._usage_history[pool_id])},
        }

    def _get_pool_status(self, p: Dict) -> Dict:
        pool_id = p.get("pool_id")
        if not pool_id or pool_id not in self._pools:
            return {"success": False, "error": "pool not found"}

        pool = self._pools[pool_id]
        history = self._usage_history.get(pool_id, [])
        latest = history[-1] if history else None
        utilization = (latest.used / pool.total_capacity * 100) if latest and pool.total_capacity > 0 else 0

        if utilization > 90:
            level = AlertLevel.CRITICAL
        elif utilization > 75:
            level = AlertLevel.WARNING
        else:
            level = AlertLevel.NORMAL

        return {
            "success": True,
            "result": {
                "pool_id": pool_id,
                "name": pool.name,
                "resource_type": pool.resource_type.value,
                "total_capacity": pool.total_capacity,
                "allocated": pool.allocated,
                "reserved": pool.reserved,
                "available": pool.total_capacity - pool.allocated - pool.reserved,
                "utilization_pct": round(utilization, 1),
                "alert_level": level.value,
                "samples": len(history),
            },
        }

    def _forecast(self, p: Dict) -> Dict:
        pool_id = p.get("pool_id")
        horizon_days = p.get("horizon_days", 30)

        if not pool_id or pool_id not in self._pools:
            return {"success": False, "error": "pool not found"}

        pool = self._pools[pool_id]
        history = self._usage_history.get(pool_id, [])
        if len(history) < 3:
            return {"success": True, "result": {"message": "insufficient data", "samples": len(history)}}

        values = [s.used for s in history]
        n = len(values)

        # Linear regression for trend
        x = list(range(n))
        x_mean = sum(x) / n
        y_mean = sum(values) / n
        num = sum((xi - x_mean) * (yi - y_mean) for xi, yi in zip(x, values))
        den = sum((xi - x_mean) ** 2 for xi in x)
        slope = num / den if den else 0

        growth_rate = (slope / y_mean * 100) if y_mean else 0
        predicted_peak = (
            max(values[-7:]) * (1 + growth_rate / 100 * horizon_days / 30)
            if len(values) >= 7
            else values[-1] * (1 + growth_rate / 100 * horizon_days / 30)
        )
        predicted_avg = y_mean * (1 + growth_rate / 100 * horizon_days / 60)

        recommended = predicted_peak * 1.2  # 20% headroom
        confidence = max(40, 90 - abs(growth_rate) - horizon_days * 0.5)

        if recommended > pool.total_capacity:
            rec_text = f"需要扩容至 {recommended:.0f} {pool.unit}，当前 {pool.total_capacity}"
        elif recommended < pool.total_capacity * 0.7:
            rec_text = f"可考虑缩容至 {recommended:.0f} {pool.unit}"
        else:
            rec_text = "当前容量充足，无需调整"

        fc = ForecastResult(
            pool_id=pool_id,
            horizon_days=horizon_days,
            predicted_peak=round(predicted_peak, 2),
            predicted_avg=round(predicted_avg, 2),
            growth_rate=round(growth_rate, 2),
            recommended_capacity=round(recommended, 2),
            recommendation=rec_text,
            confidence=round(confidence, 1),
        )
        self._forecasts[fc.forecast_id] = fc
        self._forecast_count += 1

        return {
            "success": True,
            "result": {
                "forecast_id": fc.forecast_id,
                "pool_id": pool_id,
                "horizon_days": horizon_days,
                "predicted_peak": fc.predicted_peak,
                "predicted_avg": fc.predicted_avg,
                "growth_rate": fc.growth_rate,
                "recommended": fc.recommended_capacity,
                "recommendation": fc.recommendation,
                "confidence": fc.confidence,
            },
        }

    def _generate_plan(self, p: Dict) -> Dict:
        plans = []
        for pool_id, pool in self._pools.items():
            history = self._usage_history.get(pool_id, [])
            if not history:
                continue
            latest = history[-1]
            util = latest.used / pool.total_capacity if pool.total_capacity > 0 else 0

            if util > 0.9:
                action = "scale_up"
                target = pool.total_capacity * 1.5
                urgency = "immediate"
                reason = f"利用率 {util * 100:.1f}% 超过90%警戒线"
            elif util > 0.75:
                action = "scale_up"
                target = pool.total_capacity * 1.3
                urgency = "soon"
                reason = f"利用率 {util * 100:.1f}% 超过75%预警线"
            elif util < 0.2:
                action = "scale_down"
                target = pool.total_capacity * 0.6
                urgency = "normal"
                reason = f"利用率 {util * 100:.1f}% 低于20%，资源浪费"
            else:
                action = "maintain"
                target = pool.total_capacity
                urgency = "normal"
                reason = f"利用率 {util * 100:.1f}% 在正常范围内"

            cost_impact = (target - pool.total_capacity) * pool.cost_per_unit
            sp = ScalePlan(
                pool_id=pool_id,
                action=action,
                current_capacity=pool.total_capacity,
                target_capacity=round(target, 2),
                urgency=urgency,
                reason=reason,
                estimated_cost_impact=round(cost_impact, 2),
            )
            plans.append(sp)
            self._scale_plans[sp.plan_id] = sp

        return {
            "success": True,
            "result": [
                {
                    "plan_id": p.plan_id,
                    "pool_id": p.pool_id,
                    "action": p.action,
                    "current": p.current_capacity,
                    "target": p.target_capacity,
                    "urgency": p.urgency,
                    "reason": p.reason,
                    "cost_impact": p.estimated_cost_impact,
                }
                for p in plans
            ],
            "total": len(plans),
        }

    def _get_alerts(self, p: Dict) -> Dict:
        alerts = []
        for pool_id, pool in self._pools.items():
            history = self._usage_history.get(pool_id, [])
            if not history:
                continue
            latest = history[-1]
            util = latest.used / pool.total_capacity if pool.total_capacity > 0 else 0
            if util > 0.9:
                alerts.append(
                    {
                        "pool_id": pool_id,
                        "level": "critical",
                        "utilization": round(util * 100, 1),
                        "message": f"{pool.name} 利用率超过90%",
                    }
                )
            elif util > 0.75:
                alerts.append(
                    {
                        "pool_id": pool_id,
                        "level": "warning",
                        "utilization": round(util * 100, 1),
                        "message": f"{pool.name} 利用率超过75%",
                    }
                )
        alerts.sort(key=lambda x: 0 if x["level"] == "critical" else 1)
        return {"success": True, "result": alerts, "total": len(alerts)}

    def _get_all_pools(self, p: Dict) -> Dict:
        pools = []
        for pool_id, pool in self._pools.items():
            history = self._usage_history.get(pool_id, [])
            latest = history[-1] if history else None
            util = (latest.used / pool.total_capacity * 100) if latest and pool.total_capacity > 0 else 0
            pools.append(
                {
                    "pool_id": pool_id,
                    "name": pool.name,
                    "resource_type": pool.resource_type.value,
                    "total": pool.total_capacity,
                    "unit": pool.unit,
                    "allocated": pool.allocated,
                    "utilization_pct": round(util, 1),
                    "samples": len(history),
                }
            )
        return {"success": True, "result": pools, "total": len(pools)}

    def _cost_analysis(self, p: Dict) -> Dict:
        total_cost = 0
        pool_costs = []
        for pool_id, pool in self._pools.items():
            cost = pool.allocated * pool.cost_per_unit * 730  # monthly hours
            total_cost += cost
            history = self._usage_history.get(pool_id, [])
            util = 0
            if history and pool.total_capacity > 0:
                util = history[-1].used / pool.total_capacity
            efficiency = (util * 100) if cost > 0 else 0
            pool_costs.append(
                {
                    "pool_id": pool_id,
                    "name": pool.name,
                    "monthly_cost": round(cost, 2),
                    "efficiency_pct": round(efficiency, 1),
                    "waste_pct": round(100 - efficiency, 1),
                }
            )
        pool_costs.sort(key=lambda x: x["monthly_cost"], reverse=True)
        return {
            "success": True,
            "result": {
                "total_monthly_cost": round(total_cost, 2),
                "pools": pool_costs,
            },
        }

    def _utilization_report(self, p: Dict) -> Dict:
        report = []
        for pool_id, pool in self._pools.items():
            history = self._usage_history.get(pool_id, [])
            if not history:
                continue
            values = [s.used for s in history]
            avg_util = sum(values) / len(values) / pool.total_capacity if pool.total_capacity > 0 else 0
            peak = max(values) / pool.total_capacity if pool.total_capacity > 0 else 0
            min_val = min(values) / pool.total_capacity if pool.total_capacity > 0 else 0
            report.append(
                {
                    "pool_id": pool_id,
                    "name": pool.name,
                    "avg_utilization": round(avg_util * 100, 1),
                    "peak_utilization": round(peak * 100, 1),
                    "min_utilization": round(min_val * 100, 1),
                    "samples": len(values),
                }
            )
        return {"success": True, "result": report, "total": len(report)}

    def shutdown(self):
        self._initialized = False
        self._audit.log("shutdown", "capacity_planner shutdown")

    def health_check(self) -> Dict[str, Any]:
        base = super().health_check() or {}
        result = dict(base)
        result.update(
            {
                "status": "healthy" if self._initialized else "not_initialized",
                "pools": len(self._pools),
                "forecasts": self._forecast_count,
                "scale_plans": len(self._scale_plans),
            }
        )
        return result

    def get_utilization_report(self) -> Dict:
        """获取资源利用率报告"""
        pools = self._pools if hasattr(self, "_pools") else {}
        report = {}
        for name, pool in pools.items():
            if hasattr(pool, "current") and hasattr(pool, "max_capacity"):
                util = pool.current / max(pool.max_capacity, 1) * 100
                report[name] = {
                    "current": pool.current,
                    "max": pool.max_capacity,
                    "utilization": round(util, 2),
                    "status": "critical" if util > 90 else "warning" if util > 75 else "healthy",
                }
        return report

    def recommend_scale_actions(self) -> List[Dict]:
        """基于当前利用率推荐扩缩容操作"""
        report = self.get_utilization_report()
        actions = []
        for name, info in report.items():
            if info["status"] == "critical":
                actions.append(
                    {
                        "resource": name,
                        "action": "scale_up",
                        "reason": f"utilization {info['utilization']}%",
                        "priority": "high",
                    }
                )
            elif info["status"] == "healthy" and info["utilization"] < 20:
                actions.append(
                    {
                        "resource": name,
                        "action": "scale_down",
                        "reason": f"utilization {info['utilization']}%",
                        "priority": "low",
                    }
                )
        return sorted(actions, key=lambda x: 0 if x["priority"] == "high" else 1)

    def forecast_resource_demand(self, days: int = 7) -> Dict[str, Any]:
        """预测未来资源需求：基于历史趋势线性外推，生成容量预警"""
        resources = self._resources if hasattr(self, "_resources") else {}
        if not resources:
            return {"forecast_days": days, "resources": []}
        forecast = []
        for name, info in resources.items():
            current = info.get("utilization", 0)
            growth_rate = info.get("growth_rate", 0.02)
            projected = min(current + growth_rate * days * 100, 100)
            days_to_full = int((100 - current) / max(growth_rate * 100, 0.01)) if current < 100 else 0
            urgency = "critical" if days_to_full < 3 else "warning" if days_to_full < 7 else "normal"
            forecast.append(
                {
                    "resource": name,
                    "current_utilization": current,
                    "projected_utilization": round(projected, 1),
                    "days_to_saturation": days_to_full,
                    "urgency": urgency,
                    "recommended_action": "scale_up" if urgency in ("critical", "warning") else "monitor",
                }
            )
        return {"forecast_days": days, "resources": forecast}

module_class = CapacityPlannerManager
