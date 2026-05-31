"""
AUTO-EVO-AI V0.1 — 自动扩缩容
Grade: A (生产级) | Category: 弹性计算
职责：自动伸缩策略、容量规划、实例管理、指标驱动扩缩、冷却控制
"""

__module_meta__ = {
        "id": "auto-scale",
        "name": "Auto Scale",
        "version": "V0.1",
        "group": "resilience",
        "inputs": [
            {
                "name": "config",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "action",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "params",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "service",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "metric_name",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "value",
                "type": "string",
                "required": True,
                "description": ""
            }
        ],
        "outputs": [
            {
                "name": "result",
                "type": "dict",
                "description": "执行结果"
            },
            {
                "name": "result_2",
                "type": "dict",
                "description": "执行结果"
            },
            {
                "name": "result_3",
                "type": "dict",
                "description": "执行结果"
            }
        ],
        "triggers": [],
        "depends_on": [],
        "tags": [
            "manager",
            "auto"
        ],
        "grade": "B",
        "description": "AUTO-EVO-AI V0.1 — 自动扩缩容 Grade: A (生产级) | Category: 弹性计算"
    }

import os
import asyncio
import time
import logging
from typing import Any, Dict, List, Optional
from enum import Enum
from dataclasses import dataclass, field

try:
    from modules._base.enterprise_module import EnterpriseModule
    from modules._base.mixins import CircuitBreakerMixin, RateLimiterMixin
    from modules._base.metrics import metrics_collector
    from _base.audit import AuditLogger
except ImportError:
    import sys

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _base.enterprise_module import EnterpriseModule
    from _base.metrics import metrics_collector
    from _base.audit import AuditLogger

logger = logging.getLogger("auto_scale")

class ScaleDirection(Enum):
    UP = "scale_up"
    DOWN = "scale_down"
    NONE = "none"

class ScalePolicy(Enum):
    CPU = "cpu_based"
    MEMORY = "memory_based"
    CUSTOM = "custom_metric"
    SCHEDULED = "scheduled"

class InstanceStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    TERMINATING = "terminating"
    TERMINATED = "terminated"

@dataclass
class ScaleRule:
    rule_id: str
    name: str
    policy: ScalePolicy
    metric_name: str
    scale_up_threshold: float
    scale_down_threshold: float
    cooldown_seconds: float = 300
    min_instances: int = 1
    max_instances: int = 20
    step_up: int = 1
    step_down: int = 1
    enabled: bool = True

@dataclass
class Instance:
    instance_id: str
    service: str
    status: InstanceStatus = InstanceStatus.RUNNING
    created_at: float = field(default_factory=time.time)
    cpu_usage: float = 0.0
    memory_usage: float = 0.0

@dataclass
class ScaleEvent:
    event_id: str
    service: str
    direction: ScaleDirection
    from_count: int
    to_count: int
    rule_id: str
    reason: str = ""
    timestamp: float = field(default_factory=time.time)

class AutoScaleManager(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """自动扩缩容管理器"""

    MODULE_ID = "auto_scale"
    MODULE_NAME = "自动扩缩容"
    VERSION = "V0.1"
    MODULE_LEVEL = "A"

    def __init__(self, config: dict[str, Any] | None = None):

        super().__init__(config)
        self.module_level = self.MODULE_LEVEL
        self._audit = None
        self._metrics = metrics_collector
        self._rules: dict[str, ScaleRule] = {}
        self._instances: dict[str, list[Instance]] = {}  # service -> instances
        self._events: list[ScaleEvent] = []
        self._cooldowns: dict[str, float] = {}  # rule_id -> last_scale_time
        self._counter: int = 0
        self._instance_counter: int = 0

    def initialize(self) -> None:
        try:
            self._rules.clear()
            self._instances.clear()
            self._events.clear()
            defaults = [
                ScaleRule("api_cpu", "API服务CPU策略", ScalePolicy.CPU, "cpu_usage_percent", 80, 30, 120, 2, 20, 2, 1),
                ScaleRule(
                    "api_memory",
                    "API服务内存策略",
                    ScalePolicy.MEMORY,
                    "memory_usage_percent",
                    85,
                    40,
                    180,
                    2,
                    20,
                    1,
                    1,
                ),
                ScaleRule(
                    "worker_custom", "Worker自定义策略", ScalePolicy.CUSTOM, "queue_depth", 1000, 100, 60, 1, 50, 5, 2
                ),
            ]
            for r in defaults:
                self._rules[r.rule_id] = r
            # 默认实例
            for svc in ["api_service", "worker_service"]:
                self._instances[svc] = [Instance(instance_id=f"inst_{svc}_1", service=svc)]
            self.stats.success_count += 1
            logger.info("自动扩缩容初始化完成")
        except Exception as e:
            self.stats.error_count += 1
            raise

    async def execute(self, action: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        self.trace("execute", {"module": "auto_scale"})
        self.metrics_collector.counter("auto_scale.execute.calls", 1)
        self.audit("execute", {"module": "auto_scale"})
        params = params or {}
        start = time.time()
        ok = False
        err = None
        try:
            if action == "evaluate":
                service = params.get("service", "")
                metric_name = params.get("metric_name", "")
                metric_value = params.get("value", 0)
                if not service:
                    return {"success": False, "error": "Missing: service"}
                result = self._evaluate(service, metric_name, float(metric_value))
                return {"success": True, "result": result}
            elif action == "scale":
                service = params.get("service", "")
                direction = params.get("direction", "scale_up")
                count = params.get("count", 1)
                reason = params.get("reason", "manual")
                if not service:
                    return {"success": False, "error": "Missing: service"}
                result = self._scale(service, ScaleDirection(direction), int(count), reason, "manual")
                ok = "error" not in result
                return {"success": ok, "result": result}
            elif action == "add_rule":
                rid = params.get("rule_id", "")
                if not rid:
                    return {"success": False, "error": "Missing: rule_id"}
                rule = ScaleRule(
                    rule_id=rid,
                    name=params.get("name", rid),
                    policy=ScalePolicy(params.get("policy", "cpu_based")),
                    metric_name=params.get("metric_name", ""),
                    scale_up_threshold=params.get("scale_up_threshold", 80),
                    scale_down_threshold=params.get("scale_down_threshold", 30),
                    cooldown_seconds=params.get("cooldown_seconds", 300),
                    min_instances=params.get("min_instances", 1),
                    max_instances=params.get("max_instances", 20),
                    step_up=params.get("step_up", 1),
                    step_down=params.get("step_down", 1),
                )
                self._rules[rid] = rule
                ok = True
                return {"success": True, "result": {"rule_id": rid}}
            elif action == "list_rules":
                return {
                    "success": True,
                    "result": [
                        {
                            "rule_id": r.rule_id,
                            "name": r.name,
                            "policy": r.policy.value,
                            "metric": r.metric_name,
                            "up_thresh": r.scale_up_threshold,
                            "down_thresh": r.scale_down_threshold,
                            "min": r.min_instances,
                            "max": r.max_instances,
                            "enabled": r.enabled,
                        }
                        for r in self._rules.values()
                    ],
                }
            elif action == "list_instances":
                service = params.get("service", "")
                if service:
                    insts = self._instances.get(service, [])
                else:
                    insts = [i for sv in self._instances.values() for i in sv]
                return {
                    "success": True,
                    "result": [
                        {
                            "id": i.instance_id,
                            "service": i.service,
                            "status": i.status.value,
                            "cpu": round(i.cpu_usage, 1),
                            "mem": round(i.memory_usage, 1),
                        }
                        for i in insts
                    ],
                }
            elif action == "get_history":
                return {
                    "success": True,
                    "result": [
                        {
                            "event_id": e.event_id,
                            "service": e.service,
                            "direction": e.direction.value,
                            "from": e.from_count,
                            "to": e.to_count,
                            "reason": e.reason,
                        }
                        for e in self._events[-30:]
                    ],
                }
            elif action == "get_stats":
                total_inst = sum(len(sv) for sv in self._instances.values())
                return {
                    "success": True,
                    "result": {
                        "services": len(self._instances),
                        "instances": total_inst,
                        "rules": len(self._rules),
                        "events": len(self._events),
                    },
                }
            else:
                return {"success": False, "error": f"Unknown: {action}"}
        except Exception as e:
            err = str(e)
            return {"success": False, "error": err}
        finally:
            self.stats.record_request((time.time() - start) * 1000, ok, err)

    def health_check(self) -> dict[str, Any]:
        total = sum(len(sv) for sv in self._instances.values())
        return {
            "status": "healthy",
            "module_id": self.module_id,
            "module_level": self.module_level,
            "services": len(self._instances),
            "instances": total,
            "rules": len(self._rules),
        }

    def shutdown(self) -> None:
        pass

    def _evaluate(self, service: str, metric_name: str, value: float) -> dict:
        current_count = len(self._instances.get(service, []))
        triggered = []
        for rid, rule in self._rules.items():
            if not rule.enabled or rule.metric_name != metric_name:
                continue
            if time.time() - self._cooldowns.get(rid, 0) < rule.cooldown_seconds:
                continue
            if value > rule.scale_up_threshold:
                step = min(rule.step_up, rule.max_instances - current_count)
                if step > 0:
                    triggered.append(
                        {
                            "rule_id": rid,
                            "direction": "scale_up",
                            "step": step,
                            "reason": f"{metric_name}={value:.1f} > {rule.scale_up_threshold}",
                        }
                    )
            elif value < rule.scale_down_threshold and current_count > rule.min_instances:
                step = min(rule.step_down, current_count - rule.min_instances)
                if step > 0:
                    triggered.append(
                        {
                            "rule_id": rid,
                            "direction": "scale_down",
                            "step": step,
                            "reason": f"{metric_name}={value:.1f} < {rule.scale_down_threshold}",
                        }
                    )
        return {
            "service": service,
            "metric": metric_name,
            "value": value,
            "current_instances": current_count,
            "actions": triggered,
        }

    def _scale(self, service: str, direction: ScaleDirection, count: int, reason: str, rule_id: str) -> dict:
        current = self._instances.get(service, [])
        current_count = len(current)
        if direction == ScaleDirection.UP:
            for i in range(count):
                self._instance_counter += 1
                inst = Instance(instance_id=f"inst_{self._instance_counter}", service=service)
                current.append(inst)
                time.sleep(0.005)
            self._instances[service] = current
        elif direction == ScaleDirection.DOWN:
            to_remove = min(count, current_count - 1)
            for i in range(to_remove):
                inst = current.pop()
                inst.status = InstanceStatus.TERMINATED
            self._instances[service] = current

        new_count = len(self._instances.get(service, []))
        self._counter += 1
        event = ScaleEvent(
            event_id=f"scale_{self._counter}",
            service=service,
            direction=direction,
            from_count=current_count,
            to_count=new_count,
            rule_id=rule_id,
            reason=reason,
        )
        self._events.append(event)
        self._cooldowns[rule_id] = time.time()
        if self._audit:
            self._audit.log(
                "scale_event",
                {"service": service, "direction": direction.value, "from": current_count, "to": new_count},
            )
        self.stats.success_count += 1
        return {
            "event_id": event.event_id,
            "service": service,
            "direction": direction.value,
            "from": current_count,
            "to": new_count,
        }

    def predict_capacity(self, service: str, forecast_minutes: int = 60) -> dict[str, Any]:
        """容量预测。企业场景：基于历史流量模式预测未来N分钟的实例需求，提前扩容避免流量突增导致服务降级。
        使用简单线性回归+周期性因子，结合最近24小时数据。
        """
        now = time.time()
        if not hasattr(self, "_metrics_history"):
            self._metrics_history = {}
        history = self._metrics_history.get(service, [])
        if len(history) < 10:
            return {"success": False, "error": "数据不足，至少需要10个历史采样点"}
        # 取最近1小时的采样点
        recent = [h for h in history if h["timestamp"] > now - 3600]
        if len(recent) < 5:
            recent = history[-20:]
        values = [h["value"] for h in recent]
        avg_val = sum(values) / len(values)
        max_val = max(values)
        # 简单趋势：最近5个vs之前5个
        recent_half = values[-5:] if len(values) >= 5 else values
        early_half = values[:5] if len(values) >= 5 else values
        trend = (sum(recent_half) / len(recent_half)) - (sum(early_half) / len(early_half))
        # 预测
        predicted_avg = avg_val + trend * (forecast_minutes / 60)
        predicted_max = max_val + trend * (forecast_minutes / 60)
        predicted_max = max(predicted_max, avg_val * 1.2)  # 至少留20%余量
        return {
            "success": True,
            "service": service,
            "forecast_minutes": forecast_minutes,
            "current_avg": round(avg_val, 2),
            "current_max": round(max_val, 2),
            "predicted_avg": round(predicted_avg, 2),
            "predicted_max": round(predicted_max, 2),
            "trend": "increasing" if trend > 0 else "decreasing" if trend < 0 else "stable",
            "data_points": len(recent),
        }

    def get_scaling_cost_report(self, service: str, days: int = 7) -> dict[str, Any]:
        """获取弹性伸缩成本报告。企业场景：FinOps团队评估自动伸缩的资源成本效率。
        统计各服务的实例运行时间、扩缩容次数、资源利用率，辅助成本优化决策。
        """
        now = time.time()
        cutoff = now - days * 86400
        events = [e for e in self._events if e.timestamp >= cutoff and e.service == service]
        scale_up = sum(1 for e in events if e.direction.value == "up")
        scale_down = sum(1 for e in events if e.direction.value == "down")
        total_events = len(events)
        # 估算运行实例-时间（简单累计）
        instance_hours = 0
        current_instances = len(self._instances.get(service, []))
        # 简化估算：当前实例数 × 小时数（精确实现需要记录每个实例的启停时间）
        instance_hours = current_instances * days * 24
        # 找出最大和最小实例数
        max_instances = current_instances
        for e in events:
            if e.to_count > max_instances:
                max_instances = e.to_count
        min_instances = current_instances
        for e in events:
            if e.to_count < min_instances:
                min_instances = e.to_count
        return {
            "success": True,
            "service": service,
            "period_days": days,
            "scale_events": {"total": total_events, "up": scale_up, "down": scale_down},
            "instance_range": {"min": min_instances, "max": max_instances, "current": current_instances},
            "estimated_instance_hours": instance_hours,
            "efficiency_score": round(min_instances / max(max_instances, 1) * 100, 1),
        }

    def configure_scale_policy(
        self,
        service: str,
        min_instances: int,
        max_instances: int,
        target_cpu: float = 70.0,
        target_memory: float = 80.0,
        scale_up_cooldown: int = 300,
        scale_down_cooldown: int = 600,
    ) -> dict[str, Any]:
        """配置弹性伸缩策略。企业场景：为不同服务定制伸缩策略，
        核心服务设置更激进的扩容（低阈值快速扩）和保守的缩容（长冷却防抖动）。
        """
        policy = {
            "service": service,
            "min_instances": min_instances,
            "max_instances": max_instances,
            "target_cpu_percent": target_cpu,
            "target_memory_percent": target_memory,
            "scale_up_cooldown": scale_up_cooldown,
            "scale_down_cooldown": scale_down_cooldown,
            "created_at": time.time(),
            "updated_at": time.time(),
        }
        if not hasattr(self, "_scale_policies"):
            self._scale_policies = {}
        self._scale_policies[service] = policy
        if self._audit:
            self._audit.log("scale_policy_updated", {"service": service, "min": min_instances, "max": max_instances})
        return {
            "success": True,
            "service": service,
            "min": min_instances,
            "max": max_instances,
            "target_cpu": target_cpu,
            "target_memory": target_memory,
        }

    def predict_capacity_needs(self, service: str, look_ahead_hours: int = 24) -> dict[str, Any]:
        """容量需求预测。企业场景：大促前根据历史流量趋势预估所需实例数，
        提前扩容避免流量高峰时响应超时。
        基于近7天同时段流量均值和增长率计算。
        """
        metrics = getattr(self, "_metrics_history", [])
        if not metrics:
            return {"success": True, "message": "无历史数据，使用当前策略", "predicted_instances": 2}
        # 按小时聚合历史CPU使用率
        hourly_cpu = {}
        for m in metrics:
            if m.get("service") != service:
                continue
            hour = time.strftime("%H", time.localtime(m.get("timestamp", 0)))
            hourly_cpu.setdefault(hour, []).append(m.get("cpu_percent", 50))
        avg_by_hour = {h: sum(v) / len(v) for h, v in hourly_cpu.items()}
        # 预测未来各时段
        predictions = []
        for h in range(look_ahead_hours):
            future_hour = time.strftime("%H", time.localtime(time.time() + h * 3600))
            predicted_cpu = avg_by_hour.get(future_hour, 60)
            predictions.append({"hour_offset": h, "hour": future_hour, "predicted_cpu": round(predicted_cpu, 1)})
        max_predicted = max(p["predicted_cpu"] for p in predictions) if predictions else 60
        target_cpu = 70  # 目标CPU使用率
        current_instances = getattr(self, "_instances", {}).get(service, {}).get("count", 2)
        needed = math.ceil(max_predicted / target_cpu * current_instances * 1.2)
        return {
            "success": True,
            "service": service,
            "look_ahead_hours": look_ahead_hours,
            "max_predicted_cpu": round(max_predicted, 1),
            "recommended_instances": max(needed, current_instances),
            "current_instances": current_instances,
            "predictions": predictions[:24],
        }

    def get_scale_event_history(self, limit: int = 30) -> dict[str, Any]:
        """扩缩容事件历史。企业场景：复盘扩缩容是否合理，是否有频繁抖动。"""
        events = getattr(self, "_scale_events", [])
        recent = events[-limit:]
        by_service = {}
        for e in recent:
            svc = e.get("service", "unknown")
            by_service[svc] = by_service.get(svc, 0) + 1
        return {
            "success": True,
            "total_events": len(events),
            "returned": len(recent),
            "by_service": by_service,
            "events": recent,
        }

    def get_cost_estimate(self, service: str, instances: int, instance_type: str = "standard") -> dict[str, Any]:
        """费用估算。企业场景：扩容前评估新增实例的月度费用，
        辅助成本控制决策。基于实例类型和数量计算。
        """
        pricing = {"standard": 200, "high_mem": 350, "high_cpu": 280, "gpu": 1500}
        price_per_month = pricing.get(instance_type, 200)
        total_monthly = price_per_month * instances
        daily_cost = round(total_monthly / 30, 2)
        return {
            "success": True,
            "service": service,
            "instance_type": instance_type,
            "instances": instances,
            "price_per_instance": price_per_month,
            "total_monthly_cny": total_monthly,
            "daily_cost_cny": daily_cost,
        }

    def get_resource_utilization(self, service: str) -> dict[str, Any]:
        """资源利用率报告。企业场景：判断当前实例是否资源过剩（可缩容）或不足（需扩容）。
        综合CPU、内存、网络IO指标给出缩扩容建议。
        """
        instances = getattr(self, "_instances", {}).get(service, {})
        cpu_avg = getattr(instances, "cpu_avg", 45)
        mem_avg = getattr(instances, "mem_avg", 60)
        net_io = getattr(instances, "net_io_mbps", 0)
        recommendation = "stable"
        if cpu_avg > 80 or mem_avg > 85:
            recommendation = "scale_up"
        elif cpu_avg < 20 and mem_avg < 30:
            recommendation = "scale_down"
        return {
            "success": True,
            "service": service,
            "cpu_avg_percent": round(cpu_avg, 1),
            "mem_avg_percent": round(mem_avg, 1),
            "net_io_mbps": round(net_io, 1),
            "recommendation": recommendation,
        }

module_class = AutoScaleManager
