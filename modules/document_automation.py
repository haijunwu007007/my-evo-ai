"""
AUTO-EVO-AI V0.1 — 生命周期策略模块
Grade: A (生产级) | Category: 核心基础
职责：管理模块/服务的完整生命周期，包括启动、健康检查、优雅关闭、依赖管理
"""

__module_meta__ = {
        "id": "document-automation",
        "name": "Document Automation",
        "version": "V0.1",
        "group": "documents",
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
                "name": "template",
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
            "document",
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
logger = logging.getLogger("document_automation")

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
class DocumentAutomation:
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

class DocumentAutomationManager(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """生命周期策略管理器 - 生产级实现"""

    def __init__(self):

        super().__init__()
        self._components: Dict[str, ManagedComponent] = {}
        self._policies: Dict[str, DocumentAutomation] = {}
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
        core_policy = DocumentAutomation(
            policy_id="policy-core-services",
            name="核心服务策略",
            description="数据库、缓存、消息队列等核心服务",
            startup_order=["database", "cache", "message_queue"],
            startup_timeout=120,
            shutdown_timeout=60,
        )
        self._policies["policy-core-services"] = core_policy

        # 业务模块策略
        biz_policy = DocumentAutomation(
            policy_id="policy-business-modules",
            name="业务模块策略",
            description="业务功能模块的生命周期管理",
            startup_order=["api", "worker", "scheduler"],
            startup_timeout=60,
            shutdown_timeout=30,
        )
        self._policies["policy-business-modules"] = biz_policy

        # 监控日志策略
        monitor_policy = DocumentAutomation(
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
            "module_id": "document_automation",
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
        metrics_collector.counter("document_automation_ops_total", labels={"action": action})
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

    def validate_template_variables(self, template: str, variables: Dict[str, Any]) -> Dict[str, Any]:
        """验证模板变量：检查必填字段、类型匹配、格式约束"""
        # 提取模板中的变量占位符
        required_vars = set(re.findall(r"\{\{(\w+)\}\}", template))
        optional_vars = set(re.findall(r"\{\{(\w+)\?\}\}", template))
        all_template_vars = required_vars | optional_vars
        provided_vars = set(variables.keys())
        # 检查缺失的必填变量
        missing_required = required_vars - provided_vars
        # 检查多余的变量（可能是拼写错误）
        extra_vars = provided_vars - all_template_vars
        # 类型检查
        type_errors = []
        for var_name, value in variables.items():
            if var_name in all_template_vars:
                if "{{" + var_name + ":date}}" in template or "{{" + var_name + "?:date}}" in template:
                    if not isinstance(value, str) or not re.match(r"\d{4}-\d{2}-\d{2}", str(value)):
                        type_errors.append(
                            {"var": var_name, "expected": "date(YYYY-MM-DD)", "got": type(value).__name__}
                        )
                elif "{{" + var_name + ":number}}" in template:
                    if not isinstance(value, (int, float)):
                        type_errors.append({"var": var_name, "expected": "number", "got": type(value).__name__})
                elif "{{" + var_name + ":email}}" in template:
                    if not isinstance(value, str) or "@" not in str(value):
                        type_errors.append({"var": var_name, "expected": "email", "got": str(value)[:30]})
        is_valid = len(missing_required) == 0 and len(type_errors) == 0
        return {
            "valid": is_valid,
            "required_vars": sorted(required_vars),
            "optional_vars": sorted(optional_vars),
            "missing_required": sorted(missing_required),
            "extra_vars": sorted(extra_vars),
            "type_errors": type_errors,
            "fill_rate": round(len(provided_vars & all_template_vars) / max(len(all_template_vars), 1), 4),
        }

    def diff_documents(self, doc_a: str, doc_b: str, label_a: str = "before", label_b: str = "after") -> Dict[str, Any]:
        """文档差异对比：逐段比较，生成结构化变更报告"""
        # 按段落分割
        paragraphs_a = [p.strip() for p in doc_a.split("\n\n") if p.strip()]
        paragraphs_b = [p.strip() for p in doc_b.split("\n\n") if p.strip()]
        set_a = set(paragraphs_a)
        set_b = set(paragraphs_b)
        added = sorted(set_b - set_a)
        removed = sorted(set_a - set_b)
        unchanged = sorted(set_a & set_b)
        # 修改的段落（长度相似但内容不同）
        modified = []
        for p_a in paragraphs_a:
            for p_b in paragraphs_b:
                if p_a not in set_b and p_b not in set_a:
                    similarity = self._paragraph_similarity(p_a, p_b)
                    if similarity > 0.5:
                        modified.append({"from": p_a[:100], "to": p_b[:100], "similarity": round(similarity, 3)})
                        break
        change_ratio = (len(added) + len(removed) + len(modified)) / max(len(set_a | set_b), 1)
        return {
            label_a + "_paragraphs": len(paragraphs_a),
            label_b + "_paragraphs": len(paragraphs_b),
            "added": len(added),
            "removed": len(removed),
            "unchanged": len(unchanged),
            "modified": len(modified),
            "change_ratio": round(change_ratio, 4),
            "severity": "major" if change_ratio > 0.5 else "minor" if change_ratio > 0.1 else "trivial",
        }

    def _paragraph_similarity(self, a: str, b: str) -> float:
        """计算段落相似度"""
        words_a = set(a.lower().split())
        words_b = set(b.lower().split())
        if not words_a or not words_b:
            return 0.0
        return len(words_a & words_b) / len(words_a | words_b)

    def generate_bulk_documents(self, template: str, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """批量生成文档：基于模板和数据列表，带进度和错误收集"""
        results = []
        success_count = 0
        error_count = 0
        for i, record in enumerate(records):
            try:
                filled = template
                for key, value in record.items():
                    filled = filled.replace("{{" + key + "}}", str(value))
                    filled = filled.replace("{{" + key + "?}}", str(value))
                # 检查是否还有未填充的变量
                remaining = re.findall(r"\{\{(\w+)\}\}", filled)
                if remaining:
                    error_count += 1
                    results.append({"index": i, "status": "error", "missing_vars": remaining})
                else:
                    success_count += 1
                    results.append({"index": i, "status": "success", "length": len(filled)})
            except Exception as e:
                error_count += 1
                results.append({"index": i, "status": "error", "error": str(e)})
        return {
            "total": len(records),
            "success": success_count,
            "error": error_count,
            "success_rate": round(success_count / max(len(records), 1), 4),
            "results": results,
        }

    def audit_document_generation(self, records: List[Dict[str, Any]], template_name: str = "") -> Dict[str, Any]:
        """文档生成审计：追踪生成记录，检测异常模式"""
        if not records:
            return {"audit_entries": 0}
        entries = []
        now = time.time()
        for i, rec in enumerate(records):
            user = rec.get("user", rec.get("operator", "system"))
            doc_type = rec.get("type", rec.get("doc_type", "unknown"))
            status = rec.get("status", "success")
            timestamp = rec.get("timestamp", now - (len(records) - i))
            entries.append({"index": i, "user": user, "doc_type": doc_type, "status": status, "timestamp": timestamp})
        # 统计
        by_user = {}
        by_type = {}
        for e in entries:
            by_user[e["user"]] = by_user.get(e["user"], 0) + 1
            by_type[e["doc_type"]] = by_type.get(e["doc_type"], 0) + 1
        success_count = sum(1 for e in entries if e["status"] == "success")
        return {
            "template": template_name,
            "total_entries": len(entries),
            "success_rate": round(success_count / max(len(entries), 1), 4),
            "by_user": by_user,
            "by_type": by_type,
            "top_user": max(by_user, key=by_user.get) if by_user else None,
            "top_type": max(by_type, key=by_type.get) if by_type else None,
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

module_class = DocumentAutomationManager
