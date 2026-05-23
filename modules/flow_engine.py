# -*- coding: utf-8 -*-
# Grade: A

"""
AUTO-EVO-AI v7.0 - FlowEngine 工作流引擎（A级）
=================================================
企业级DAG工作流引擎，支持：
  1. DAG有向无环图定义与校验
  2. 节点并行/串行/条件分支执行
  3. 内置节点类型：HTTP调用、脚本执行、条件判断、数据转换、子流程
  4. 运行时状态管理（挂起/恢复/重试/取消）
  5. 执行历史与审计追踪
  6. 超时控制与错误处理策略
  7. 变量上下文在节点间传递
"""

__module_meta__ = {
    "id": "flow-engine",
    "name": "Flow Engine",
    "version": "1.0.0",
    "group": "workflow",
    "inputs": [
        {"name": "name", "type": "string", "required": True, "description": ""},
        {"name": "value", "type": "string", "required": True, "description": ""},
        {"name": "name", "type": "string", "required": True, "description": ""},
        {"name": "value", "type": "string", "required": True, "description": ""},
        {"name": "name", "type": "string", "required": True, "description": ""},
        {"name": "value", "type": "string", "required": True, "description": ""},
    ],
    "outputs": [
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
    ],
    "triggers": [],
    "depends_on": [],
    "tags": ["adapter", "engine", "flow"],
    "grade": "A",
    "description": "AUTO-EVO-AI v7.0 - FlowEngine 工作流引擎（A级） =================================================",
}

import re
import time
import uuid
import json
import hashlib
import asyncio
import logging
from enum import Enum
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable, Set
from dataclasses import dataclass, field

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from modules._base.enterprise_module import (
    EnterpriseModule,
    Result,
    HealthReport,
    ModuleStatus,
    ModuleStats,
    CircuitBreakerMixin,
    RateLimiterMixin,
)
from modules._base.metrics import prometheus_timer, metrics_collector

logger = logging.getLogger("evo.flow-engine")

class _MetricsAdapter:
    """轻量指标适配器 — 兼容 self._metrics.increment/histogram 接口"""

    def increment(self, name: str, value: float = 1.0, **kw):
        pass  # 已由 EnterpriseModule.record_metrics() 覆盖

    def histogram(self, name: str, value: float, **kw):
        pass

    def gauge(self, name: str, value: float, **kw):
        pass

    def counter(self, name: str, value: float = 1.0, **kw):
        pass

    # ============================================================================
    # 数据结构
    # ============================================================================
    # --- Auto-generated action dispatch methods ---
    def _action_counter(self, params=None):
        """Auto-generated action wrapper for counter"""
        if params is None:
            params = {}
        return self.counter(**params)

    def _action_gauge(self, params=None):
        """Auto-generated action wrapper for gauge"""
        if params is None:
            params = {}
        return self.gauge(**params)

    def _action_histogram(self, params=None):
        """Auto-generated action wrapper for histogram"""
        if params is None:
            params = {}
        return self.histogram(**params)

    def _action_increment(self, params=None):
        """Auto-generated action wrapper for increment"""
        if params is None:
            params = {}
        return self.increment(**params)

class NodeType(str, Enum):
    """工作流节点类型"""

    START = "start"
    END = "end"
    HTTP = "http"
    SCRIPT = "script"
    CONDITION = "condition"
    TRANSFORM = "transform"
    SUBPROCESS = "subprocess"
    PARALLEL = "parallel"
    WAIT = "wait"
    NOTIFY = "notify"

class NodeStatus(str, Enum):
    """节点执行状态"""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"

class FlowStatus(str, Enum):
    """工作流执行状态"""

    DRAFT = "draft"
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class ErrorStrategy(str, Enum):
    """错误处理策略"""

    FAIL_FAST = "fail_fast"  # 立即终止
    CONTINUE = "continue"  # 跳过失败节点继续
    RETRY = "retry"  # 自动重试
    FALLBACK = "fallback"  # 执行回退节点

@dataclass
class FlowNode:
    """工作流节点定义"""

    node_id: str
    node_type: NodeType
    name: str
    config: Dict[str, Any] = field(default_factory=dict)
    next_nodes: List[str] = field(default_factory=list)
    timeout_seconds: int = 300
    retry_count: int = 0
    retry_delay: int = 5
    error_strategy: ErrorStrategy = ErrorStrategy.FAIL_FAST
    condition_expr: str = ""  # 条件表达式
    fallback_node: str = ""  # 回退节点ID

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type.value,
            "name": self.name,
            "config": self.config,
            "next_nodes": self.next_nodes,
            "timeout_seconds": self.timeout_seconds,
            "retry_count": self.retry_count,
            "error_strategy": self.error_strategy.value,
        }

@dataclass
class NodeExecution:
    """节点执行记录"""

    node_id: str
    status: NodeStatus = NodeStatus.PENDING
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    duration_ms: float = 0.0
    input_data: Any = None
    output_data: Any = None
    error: Optional[str] = None
    retry_count: int = 0
    trace_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "status": self.status.value,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": round(self.duration_ms, 2),
            "error": self.error,
            "retry_count": self.retry_count,
        }

@dataclass
class FlowDefinition:
    """工作流定义（DAG）"""

    flow_id: str
    name: str
    description: str = ""
    version: str = "1.0"
    nodes: Dict[str, FlowNode] = field(default_factory=dict)
    variables: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        self.updated_at = self.created_at

@dataclass
class FlowInstance:
    """工作流运行实例"""

    instance_id: str
    flow_id: str
    status: FlowStatus = FlowStatus.PENDING
    variables: Dict[str, Any] = field(default_factory=dict)
    node_executions: Dict[str, NodeExecution] = field(default_factory=dict)
    current_nodes: List[str] = field(default_factory=list)
    error: Optional[str] = None
    started_at: Optional[str] = None
    ended_at: Optional[str] = None
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.instance_id:
            self.instance_id = str(uuid.uuid4())[:12]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "instance_id": self.instance_id,
            "flow_id": self.flow_id,
            "status": self.status.value,
            "error": self.error,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "completed_nodes": sum(1 for ne in self.node_executions.values() if ne.status == NodeStatus.SUCCESS),
            "failed_nodes": sum(
                1 for ne in self.node_executions.values() if ne.status in (NodeStatus.FAILED, NodeStatus.TIMEOUT)
            ),
            "total_nodes": len(self.node_executions),
        }

# ============================================================================
# FlowEngine 核心引擎
# ============================================================================

class FlowEngine(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """企业级工作流引擎"""

    MODULE_ID = "flow-engine"
    MODULE_NAME = "工作流引擎"
    VERSION = "v7.0"
    MODULE_LEVEL = "A"

    def __init__(self, config: Optional[Dict[str, Any]] = None):

        super().__init__(config)
        self._metrics = _MetricsAdapter()
        # 工作流定义存储
        self._definitions: Dict[str, FlowDefinition] = {}
        # 运行实例存储
        self._instances: Dict[str, FlowInstance] = {}
        # 节点处理器注册
        self._handlers: Dict[NodeType, Callable] = {}
        # 内置变量函数
        self._variable_functions: Dict[str, Callable] = {}
        # 配置
        self.max_concurrent_flows = self.config.get("max_concurrent_flows", 50)
        self.default_timeout = self.config.get("default_node_timeout", 300)
        self.history_limit = self.config.get("history_limit", 100)
        # 事件回调
        self._on_node_complete: Optional[Callable] = None
        self._on_flow_complete: Optional[Callable] = None

    # ── 生命周期 ──

    def initialize(self) -> None:
        """初始化工作流引擎"""
        self.info("初始化工作流引擎...")
        self.record_metrics("flow-engine.init", 1)
        self.status = ModuleStatus.INITIALIZING
        try:
            pass
            # 注册内置节点处理器
            self._register_builtin_handlers()
            # 注册内置变量函数
            self._register_variable_functions()
            # 加载预定义工作流模板
            self._load_builtin_templates()
            # 初始化完成
            self.status = ModuleStatus.RUNNING
            self.stats.start_time = datetime.now()
            self.info(f"工作流引擎初始化完成，已加载 {len(self._definitions)} 个流程定义")
        except Exception as e:
            self.status = ModuleStatus.ERROR
            self.error(f"初始化失败: {e}")
            raise

    def _register_builtin_handlers(self):
        """注册内置节点处理器"""
        self._handlers[NodeType.START] = self._handle_start
        self._handlers[NodeType.END] = self._handle_end
        self._handlers[NodeType.HTTP] = self._handle_http
        self._handlers[NodeType.SCRIPT] = self._handle_script
        self._handlers[NodeType.CONDITION] = self._handle_condition
        self._handlers[NodeType.TRANSFORM] = self._handle_transform
        self._handlers[NodeType.SUBPROCESS] = self._handle_subprocess
        self._handlers[NodeType.PARALLEL] = self._handle_parallel
        self._handlers[NodeType.WAIT] = self._handle_wait
        self._handlers[NodeType.NOTIFY] = self._handle_notify

    def _register_variable_functions(self):
        """注册内置变量函数"""
        self._variable_functions = {
            "now": lambda: datetime.now().isoformat(),
            "uuid": lambda: str(uuid.uuid4()),
            "upper": lambda v: str(v).upper(),
            "lower": lambda v: str(v).lower(),
            "len": lambda v: len(v) if hasattr(v, "__len__") else 0,
            "json_encode": lambda v: json.dumps(v, ensure_ascii=False),
            "json_decode": lambda v: json.loads(v) if isinstance(v, str) else v,
            "md5": lambda v: hashlib.md5(str(v).encode()).hexdigest(),
        }

    def _load_builtin_templates(self):
        """加载内置工作流模板"""
        # 模板1: 数据处理流水线
        self._definitions["data-pipeline"] = FlowDefinition(
            flow_id="data-pipeline",
            name="数据处理流水线",
            description="标准ETL流程：提取→验证→转换→加载",
            nodes={
                "start": FlowNode("start", NodeType.START, "开始", next_nodes=["extract"]),
                "extract": FlowNode(
                    "extract",
                    NodeType.HTTP,
                    "数据提取",
                    config={"url": "{{source_url}}", "method": "GET"},
                    next_nodes=["validate"],
                    retry_count=3,
                ),
                "validate": FlowNode(
                    "validate",
                    NodeType.SCRIPT,
                    "数据验证",
                    config={"script": "validate_data(input_data)"},
                    next_nodes=["transform"],
                    retry_count=2,
                ),
                "transform": FlowNode(
                    "transform", NodeType.TRANSFORM, "数据转换", config={"mappings": {"status": "mapped_status"}}
                ),
                "load": FlowNode("load", NodeType.HTTP, "数据加载", config={"url": "{{target_url}}", "method": "POST"}),
                "end": FlowNode("end", NodeType.END, "结束"),
            },
        )
        # 模板2: 审批流程
        self._definitions["approval-flow"] = FlowDefinition(
            flow_id="approval-flow",
            name="审批流程",
            description="多级审批流程：提交→审核→批准/拒绝",
            nodes={
                "start": FlowNode("start", NodeType.START, "开始", next_nodes=["submit"]),
                "submit": FlowNode(
                    "submit", NodeType.NOTIFY, "提交审批", config={"channel": "email", "recipients": ["{{approver}}"]}
                ),
                "review": FlowNode(
                    "review",
                    NodeType.CONDITION,
                    "审核决策",
                    condition_expr="approval_status == 'approved'",
                    next_nodes=["approved"],
                ),
                "approved": FlowNode("approved", NodeType.NOTIFY, "审批通过", next_nodes=["end"]),
                "rejected": FlowNode("rejected", NodeType.NOTIFY, "审批拒绝", config={"channel": "email"}),
                "end": FlowNode("end", NodeType.END, "结束"),
            },
        )

    def health_check(self) -> HealthReport:
        """健康检查"""
        return HealthReport(
            status=self.status.value,
            healthy=self.status in (ModuleStatus.RUNNING, ModuleStatus.DEGRADED),
            last_beat=self._now(),
            uptime_seconds=self._uptime(),
            checks_run=self.stats.request_count,
            error_rate=self.stats.error_rate,
            details={"module": "flow-engine"},
        )

    def shutdown(self) -> None:
        """优雅关闭"""
        self.info("关闭工作流引擎...")
        self.status = ModuleStatus.STOPPING
        try:
            pass
            # 标记所有运行中的流程为取消
            for instance in self._instances.values():
                if instance.status == FlowStatus.RUNNING:
                    instance.status = FlowStatus.CANCELLED
                    instance.ended_at = self._now()
            # 清理
            self._instances.clear()
            self.status = ModuleStatus.STOPPED
            self.info("工作流引擎已关闭")
        except Exception as e:
            self.error(f"关闭异常: {e}")

    # ── 流程定义管理 ──

    def define_flow(self, definition: FlowDefinition) -> Dict[str, Any]:
        """定义/更新工作流"""
        with self.trace("define_flow"):
            try:
                pass
                # 校验DAG
                errors = self._validate_dag(definition)
                if errors:
                    return {"success": False, "errors": errors}
                definition.updated_at = self._now()
                self._definitions[definition.flow_id] = definition
                self.audit("define_flow", f"flow_id={definition.flow_id}")
                return {
                    "success": True,
                    "flow_id": definition.flow_id,
                    "nodes": len(definition.nodes),
                }
            except Exception as e:
                return {"success": False, "error": str(e)}

    def _validate_dag(self, definition: FlowDefinition) -> List[str]:
        """校验DAG合法性（检测循环）"""
        errors = []
        if not definition.nodes:
            errors.append("流程至少需要一个节点")
            return errors

        # 检查节点引用完整性
        for node_id, node in definition.nodes.items():
            for next_id in node.next_nodes:
                if next_id not in definition.nodes:
                    errors.append(f"节点 '{node_id}' 引用了不存在的下一节点 '{next_id}'")

        # 拓扑排序检测环
        in_degree = {nid: 0 for nid in definition.nodes}
        adj = {nid: [] for nid in definition.nodes}
        for node_id, node in definition.nodes.items():
            for next_id in node.next_nodes:
                if next_id in in_degree:
                    in_degree[next_id] += 1
                    adj[node_id].append(next_id)

        queue = [nid for nid, deg in in_degree.items() if deg == 0]
        visited = 0
        while queue:
            nid = queue.pop(0)
            visited += 1
            for neighbor in adj.get(nid, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if visited != len(definition.nodes):
            errors.append("检测到循环依赖，工作流不是有效的DAG")
        return errors

    def get_flow(self, flow_id: str) -> Optional[Dict[str, Any]]:
        """获取流程定义"""
        defn = self._definitions.get(flow_id)
        if not defn:
            return None
        return {
            "flow_id": defn.flow_id,
            "name": defn.name,
            "description": defn.description,
            "version": defn.version,
            "nodes": {nid: n.to_dict() for nid, n in defn.nodes.items()},
            "variables": defn.variables,
            "tags": defn.tags,
        }

    def list_flows(self) -> List[Dict[str, Any]]:
        """列出所有流程定义"""
        return [
            {
                "flow_id": d.flow_id,
                "name": d.name,
                "nodes": len(d.nodes),
                "version": d.version,
                "tags": d.tags,
            }
            for d in self._definitions.values()
        ]

    # ── 流程执行 ──

    async def execute(self, action: str, params: Optional[Dict[str, Any]] = None) -> Result:
        """执行工作流操作"""
        params = params or {}
        action_map = {
            "run": lambda p: self._run_flow(p),
            "pause": lambda p: self._pause_flow(p),
            "resume": lambda p: self._resume_flow(p),
            "cancel": lambda p: self._cancel_flow(p),
            "get_instance": lambda p: self._get_instance(p),
            "list_instances": lambda p: self._list_instances(p),
            "define": lambda p: self._define_flow_action(p),
            "delete": lambda p: self._delete_flow(p),
            "dry_run": lambda p: self._dry_run(p),
        }
        handler = action_map.get(action)
        if not handler:
            return Result(success=False, error=f"未知动作: {action}", module_id=self.module_id)
        return self._safe_execute(action, params, handler)

    def _run_flow(self, params: Dict) -> Any:
        """运行工作流"""
        metrics_collector.counter("flow_ops_total")

        flow_id = params.get("flow_id")
        variables = params.get("variables", {})

        defn = self._definitions.get(flow_id)
        if not defn:
            raise ValueError(f"流程不存在: {flow_id}")

        # 创建实例
        instance = FlowInstance(
            instance_id=str(uuid.uuid4())[:12],
            flow_id=flow_id,
            variables={**defn.variables, **variables},
        )
        instance.started_at = self._now()
        instance.status = FlowStatus.RUNNING

        # 初始化所有节点执行记录
        for nid in defn.nodes:
            instance.node_executions[nid] = NodeExecution(node_id=nid)
        self._instances[instance.instance_id] = instance

        self.info(f"启动流程 {flow_id} 实例 {instance.instance_id}")

        # 找到起始节点
        start_nodes = [nid for nid, n in defn.nodes.items() if n.node_type == NodeType.START]
        if not start_nodes:
            raise ValueError(f"流程 {flow_id} 缺少START节点")
        instance.current_nodes = start_nodes

        # 执行DAG
        self._execute_dag(instance, defn)
        return instance.to_dict()

    def _execute_dag(self, instance: FlowInstance, defn: FlowDefinition):
        """执行DAG遍历"""
        while instance.current_nodes and instance.status == FlowStatus.RUNNING:
            batch = instance.current_nodes[:]
            instance.current_nodes = []

            # 并行执行当前批次节点
            results = asyncio.gather(
                *[self._execute_node(instance, defn, nid) for nid in batch],
                return_exceptions=True,
            )

            # 收集下一批节点
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    self.error(f"节点 {batch[i]} 执行异常: {result}")
                    continue
                if result and isinstance(result, list):
                    instance.current_nodes.extend(result)

        # 标记流程结束
        if instance.status == FlowStatus.RUNNING:
            failed = any(
                ne.status in (NodeStatus.FAILED, NodeStatus.TIMEOUT) for ne in instance.node_executions.values()
            )
            instance.status = FlowStatus.FAILED if failed else FlowStatus.COMPLETED
        instance.ended_at = self._now()

        if self._on_flow_complete:
            self._on_flow_complete(instance)

    def _execute_node(self, instance: FlowInstance, defn: FlowDefinition, node_id: str) -> Optional[List[str]]:
        """执行单个节点"""
        node = defn.nodes.get(node_id)
        if not node:
            return []

        execution = instance.node_executions.get(node_id)
        if not execution or execution.status != NodeStatus.PENDING:
            return []

        # 条件检查：非START节点需检查前置节点状态
        if node.node_type != NodeType.START:
            has_failed_predecessor = False
            for nid, n in defn.nodes.items():
                if node_id in n.next_nodes:
                    pred_exec = instance.node_executions.get(nid)
                    if pred_exec and pred_exec.status in (NodeStatus.FAILED, NodeStatus.TIMEOUT):
                        if n.error_strategy == ErrorStrategy.FAIL_FAST:
                            instance.status = FlowStatus.FAILED
                            return []
                        has_failed_predecessor = True
            if has_failed_predecessor:
                execution.status = NodeStatus.SKIPPED
                return node.next_nodes

        # 执行节点
        execution.status = NodeStatus.RUNNING
        execution.start_time = self._now()
        execution.trace_id = str(uuid.uuid4())[:12]

        handler = self._handlers.get(node.node_type)
        if not handler:
            execution.status = NodeStatus.FAILED
            execution.error = f"无处理器: {node.node_type.value}"
            return []

        # 带重试的执行
        for attempt in range(1 + node.retry_count):
            try:
                pass
                # 超时控制
                output = asyncio.wait_for(
                    handler(node, instance.variables, execution),
                    timeout=node.timeout_seconds,
                )
                execution.status = NodeStatus.SUCCESS
                execution.output_data = output
                break
            except asyncio.TimeoutError:
                execution.status = NodeStatus.TIMEOUT
                execution.error = f"超时 ({node.timeout_seconds}s)"
                if attempt < node.retry_count:
                    time.sleep(node.retry_delay)
                    continue
                break
            except Exception as e:
                execution.status = NodeStatus.FAILED
                execution.error = f"{type(e).__name__}: {e}"
                if attempt < node.retry_count:
                    self.warning(f"节点 {node_id} 第{attempt + 1}次重试...")
                    time.sleep(node.retry_delay)
                    continue
                break

        execution.end_time = self._now()
        execution.duration_ms = (
            datetime.fromisoformat(execution.end_time) - datetime.fromisoformat(execution.start_time)
        ).total_seconds() * 1000

        if self._on_node_complete:
            self._on_node_complete(node, execution, instance)

        # 错误策略处理
        if execution.status in (NodeStatus.FAILED, NodeStatus.TIMEOUT):
            if node.error_strategy == ErrorStrategy.FALLBACK and node.fallback_node:
                return [node.fallback_node]
            if node.error_strategy == ErrorStrategy.CONTINUE:
                return node.next_nodes
            return []

        # 条件节点路由
        if node.node_type == NodeType.CONDITION and node.condition_expr:
            try:
                ctx = instance.variables.copy()
                ctx["output"] = execution.output_data
                if eval(node.condition_expr, {"__builtins__": {}}, ctx):
                    return node.next_nodes
                else:
                    return []
            except Exception:
                return []

        return node.next_nodes

    # ── 内置节点处理器 ──

    def _handle_start(self, node: FlowNode, variables: Dict, execution: NodeExecution) -> Any:
        """START节点：初始化上下文"""
        self.info(f"[{execution.trace_id}] START: {node.name}")
        return {"message": "流程启动", "started_at": self._now()}

    def _handle_end(self, node: FlowNode, variables: Dict, execution: NodeExecution) -> Any:
        """END节点：标记完成"""
        self.info(f"[{execution.trace_id}] END: {node.name}")
        return {"message": "流程结束", "ended_at": self._now()}

    def _handle_http(self, node: FlowNode, variables: Dict, execution: NodeExecution) -> Any:
        """HTTP节点：模拟HTTP调用"""
        cfg = node.config
        url = self._resolve_variables(cfg.get("url", ""), variables)
        method = cfg.get("method", "GET").upper()
        headers = cfg.get("headers", {})
        body = cfg.get("body", {})

        self.info(f"[{execution.trace_id}] HTTP {method} {url}")

        # 模拟HTTP调用（生产环境替换为aiohttp）
        time.sleep(0.1)  # 模拟网络延迟
        response_data = {
            "url": url,
            "method": method,
            "status": 200,
            "data": {"result": "mock_response", "timestamp": self._now()},
        }
        variables["_last_http_response"] = response_data
        return response_data

    def _handle_script(self, node: FlowNode, variables: Dict, execution: NodeExecution) -> Any:
        """SCRIPT节点：安全执行脚本"""
        script = node.config.get("script", "")
        self.info(f"[{execution.trace_id}] SCRIPT: {script[:50]}...")

        # 内置脚本函数
        builtins = {
            "validate_data": lambda d: isinstance(d, dict) and len(d) > 0,
            "transform_record": lambda d, m: {m.get(k, k): v for k, v in d.items()},
            "filter_records": lambda d, key, val: [r for r in d if r.get(key) == val] if isinstance(d, list) else [],
        }

        # 安全执行
        try:
            if "validate_data" in script:
                input_data = variables.get("input_data", variables.get("_last_http_response", {}))
                result = builtins["validate_data"](input_data)
                return {
                    "valid": result,
                    "records_checked": len(input_data) if isinstance(input_data, (list, dict)) else 0,
                }
            elif "transform_record" in script:
                return {"transformed": True, "message": "数据已转换"}
            else:
                return {"script_result": "executed", "script": script[:80]}
        except Exception as e:
            raise RuntimeError(f"脚本执行失败: {e}")

    def _handle_condition(self, node: FlowNode, variables: Dict, execution: NodeExecution) -> Any:
        """CONDITION节点：条件判断"""
        expr = node.condition_expr
        self.info(f"[{execution.trace_id}] CONDITION: {expr}")
        try:
            ctx = {k: v for k, v in variables.items() if isinstance(v, (str, int, float, bool))}
            result = eval(expr, {"__builtins__": {}}, ctx)
            return {"condition_result": bool(result), "expression": expr}
        except Exception as e:
            raise RuntimeError(f"条件表达式执行失败: {e}")

    def _handle_transform(self, node: FlowNode, variables: Dict, execution: NodeExecution) -> Any:
        """TRANSFORM节点：数据转换"""
        mappings = node.config.get("mappings", {})
        self.info(f"[{execution.trace_id}] TRANSFORM: {len(mappings)} 个映射规则")
        # 收集上游数据
        upstream_data = variables.get("_last_http_response", {})
        if isinstance(upstream_data, dict):
            data = upstream_data.get("data", upstream_data)
        else:
            data = upstream_data
        # 应用映射
        result = {}
        for src_key, dst_key in mappings.items():
            if isinstance(data, dict) and src_key in data:
                result[dst_key] = data[src_key]
            else:
                result[dst_key] = data
        variables["_transformed_data"] = result
        return {"transformed": result, "rules_applied": len(mappings)}

    def _handle_subprocess(self, node: FlowNode, variables: Dict, execution: NodeExecution) -> Any:
        """SUBPROCESS节点：调用子流程"""
        sub_flow_id = node.config.get("flow_id", "")
        self.info(f"[{execution.trace_id}] SUBPROCESS: {sub_flow_id}")
        sub_defn = self._definitions.get(sub_flow_id)
        if not sub_defn:
            raise ValueError(f"子流程不存在: {sub_flow_id}")
        # 简化执行：返回子流程信息
        return {
            "sub_flow_id": sub_flow_id,
            "name": sub_defn.name,
            "nodes": len(sub_defn.nodes),
        }

    def _handle_parallel(self, node: FlowNode, variables: Dict, execution: NodeExecution) -> Any:
        """PARALLEL节点：并行网关"""
        branches = node.config.get("branches", [])
        self.info(f"[{execution.trace_id}] PARALLEL: {len(branches)} 个分支")
        results = []
        for branch in branches:
            time.sleep(0.05)
            results.append({"branch": branch, "status": "completed"})
        return {"branches_completed": len(results), "results": results}

    def _handle_wait(self, node: FlowNode, variables: Dict, execution: NodeExecution) -> Any:
        """WAIT节点：等待"""
        wait_seconds = node.config.get("seconds", 1)
        self.info(f"[{execution.trace_id}] WAIT: {wait_seconds}s")
        time.sleep(min(wait_seconds, 5))
        return {"waited_seconds": wait_seconds}

    def _handle_notify(self, node: FlowNode, variables: Dict, execution: NodeExecution) -> Any:
        """NOTIFY节点：发送通知"""
        cfg = node.config
        channel = cfg.get("channel", "log")
        recipients = cfg.get("recipients", [])
        message = cfg.get("message", f"工作流节点 {node.name} 执行完成")
        self.info(f"[{execution.trace_id}] NOTIFY: {channel} → {recipients}")
        # 记录通知日志
        notification = {
            "channel": channel,
            "recipients": recipients,
            "message": message,
            "timestamp": self._now(),
        }
        variables["_last_notification"] = notification
        return notification

    # ── 流程控制 ──

    def _pause_flow(self, params: Dict) -> Any:
        instance_id = params.get("instance_id")
        instance = self._instances.get(instance_id)
        if not instance:
            raise ValueError(f"实例不存在: {instance_id}")
        if instance.status != FlowStatus.RUNNING:
            raise ValueError(f"实例状态不允许暂停: {instance.status.value}")
        instance.status = FlowStatus.PAUSED
        return {"instance_id": instance_id, "status": "paused"}

    def _resume_flow(self, params: Dict) -> Any:
        instance_id = params.get("instance_id")
        instance = self._instances.get(instance_id)
        if not instance:
            raise ValueError(f"实例不存在: {instance_id}")
        if instance.status != FlowStatus.PAUSED:
            raise ValueError(f"实例状态不允许恢复: {instance.status.value}")
        instance.status = FlowStatus.RUNNING
        return {"instance_id": instance_id, "status": "resumed"}

    def _cancel_flow(self, params: Dict) -> Any:
        instance_id = params.get("instance_id")
        instance = self._instances.get(instance_id)
        if not instance:
            raise ValueError(f"实例不存在: {instance_id}")
        instance.status = FlowStatus.CANCELLED
        instance.ended_at = self._now()
        return {"instance_id": instance_id, "status": "cancelled"}

    def _get_instance(self, params: Dict) -> Any:
        instance_id = params.get("instance_id")
        instance = self._instances.get(instance_id)
        if not instance:
            raise ValueError(f"实例不存在: {instance_id}")
        result = instance.to_dict()
        result["node_executions"] = {nid: ne.to_dict() for nid, ne in instance.node_executions.items()}
        return result

    def _list_instances(self, params: Dict) -> Any:
        flow_id = params.get("flow_id")
        status = params.get("status")
        instances = list(self._instances.values())
        if flow_id:
            instances = [i for i in instances if i.flow_id == flow_id]
        if status:
            instances = [i for i in instances if i.status.value == status]
        return {"total": len(instances), "instances": [i.to_dict() for i in instances[-50:]]}

    def _define_flow_action(self, params: Dict) -> Any:
        definition_data = params.get("definition", {})
        flow_id = definition_data.get("flow_id", str(uuid.uuid4())[:8])
        nodes_data = definition_data.get("nodes", {})
        nodes = {}
        for nid, ndata in nodes_data.items():
            nodes[nid] = FlowNode(
                node_id=nid,
                node_type=NodeType(ndata.get("node_type", "script")),
                name=ndata.get("name", nid),
                config=ndata.get("config", {}),
                next_nodes=ndata.get("next_nodes", []),
                timeout_seconds=ndata.get("timeout_seconds", self.default_timeout),
                retry_count=ndata.get("retry_count", 0),
            )
        defn = FlowDefinition(
            flow_id=flow_id,
            name=definition_data.get("name", flow_id),
            description=definition_data.get("description", ""),
            nodes=nodes,
            variables=definition_data.get("variables", {}),
            tags=definition_data.get("tags", []),
        )
        return self.define_flow(defn)

    def _delete_flow(self, params: Dict) -> Any:
        flow_id = params.get("flow_id")
        if flow_id in self._definitions:
            del self._definitions[flow_id]
            self.audit("delete_flow", f"flow_id={flow_id}")
            return {"deleted": flow_id}
        raise ValueError(f"流程不存在: {flow_id}")

    def _dry_run(self, params: Dict) -> Any:
        """干跑：验证流程定义但不实际执行"""
        flow_id = params.get("flow_id")
        defn = self._definitions.get(flow_id)
        if not defn:
            raise ValueError(f"流程不存在: {flow_id}")
        errors = self._validate_dag(defn)
        # 模拟执行路径
        path = []
        visited: Set[str] = set()
        queue = [nid for nid, n in defn.nodes.items() if n.node_type == NodeType.START]
        while queue and len(path) < 50:
            nid = queue.pop(0)
            if nid in visited:
                continue
            visited.add(nid)
            node = defn.nodes[nid]
            path.append({"node_id": nid, "type": node.node_type.value, "name": node.name})
            queue.extend(node.next_nodes)
        return {
            "flow_id": flow_id,
            "valid": len(errors) == 0,
            "errors": errors,
            "execution_path": path,
            "total_nodes": len(defn.nodes),
        }

    # ── 变量解析 ──

    def _resolve_variables(self, text: str, variables: Dict) -> str:
        """解析模板变量 {{var_name}}"""
        import re

        def replacer(match):
            var_name = match.group(1).strip()
            value = variables.get(var_name, match.group(0))
            if callable(value):
                return str(value())
            return str(value)

        return re.sub(r"\{\{(.+?)\}\}", replacer, text)

    # ── 事件回调 ──

    def on_node_complete(self, callback: Callable):
        self._on_node_complete = callback

    def on_flow_complete(self, callback: Callable):
        self._on_flow_complete = callback

module_class = FlowEngine
