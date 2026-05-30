# -*- coding: utf-8 -*-
"""
# Grade: A
断点1: 统一模块执行接口 - ModuleAdapter
=========================================
为所有核心模块注入 execute() 标准入口

标准接口规范:
    async def execute(self, task: str, context: Dict = None) -> Dict:
        '''
        统一执行接口
        - task: 任务描述或指令
        - context: 上下文信息（含元数据）
        返回: {"success": bool, "result": Any, "error": str, "metadata": Dict}
        '''
        ...

标准metadata包含:
    - execution_time: float    # 执行耗时（秒）
    - module_id: str          # 模块标识
    - event_published: bool  # 是否发布了事件
    - validated: bool        # 是否经过结果验证

适配策略:
    1. 内部模块(已实现execute) → 直接代理
    2. 旧模块(无execute) → 自动包装execute()方法
    3. 外部执行器 → 映射到对应执行方法
    4. AI网关 → chat() 包装
    5. 自主智能体 → execute_action() 包装
"""

__module_meta__ = {
    "id": "module-adapter",
    "name": "Module Adapter",
    "version": "V0.1",
    "group": "system",
    "inputs": [
        {"name": "coordinator", "type": "string", "required": True, "description": ""},
        {"name": "context", "type": "string", "required": True, "description": ""},
        {"name": "keyword", "type": "string", "required": True, "description": ""},
        {"name": "limit", "type": "string", "required": True, "description": ""},
        {"name": "hours_a", "type": "string", "required": True, "description": ""},
        {"name": "hours_b", "type": "string", "required": True, "description": ""},
    ],
    "outputs": [
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
    ],
    "triggers": [],
    "depends_on": [],
    "tags": ["adapter", "module"],
    "grade": "A",
    "description": "断点1: 统一模块执行接口 - ModuleAdapter =========================================",
}

import asyncio
import logging
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from modules._base.enterprise_module import EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin
from modules._base.metrics import prometheus_timer, metrics_collector

logger = logging.getLogger("evo.module_adapter")

# ============================================================================
# 标准执行结果
# ============================================================================

@dataclass
class ModuleAdapterAnalyzer(object):
    """module_adapter 分析引擎 - 运营分析核心组件

    聚合模块运行指标，检测异常模式，统计操作分布与成功率。
    """

    def __init__(self):
        EnterpriseModule.__init__(self)
        CircuitBreakerMixin.__init__(self)
        RateLimiterMixin.__init__(self)
        self.name = "module_adapter"
        self.version = "1.0.0"
        self._analyzer = ModuleAdapterAnalyzer()
        self._history = []
        self._max_history = 10000

    def analyze(self, context: dict = None) -> dict:
        context = context or {}
        result = {
            "analyzer": "ModuleAdapterAnalyzer",
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
        return {"valid": True, "module": "module_adapter"}

    def export_report(self) -> dict:
        s = self._summary()
        return {
            "report_lines": [
                f"=== module_adapter ===",
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

class StandardResult(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """标准执行结果格式"""

    success: bool
    result: Any = None
    error: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    execution_time: float = 0.0
    module_id: str = ""
    event_published: bool = False
    validated: bool = False

    def to_dict(self) -> Dict:
        return {
            "success": self.success,
            "result": self.result,
            "error": self.error,
            "metadata": self.metadata,
            "execution_time": self.execution_time,
            "module_id": self.module_id,
            "event_published": self.event_published,
            "validated": self.validated,
        }

# ============================================================================
# 适配器注册表
# ============================================================================

class ModuleAdapterRegistry:
    """
    模块适配器注册表
    负责将任意模块适配到标准 execute() 接口
    """

    def __init__(self):
        super().__init__()
        # 适配器函数: module_id -> async function(executor, task, context)
        self._adapters: Dict[str, Callable] = {}
        # 已注册的标准接口模块
        self._standard_modules: Dict[str, Any] = {}
        self._build_default_adapters()

    def _build_default_adapters(self):
        """构建默认适配器"""
        # 这些适配器在 register_adapter() 时由外部注入
        pass

    def register_adapter(self, module_id: str, adapter: Callable):
        """注册适配器"""
        self._adapters[module_id] = adapter
        logger.debug(f"[AdapterRegistry] 注册适配器: {module_id}")

    def register_standard_module(self, module_id: str, module: Any):
        """注册已实现标准接口的模块"""
        self._standard_modules[module_id] = module
        logger.debug(f"[AdapterRegistry] 注册标准模块: {module_id}")

    def get_adapter(self, module_id: str) -> Optional[Callable]:
        """获取适配器"""
        return self._adapters.get(module_id)

    def is_standard_module(self, module_id: str) -> bool:
        """检查是否为标准模块"""
        return module_id in self._standard_modules

    def has_execute_method(self, module: Any) -> bool:
        """检查模块是否有 execute() 方法"""
        return hasattr(module, "execute") and callable(getattr(module, "execute"))

    def get_all_module_ids(self) -> List[str]:
        """获取所有已注册模块ID"""
        return list(set(list(self._adapters.keys()) + list(self._standard_modules.keys())))

# ============================================================================
# 全局注册表单例
# ============================================================================

_adapter_registry: Optional[ModuleAdapterRegistry] = None

def get_adapter_registry() -> ModuleAdapterRegistry:
    """获取全局适配器注册表"""
    global _adapter_registry
    if _adapter_registry is None:
        _adapter_registry = ModuleAdapterRegistry()
    return _adapter_registry

# ============================================================================
# 统一执行器
# ============================================================================

class UnifiedExecutor:
    """
    统一执行器 - 断点1核心
    所有模块通过此执行器调用，保证：
    1. 统一接口（execute方法）
    2. 事件发布（执行前后）
    3. 结果验证（执行后）
    4. 性能追踪
    """

    def __init__(self, coordinator=None):
        self.coordinator = coordinator
        self.registry = get_adapter_registry()
        self._execution_count = 0
        self._setup_system_adapters()

    def _setup_system_adapters(self):
        """设置系统级适配器"""
        reg = self.registry

        # ExternalExecutor 适配器
        reg.register_adapter("external_executor", self._adapt_external_executor)
        # AI Gateway 适配器
        reg.register_adapter("ai-gateway", self._adapt_ai_gateway)
        # Autonomous Agent 适配器
        reg.register_adapter("autonomous-agent", self._adapt_autonomous_agent)
        # Workflow Manager 适配器
        reg.register_adapter("workflow-manager", self._adapt_workflow_manager)
        # Memory Engine 适配器
        reg.register_adapter("memory-engine", self._adapt_memory_engine)

    # ========================================================================
    # 系统级适配器实现
    # ========================================================================

    async def _adapt_external_executor(self, task: str, context: Dict = None) -> StandardResult:
        """适配 ExternalExecutor"""
        import time

        start = time.time()
        context = context or {}

        executor = getattr(self.coordinator, "_external_executor", None)
        if not executor:
            return StandardResult(success=False, error="ExternalExecutor未初始化", module_id="external_executor")

        op = context.get("operation", "")
        params = context.get("params", {})

        try:
            pass
            # 路由到对应方法
            if op == "fs_read" or "读取" in task:
                r = executor.fs_read(params.get("path", ""))
            elif op == "fs_write" or "写入" in task:
                r = executor.fs_write(params.get("path", ""), params.get("content", ""))
            elif op == "cmd" or "命令" in task:
                r = executor.cmd_execute(params.get("command", task))
            elif op == "scrape":
                r = executor.scrape_url(params.get("url", ""))
            elif op == "browser":
                r = await executor.browser_navigate(params.get("url", ""))
            else:
                # 智能路由
                r = await self._auto_route_external(task, executor, params)

            return StandardResult(
                success=r.success,
                result=r.output,
                error=r.error or "",
                metadata=r.metadata or {},
                execution_time=r.execution_time,
                module_id="external_executor",
                event_published=True,
            )
        except Exception as e:
            return StandardResult(
                success=False,
                error=str(e),
                execution_time=time.time() - start,
                module_id="external_executor",
            )

    async def _auto_route_external(self, task: str, executor, params: Dict) -> Any:
        """自动路由到外部执行器方法"""
        # 简单规则路由
        if "文件" in task or "file" in task.lower():
            path = params.get("path", "")
            if path:
                return executor.fs_read(path)
            return executor.fs_write(params.get("path", "."), task)
        if "爬取" in task or "抓取" in task or "scrape" in task.lower():
            return executor.scrape_url(params.get("url", "https://httpbin.org/get"))
        if "浏览器" in task or "browser" in task.lower():
            return await executor.browser_navigate(params.get("url", "https://example.com"))
        if "git" in task.lower() or "npm" in task.lower() or "pip" in task.lower():
            return executor.cmd_execute(task)
        return executor.cmd_execute(task)

    async def _adapt_ai_gateway(self, task: str, context: Dict = None) -> StandardResult:
        """适配 AI Gateway"""
        import time

        start = time.time()
        context = context or {}

        gateway = getattr(self.coordinator, "_ai_gateway", None)
        if not gateway:
            return StandardResult(success=False, error="AIGateway未初始化", module_id="ai-gateway")

        try:
            messages = context.get("messages", [{"role": "user", "content": task}])
            model = context.get("model", gateway.default_model)
            result = gateway.chat(messages=messages, model=model)

            return StandardResult(
                success=True,
                result=result,
                execution_time=time.time() - start,
                module_id="ai-gateway",
                metadata={"model": model, "provider": getattr(gateway, "default_provider", "unknown")},
            )
        except Exception as e:
            return StandardResult(
                success=False,
                error=str(e),
                execution_time=time.time() - start,
                module_id="ai-gateway",
            )

    async def _adapt_autonomous_agent(self, task: str, context: Dict = None) -> StandardResult:
        """适配 Autonomous Agent"""
        import time

        start = time.time()
        context = context or {}

        agent = getattr(self.coordinator, "_autonomous_agent", None)
        if not agent:
            return StandardResult(success=False, error="AutonomousAgent未初始化", module_id="autonomous-agent")

        try:
            action_type = context.get("action_type", "ai_task")
            result = agent.execute_action(
                {
                    "type": action_type,
                    "task": task,
                    "context": context,
                }
            )

            return StandardResult(
                success=result.get("success", False),
                result=result,
                error=result.get("error", ""),
                execution_time=time.time() - start,
                module_id="autonomous-agent",
            )
        except Exception as e:
            return StandardResult(
                success=False,
                error=str(e),
                execution_time=time.time() - start,
                module_id="autonomous-agent",
            )

    async def _adapt_workflow_manager(self, task: str, context: Dict = None) -> StandardResult:
        """适配 Workflow Manager"""
        import time

        start = time.time()
        context = context or {}

        workflow = getattr(self.coordinator, "_workflow", None)
        if not workflow:
            return StandardResult(success=False, error="WorkflowManager未初始化", module_id="workflow-manager")

        try:
            params = context.get("params", {})
            result = await workflow.run_workflow(task, params)

            return StandardResult(
                success=result.get("success", False),
                result=result,
                error=result.get("error", ""),
                execution_time=time.time() - start,
                module_id="workflow-manager",
            )
        except Exception as e:
            return StandardResult(
                success=False,
                error=str(e),
                execution_time=time.time() - start,
                module_id="workflow-manager",
            )

    async def _adapt_memory_engine(self, task: str, context: Dict = None) -> StandardResult:
        """适配 Memory Engine"""
        import time

        start = time.time()
        context = context or {}

        memory = getattr(self.coordinator, "_memory", None)
        if not memory:
            return StandardResult(success=False, error="MemoryEngine未初始化", module_id="memory-engine")

        try:
            op = context.get("operation", "store")
            if op == "store" or "存储" in task:
                result = memory.store(task, context.get("data", {}))
            elif op == "retrieve" or "检索" in task:
                result = memory.retrieve(task)
            elif op == "search" or "搜索" in task:
                result = memory.search(context.get("query", task))
            else:
                result = memory.store(task, {"context": context})

            return StandardResult(
                success=True,
                result=result,
                execution_time=time.time() - start,
                module_id="memory-engine",
            )
        except Exception as e:
            return StandardResult(
                success=False,
                error=str(e),
                execution_time=time.time() - start,
                module_id="memory-engine",
            )

    # ========================================================================
    # 统一执行接口 - 断点1核心
    # ========================================================================

    async def execute(self, module_id: str, task: str, context: Dict = None) -> Dict:
        """
        统一执行接口 - 断点1核心实现
        所有模块调用必须经过此接口

        执行流程:
        1. 发布执行开始事件
        2. 获取适配器
        3. 执行模块
        4. 结果验证
        5. 发布执行完成事件
        6. 返回标准结果
        """
        import time

        start = time.time()
        context = context or {}
        context["_module_id"] = module_id
        context["_timestamp"] = datetime.now().isoformat()

        self._execution_count += 1
        context["_execution_count"] = self._execution_count

        # Step 1: 发布执行开始事件
        await self._publish_start_event(module_id, task, context)

        # Step 2: 获取适配器并执行
        adapter = self.registry.get_adapter(module_id)
        is_standard = self.registry.is_standard_module(module_id)

        if is_standard:
            # 标准模块: 直接调用execute
            module = self.registry._standard_modules.get(module_id)
            result = await self._execute_standard_module(module, task, context)
        elif adapter:
            # 适配器模式
            result = await adapter(task, context)
        else:
            # 降级: 尝试ModuleManager
            result = await self._execute_via_mm(module_id, task, context)

        # Step 3: 结果验证（如果未验证）
        if not result.validated and hasattr(self.coordinator, "_validate_result"):
            validation = self.coordinator._validate_result(module_id, result.to_dict(), task)
            result.validated = True
            result.metadata["_validation"] = validation

        # Step 4: 设置执行时间
        result.execution_time = time.time() - start

        # Step 5: 发布执行完成事件
        await self._publish_complete_event(module_id, result, task)

        return result.to_dict()

    async def _execute_standard_module(self, module: Any, task: str, context: Dict) -> StandardResult:
        """执行已实现标准接口的模块"""
        if self.registry.has_execute_method(module):
            try:
                pass
                # 统一传入 params dict 格式
                params = {"input": task, "context": context}
                r = await module.execute(params)
                if isinstance(r, StandardResult):
                    return r
                if isinstance(r, dict):
                    return StandardResult(
                        success=r.get("success", False),
                        result=r.get("result", r.get("data")),
                        error=r.get("error", ""),
                        metadata=r.get("metadata", {}),
                        module_id=r.get(
                            "module_id", getattr(module, "__name__", getattr(type(module), "__name__", "unknown"))
                        ),
                        event_published=True,
                    )
                return StandardResult(success=True, result=r)
            except Exception as e:
                return StandardResult(success=False, error=str(e))
        return StandardResult(success=False, error=f"模块 {module} 未实现execute()方法")

    async def _execute_via_mm(self, module_id: str, task: str, context: Dict) -> StandardResult:
        """通过ModuleManager执行"""
        mm = getattr(self.coordinator, "_mm", None)
        if mm and hasattr(mm, "execute_module"):
            try:
                r = await mm.execute_module(module_id, {"input": task, "context": context})
                return StandardResult(
                    success=r.get("success", False),
                    result=r.get("result", r.get("data")),
                    error=r.get("error", ""),
                    module_id=module_id,
                )
            except Exception as e:
                return StandardResult(success=False, error=str(e), module_id=module_id)
        return StandardResult(success=False, error=f"无可用执行路径: {module_id}", module_id=module_id)

    async def _publish_start_event(self, module_id: str, task: str, context: Dict):
        """发布执行开始事件"""
        eb = getattr(self.coordinator, "_event_bus", None)
        if eb:
            try:
                await eb.publish(
                    "module.execute.start",
                    data={"module_id": module_id, "task": task[:200], "context_keys": list(context.keys())},
                    source="unified_executor",
                )
            except Exception:
                pass

    async def _publish_complete_event(self, module_id: str, result: StandardResult, task: str):
        """发布执行完成事件"""
        eb = getattr(self.coordinator, "_event_bus", None)
        if eb:
            try:
                await eb.publish(
                    "module.execute.complete",
                    data={
                        "module_id": module_id,
                        "success": result.success,
                        "task": task[:200],
                        "execution_time": result.execution_time,
                    },
                    source="unified_executor",
                )
            except Exception:
                pass

    # ========================================================================
    # 批量执行
    # ========================================================================

    async def execute_batch(self, tasks: List[Dict]) -> List[Dict]:
        """
        批量执行多个任务
        tasks: [{"module_id": str, "task": str, "context": Dict}, ...]
        """
        results = []
        for t in tasks:
            r = await self.execute(t.get("module_id", ""), t.get("task", ""), t.get("context", {}))
            results.append(r)
        return results

    def get_stats(self) -> Dict:
        """获取执行统计"""
        return {
            "total_executions": self._execution_count,
            "registered_adapters": len(self.registry._adapters),
            "standard_modules": len(self.registry._standard_modules),
        }

# ============================================================================
# 便捷函数
# ============================================================================

def create_unified_executor(coordinator=None) -> UnifiedExecutor:
    """创建统一执行器"""
    return UnifiedExecutor(coordinator)

    async def execute(self, action: str = "status", params: dict = None) -> dict:
        params = params or {}
        self.trace("module_adapter.execute", "start", action=action)
        self.metrics_collector.counter("module_adapter.execute.total", 1)
        try:
            action = action.lower().strip()
            if action in ("status", "info", "stats"):
                result = self.health_check()
            elif action == "analyze":
                result = self._analyzer.analyze(params)
            elif action == "help":
                result = {"actions": ["status", "analyze", "help"], "module": "module_adapter"}
            else:
                result = {"success": True, "action": action, "module": "module_adapter"}
            self.metrics_collector.counter("module_adapter.execute.success", 1)
            self.trace("module_adapter.execute", "end")
            return result
        except Exception as e:
            self.metrics_collector.counter("module_adapter.execute.error", 1)
            return {"success": False, "error": str(e)}

    def shutdown(self) -> dict:
        self.status = "stopped"
        return {"success": True, "module": "module_adapter"}

    def health_check(self) -> dict:
        return {"status": "healthy", "module": "module_adapter", "version": getattr(self, "version", "1.0.0")}

    def initialize(self) -> dict:
        self.trace("module_adapter.initialize", "start")
        self.metrics_collector.gauge("module_adapter.initialized", 1)
        self.audit("初始化module_adapter", level="info")
        self.trace("module_adapter.initialize", "end")
        return {"success": True, "module": "module_adapter"}

module_class = UnifiedExecutor
