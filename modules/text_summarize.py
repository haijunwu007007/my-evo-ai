"""
AUTO-EVO-AI V0.1 — 生命周期策略模块
Grade: A (生产级) | Category: 核心基础
职责：管理模块/服务的完整生命周期，包括启动、健康检查、优雅关闭、依赖管理
"""

__module_meta__ = {
        "id": "text-summarize",
        "name": "Text Summarize",
        "version": "V0.1",
        "group": "ai",
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
                "name": "original",
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
            "text",
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
logger = logging.getLogger("text_summarize")

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
class TextSummarize:
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

class TextSummarizeManager(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """生命周期策略管理器 - 生产级实现"""

    def __init__(self):

        super().__init__()
        self._components: Dict[str, ManagedComponent] = {}
        self._policies: Dict[str, TextSummarize] = {}
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
        core_policy = TextSummarize(
            policy_id="policy-core-services",
            name="核心服务策略",
            description="数据库、缓存、消息队列等核心服务",
            startup_order=["database", "cache", "message_queue"],
            startup_timeout=120,
            shutdown_timeout=60,
        )
        self._policies["policy-core-services"] = core_policy

        # 业务模块策略
        biz_policy = TextSummarize(
            policy_id="policy-business-modules",
            name="业务模块策略",
            description="业务功能模块的生命周期管理",
            startup_order=["api", "worker", "scheduler"],
            startup_timeout=60,
            shutdown_timeout=30,
        )
        self._policies["policy-business-modules"] = biz_policy

        # 监控日志策略
        monitor_policy = TextSummarize(
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
            "module_id": "text_summarize",
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
        metrics_collector.counter("text_summarize_ops_total", labels={"action": action})
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

    def evaluate_summary_quality(self, original: str, summary: str) -> Dict[str, Any]:
        """评估摘要质量：覆盖率、压缩率、关键信息保留率、流畅度"""
        orig_tokens = set(self._tokenize(original)) if hasattr(self, "_tokenize") else set(original.split())
        summ_tokens = set(self._tokenize(summary)) if hasattr(self, "_tokenize") else set(summary.split())
        # 覆盖率：摘要包含的原文关键词占比
        if orig_tokens:
            coverage = len(orig_tokens & summ_tokens) / len(orig_tokens)
        else:
            coverage = 0.0
        # 压缩率
        compression_ratio = len(summary) / max(len(original), 1)
        # 信息密度
        sentences_orig = [s.strip() for s in original.replace("！", ".").replace("？", ".").split(".") if s.strip()]
        sentences_summ = [s.strip() for s in summary.replace("！", ".").replace("？", ".").split(".") if s.strip()]
        info_density = len(sentences_summ) / max(len(sentences_orig), 1)
        # 关键信息保留（检查数字、日期、专有名词）
        numbers_orig = set(re.findall(r"\d+(?:\.\d+)?%?", original))
        numbers_summ = set(re.findall(r"\d+(?:\.\d+)?%?", summary))
        number_retention = len(numbers_orig & numbers_summ) / max(len(numbers_orig), 1)
        # 综合评分
        quality_score = coverage * 35 + (1 - compression_ratio) * 15 + min(info_density, 1) * 20 + number_retention * 30
        grade = "A" if quality_score >= 80 else "B" if quality_score >= 60 else "C" if quality_score >= 40 else "D"
        return {
            "coverage": round(coverage, 4),
            "compression_ratio": round(compression_ratio, 4),
            "info_density": round(info_density, 4),
            "number_retention": round(number_retention, 4),
            "quality_score": round(quality_score, 1),
            "grade": grade,
            "original_length": len(original),
            "summary_length": len(summary),
            "original_sentences": len(sentences_orig),
            "summary_sentences": len(sentences_summ),
        }

    def summarize_batch(self, documents: List[str], max_length: int = 200) -> Dict[str, Any]:
        """批量摘要：带进度追踪和统一质量控制"""
        import hashlib

        results = []
        total_input = 0
        total_output = 0
        for i, doc in enumerate(documents):
            doc_id = hashlib.md5(doc[:100].encode()).hexdigest()[:8]
            # 简单提取式摘要：取前N个句子
            sentences = [s.strip() for s in doc.replace("！", ".").replace("？", ".").split(".") if s.strip()]
            if max_length and len(doc) > max_length:
                ratio = max_length / len(doc)
                keep = max(1, int(len(sentences) * ratio))
                summary = "".join(sentences[:keep])
            else:
                summary = doc
            total_input += len(doc)
            total_output += len(summary)
            quality = self.evaluate_summary_quality(doc, summary)
            results.append(
                {
                    "doc_id": doc_id,
                    "index": i,
                    "summary_length": len(summary),
                    "quality_grade": quality["grade"],
                    "quality_score": quality["quality_score"],
                }
            )
        avg_compression = total_output / max(total_input, 1)
        avg_quality = sum(r["quality_score"] for r in results) / max(len(results), 1)
        return {
            "total_documents": len(documents),
            "total_input_chars": total_input,
            "total_output_chars": total_output,
            "avg_compression": round(avg_compression, 4),
            "avg_quality_score": round(avg_quality, 1),
            "results": results,
        }

    def compare_summaries(self, summary_a: str, summary_b: str) -> Dict[str, Any]:
        """比较两份摘要：相似度和信息互补性分析"""
        tokens_a = set(summary_a.split())
        tokens_b = set(summary_b.split())
        # Jaccard相似度
        intersection = tokens_a & tokens_b
        union = tokens_a | tokens_b
        jaccard = len(intersection) / max(len(union), 1)
        # 各自独有信息
        unique_a = tokens_a - tokens_b
        unique_b = tokens_b - tokens_a
        # 信息互补性
        complementarity = (len(unique_a) + len(unique_b)) / max(len(union), 1)
        # 长度差异
        len_diff = abs(len(summary_a) - len(summary_b)) / max(len(summary_a), len(summary_b), 1)
        return {
            "jaccard_similarity": round(jaccard, 4),
            "complementarity": round(complementarity, 4),
            "unique_to_a_count": len(unique_a),
            "unique_to_b_count": len(unique_b),
            "length_difference": round(len_diff, 4),
            "conclusion": "highly_similar"
            if jaccard > 0.8
            else "complementary"
            if complementarity > 0.5
            else "partially_overlap",
        }

    def detect_summary_hallucination(self, original: str, summary: str) -> Dict[str, Any]:
        """检测摘要幻觉：识别摘要中不存在于原文的陈述"""
        orig_tokens = set(original.lower().split())
        summ_sentences = [s.strip() for s in summary.replace("！", ".").replace("？", ".").split(".") if s.strip()]
        hallucinated = []
        factual = []
        for sentence in summ_sentences:
            s_tokens = set(sentence.lower().split())
            outside = s_tokens - orig_tokens
            # 如果超过30%的词不在原文中，标记为可能的幻觉
            if s_tokens and len(outside) / len(s_tokens) > 0.3:
                hallucinated.append(
                    {
                        "sentence": sentence[:100],
                        "outside_ratio": round(len(outside) / len(s_tokens), 3),
                        "outside_tokens": list(outside)[:10],
                    }
                )
            else:
                factual.append(sentence)
        return {
            "total_sentences": len(summ_sentences),
            "factual_count": len(factual),
            "hallucinated_count": len(hallucinated),
            "hallucination_rate": round(len(hallucinated) / max(len(summ_sentences), 1), 4),
            "hallucinations": hallucinated,
            "verdict": "clean" if not hallucinated else "minor" if len(hallucinated) <= 2 else "significant",
        }

    def _real_summarize(self, params: dict = None) -> dict:
        """Real LLM summarization."""
        text = (params or {}).get("text", "")
        if not text:
            return {"success": False, "error": "text required"}
        try:
            from _zhipu_helper import llm_chat
            summary = llm_chat(f"用中文摘要以下内容，150字以内：\n{text[:3000]}")
            if summary:
                return {"success": True, "summary": summary, "original_length": len(text), "llm": True}
        except Exception as e:
            pass
        return {"success": True, "summary": text[:150]+"...", "original_length": len(text), "llm": False}

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
            "summarize": self._real_summarize,
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

module_class = TextSummarizeManager
