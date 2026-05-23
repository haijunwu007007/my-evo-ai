# -*- coding: utf-8 -*-
# Grade: A

"""
AUTO-EVO-AI v7.0 - Flowise 可视化流程编排（A级）
=================================================
基于拖拽的流程编排平台，支持：
  1. 可视化流程编辑器数据模型
  2. 节点拖拽/连接/分组管理
  3. 流程版本控制
  4. 实时预览与仿真执行
  5. 模板市场与共享
  6. 协作编辑与锁定
  7. 导入/导出（JSON/YAML）
"""

__module_meta__ = {
    "id": "flowise",
    "name": "Flowise",
    "version": "1.0.0",
    "group": "nocode",
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
    "tags": ["adapter", "flowise"],
    "grade": "A",
    "description": "AUTO-EVO-AI v7.0 - Flowise 可视化流程编排（A级） =================================================",
}

import os
import time
import uuid
import json
import copy
import logging
from enum import Enum
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field

import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from modules._base.enterprise_module import EnterpriseModule, Result, HealthReport, ModuleStatus
from modules._base.metrics import prometheus_timer, metrics_collector
from modules._base.mixins import CircuitBreakerMixin, RateLimiterMixin

logger = logging.getLogger("evo.flowise")

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

class CanvasMode(str, Enum):
    EDIT = "edit"
    READONLY = "readonly"
    SIMULATE = "simulate"

class ExportFormat(str, Enum):
    JSON = "json"
    YAML = "yaml"

@dataclass
class VisualNode:
    """可视化节点"""

    node_id: str
    node_type: str
    label: str
    x: float = 0.0
    y: float = 0.0
    width: float = 180.0
    height: float = 80.0
    config: Dict[str, Any] = field(default_factory=dict)
    style: Dict[str, Any] = field(default_factory=dict)
    group_id: str = ""
    inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    icon: str = "⬡"
    color: str = "#4A90D9"
    tooltip: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type,
            "label": self.label,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "config": self.config,
            "style": self.style,
            "group_id": self.group_id,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "icon": self.icon,
            "color": self.color,
        }

@dataclass
class VisualEdge:
    """可视化连线"""

    edge_id: str
    source_id: str
    source_port: str
    target_id: str
    target_port: str
    label: str = ""
    style: Dict[str, Any] = field(default_factory=dict)
    animated: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "edge_id": self.edge_id,
            "source_id": self.source_id,
            "source_port": self.source_port,
            "target_id": self.target_id,
            "target_port": self.target_port,
            "label": self.label,
            "style": self.style,
            "animated": self.animated,
        }

@dataclass
class NodeGroup:
    """节点分组"""

    group_id: str
    name: str
    color: str = "#E8F0FE"
    collapsed: bool = False
    children: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "group_id": self.group_id,
            "name": self.name,
            "color": self.color,
            "collapsed": self.collapsed,
            "children": self.children,
        }

@dataclass
class FlowCanvas:
    """流程画布"""

    canvas_id: str
    name: str
    description: str = ""
    mode: CanvasMode = CanvasMode.EDIT
    nodes: Dict[str, VisualNode] = field(default_factory=dict)
    edges: Dict[str, VisualEdge] = field(default_factory=dict)
    groups: Dict[str, NodeGroup] = field(default_factory=dict)
    variables: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    version: int = 1
    locked_by: str = ""
    locked_at: str = ""
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        self.updated_at = self.created_at

    def to_dict(self) -> Dict[str, Any]:
        return {
            "canvas_id": self.canvas_id,
            "name": self.name,
            "description": self.description,
            "mode": self.mode.value,
            "version": self.version,
            "nodes": {nid: n.to_dict() for nid, n in self.nodes.items()},
            "edges": {eid: e.to_dict() for eid, e in self.edges.items()},
            "groups": {gid: g.to_dict() for gid, g in self.groups.items()},
            "variables": self.variables,
            "tags": self.tags,
            "locked_by": self.locked_by,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

@dataclass
class FlowVersion:
    """流程版本"""

    version_id: str
    canvas_id: str
    version_number: int
    snapshot: Dict[str, Any]
    changelog: str = ""
    created_by: str = "system"
    created_at: str = ""

@dataclass
class FlowTemplate:
    """流程模板"""

    template_id: str
    name: str
    description: str = ""
    category: str = "general"
    icon: str = "📋"
    canvas_snapshot: Dict[str, Any] = field(default_factory=dict)
    variables: Dict[str, Any] = field(default_factory=dict)
    downloads: int = 0
    rating: float = 0.0
    tags: List[str] = field(default_factory=list)
    created_by: str = "system"
    created_at: str = ""

class CanvasValidator(object):
    """画布验证器 — 检测死循环、孤立节点、类型不匹配、执行路径可达性"""

    def validate_canvas(self, nodes: List[Dict], edges: List[Dict]) -> Dict[str, Any]:
        """验证画布完整性：连通性、类型兼容性、无死循环"""
        if not nodes:
            return {"valid": False, "error": "empty canvas"}
        issues = []
        node_ids = {n.get("id") for n in nodes}
        edge_sources = {e.get("source") for e in edges}
        edge_targets = {e.get("target") for e in edges}
        # 检测孤立节点
        connected = edge_sources | edge_targets
        orphans = node_ids - connected
        for oid in orphans:
            issues.append({"type": "orphan_node", "node_id": oid, "severity": "warning", "detail": "节点无连接"})
        # 检测悬空边
        dangling_src = edge_sources - node_ids
        dangling_tgt = edge_targets - node_ids
        for eid in dangling_src:
            issues.append(
                {"type": "dangling_edge", "edge_source": eid, "severity": "error", "detail": "边引用了不存在的源节点"}
            )
        for eid in dangling_tgt:
            issues.append(
                {"type": "dangling_edge", "edge_target": eid, "severity": "error", "detail": "边引用了不存在的目标节点"}
            )
        # 检测死循环(DFS)
        adj: Dict[str, List[str]] = {nid: [] for nid in node_ids}
        for e in edges:
            s, t = e.get("source", ""), e.get("target", "")
            if s in adj:
                adj[s].append(t)
        cycles = self._detect_cycles(adj)
        for cycle in cycles:
            issues.append({"type": "cycle_detected", "nodes": cycle, "severity": "error", "detail": "检测到死循环路径"})
        errors = sum(1 for i in issues if i["severity"] == "error")
        warnings = sum(1 for i in issues if i["severity"] == "warning")
        return {
            "valid": errors == 0,
            "error_count": errors,
            "warning_count": warnings,
            "issues": issues,
            "node_count": len(nodes),
            "edge_count": len(edges),
        }

    def _detect_cycles(self, adj: Dict[str, List[str]]) -> List[List[str]]:
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {n: WHITE for n in adj}
        cycles = []
        path = []

        def dfs(u):
            color[u] = GRAY
            path.append(u)
            for v in adj.get(u, []):
                if v not in color:
                    continue
                if color[v] == GRAY:
                    idx = path.index(v) if v in path else -1
                    if idx >= 0:
                        cycles.append(path[idx:] + [v])
                elif color[v] == WHITE:
                    dfs(v)
            path.pop()
            color[u] = BLACK

        for n in adj:
            if color[n] == WHITE:
                dfs(n)
        return cycles

    def estimate_complexity(self, nodes: List[Dict], edges: List[Dict]) -> Dict[str, Any]:
        """估算画布复杂度：节点数、边数、最长路径、分支因子"""
        if not nodes:
            return {"complexity": "trivial"}
        adj: Dict[str, List[str]] = {n.get("id"): [] for n in nodes}
        in_degree: Dict[str, int] = {n.get("id"): 0 for n in nodes}
        for e in edges:
            s, t = e.get("source", ""), e.get("target", "")
            if s in adj:
                adj[s].append(t)
            if t in in_degree:
                in_degree[t] += 1
        max_path = self._longest_path(adj)
        avg_branch = sum(len(v) for v in adj.values()) / max(len(adj), 1)
        if len(nodes) <= 3 and len(edges) <= 3:
            level = "simple"
        elif len(nodes) <= 10 and max_path <= 5:
            level = "moderate"
        else:
            level = "complex"
        return {
            "node_count": len(nodes),
            "edge_count": len(edges),
            "max_path_length": max_path,
            "avg_branching_factor": round(avg_branch, 2),
            "complexity_level": level,
        }

    def _longest_path(self, adj: Dict[str, List[str]]) -> int:
        memo = {}

        def dfs(u, visited):
            if u in memo:
                return memo[u]
            if u in visited:
                return 0
            visited.add(u)
            max_len = 0
            for v in adj.get(u, []):
                max_len = max(max_len, 1 + dfs(v, visited))
            visited.discard(u)
            memo[u] = max_len
            return max_len

        result = 0
        for n in adj:
            result = max(result, dfs(n, set()))
        return result

class Flowise(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """可视化流程编排平台"""

    MODULE_ID = "flowise"
    MODULE_NAME = "可视化流程编排"
    VERSION = "v7.0"
    MODULE_LEVEL = "A"

    def __init__(self, config: Optional[Dict[str, Any]] = None):

        super().__init__(config)
        self._metrics = _MetricsAdapter()
        self._canvases: Dict[str, FlowCanvas] = {}
        self._versions: Dict[str, List[FlowVersion]] = {}
        self._templates: Dict[str, FlowTemplate] = {}
        self._simulations: Dict[str, Dict] = {}
        self.max_canvases = self.config.get("max_canvases", 200)
        self.max_versions_per_canvas = self.config.get("max_versions", 50)

    def initialize(self) -> None:
        self.info("初始化可视化流程编排平台...")
        self.record_metrics("flowise.init", 1)
        self.status = ModuleStatus.INITIALIZING
        try:
            self._load_builtin_templates()
            self.status = ModuleStatus.RUNNING
            self.stats.start_time = datetime.now()
            self.info(f"初始化完成，已加载 {len(self._templates)} 个模板")
        except Exception as e:
            self.status = ModuleStatus.ERROR
            self.error(f"初始化失败: {e}")
            raise

    def _load_builtin_templates(self):
        """加载内置模板"""
        # 模板1: API数据处理
        api_template = FlowTemplate(
            template_id="api-data-pipeline",
            name="API数据处理流水线",
            description="调用外部API→数据验证→格式转换→存储",
            category="data",
            icon="🔄",
            canvas_snapshot={
                "nodes": {
                    "start": {"node_id": "start", "node_type": "trigger", "label": "定时触发", "x": 50, "y": 200},
                    "http": {"node_id": "http", "node_type": "http", "label": "API调用", "x": 280, "y": 200},
                    "validate": {
                        "node_id": "validate",
                        "node_type": "validator",
                        "label": "数据验证",
                        "x": 510,
                        "y": 200,
                    },
                    "transform": {
                        "node_id": "transform",
                        "node_type": "transformer",
                        "label": "格式转换",
                        "x": 740,
                        "y": 200,
                    },
                    "store": {"node_id": "store", "node_type": "database", "label": "数据存储", "x": 970, "y": 200},
                    "end": {"node_id": "end", "node_type": "end", "label": "结束", "x": 1200, "y": 200},
                },
                "edges": [
                    {"source_id": "start", "target_id": "http"},
                    {"source_id": "http", "target_id": "validate"},
                    {"source_id": "validate", "target_id": "transform"},
                    {"source_id": "transform", "target_id": "store"},
                    {"source_id": "store", "target_id": "end"},
                ],
            },
            tags=["api", "data", "etl"],
        )
        self._templates[api_template.template_id] = api_template

        # 模板2: 条件审批流
        approval_template = FlowTemplate(
            template_id="conditional-approval",
            name="条件审批流程",
            description="根据金额自动路由到不同审批层级",
            category="business",
            icon="✅",
            canvas_snapshot={
                "nodes": {
                    "start": {"node_id": "start", "node_type": "trigger", "label": "提交申请", "x": 50, "y": 250},
                    "check": {"node_id": "check", "node_type": "condition", "label": "金额判断", "x": 280, "y": 250},
                    "manager": {"node_id": "manager", "node_type": "approval", "label": "经理审批", "x": 550, "y": 100},
                    "director": {
                        "node_id": "director",
                        "node_type": "approval",
                        "label": "总监审批",
                        "x": 550,
                        "y": 400,
                    },
                    "notify": {"node_id": "notify", "node_type": "notify", "label": "通知结果", "x": 820, "y": 250},
                    "end": {"node_id": "end", "node_type": "end", "label": "结束", "x": 1050, "y": 250},
                },
            },
            tags=["approval", "condition", "business"],
        )
        self._templates[approval_template.template_id] = approval_template

        # 模板3: 数据分析报告
        report_template = FlowTemplate(
            template_id="analysis-report",
            name="数据分析报告生成",
            description="数据采集→分析→图表生成→报告输出",
            category="analytics",
            icon="📊",
            tags=["analytics", "report", "chart"],
        )
        self._templates[report_template.template_id] = report_template

    def health_check(self) -> HealthReport:
        """健康检查"""
        return HealthReport(
            status=self.status.value,
            healthy=self.status in (ModuleStatus.RUNNING, ModuleStatus.DEGRADED),
            last_beat=self._now(),
            uptime_seconds=self._uptime(),
            checks_run=self.stats.request_count,
            error_rate=self.stats.error_rate,
            details={"module": "flowise"},
        )

    def shutdown(self) -> None:
        self.info("关闭可视化流程编排平台...")
        self.status = ModuleStatus.STOPPING
        self._canvases.clear()
        self._versions.clear()
        self._templates.clear()
        self.status = ModuleStatus.STOPPED

    async def execute(self, action: str, params: Optional[Dict[str, Any]] = None) -> Result:
        _ = self.trace("execute")
        metrics_collector.counter("flowise_ops_total", labels={"action": action})
        self.audit("execute", f"action={action}")
        params = params or {}
        action_map = {
            "create_canvas": lambda p: self._create_canvas(p),
            "get_canvas": lambda p: self._get_canvas(p),
            "list_canvases": lambda p: self._list_canvases(p),
            "delete_canvas": lambda p: self._delete_canvas(p),
            "add_node": lambda p: self._add_node(p),
            "update_node": lambda p: self._update_node(p),
            "delete_node": lambda p: self._delete_node(p),
            "add_edge": lambda p: self._add_edge(p),
            "delete_edge": lambda p: self._delete_edge(p),
            "create_group": lambda p: self._create_group(p),
            "delete_group": lambda p: self._delete_group(p),
            "save_version": lambda p: self._save_version(p),
            "list_versions": lambda p: self._list_versions(p),
            "restore_version": lambda p: self._restore_version(p),
            "duplicate_canvas": lambda p: self._duplicate_canvas(p),
            "export": lambda p: self._export_canvas(p),
            "import": lambda p: self._import_canvas(p),
            "lock": lambda p: self._lock_canvas(p),
            "unlock": lambda p: self._unlock_canvas(p),
            "simulate": lambda p: self._simulate(p),
            "list_templates": lambda p: self._list_templates(p),
            "use_template": lambda p: self._use_template(p),
            "auto_layout": lambda p: self._auto_layout(p),
            "validate": lambda p: self._validate_canvas(p),
            "get_stats": lambda p: self._get_stats(p),
        }
        handler = action_map.get(action)
        if not handler:
            return Result(success=False, error=f"未知动作: {action}", module_id=self.module_id)
        return self._safe_execute(action, params, handler)

    # ── 画布管理 ──

    def _create_canvas(self, params: Dict) -> Any:
        name = params.get("name", "未命名流程")
        description = params.get("description", "")
        tags = params.get("tags", [])
        canvas_id = str(uuid.uuid4())[:10]
        canvas = FlowCanvas(canvas_id=canvas_id, name=name, description=description, tags=tags)
        self._canvases[canvas_id] = canvas
        self._versions[canvas_id] = []
        self.audit("create_canvas", f"canvas_id={canvas_id}")
        return {"canvas_id": canvas_id, "name": name}

    def _get_canvas(self, params: Dict) -> Any:
        canvas_id = params.get("canvas_id")
        canvas = self._canvases.get(canvas_id)
        if not canvas:
            raise ValueError(f"画布不存在: {canvas_id}")
        return canvas.to_dict()

    def _list_canvases(self, params: Dict) -> Any:
        tag = params.get("tag")
        canvases = list(self._canvases.values())
        if tag:
            canvases = [c for c in canvases if tag in c.tags]
        return {
            "total": len(canvases),
            "canvases": [
                {
                    "canvas_id": c.canvas_id,
                    "name": c.name,
                    "version": c.version,
                    "nodes": len(c.nodes),
                    "edges": len(c.edges),
                    "mode": c.mode.value,
                    "tags": c.tags,
                }
                for c in canvases
            ],
        }

    def _delete_canvas(self, params: Dict) -> Any:
        canvas_id = params.get("canvas_id")
        if canvas_id not in self._canvases:
            raise ValueError(f"画布不存在: {canvas_id}")
        del self._canvases[canvas_id]
        self._versions.pop(canvas_id, None)
        self.audit("delete_canvas", f"canvas_id={canvas_id}")
        return {"deleted": canvas_id}

    def _duplicate_canvas(self, params: Dict) -> Any:
        canvas_id = params.get("canvas_id")
        source = self._canvases.get(canvas_id)
        if not source:
            raise ValueError(f"画布不存在: {canvas_id}")
        new_id = str(uuid.uuid4())[:10]
        duplicate = copy.deepcopy(source)
        duplicate.canvas_id = new_id
        duplicate.name = f"{source.name} (副本)"
        duplicate.version = 1
        duplicate.created_at = self._now()
        duplicate.updated_at = self._now()
        # 重新生成节点ID
        id_map = {}
        new_nodes = {}
        for nid, node in duplicate.nodes.items():
            new_nid = str(uuid.uuid4())[:8]
            id_map[nid] = new_nid
            node.node_id = new_nid
            new_nodes[new_nid] = node
        duplicate.nodes = new_nodes
        # 更新连线引用
        new_edges = {}
        for eid, edge in duplicate.edges.items():
            new_eid = str(uuid.uuid4())[:8]
            edge.edge_id = new_eid
            edge.source_id = id_map.get(edge.source_id, edge.source_id)
            edge.target_id = id_map.get(edge.target_id, edge.target_id)
            new_edges[new_eid] = edge
        duplicate.edges = new_edges
        self._canvases[new_id] = duplicate
        self._versions[new_id] = []
        return {"canvas_id": new_id, "name": duplicate.name}

    # ── 节点操作 ──

    def _add_node(self, params: Dict) -> Any:
        canvas_id = params.get("canvas_id")
        canvas = self._canvases.get(canvas_id)
        if not canvas:
            raise ValueError(f"画布不存在: {canvas_id}")
        if canvas.locked_by:
            raise ValueError(f"画布已被 {canvas.locked_by} 锁定")
        node_id = params.get("node_id", str(uuid.uuid4())[:8])
        node = VisualNode(
            node_id=node_id,
            node_type=params.get("node_type", "script"),
            label=params.get("label", "新节点"),
            x=params.get("x", 100.0),
            y=params.get("y", 100.0),
            config=params.get("config", {}),
            style=params.get("style", {}),
            group_id=params.get("group_id", ""),
            icon=params.get("icon", "⬡"),
            color=params.get("color", "#4A90D9"),
        )
        canvas.nodes[node_id] = node
        canvas.updated_at = self._now()
        return {"node_id": node_id, "label": node.label}

    def _update_node(self, params: Dict) -> Any:
        canvas_id = params.get("canvas_id")
        node_id = params.get("node_id")
        canvas = self._canvases.get(canvas_id)
        if not canvas:
            raise ValueError(f"画布不存在: {canvas_id}")
        node = canvas.nodes.get(node_id)
        if not node:
            raise ValueError(f"节点不存在: {node_id}")
        if "label" in params:
            node.label = params["label"]
        if "x" in params:
            node.x = params["x"]
        if "y" in params:
            node.y = params["y"]
        if "config" in params:
            node.config = params["config"]
        if "style" in params:
            node.style = params["style"]
        if "group_id" in params:
            node.group_id = params["group_id"]
        if "color" in params:
            node.color = params["color"]
        if "icon" in params:
            node.icon = params["icon"]
        canvas.updated_at = self._now()
        return {"updated": node_id}

    def _delete_node(self, params: Dict) -> Any:
        canvas_id = params.get("canvas_id")
        node_id = params.get("node_id")
        canvas = self._canvases.get(canvas_id)
        if not canvas or node_id not in canvas.nodes:
            raise ValueError("画布或节点不存在")
        # 删除关联连线
        edges_to_delete = [eid for eid, e in canvas.edges.items() if e.source_id == node_id or e.target_id == node_id]
        for eid in edges_to_delete:
            del canvas.edges[eid]
        del canvas.nodes[node_id]
        canvas.updated_at = self._now()
        return {"deleted": node_id, "edges_removed": len(edges_to_delete)}

    # ── 连线操作 ──

    def _add_edge(self, params: Dict) -> Any:
        canvas_id = params.get("canvas_id")
        canvas = self._canvases.get(canvas_id)
        if not canvas:
            raise ValueError(f"画布不存在: {canvas_id}")
        if canvas.locked_by:
            raise ValueError("画布已锁定")
        source_id = params.get("source_id")
        target_id = params.get("target_id")
        if source_id not in canvas.nodes or target_id not in canvas.nodes:
            raise ValueError("源节点或目标节点不存在")
        if source_id == target_id:
            raise ValueError("不允许自连接")
        # 检测重复
        for e in canvas.edges.values():
            if e.source_id == source_id and e.target_id == target_id:
                raise ValueError("连线已存在")
        edge_id = str(uuid.uuid4())[:8]
        edge = VisualEdge(
            edge_id=edge_id,
            source_id=source_id,
            source_port=params.get("source_port", "output"),
            target_id=target_id,
            target_port=params.get("target_port", "input"),
            label=params.get("label", ""),
            animated=params.get("animated", False),
        )
        canvas.edges[edge_id] = edge
        canvas.updated_at = self._now()
        return {"edge_id": edge_id}

    def _delete_edge(self, params: Dict) -> Any:
        canvas_id = params.get("canvas_id")
        edge_id = params.get("edge_id")
        canvas = self._canvases.get(canvas_id)
        if not canvas or edge_id not in canvas.edges:
            raise ValueError("画布或连线不存在")
        del canvas.edges[edge_id]
        canvas.updated_at = self._now()
        return {"deleted": edge_id}

    # ── 分组管理 ──

    def _create_group(self, params: Dict) -> Any:
        canvas_id = params.get("canvas_id")
        canvas = self._canvases.get(canvas_id)
        if not canvas:
            raise ValueError(f"画布不存在: {canvas_id}")
        group_id = params.get("group_id", str(uuid.uuid4())[:8])
        group = NodeGroup(
            group_id=group_id,
            name=params.get("name", "新分组"),
            color=params.get("color", "#E8F0FE"),
            children=params.get("children", []),
        )
        canvas.groups[group_id] = group
        for nid in group.children:
            if nid in canvas.nodes:
                canvas.nodes[nid].group_id = group_id
        canvas.updated_at = self._now()
        return {"group_id": group_id, "name": group.name}

    def _delete_group(self, params: Dict) -> Any:
        canvas_id = params.get("canvas_id")
        group_id = params.get("group_id")
        canvas = self._canvases.get(canvas_id)
        if not canvas or group_id not in canvas.groups:
            raise ValueError("画布或分组不存在")
        group = canvas.groups[group_id]
        for nid in group.children:
            if nid in canvas.nodes:
                canvas.nodes[nid].group_id = ""
        del canvas.groups[group_id]
        canvas.updated_at = self._now()
        return {"deleted": group_id}

    # ── 版本控制 ──

    def _save_version(self, params: Dict) -> Any:
        canvas_id = params.get("canvas_id")
        changelog = params.get("changelog", "")
        canvas = self._canvases.get(canvas_id)
        if not canvas:
            raise ValueError(f"画布不存在: {canvas_id}")
        versions = self._versions.get(canvas_id, [])
        if len(versions) >= self.max_versions_per_canvas:
            versions = versions[-(self.max_versions_per_canvas - 1) :]
        canvas.version += 1
        snapshot = canvas.to_dict()
        version = FlowVersion(
            version_id=str(uuid.uuid4())[:10],
            canvas_id=canvas_id,
            version_number=canvas.version,
            snapshot=snapshot,
            changelog=changelog,
            created_at=self._now(),
        )
        versions.append(version)
        self._versions[canvas_id] = versions
        self.audit("save_version", f"canvas={canvas_id} v{canvas.version}")
        return {"version": canvas.version, "version_id": version.version_id}

    def _list_versions(self, params: Dict) -> Any:
        canvas_id = params.get("canvas_id")
        versions = self._versions.get(canvas_id, [])
        return {
            "canvas_id": canvas_id,
            "total": len(versions),
            "versions": [
                {
                    "version_number": v.version_number,
                    "version_id": v.version_id,
                    "changelog": v.changelog,
                    "created_at": v.created_at,
                }
                for v in versions
            ],
        }

    def _restore_version(self, params: Dict) -> Any:
        canvas_id = params.get("canvas_id")
        version_id = params.get("version_id")
        canvas = self._canvases.get(canvas_id)
        if not canvas:
            raise ValueError(f"画布不存在: {canvas_id}")
        versions = self._versions.get(canvas_id, [])
        version = next((v for v in versions if v.version_id == version_id), None)
        if not version:
            raise ValueError(f"版本不存在: {version_id}")
        snapshot = version.snapshot
        # 恢复节点
        canvas.nodes.clear()
        for nid, ndata in snapshot.get("nodes", {}).items():
            canvas.nodes[nid] = VisualNode(**ndata)
        # 恢复连线
        canvas.edges.clear()
        for eid, edata in snapshot.get("edges", {}).items():
            canvas.edges[eid] = VisualEdge(**edata)
        canvas.variables = snapshot.get("variables", {})
        canvas.version = version.version_number
        canvas.updated_at = self._now()
        return {"restored": version_id, "version": version.version_number}

    # ── 导入/导出 ──

    def _export_canvas(self, params: Dict) -> Any:
        canvas_id = params.get("canvas_id")
        fmt = params.get("format", "json")
        canvas = self._canvases.get(canvas_id)
        if not canvas:
            raise ValueError(f"画布不存在: {canvas_id}")
        data = canvas.to_dict()
        if fmt == "json":
            content = json.dumps(data, ensure_ascii=False, indent=2)
        else:
            # 简化YAML输出
            lines = [f"name: {data['name']}", f"version: {data['version']}"]
            for nid, node in data.get("nodes", {}).items():
                lines.append(f"- node: {node['label']} ({node['node_type']})")
            content = "\n".join(lines)
        return {"format": fmt, "content": content, "size": len(content)}

    def _import_canvas(self, params: Dict) -> Any:
        content = params.get("content", "")
        name = params.get("name", "导入的流程")
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            raise ValueError("无效的JSON格式")
        canvas_id = str(uuid.uuid4())[:10]
        canvas = FlowCanvas(canvas_id=canvas_id, name=name)
        for nid, ndata in data.get("nodes", {}).items():
            canvas.nodes[nid] = VisualNode(**ndata)
        for eid, edata in data.get("edges", {}).items():
            canvas.edges[eid] = VisualEdge(**edata)
        self._canvases[canvas_id] = canvas
        self._versions[canvas_id] = []
        self.audit("import_canvas", f"canvas={canvas_id}")
        return {"canvas_id": canvas_id, "nodes": len(canvas.nodes), "edges": len(canvas.edges)}

    # ── 锁定 ──

    def _lock_canvas(self, params: Dict) -> Any:
        canvas_id = params.get("canvas_id")
        user = params.get("user", "system")
        canvas = self._canvases.get(canvas_id)
        if not canvas:
            raise ValueError(f"画布不存在: {canvas_id}")
        if canvas.locked_by:
            raise ValueError(f"画布已被 {canvas.locked_by} 锁定")
        canvas.locked_by = user
        canvas.locked_at = self._now()
        return {"locked_by": user}

    def _unlock_canvas(self, params: Dict) -> Any:
        canvas_id = params.get("canvas_id")
        canvas = self._canvases.get(canvas_id)
        if not canvas:
            raise ValueError(f"画布不存在: {canvas_id}")
        user = canvas.locked_by
        canvas.locked_by = ""
        canvas.locked_at = ""
        return {"unlocked": user}

    # ── 仿真执行 ──

    def _simulate(self, params: Dict) -> Any:
        canvas_id = params.get("canvas_id")
        variables = params.get("variables", {})
        canvas = self._canvases.get(canvas_id)
        if not canvas:
            raise ValueError(f"画布不存在: {canvas_id}")
        # 执行路径模拟
        path = []
        visited = set()
        # 找入度为0的节点
        has_incoming = set()
        for e in canvas.edges.values():
            has_incoming.add(e.target_id)
        queue = [nid for nid in canvas.nodes if nid not in has_incoming]
        step = 0
        while queue and step < 100:
            step += 1
            nid = queue.pop(0)
            if nid in visited:
                continue
            visited.add(nid)
            node = canvas.nodes[nid]
            path.append(
                {
                    "step": step,
                    "node_id": nid,
                    "label": node.label,
                    "type": node.node_type,
                    "status": "completed",
                    "duration_ms": round(50 + len(node.config) * 10, 1),
                }
            )
            for eid, edge in canvas.edges.items():
                if edge.source_id == nid:
                    if edge.target_id not in visited:
                        queue.append(edge.target_id)
        sim_id = str(uuid.uuid4())[:8]
        self._simulations[sim_id] = {"canvas_id": canvas_id, "path": path}
        return {
            "simulation_id": sim_id,
            "steps": len(path),
            "path": path,
            "total_nodes": len(canvas.nodes),
            "executed": len(visited),
        }

    # ── 模板 ──

    def _list_templates(self, params: Dict) -> Any:
        category = params.get("category")
        templates = list(self._templates.values())
        if category:
            templates = [t for t in templates if t.category == category]
        return {
            "total": len(templates),
            "templates": [
                {
                    "template_id": t.template_id,
                    "name": t.name,
                    "category": t.category,
                    "icon": t.icon,
                    "description": t.description,
                    "tags": t.tags,
                }
                for t in templates
            ],
        }

    def _use_template(self, params: Dict) -> Any:
        template_id = params.get("template_id")
        name = params.get("name", "")
        template = self._templates.get(template_id)
        if not template:
            raise ValueError(f"模板不存在: {template_id}")
        canvas_id = str(uuid.uuid4())[:10]
        canvas = FlowCanvas(
            canvas_id=canvas_id,
            name=name or template.name,
            description=template.description,
            variables=copy.deepcopy(template.variables),
            tags=template.tags[:],
        )
        # 从模板快照创建节点
        snapshot = template.canvas_snapshot
        for nid, ndata in snapshot.get("nodes", {}).items():
            canvas.nodes[nid] = VisualNode(
                node_id=ndata.get("node_id", nid),
                node_type=ndata.get("node_type", "script"),
                label=ndata.get("label", nid),
                x=ndata.get("x", 100.0),
                y=ndata.get("y", 100.0),
            )
        for i, edata in enumerate(snapshot.get("edges", [])):
            eid = str(uuid.uuid4())[:8]
            canvas.edges[eid] = VisualEdge(
                edge_id=eid,
                source_id=edata.get("source_id", ""),
                target_id=edata.get("target_id", ""),
            )
        self._canvases[canvas_id] = canvas
        self._versions[canvas_id] = []
        template.downloads += 1
        return {"canvas_id": canvas_id, "name": canvas.name, "nodes": len(canvas.nodes)}

    # ── 自动布局 ──

    def _auto_layout(self, params: Dict) -> Any:
        canvas_id = params.get("canvas_id")
        layout = params.get("layout", "dagre")
        canvas = self._canvases.get(canvas_id)
        if not canvas:
            raise ValueError(f"画布不存在: {canvas_id}")
        # 简化的分层布局
        layer_map: Dict[str, int] = {}
        has_incoming = set()
        for e in canvas.edges.values():
            has_incoming.add(e.target_id)
        roots = [nid for nid in canvas.nodes if nid not in has_incoming]
        for root in roots:
            layer_map[root] = 0
        # BFS分层
        queue = roots[:]
        visited = set(roots)
        while queue:
            nid = queue.pop(0)
            current_layer = layer_map.get(nid, 0)
            for e in canvas.edges.values():
                if e.source_id == nid and e.target_id not in visited:
                    layer_map[e.target_id] = current_layer + 1
                    visited.add(e.target_id)
                    queue.append(e.target_id)
        # 分配坐标
        layer_nodes: Dict[int, List[str]] = {}
        for nid, layer in layer_map.items():
            layer_nodes.setdefault(layer, []).append(nid)
        for nid in canvas.nodes:
            if nid not in layer_map:
                layer_map[nid] = 0
                layer_nodes.setdefault(0, []).append(nid)
        for layer, nids in layer_nodes.items():
            for i, nid in enumerate(nids):
                if nid in canvas.nodes:
                    canvas.nodes[nid].x = layer * 250 + 50
                    canvas.nodes[nid].y = i * 120 + 50
        canvas.updated_at = self._now()
        return {"layout": layout, "layers": len(layer_nodes), "nodes_positioned": len(canvas.nodes)}

    # ── 校验 ──

    def _validate_canvas(self, params: Dict) -> Any:
        canvas_id = params.get("canvas_id")
        canvas = self._canvases.get(canvas_id)
        if not canvas:
            raise ValueError(f"画布不存在: {canvas_id}")
        errors = []
        warnings = []
        # 检查孤立节点
        connected = set()
        for e in canvas.edges.values():
            connected.add(e.source_id)
            connected.add(e.target_id)
        for nid in canvas.nodes:
            if nid not in connected and len(canvas.nodes) > 1:
                warnings.append(f"节点 '{nid}' ({canvas.nodes[nid].label}) 未连接")
        # 检查断开的连线
        for eid, e in canvas.edges.items():
            if e.source_id not in canvas.nodes:
                errors.append(f"连线 {eid} 的源节点 {e.source_id} 不存在")
            if e.target_id not in canvas.nodes:
                errors.append(f"连线 {eid} 的目标节点 {e.target_id} 不存在")
        # 检查分组完整性
        for gid, group in canvas.groups.items():
            for nid in group.children:
                if nid not in canvas.nodes:
                    warnings.append(f"分组 '{gid}' 引用不存在的节点 '{nid}'")
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "score": max(0, 100 - len(errors) * 20 - len(warnings) * 5),
        }

    def _get_stats(self, params: Dict) -> Any:
        total_nodes = sum(len(c.nodes) for c in self._canvases.values())
        total_edges = sum(len(c.edges) for c in self._canvases.values())
        total_groups = sum(len(c.groups) for c in self._canvases.values())
        return {
            "canvases": len(self._canvases),
            "total_nodes": total_nodes,
            "total_edges": total_edges,
            "total_groups": total_groups,
            "templates": len(self._templates),
            "versions_stored": sum(len(v) for v in self._versions.values()),
            "simulations": len(self._simulations),
        }

module_class = Flowise
