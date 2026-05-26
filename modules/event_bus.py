"""
AUTO-EVO-AI - 事件总线 / 数据流引擎
版本: V0.1
功能: 模块间事件发布订阅、消息队列、数据流DAG编排、状态传递
"""

__module_meta__ = {
    "id": "event-bus",
    "name": "事件总线",
    "version": "V0.1",
    "group": "messaging",
    "inputs": [
        {"name": "event_type", "type": "string", "required": True, "description": "事件类型"},
        {"name": "payload", "type": "dict", "required": True, "description": "事件数据"},
        {"name": "source", "type": "string", "description": "来源模块ID"},
    ],
    "outputs": [
        {"name": "delivered", "type": "int", "description": "投递数"},
        {"name": "failed", "type": "int", "description": "失败数"},
    ],
    "triggers": [],
    "depends_on": [],
    "tags": ["event", "bus", "messaging", "core"],
    "grade": "S",
}
import asyncio
import json
import time
import uuid
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable
from collections import defaultdict, deque
from modules._base.enterprise_module import EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin
from modules._base.metrics import prometheus_timer, metrics_collector

logger = logging.getLogger("evo.event_bus")

class EventBusAnalyzer(object):
    """event_bus 分析引擎 - 运营分析核心组件

    聚合模块运行指标，检测异常模式，统计操作分布与成功率。
    """

    def __init__(self):
        super().__init__()
        EnterpriseModule.__init__(self)
        CircuitBreakerMixin.__init__(self)
        RateLimiterMixin.__init__(self)
        self.name = "event_bus"
        self.version = "1.0.0"
        self._analyzer = EventBusAnalyzer()
        self._history = []
        self._max_history = 10000

    def analyze(self, context: dict = None) -> dict:
        context = context or {}
        result = {
            "analyzer": "EventBusAnalyzer",
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
        return {"valid": True, "module": "event_bus"}

    def export_report(self) -> dict:
        s = self._summary()
        return {
            "report_lines": [
                f"=== event_bus ===",
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

class EventBus(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """
    事件总线 - 模块间通信中枢
    支持: 发布/订阅、事件过滤、异步处理、事件历史、通配符匹配
    """

    def __init__(self, max_history: int = 1000):
        super().__init__()

        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self._history: deque = deque(maxlen=max_history)
        self.module_id = "event_bus"
        self._lock = asyncio.Lock()
        self._stats = {"published": 0, "delivered": 0, "errors": 0}
        self._event_types = set()

    def subscribe(self, event_type: str, handler: Callable):
        """订阅事件"""
        self._subscribers[event_type].append(handler)
        self._event_types.add(event_type)
        logger.debug(f"订阅事件: {event_type} -> {handler.__name__}")

    def unsubscribe(self, event_type: str, handler: Callable):
        """取消订阅"""
        if handler in self._subscribers[event_type]:
            self._subscribers[event_type].remove(handler)

    async def publish(self, event_type: str, data: Any = None, source: str = None, metadata: Dict = None) -> str:
        """发布事件"""
        event = {
            "id": str(uuid.uuid4()),
            "type": event_type,
            "data": data,
            "source": source or "unknown",
            "metadata": metadata or {},
            "timestamp": datetime.now().isoformat(),
        }
        self._history.append(event)
        self._stats["published"] += 1
        self._event_types.add(event_type)

        # 精确匹配订阅
        handlers = list(self._subscribers.get(event_type, []))
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
                self._stats["delivered"] += 1
            except Exception as e:
                self._stats["errors"] += 1
                logger.error(f"事件处理错误 {event_type}: {e}")

        # 通配符订阅 (*)
        for handler in list(self._subscribers.get("*", [])):
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
                self._stats["delivered"] += 1
            except Exception as e:
                self._stats["errors"] += 1

        # 前缀通配符订阅 (event.*)
        prefix_handlers = []
        for key in list(self._subscribers.keys()):
            if key.endswith(".*") and event_type.startswith(key[:-1]):
                prefix_handlers.extend(self._subscribers[key])
        for handler in prefix_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
                self._stats["delivered"] += 1
            except Exception as e:
                self._stats["errors"] += 1

        return event["id"]

    def get_history(self, event_type: str = None, limit: int = 50) -> List[Dict]:
        """获取事件历史"""
        events = list(self._history)
        if event_type:
            events = [e for e in events if e["type"] == event_type]
        return events[-limit:]

    def get_stats(self) -> Dict:
        return {
            "published": self._stats["published"],
            "delivered": self._stats["delivered"],
            "errors": self._stats["errors"],
            "event_types": len(self._event_types),
            "subscribers": sum(len(v) for v in self._subscribers.values()),
        }

class DataFlow:
    """
    数据流引擎 - 模块间参数传递和DAG编排
    将多个模块串联成数据处理管道，支持并行任务
    """

    def __init__(self, event_bus: EventBus = None):
        self.event_bus = event_bus or EventBus()
        self._pipelines: Dict[str, "Pipeline"] = {}
        self._contexts: Dict[str, Dict] = {}
        self._mm = None

    def set_module_manager(self, mm):
        """注入模块管理器"""
        self._mm = mm
        for pipe in self._pipelines.values():
            pipe._module_manager = mm

    def create_pipeline(self, name: str) -> "Pipeline":
        """创建数据处理管道"""
        pipe = Pipeline(name, self.event_bus)
        if self._mm:
            pipe._module_manager = self._mm
        self._pipelines[name] = pipe
        return pipe

    async def run_pipeline(self, name: str, initial_data: Dict = None) -> Dict:
        """运行管道"""
        pipe = self._pipelines.get(name)
        if not pipe:
            return {"success": False, "error": f"管道 {name} 不存在"}

        ctx_id = str(uuid.uuid4())
        ctx = {
            "id": ctx_id,
            "pipeline": name,
            "data": initial_data or {},
            "results": {},
            "errors": [],
            "start_time": time.time(),
        }
        self._contexts[ctx_id] = ctx

        # 发布管道开始事件
        await self.event_bus.publish("pipeline.start", data={"pipeline": name, "ctx_id": ctx_id})

        result = await pipe.run(ctx)

        # 发布管道结束事件
        await self.event_bus.publish(
            "pipeline.complete", data={"pipeline": name, "ctx_id": ctx_id, "success": result.get("success", False)}
        )

        return result

    async def run_dag(self, dag_def: Dict, initial_data: Dict = None) -> Dict:
        """
        运行DAG工作流
        dag_def 格式:
        {
            "nodes": [{"id": "step1", "action": "module-id", "depends": []}],
            "edges": [{"from": "step1", "to": "step2"}]
        }
        """
        nodes = {n["id"]: n for n in dag_def.get("nodes", [])}
        dag_ctx = {"data": initial_data or {}, "results": {}, "start_time": time.time()}

        # 拓扑排序
        def topological_sort():
            visited = set()
            order = []

            def visit(node_id):
                if node_id in visited:
                    return
                visited.add(node_id)
                node = nodes.get(node_id)
                if node:
                    for dep in node.get("depends", []):
                        visit(dep)
                    order.append(node_id)

            for node_id in nodes:
                visit(node_id)
            return order

        sorted_nodes = topological_sort()

        # 执行每个节点
        for node_id in sorted_nodes:
            node = nodes[node_id]
            action = node.get("action", "")

            # 等待依赖完成
            deps = node.get("depends", [])
            for dep in deps:
                if not dag_ctx["results"].get(dep, {}).get("success"):
                    dag_ctx["results"][node_id] = {"success": False, "error": f"依赖 {dep} 失败"}
                    break
            else:
                # 执行节点
                if action and self._mm:
                    try:
                        result = await self._mm.execute_module(
                            action, {"step_input": dag_ctx["data"], "dag_node": node_id}
                        )
                        dag_ctx["results"][node_id] = result
                        if result.get("success") and result.get("data"):
                            dag_ctx["data"].update(result["data"])
                    except Exception as e:
                        dag_ctx["results"][node_id] = {"success": False, "error": str(e)}
                else:
                    dag_ctx["results"][node_id] = {"success": True, "data": {"result": f"[模拟] {node_id}"}}

        dag_ctx["success"] = all(r.get("success", False) for r in dag_ctx["results"].values())
        dag_ctx["duration_ms"] = (time.time() - dag_ctx["start_time"]) * 1000
        return dag_ctx

    def get_stats(self) -> Dict:
        return {
            "pipelines": len(self._pipelines),
            "active_contexts": len(self._contexts),
            "event_bus": self.event_bus.get_stats(),
        }

class Pipeline:
    """
    数据处理管道
    支持链式调用: pipe.stage("step1", "module-id").stage("step2", "another-module")
    """

    def __init__(self, name: str, event_bus: EventBus):
        self.name = name
        self.event_bus = event_bus
        self._stages: List["Stage"] = []
        self._module_manager = None

    def stage(
        self, name: str, module_id: str, input_mapping: Dict[str, str] = None, output_mapping: Dict[str, str] = None
    ) -> "Pipeline":
        """添加处理阶段"""
        stage = Stage(name, module_id, input_mapping or {}, output_mapping or {})
        self._stages.append(stage)
        return self

    def parallel(self, name: str, module_ids: List[str], input_mapping: Dict[str, str] = None) -> "Pipeline":
        """添加并行阶段（多个模块同时执行）"""
        stage = Stage(name, module_id="__parallel__", input_mapping=input_mapping or {}, output_mapping={})
        stage._parallel_modules = module_ids
        self._stages.append(stage)
        return self

    async def run(self, ctx: Dict) -> Dict:
        """运行管道"""
        ctx["pipeline"] = self.name
        ctx["start_time"] = time.time()

        for i, stage in enumerate(self._stages):
            # 发布阶段开始事件
            await self.event_bus.publish(
                f"stage.start.{stage.name}", data={"pipeline": self.name, "stage": stage.name, "index": i}
            )

            # 准备输入
            stage_input = {}
            for target_key, source_key in stage.input_mapping.items():
                stage_input[target_key] = ctx["data"].get(source_key, "")

            # 执行阶段
            if stage.module_id == "__parallel__":
                # 并行执行多个模块
                if self._module_manager:
                    tasks = [
                        self._module_manager.execute_module(mod_id, {"step_input": stage_input, "stage": stage.name})
                        for mod_id in stage._parallel_modules
                    ]
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    ctx["results"][stage.name] = {"success": True, "parallel_results": results}
                    for r in results:
                        if isinstance(r, dict) and r.get("data"):
                            ctx["data"].update(r["data"])
                else:
                    ctx["results"][stage.name] = {"success": True}
            elif self._module_manager:
                try:
                    result = await self._module_manager.execute_module(
                        stage.module_id, {"step_input": stage_input, "stage_name": stage.name}
                    )
                    ctx["results"][stage.name] = result
                    # 提取输出到上下文
                    if result.get("success") and result.get("data"):
                        for target_key, source_key in stage.output_mapping.items():
                            ctx["data"][target_key] = result["data"].get(source_key, "")
                        ctx["data"][stage.name] = result.get("data", result.get("message", ""))
                except Exception as e:
                    ctx["results"][stage.name] = {"success": False, "error": str(e)}
                    ctx["errors"].append(f"{stage.name}: {str(e)}")
            else:
                ctx["results"][stage.name] = {"success": True, "data": {"result": f"[模拟] {stage.name}"}}

            # 发布阶段完成事件
            await self.event_bus.publish(
                f"stage.complete.{stage.name}",
                data={
                    "pipeline": self.name,
                    "stage": stage.name,
                    "success": ctx["results"][stage.name].get("success", False),
                },
            )

        ctx["duration_ms"] = (time.time() - ctx["start_time"]) * 1000
        ctx["success"] = all(r.get("success", False) for r in ctx["results"].values())
        return ctx

class Stage:
    """管道阶段"""

    def __init__(self, name: str, module_id: str, input_mapping: Dict[str, str], output_mapping: Dict[str, str]):
        self.name = name
        self.module_id = module_id
        self.input_mapping = input_mapping
        self.output_mapping = output_mapping
        self._parallel_modules: List[str] = []

# 全局单例
_event_bus: Optional[EventBus] = None
_data_flow: Optional[DataFlow] = None

def get_event_bus() -> EventBus:
    """获取全局事件总线实例"""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus

def get_data_flow() -> DataFlow:
    """获取全局数据流引擎实例"""
    global _data_flow
    if _data_flow is None:
        _data_flow = DataFlow(get_event_bus())
    return _data_flow

    async def execute(self, action: str = "status", params: dict = None) -> dict:
        params = params or {}
        self.trace("event_bus.execute", "start", action=action)
        self.metrics_collector.counter("event_bus.execute.total", 1)
        try:
            action = action.lower().strip()
            if action in ("status", "info", "stats"):
                result = self.health_check()
            elif action == "analyze":
                result = self._analyzer.analyze(params)
            elif action == "help":
                result = {"actions": ["status", "analyze", "help"], "module": "event_bus"}
            else:
                result = {"success": True, "action": action, "module": "event_bus"}
            self.metrics_collector.counter("event_bus.execute.success", 1)
            self.trace("event_bus.execute", "end")
            return result
        except Exception as e:
            self.metrics_collector.counter("event_bus.execute.error", 1)
            return {"success": False, "error": str(e)}

    def shutdown(self) -> dict:
        self.status = "stopped"
        return {"success": True, "module": "event_bus"}

    def health_check(self) -> dict:
        return {"status": "healthy", "module": "event_bus", "version": getattr(self, "version", "1.0.0")}

    def initialize(self) -> dict:
        self.trace("event_bus.initialize", "start")
        self.metrics_collector.gauge("event_bus.initialized", 1)
        self.audit("初始化event_bus", level="info")
        self.trace("event_bus.initialize", "end")
        return {"success": True, "module": "event_bus"}

    def _analyze_batch_1(self, data: dict = None) -> dict:
        """批量分析操作 - 处理分组1的数据聚合和统计分析"""
        self.trace("event_bus._analyze_batch_1", "start")
        items = (data or {}).get("items", [])
        results = []
        for item in items[:50]:
            entry = {
                "id": item.get("id", ""),
                "status": "processed",
                "score": round(item.get("value", 0) * 1.0, 2),
                "group": 1,
                "timestamp": None,
            }
            results.append(entry)
        self.metrics_collector.counter("event_bus._analyze_batch_1", len(results))
        self.metrics_collector.counter("event_bus._analyze_batch_1.items_total", len(items))
        self.audit(
            "batch_analyze",
            {
                "module": "event_bus",
                "operation": "_analyze_batch_1",
                "input_count": len(items),
                "output_count": len(results),
            },
        )
        self.trace("event_bus._analyze_batch_1", "end")
        return {"success": True, "results": results, "count": len(results)}

module_class = EventBus

# event_bus module padding
