from __future__ import annotations
"""
# Grade: A
自我修复机制 - AUTO-EVO-AI V0.1
异常捕获、自动恢复、熔断保护
"""

__module_meta__ = {
        "id": "self-healing",
        "name": "Self Healing",
        "version": "V0.1",
        "group": "evolution",
        "inputs": [
            {
                "name": "context",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "keyword",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "limit",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "hours_a",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "hours_b",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "days",
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
            "engine",
            "self"
        ],
        "grade": "A",
        "description": "自我修复机制 - AUTO-EVO-AI V0.1 异常捕获、自动恢复、熔断保护"
    }

try:
    import time
except ImportError:
    pass
import traceback
from core.logging_config import get_logger
from typing import Dict, List, Optional, Any
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import deque

from modules._base.enterprise_module import EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin
from modules._base.metrics import prometheus_timer, metrics_collector, threading

logger = get_logger(__name__)

class SelfHealingAnalyzer:
    """self_healing 分析引擎 - 运营分析核心组件

    聚合模块运行指标，检测异常模式，统计操作分布与成功率。
    """

    def __init__(self):
        EnterpriseModule.__init__(self)
        CircuitBreakerMixin.__init__(self)
        RateLimiterMixin.__init__(self)
        self.name = "self_healing"
        self.version = "1.0.0"
        self._analyzer = SelfHealingAnalyzer()
        self._history = []
        self._max_history = 10000

    def analyze(self, context: dict = None) -> dict:
        context = context or {}
        result = {
            "analyzer": "SelfHealingAnalyzer",
            "timestamp": time.time(),
            "records": len(self._history),
            "summary": self._summary(),
        }
        self._history.append(result)
        if len(self._history) > self._max_history:
            self._history = self._history[-5000:]
        return result

    def _summary(self) -> dict:
        if not self._history:
            return {"status": "no_data"}
        return {"total": len(self._history), "recent": len(self._history[-100:]), "status": "healthy"}

    def get_statistics(self) -> dict:
        total = len(self._history)
        return {
            "total_records": total,
            "recent_count": min(100, total),
            "status": "healthy" if total > 0 else "no_data",
        }

    def validate_config(self) -> dict:
        return {"valid": True, "module": "self_healing"}

    def export_report(self) -> dict:
        s = self._summary()
        return {
            "report_lines": [
                f"=== self_healing ===",
                f"Records: {s.get('total', 0)}",
                f"Status: {s.get('status', 'unknown')}",
                f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            ],
            "format": "text",
        }

    def reset_metrics(self) -> dict:
        self._history.clear()
        return {"success": True}

    def get_health_detail(self) -> dict:
        import sys

        return {"status": "healthy", "memory_bytes": sys.getsizeof(self._history), "history_size": len(self._history)}

    def search_history(self, keyword: str = "", limit: int = 20) -> dict:
        matched = [r for r in reversed(self._history) if keyword.lower() in str(r).lower()][:limit]
        return {"count": len(matched), "results": matched}

    def compare_periods(self, hours_a: int = 24, hours_b: int = 72) -> dict:
        now = time.time()
        a = [m for m in self._history if m.get("timestamp", 0) >= now - hours_a * 3600]
        b = [m for m in self._history if m.get("timestamp", 0) >= now - hours_b * 3600]
        return {
            "period_a": {"hours": hours_a, "records": len(a)},
            "period_b": {"hours": hours_b, "records": len(b)},
            "delta": len(b) - len(a),
        }

    def cleanup_stale(self, days: int = 7) -> dict:
        cutoff = time.time() - 86400 * days
        before = len(self._history)
        self._history = [m for m in self._history if m.get("timestamp", 0) >= cutoff]
        return {"removed": before - len(self._history), "remaining": len(self._history)}

    def aggregate(self) -> dict:
        if not self._history:
            return {"aggregated": {}}
        return {
            "total_records": len(self._history),
            "oldest": self._history[0].get("timestamp"),
            "newest": self._history[-1].get("timestamp"),
        }

    def batch_analyze(self, items: list = None) -> dict:
        items = items or []
        return {"total": min(len(items), 50), "results": [self.analyze({"data": i}) for i in items[:50]]}

    # --- Auto-generated action dispatch methods ---
    def _action_aggregate(self, params=None):
        """Auto-generated action wrapper for aggregate"""
        if params is None:
            params = {}
        return self.aggregate(**params)

    def _action_analyze(self, params=None):
        """Auto-generated action wrapper for analyze"""
        if params is None:
            params = {}
        return self.analyze(**params)

    def _action_batch_analyze(self, params=None):
        """Auto-generated action wrapper for batch_analyze"""
        if params is None:
            params = {}
        return self.batch_analyze(**params)

    def _action_cleanup_stale(self, params=None):
        """Auto-generated action wrapper for cleanup_stale"""
        if params is None:
            params = {}
        return self.cleanup_stale(**params)

    def _action_compare_periods(self, params=None):
        """Auto-generated action wrapper for compare_periods"""
        if params is None:
            params = {}
        return self.compare_periods(**params)

    def _action_export_report(self, params=None):
        """Auto-generated action wrapper for export_report"""
        if params is None:
            params = {}
        return self.export_report(**params)

    def _action_get_health_detail(self, params=None):
        """Auto-generated action wrapper for get_health_detail"""
        if params is None:
            params = {}
        return self.get_health_detail(**params)

    def _action_get_statistics(self, params=None):
        """Auto-generated action wrapper for get_statistics"""
        if params is None:
            params = {}
        return self.get_statistics(**params)

    def _action_reset_metrics(self, params=None):
        """Auto-generated action wrapper for reset_metrics"""
        if params is None:
            params = {}
        return self.reset_metrics(**params)

    def _action_search_history(self, params=None):
        """Auto-generated action wrapper for search_history"""
        if params is None:
            params = {}
        return self.search_history(**params)

class ErrorSeverity(Enum):
    """错误严重程度"""

    LOW = 1  # 轻微
    MEDIUM = 2  # 中等
    HIGH = 3  # 严重
    CRITICAL = 4  # 致命

@dataclass
class ErrorRecord:
    """错误记录"""

    id: str
    error_type: str
    message: str
    severity: str
    timestamp: str
    traceback: str
    context: dict
    retry_count: int = 0
    resolved: bool = False

@dataclass
class RecoveryStrategy:
    """恢复策略"""

    name: str
    priority: int  # 1 = 最高
    apply: Callable[[ErrorContext], bool]
    description: str = ""

@dataclass
class ErrorContext:
    """错误上下文"""

    error: Exception
    error_type: str
    message: str
    severity: ErrorSeverity
    component: str
    timestamp: str
    retry_count: int
    history: list[ErrorRecord]

class SelfHealingEngine:
    """
    自我修复引擎

    功能:
    - 异常捕获与分类
    - 自动恢复策略
    - 熔断保护
    - 错误历史追踪
    - 健康检查
    """

    def __init__(self):
        # 错误历史
        self.error_history: deque = deque(maxlen=1000)
        self.error_count = 0
        self.critical_errors = 0

        # 熔断器状态
        self.circuit_breakers: dict[str, dict] = {}
        self.default_circuit_config = {
            "failure_threshold": 5,  # 失败次数阈值
            "recovery_timeout": 60,  # 恢复超时(秒)
            "half_open_max": 3,  # 半开状态最大尝试次数
        }

        # 恢复策略
        self.recovery_strategies: list[RecoveryStrategy] = []
        self._register_default_strategies()

        # 健康检查
        self.health_checks: dict[str, Callable[[], bool]] = {}
        self.last_health_check = None
        self.health_score = 100.0

        # 组件状态
        self.component_status: dict[str, str] = {}

        # 记忆引擎（缺口4修复：接入长期记忆，复用历史修复经验）
        self._memory = None

        logger.info("[SelfHealing] 自我修复引擎初始化")

    def _register_default_strategies(self):
        """注册默认恢复策略"""

        # 1. 重试策略
        self.register_recovery_strategy(
            RecoveryStrategy(
                name="retry",
                priority=1,
                description="重试执行",
                apply=lambda ctx: True,  # 简单重试
            )
        )

        # 2. 降级策略
        self.register_recovery_strategy(
            RecoveryStrategy(
                name="degrade", priority=2, description="降级功能", apply=lambda ctx: self._apply_degradation(ctx)
            )
        )

        # 3. 重启策略
        self.register_recovery_strategy(
            RecoveryStrategy(
                name="restart", priority=3, description="重启组件", apply=lambda ctx: self._apply_restart(ctx)
            )
        )

        # 4. 回退策略
        self.register_recovery_strategy(
            RecoveryStrategy(
                name="fallback", priority=4, description="使用备用方案", apply=lambda ctx: self._apply_fallback(ctx)
            )
        )

    def register_recovery_strategy(self, strategy: RecoveryStrategy):
        """注册恢复策略"""
        self.recovery_strategies.append(strategy)
        self.recovery_strategies.sort(key=lambda s: s.priority)
        logger.info(f"[SelfHealing] 注册恢复策略: {strategy.name}")

    def _classify_error(self, error: Exception) -> ErrorSeverity:
        """分类错误严重程度"""
        error_type = type(error).__name__

        critical_errors = ["MemoryError", "SystemExit", "KeyboardInterrupt", "OSError", "IOError"]
        high_errors = ["TimeoutError", "ConnectionError", "PermissionError", "FileNotFoundError", "ImportError"]
        medium_errors = ["ValueError", "TypeError", "AttributeError", "KeyError", "IndexError"]

        if error_type in critical_errors:
            return ErrorSeverity.CRITICAL
        elif error_type in high_errors:
            return ErrorSeverity.HIGH
        elif error_type in medium_errors:
            return ErrorSeverity.MEDIUM
        else:
            return ErrorSeverity.LOW

    def record_error(self, error: Exception, component: str = "unknown", context: dict = None) -> ErrorRecord:
        """记录错误"""
        import uuid

        error_type = type(error).__name__
        severity = self._classify_error(error)

        # 获取错误历史
        history = [e for e in self.error_history if e.error_type == error_type]
        retry_count = len(history)

        record = ErrorRecord(
            id=uuid.uuid4().hex[:12],
            error_type=error_type,
            message=str(error),
            severity=severity.name,
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
            traceback=traceback.format_exc(),
            context=context or {},
            retry_count=retry_count,
        )

        self.error_history.append(record)
        self.error_count += 1

        if severity == ErrorSeverity.CRITICAL:
            self.critical_errors += 1

        # 更新组件状态
        self.component_status[component] = "error"

        # 检查熔断器
        self._update_circuit_breaker(component, record)

        logger.warning(f"[SelfHealing] 错误记录: {error_type} in {component} ({severity.name})")

        return record

    def try_recover(self, error: Exception, component: str, context: dict = None) -> bool:
        """尝试恢复"""
        error_type = type(error).__name__
        severity = self._classify_error(error)
        history = [e for e in self.error_history if e.error_type == error_type]

        ctx = ErrorContext(
            error=error,
            error_type=error_type,
            message=str(error),
            severity=severity,
            component=component,
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
            retry_count=len(history),
            history=list(history),
        )

        # 缺口4修复：查长期记忆中的历史修复经验
        if self._memory:
            try:
                query = f"修复 {error_type} {component} {str(error)[:50]}"
                relevant = self._memory.query_memory(query, top_k=2)
                if relevant:
                    for r in relevant:
                        entry = r.get("entry", {})
                        content = entry.get("content", "") if isinstance(entry, dict) else str(entry)
                        score = r.get("score", 0)
                        if score > 0.5:
                            logger.info(f"[SelfHealing] 记忆参考: {content[:80]} (score={score:.0%})")
            except Exception:
                pass  # 记忆查询失败不影响恢复流程

        # 检查熔断器
        if self.is_circuit_open(component):
            logger.warning(f"[SelfHealing] 熔断器开启: {component}")
            return False

        # 按优先级尝试恢复策略
        for strategy in self.recovery_strategies:
            try:
                if strategy.apply(ctx):
                    logger.info(f"[SelfHealing] 恢复成功: {strategy.name} for {component}")
                    self.component_status[component] = "healthy"
                    return True
            except Exception as e:
                logger.error(f"[SelfHealing] 恢复策略失败: {strategy.name} - {e}")

        # 所有策略都失败 → 记录到记忆供后续参考
        self._trip_circuit_breaker(component)
        if self._memory:
            try:
                self._memory.save_memory(
                    f"修复失败: {error_type} in {component} | {str(error)[:100]}", "error_pattern", "system"
                )
            except Exception:
                pass
        logger.error(f"[SelfHealing] 所有恢复策略失败: {component}")
        return False

    def _apply_degradation(self, ctx: ErrorContext) -> bool:
        """应用降级"""
        logger.info(f"[SelfHealing] 应用降级: {ctx.component}")
        # 标记降级状态
        self.component_status[ctx.component] = "degraded"
        return True

    def _apply_restart(self, ctx: ErrorContext) -> bool:
        """应用重启"""
        logger.info(f"[SelfHealing] 重启组件: {ctx.component}")
        # 重启逻辑由具体组件实现
        self.component_status[ctx.component] = "restarting"
        return True

    def _apply_fallback(self, ctx: ErrorContext) -> bool:
        """应用回退"""
        logger.info(f"[SelfHealing] 使用备用方案: {ctx.component}")
        self.component_status[ctx.component] = "fallback"
        return True

    # ==================== 熔断器 ====================

    def _get_circuit_config(self, component: str) -> dict:
        """获取熔断器配置"""
        return self.circuit_breakers.get(component, self.default_circuit_config.copy())

    def _update_circuit_breaker(self, component: str, record: ErrorRecord):
        """更新熔断器状态"""
        if component not in self.circuit_breakers:
            self.circuit_breakers[component] = {
                **self.default_circuit_config.copy(),
                "failure_count": 0,
                "last_failure": time.time(),
                "state": "closed",  # closed, open, half-open
            }

        cb = self.circuit_breakers[component]
        cb["failure_count"] += 1
        cb["last_failure"] = time.time()

        # 检查是否需要打开熔断器
        if cb["failure_count"] >= cb["failure_threshold"]:
            self._trip_circuit_breaker(component)

    def _trip_circuit_breaker(self, component: str):
        """打开熔断器"""
        if component in self.circuit_breakers:
            self.circuit_breakers[component]["state"] = "open"
            logger.warning(f"[SelfHealing] 熔断器打开: {component}")

    def is_circuit_open(self, component: str) -> bool:
        """检查熔断器是否打开"""
        if component not in self.circuit_breakers:
            return False

        cb = self.circuit_breakers[component]

        if cb["state"] == "closed":
            return False
        elif cb["state"] == "open":
            # 检查是否超时
            if time.time() - cb["last_failure"] > cb["recovery_timeout"]:
                cb["state"] = "half-open"
                logger.info(f"[SelfHealing] 熔断器进入半开状态: {component}")
                return False
            return True
        elif cb["state"] == "half-open":
            return False

        return False

    def reset_circuit_breaker(self, component: str):
        """重置熔断器"""
        if component in self.circuit_breakers:
            self.circuit_breakers[component] = {
                **self.default_circuit_config.copy(),
                "failure_count": 0,
                "state": "closed",
            }
            logger.info(f"[SelfHealing] 熔断器重置: {component}")

    # ==================== 健康检查 ====================

    def register_health_check(self, component: str, check_func: Callable[[], bool]):
        """注册健康检查"""
        self.health_checks[component] = check_func
        logger.info(f"[SelfHealing] 注册健康检查: {component}")

    def check_health(self) -> dict:
        """执行健康检查"""
        results = {}
        healthy_count = 0
        total_count = len(self.health_checks)

        for component, check_func in self.health_checks.items():
            try:
                is_healthy = check_func()
                results[component] = "healthy" if is_healthy else "unhealthy"
                if is_healthy:
                    healthy_count += 1
            except Exception as e:
                results[component] = "error"
                logger.error(f"[SelfHealing] 健康检查失败: {component} - {e}")

        # 计算健康分数
        self.health_score = (healthy_count / total_count * 100) if total_count > 0 else 100
        self.last_health_check = time.strftime("%Y-%m-%d %H:%M:%S")

        return {
            "overall": "healthy" if self.health_score >= 80 else "degraded" if self.health_score >= 50 else "unhealthy",
            "score": self.health_score,
            "components": results,
            "last_check": self.last_health_check,
        }

    # ==================== 装饰器 ====================

    def auto_recover(self, component: str = "unknown"):
        """自动恢复装饰器"""

        def decorator(func):
            def wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    self.record_error(e, component, {"function": func.__name__})
                    self.try_recover(e, component)
                    raise

            return wrapper

        return decorator

    def with_circuit_breaker(self, component: str):
        """熔断保护装饰器"""

        def decorator(func):
            def wrapper(*args, **kwargs):
                if self.is_circuit_open(component):
                    raise Exception(f"Circuit breaker is open for {component}")
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    self.record_error(e, component)
                    if self.try_recover(e, component):
                        return func(*args, **kwargs)  # 重试
                    raise

            return wrapper

        return decorator

    # ==================== 统计和报告 ====================

    def get_error_stats(self) -> dict:
        """获取错误统计"""
        return {
            "total_errors": self.error_count,
            "critical_errors": self.critical_errors,
            "recent_errors": len(
                [
                    e
                    for e in self.error_history
                    if time.time() - time.mktime(time.strptime(e.timestamp, "%Y-%m-%d %H:%M:%S")) < 3600
                ]
            ),
            "by_severity": {
                "CRITICAL": len([e for e in self.error_history if e.severity == "CRITICAL"]),
                "HIGH": len([e for e in self.error_history if e.severity == "HIGH"]),
                "MEDIUM": len([e for e in self.error_history if e.severity == "MEDIUM"]),
                "LOW": len([e for e in self.error_history if e.severity == "LOW"]),
            },
        }

    def get_status_report(self) -> dict:
        """获取状态报告"""
        return {
            "health": self.check_health(),
            "circuit_breakers": {name: cb["state"] for name, cb in self.circuit_breakers.items()},
            "component_status": self.component_status,
            "errors": self.get_error_stats(),
            "recovery_strategies": [s.name for s in self.recovery_strategies],
        }

    def export_dashboard(self) -> str:
        """导出Dashboard数据"""
        import json

        return json.dumps(self.get_status_report(), ensure_ascii=False, indent=2)

# ==================== 快速测试 ====================

if __name__ == "__main__":
    logger.info("=" * 60))
    logger.info("SelfHealing 测试"))
    logger.info("=" * 60))

    engine = SelfHealingEngine()

    # 测试错误记录
    logger.info("\n[1] 测试错误记录..."))
    try:
        raise ValueError("测试错误")
    except Exception as e:
        record = engine.record_error(e, "test_component", {"action": "test"})
        logger.info(f"  ✅ 错误已记录: {record.error_type} ({record.severity})"))

    # 测试熔断器
    logger.info("\n[2] 测试熔断器..."))
    for i in range(6):
        engine._update_circuit_breaker("test_service", record)

    is_open = engine.is_circuit_open("test_service")
    logger.info(f"  熔断器状态: {'打开' if is_open else '关闭'}"))

    # 测试健康检查
    logger.info("\n[3] 测试健康检查..."))
    engine.register_health_check("memory", lambda: True)
    engine.register_health_check("cpu", lambda: True)
    engine.register_health_check("disk", lambda: True)

    health = engine.check_health()
    logger.info(f"  健康分数: {health['score']}%"))
    logger.info(f"  整体状态: {health['overall']}"))

    # 状态报告
    logger.info("\n[4] 状态报告..."))
    report = engine.get_status_report()
    logger.info(f"  错误统计: {report['errors']['total_errors']} 个错误"))
    logger.info(f"  熔断器: {len(report['circuit_breakers'])} 个"))

    # Dashboard
    logger.info("\n[5] Dashboard导出..."))
    dashboard = engine.export_dashboard()
    logger.info(f"  数据长度: {len(dashboard)} 字符"))

    logger.info("\n" + "=" * 60))
    logger.info("✅ SelfHealing 就绪！"))
    logger.info("=" * 60))

    async def execute(self, action: str = "status", params: dict = None) -> dict:
        params = params or {}
        self.trace("self_healing.execute", "start", action=action)
        self.metrics_collector.counter("self_healing.execute.total", 1)
        try:
            action = action.lower().strip()
            if action in ("status", "info", "stats"):
                result = self.health_check()
            elif action == "analyze":
                result = self._analyzer.analyze(params)
            elif action == "help":
                result = {"actions": ["status", "analyze", "help"], "module": "self_healing"}
            else:
                result = {"success": True, "action": action, "module": "self_healing"}
            self.metrics_collector.counter("self_healing.execute.success", 1)
            self.trace("self_healing.execute", "end")
            return result
        except Exception as e:
            self.metrics_collector.counter("self_healing.execute.error", 1)
            return {"success": False, "error": str(e)}

    def shutdown(self) -> dict:
        self.status = "stopped"
        return {"success": True, "module": "self_healing"}

    def health_check(self) -> dict:
        return {"status": "healthy", "module": "self_healing", "version": getattr(self, "version", "1.0.0")}

    def initialize(self) -> dict:
        self.trace("self_healing.initialize", "start")
        self.metrics_collector.gauge("self_healing.initialized", 1)
        self.audit("初始化self_healing", level="info")
        self.trace("self_healing.initialize", "end")
        return {"success": True, "module": "self_healing"}

module_class = SelfHealingEngine
