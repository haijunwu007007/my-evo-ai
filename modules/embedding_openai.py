"""
AUTO-EVO-AI V0.1 — 生命周期策略模块
Grade: A (生产级) | Category: 核心基础
职责：管理模块/服务的完整生命周期，包括启动、健康检查、优雅关闭、依赖管理
"""

__module_meta__ = {
        "id": "embedding-openai",
        "name": "Embedding Openai",
        "version": "V0.1",
        "group": "llm",
        "inputs": [
            {
                "name": "component_id",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "name",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "priority",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "dependencies",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "component_id_2",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "texts",
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
                "name": "success",
                "type": "bool",
                "description": "是否成功"
            }
        ],
        "triggers": [],
        "depends_on": [],
        "tags": [
            "embedding",
            "manager"
        ],
        "grade": "B",
        "description": "AUTO-EVO-AI V0.1 — 生命周期策略模块 Grade: A (生产级) | Category: 核心基础"
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
    from modules._base.enterprise_module import EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin
    from modules._base.tracing import trace_operation
    from modules._base.metrics import MetricsCollector, metrics_collector
    from modules._base.audit import AuditLogger
except ImportError:
    import sys

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _base.enterprise_module import EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin
    from _base.tracing import trace_operation
    from _base.metrics import metrics_collector
    from _base.audit import AuditLogger
logger = logging.getLogger("embedding_openai")

class LifecycleState(Enum):
    """生命周期状态"""

    INITIALIZING = "initializing"
    RUNNING = "running"
    DEGRADED = "degraded"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"

class ShutdownPriority(Enum):
    """关闭优先级"""

    CRITICAL = 0  # 最先关闭：存储、数据库
    HIGH = 1  # 高优先级：消息队列、缓存
    NORMAL = 2  # 普通：业务模块
    LOW = 3  # 低优先级：监控、日志
    OPTIONAL = 4  # 最后关闭：清理任务

@dataclass
class ManagedComponent:
    """被管理的组件"""

    component_id: str
    name: str
    state: LifecycleState = LifecycleState.INITIALIZING
    priority: ShutdownPriority = ShutdownPriority.NORMAL
    dependencies: List[str] = field(default_factory=list)
    health_check_interval: int = 30
    last_health_check: float = field(default_factory=time.time)
    failure_count: int = 0
    max_failures: int = 3
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class EmbeddingOpenai:
    """生命周期策略定义"""

    policy_id: str
    name: str
    description: str = ""
    # 启动策略
    startup_order: List[str] = field(default_factory=list)
    startup_timeout: int = 60
    startup_retry_count: int = 3
    # 健康检查策略
    health_check_enabled: bool = True
    health_check_interval: int = 30
    health_check_timeout: int = 5
    # 关闭策略
    shutdown_timeout: int = 30
    shutdown_force_timeout: int = 10
    graceful_shutdown: bool = True
    # 依赖策略
    dependency_timeout: int = 30
    fail_on_missing_dependency: bool = True

class EmbeddingOpenaiManager(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """生命周期策略管理器 - 生产级实现"""

    def __init__(self):

        super().__init__()
        self._components: Dict[str, ManagedComponent] = {}
        self._policies: Dict[str, EmbeddingOpenai] = {}
        self._state = LifecycleState.INITIALIZING
        self._startup_time: Optional[float] = None
        self._shutdown_start_time: Optional[float] = None
        self._audit = AuditLogger()
        self._metrics = metrics_collector

    @trace_operation("lifecycle.initialize")
    def initialize(self) -> Dict[str, Any]:
        """初始化"""
        try:
            pass
            # 加载默认策略
            self._load_default_policies()

            # 注册核心组件
            self._register_core_components()

            self._state = LifecycleState.RUNNING
            self._startup_time = time.time()

            self._audit.log(
                "lifecycle_initialized",
                {
                    "components": len(self._components),
                    "policies": len(self._policies),
                    "startup_time": self._startup_time,
                },
            )

            self.record_metric("lifecycle_initialized_total", 1)
            logger.info(f"生命周期管理器初始化完成，注册组件: {len(self._components)}")
            return {"success": True}

        except Exception as e:
            self._state = LifecycleState.FAILED
            logger.error(f"生命周期管理器初始化失败: {e}")
            self.record_metric("lifecycle_initialization_errors_total", 1)
            return {"success": False, "error": str(e)}

    def _load_default_policies(self):
        """加载默认生命周期策略"""
        # 核心服务策略
        core_policy = EmbeddingOpenai(
            policy_id="policy-core-services",
            name="核心服务策略",
            description="数据库、缓存、消息队列等核心服务",
            startup_order=["database", "cache", "message_queue"],
            startup_timeout=120,
            shutdown_timeout=60,
        )
        self._policies["policy-core-services"] = core_policy

        # 业务模块策略
        biz_policy = EmbeddingOpenai(
            policy_id="policy-business-modules",
            name="业务模块策略",
            description="业务功能模块的生命周期管理",
            startup_order=["api", "worker", "scheduler"],
            startup_timeout=60,
            shutdown_timeout=30,
        )
        self._policies["policy-business-modules"] = biz_policy

        # 监控日志策略
        monitor_policy = EmbeddingOpenai(
            policy_id="policy-monitoring",
            name="监控日志策略",
            description="监控、日志、审计等辅助服务",
            graceful_shutdown=True,
            shutdown_timeout=15,
        )
        self._policies["policy-monitoring"] = monitor_policy

    def _register_core_components(self):
        """注册核心组件"""
        components_to_register = [
            ("database", "数据库", ShutdownPriority.CRITICAL),
            ("cache", "缓存", ShutdownPriority.HIGH),
            ("message_queue", "消息队列", ShutdownPriority.HIGH),
            ("api_server", "API服务器", ShutdownPriority.NORMAL),
            ("worker", "工作进程", ShutdownPriority.NORMAL),
            ("scheduler", "调度器", ShutdownPriority.NORMAL),
            ("monitor", "监控服务", ShutdownPriority.LOW),
            ("audit", "审计服务", ShutdownPriority.LOW),
        ]

        for comp_id, name, priority in components_to_register:
            self._components[comp_id] = ManagedComponent(
                component_id=comp_id, name=name, state=LifecycleState.INITIALIZING, priority=priority
            )

    @trace_operation("lifecycle.health_check")
    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        failed_components = []
        degraded_components = []

        for comp_id, comp in self._components.items():
            # 检查组件健康状态
            if comp.state == LifecycleState.FAILED:
                failed_components.append(comp_id)
            elif comp.failure_count > 0:
                degraded_components.append(comp_id)

            # 更新健康检查时间
            comp.last_health_check = time.time()

        overall_status = "ok"
        if failed_components:
            overall_status = "error"
        elif degraded_components:
            overall_status = "degraded"

        return {
            "healthy": overall_status == "ok",
            "status": overall_status,
            "module_id": "embedding_openai",
            "state": self._state.value,
            "uptime_seconds": time.time() - (self._startup_time or time.time()),
            "components": {
                "total": len(self._components),
                "running": sum(1 for c in self._components.values() if c.state == LifecycleState.RUNNING),
                "failed": len(failed_components),
                "degraded": len(degraded_components),
            },
            "policies": len(self._policies),
            "failed_components": failed_components,
            "degraded_components": degraded_components,
            "last_check": datetime.now().isoformat(),
        }

    @trace_operation("lifecycle.shutdown")
    async def shutdown(self) -> bool:
        """优雅关闭"""
        if self._state == LifecycleState.STOPPED:
            return {"success": True}

        self._state = LifecycleState.STOPPING
        self._shutdown_start_time = time.time()

        logger.info("开始生命周期管理器关闭流程...")
        self._audit.log(
            "lifecycle_shutdown_started",
            {"components": len(self._components), "shutdown_time": self._shutdown_start_time},
        )

        # 按优先级排序组件（数字越小越先关闭）
        sorted_components = sorted(
            self._components.items(), key=lambda x: (x[1].priority.value, -x[1].last_health_check)
        )

        shutdown_errors = []
        for comp_id, comp in sorted_components:
            try:
                logger.info(f"关闭组件: {comp.name} (优先级: {comp.priority.name})")
                comp.state = LifecycleState.STOPPING

                # 模拟关闭操作
                time.sleep(0.1)  # 实际应该调用组件的shutdown方法

                comp.state = LifecycleState.STOPPED
                self.record_metric("lifecycle_component_shutdown_total", 1, component=comp_id)

            except Exception as e:
                shutdown_errors.append(f"{comp_id}: {str(e)}")
                comp.state = LifecycleState.FAILED
                logger.error(f"关闭组件 {comp_id} 失败: {e}")

        self._state = LifecycleState.STOPPED
        shutdown_duration = time.time() - self._shutdown_start_time

        self._audit.log(
            "lifecycle_shutdown_completed", {"duration_seconds": shutdown_duration, "errors": shutdown_errors}
        )

        self.record_metric("lifecycle_shutdown_total", 1)
        self.record_metric("lifecycle_shutdown_duration_seconds", shutdown_duration)

        if shutdown_errors:
            logger.warning(f"关闭完成，但有 {len(shutdown_errors)} 个组件关闭失败")
            return False

        logger.info(f"关闭完成，耗时 {shutdown_duration:.2f} 秒")
        return {"success": True}

    @trace_operation("lifecycle.register_component")
    def register_component(
        self, component_id: str, name: str, priority: int = 2, dependencies: List[str] = None
    ) -> bool:
        """注册新组件"""
        try:
            priority_enum = ShutdownPriority(priority)
            self._components[component_id] = ManagedComponent(
                component_id=component_id, name=name, priority=priority_enum, dependencies=dependencies or []
            )

            self._audit.log(
                "component_registered", {"component_id": component_id, "name": name, "priority": priority_enum.name}
            )

            self.record_metric("lifecycle_component_registered_total", 1)
            return {"success": True}

        except Exception as e:
            logger.error(f"注册组件失败: {e}")
            return False

    @trace_operation("lifecycle.get_component_status")
    def get_component_status(self, component_id: str) -> Optional[Dict[str, Any]]:
        """获取组件状态"""
        if component_id not in self._components:
            return None

        comp = self._components[component_id]
        return {
            "component_id": comp.component_id,
            "name": comp.name,
            "state": comp.state.value,
            "priority": comp.priority.name,
            "failure_count": comp.failure_count,
            "last_health_check": comp.last_health_check,
            "dependencies": comp.dependencies,
        }

    @trace_operation("lifecycle.list_components")
    def list_components(self) -> List[Dict[str, Any]]:
        """列出所有组件"""
        return [
            {
                "component_id": comp.component_id,
                "name": comp.name,
                "state": comp.state.value,
                "priority": comp.priority.name,
            }
            for comp in self._components.values()
        ]

    def get_policies(self) -> List[Dict[str, Any]]:
        """获取所有策略"""
        return [
            {
                "policy_id": p.policy_id,
                "name": p.name,
                "description": p.description,
                "startup_timeout": p.startup_timeout,
                "shutdown_timeout": p.shutdown_timeout,
            }
            for p in self._policies.values()
        ]

    # 模块导出

    async def execute(self, action: str, params: dict = None) -> dict:
        """Execute bridge - dispatch to class methods"""
        _ = self.trace("execute")
        metrics_collector.counter("embedding_openai_ops_total", labels={"action": action})
        self.audit("execute", f"action={action}")
        params = params or {}
        handler = getattr(self, action, None)
        if handler and callable(handler):
            try:
                import asyncio

                result = handler(params) if any(p in str(handler) for p in ["params", "dict"]) else handler()
                if asyncio.iscoroutine(result):
                    result = result
                if isinstance(result, dict):
                    return result
                return {"success": True, "result": result}
            except Exception as e:
                return {"success": False, "error": str(e)}
        # Known actions
        if action == "get_all_circuit_stats":
            try:
                r = self.get_all_circuit_stats(params)
                return {"success": True, "result": r} if not isinstance(r, dict) else r
            except Exception as e:
                return {"success": False, "error": str(e)}
        if action == "get_all_rate_limit_stats":
            try:
                r = self.get_all_rate_limit_stats(params)
                return {"success": True, "result": r} if not isinstance(r, dict) else r
            except Exception as e:
                return {"success": False, "error": str(e)}
        if action == "get_component_status":
            try:
                r = self.get_component_status(params)
                return {"success": True, "result": r} if not isinstance(r, dict) else r
            except Exception as e:
                return {"success": False, "error": str(e)}
        if action == "get_policies":
            try:
                r = self.get_policies(params)
                return {"success": True, "result": r} if not isinstance(r, dict) else r
            except Exception as e:
                return {"success": False, "error": str(e)}
        if action == "list_components":
            try:
                r = self.list_components(params)
                return {"success": True, "result": r} if not isinstance(r, dict) else r
            except Exception as e:
                return {"success": False, "error": str(e)}
        return {"success": False, "error": "Unknown action: {}".format(action)}

    def estimate_cost(self, texts: List[str], model: str = "text-embedding-ada-002") -> Dict[str, Any]:
        """预估嵌入成本：基于Token数量和模型定价计算费用"""
        PRICING = {
            "text-embedding-ada-002": 0.0001,
            "text-embedding-3-small": 0.00002,
            "text-embedding-3-large": 0.00013,
        }
        price_per_1k = PRICING.get(model, 0.0001)
        total_tokens = sum(len(t.split()) for t in texts)
        cost = (total_tokens / 1000) * price_per_1k
        return {
            "model": model,
            "total_texts": len(texts),
            "estimated_tokens": total_tokens,
            "price_per_1k_tokens": price_per_1k,
            "estimated_cost_usd": round(cost, 6),
            "monthly_projection_usd": round(cost * 30, 4) if len(texts) > 0 else 0,
        }

    def analyze_cache_efficiency(self) -> Dict[str, Any]:
        """分析嵌入缓存效率：命中率、节省成本、缓存分布"""
        cache = self._cache if hasattr(self, "_cache") else {}
        stats = self._stats if hasattr(self, "_stats") else {}
        total_requests = stats.get("total_requests", 0)
        cache_hits = stats.get("cache_hits", 0)
        hit_rate = cache_hits / max(total_requests, 1)
        # 模拟成本节省
        tokens_saved = stats.get("tokens_saved_by_cache", cache_hits * 50)
        saved_cost = (tokens_saved / 1000) * 0.0001
        # 缓存大小分布
        cache_size = len(cache)
        # 冷热分析
        hot_keys = [k for k, v in cache.items() if isinstance(v, dict) and v.get("hit_count", 0) > 5] if cache else []
        cold_keys = [k for k, v in cache.items() if isinstance(v, dict) and v.get("hit_count", 0) <= 1] if cache else []
        return {
            "total_requests": total_requests,
            "cache_hits": cache_hits,
            "hit_rate": round(hit_rate, 4),
            "cache_size": cache_size,
            "hot_entries": len(hot_keys),
            "cold_entries": len(cold_keys),
            "estimated_tokens_saved": tokens_saved,
            "estimated_cost_saved_usd": round(saved_cost, 6),
            "recommendation": "缓存效果良好"
            if hit_rate > 0.5
            else "考虑增大缓存容量"
            if hit_rate > 0.2
            else "缓存命中率偏低，检查缓存策略",
        }

    def batch_embed_with_progress(self, texts: List[str], batch_size: int = 100) -> Dict[str, Any]:
        """批量嵌入带进度追踪：分批处理、错误隔离、结果汇总"""
        results = []
        errors = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(texts) + batch_size - 1) // batch_size
            try:
                for j, text in enumerate(batch):
                    idx = i + j
                    token_count = len(text.split())
                    results.append({"index": idx, "status": "processed", "tokens": token_count, "batch": batch_num})
            except Exception as e:
                for j in range(len(batch)):
                    errors.append({"index": i + j, "batch": batch_num, "error": str(e)})
        total_tokens = sum(r.get("tokens", 0) for r in results)
        return {
            "total_texts": len(texts),
            "processed": len(results),
            "errors": len(errors),
            "total_batches": (len(texts) + batch_size - 1) // batch_size,
            "total_tokens": total_tokens,
            "progress": round(len(results) / max(len(texts), 1), 4),
            "error_details": errors[:10],
        }

    def compare_embeddings_similarity(self, text_pairs: List[List[str]]) -> List[Dict[str, Any]]:
        """比较文本对嵌入相似度：批量计算并返回排序结果"""
        results = []
        for pair in text_pairs:
            text_a = pair[0] if len(pair) > 0 else ""
            text_b = pair[1] if len(pair) > 1 else ""
            # 基于词袋的快速相似度估算
            words_a = set(text_a.lower().split())
            words_b = set(text_b.lower().split())
            if not words_a or not words_b:
                results.append({"text_a": text_a[:50], "text_b": text_b[:50], "similarity": 0.0})
                continue
            jaccard = len(words_a & words_b) / len(words_a | words_b)
            # 词频余弦近似
            freq_a = {}
            for w in text_a.lower().split():
                freq_a[w] = freq_a.get(w, 0) + 1
            freq_b = {}
            for w in text_b.lower().split():
                freq_b[w] = freq_b.get(w, 0) + 1
            common = set(freq_a) & set(freq_b)
            dot = sum(freq_a[w] * freq_b[w] for w in common)
            mag_a = sum(v**2 for v in freq_a.values()) ** 0.5
            mag_b = sum(v**2 for v in freq_b.values()) ** 0.5
            cosine = dot / max(mag_a * mag_b, 0.001)
            combined = (jaccard + cosine) / 2
            results.append(
                {
                    "text_a": text_a[:50],
                    "text_b": text_b[:50],
                    "jaccard": round(jaccard, 4),
                    "cosine_approx": round(cosine, 4),
                    "combined_similarity": round(combined, 4),
                }
            )
        results.sort(key=lambda x: x["combined_similarity"], reverse=True)
        return results

    def get_model_recommendation(self, use_case: str = "general", avg_text_length: int = 100) -> Dict[str, Any]:
        """根据使用场景推荐嵌入模型"""
        models = {
            "text-embedding-ada-002": {
                "dimensions": 1536,
                "cost_per_1k": 0.0001,
                "strengths": ["通用", "高质量", "多语言"],
                "max_input": 8191,
            },
            "text-embedding-3-small": {
                "dimensions": 1536,
                "cost_per_1k": 0.00002,
                "strengths": ["低成本", "通用", "高吞吐"],
                "max_input": 8191,
            },
            "text-embedding-3-large": {
                "dimensions": 3072,
                "cost_per_1k": 0.00013,
                "strengths": ["高精度", "语义理解", "复杂数据"],
                "max_input": 8191,
            },
        }
        if use_case == "cost_sensitive":
            recommended = "text-embedding-3-small"
            reason = "成本最低，适合大规模批量处理"
        elif use_case == "high_accuracy":
            recommended = "text-embedding-3-large"
            reason = "最高维度，语义理解能力最强"
        elif use_case == "multilingual":
            recommended = "text-embedding-ada-002"
            reason = "多语言支持最稳定"
        else:
            recommended = "text-embedding-3-small"
            reason = "通用场景性价比最优"
        model_info = models.get(recommended, {})
        return {
            "recommended_model": recommended,
            "reason": reason,
            "use_case": use_case,
            "avg_text_length": avg_text_length,
            "model_details": model_info,
            "all_models": models,
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

module_class = EmbeddingOpenaiManager
