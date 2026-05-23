"""
AUTO-EVO-AI v6.39 — 数据血缘追踪模块
Grade: A (生产级) | Category: 数据治理
职责：追踪数据从源头到消费端的完整血缘关系，支持血缘图构建、影响分析、数据溯源
"""

__module_meta__ = {
    "id": "data-lineage",
    "name": "Data Lineage",
    "version": "1.0.0",
    "group": "data",
    "inputs": [
        {"name": "prefix", "type": "string", "required": True, "description": ""},
        {"name": "name", "type": "string", "required": True, "description": ""},
        {"name": "node_type", "type": "string", "required": True, "description": ""},
        {"name": "source_system", "type": "string", "required": True, "description": ""},
        {"name": "metadata", "type": "string", "required": True, "description": ""},
        {"name": "source_node_id", "type": "string", "required": True, "description": ""},
    ],
    "outputs": [
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
    ],
    "triggers": [],
    "depends_on": [],
    "tags": ["data", "manager"],
    "grade": "A",
    "description": "AUTO-EVO-AI v6.39 — 数据血缘追踪模块 Grade: A (生产级) | Category: 数据治理",
}

import os
import re
import json
import hashlib
import time
import logging
import threading
from typing import Any, Dict, List, Optional, Set, Tuple
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
from collections import defaultdict

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
logger = logging.getLogger("data_lineage")

class LineageNodeType(Enum):
    """血缘节点类型"""

    SOURCE = "source"  # 数据源（数据库、API、文件）
    TRANSFORM = "transform"  # 转换/处理节点
    STORAGE = "storage"  # 存储节点
    CONSUMER = "consumer"  # 消费端（报表、API输出）
    DERIVED = "derived"  # 派生数据

class LineageChangeType(Enum):
    """变更类型"""

    SCHEMA_CHANGE = "schema_change"
    DATA_FLOW_CHANGE = "data_flow_change"
    NODE_ADDED = "node_added"
    NODE_REMOVED = "node_removed"
    TRANSFORMATION_CHANGE = "transformation_change"

@dataclass
class LineageNode:
    """血缘节点"""

    node_id: str
    name: str
    node_type: LineageNodeType
    source_system: str = ""
    schema_hash: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    tags: List[str] = field(default_factory=list)

@dataclass
class LineageEdge:
    """血缘边（数据流）"""

    edge_id: str
    source_node_id: str
    target_node_id: str
    transformation: str = ""  # 转换逻辑描述
    column_mapping: Dict[str, str] = field(default_factory=dict)
    confidence: float = 1.0
    created_at: float = field(default_factory=time.time)

@dataclass
class LineageImpact:
    """影响分析结果"""

    affected_nodes: List[str] = field(default_factory=list)
    affected_edges: List[str] = field(default_factory=list)
    downstream_depth: int = 0
    risk_level: str = "low"  # low/medium/high/critical
    estimated_records_impact: int = 0

class DataLineageManager(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """数据血缘追踪管理器 - 生产级实现"""

    def __init__(self):

        super().__init__()
        self._nodes: Dict[str, LineageNode] = {}
        self._edges: Dict[str, LineageEdge] = {}
        self._outgoing: Dict[str, Set[str]] = defaultdict(set)  # node_id -> [edge_ids]
        self._incoming: Dict[str, Set[str]] = defaultdict(set)  # node_id -> [edge_ids]
        self._lock = threading.RLock()
        self._audit = AuditLogger()
        self._change_history: List[Dict[str, Any]] = []
        self._max_history = 10000

    def _generate_id(self, prefix: str, *parts: str) -> str:
        raw = "|".join(parts) + str(time.time())
        return f"{prefix}_{hashlib.md5(raw.encode()).hexdigest()[:12]}"

    @trace_operation("lineage.add_node")
    def add_node(
        self, name: str, node_type: str, source_system: str = "", metadata: dict = None, tags: list = None
    ) -> Dict[str, Any]:
        """注册血缘节点"""
        try:
            nt = LineageNodeType(node_type) if isinstance(node_type, str) else node_type
            node_id = self._generate_id("node", name, source_system)
            node = LineageNode(
                node_id=node_id,
                name=name,
                node_type=nt,
                source_system=source_system,
                metadata=metadata or {},
                tags=tags or [],
            )
            with self._lock:
                self._nodes[node_id] = node
            self._audit.log("lineage_node_added", {"node_id": node_id, "name": name, "type": nt.value})
            self.record_metric("lineage_nodes_total", 1)
            return {"success": True, "node_id": node_id, "name": name}
        except Exception as e:
            logger.error(f"添加血缘节点失败: {e}")
            return {"success": False, "error": str(e)}

    @trace_operation("lineage.add_edge")
    def add_edge(
        self, source_node_id: str, target_node_id: str, transformation: str = "", column_mapping: dict = None
    ) -> Dict[str, Any]:
        """添加血缘关系（数据流）"""
        try:
            with self._lock:
                if source_node_id not in self._nodes:
                    return {"success": False, "error": f"源节点不存在: {source_node_id}"}
                if target_node_id not in self._nodes:
                    return {"success": False, "error": f"目标节点不存在: {target_node_id}"}
                edge_id = self._generate_id("edge", source_node_id, target_node_id)
                edge = LineageEdge(
                    edge_id=edge_id,
                    source_node_id=source_node_id,
                    target_node_id=target_node_id,
                    transformation=transformation,
                    column_mapping=column_mapping or {},
                )
                self._edges[edge_id] = edge
                self._outgoing[source_node_id].add(edge_id)
                self._incoming[target_node_id].add(edge_id)
            self._record_change(LineageChangeType.DATA_FLOW_CHANGE, edge_id)
            self.record_metric("lineage_edges_total", 1)
            return {"success": True, "edge_id": edge_id}
        except Exception as e:
            logger.error(f"添加血缘边失败: {e}")
            return {"success": False, "error": str(e)}

    @trace_operation("lineage.trace_upstream")
    def trace_upstream(self, node_id: str, max_depth: int = 10) -> Dict[str, Any]:
        """向上溯源：找出影响该节点的所有上游节点"""
        try:
            visited = set()
            result_nodes = []
            result_edges = []
            queue = [(node_id, 0)]
            while queue:
                current, depth = queue.pop(0)
                if current in visited or depth > max_depth:
                    continue
                visited.add(current)
                with self._lock:
                    if current in self._nodes:
                        result_nodes.append(
                            {
                                "node_id": current,
                                "name": self._nodes[current].name,
                                "type": self._nodes[current].node_type.value,
                                "depth": depth,
                            }
                        )
                    for eid in self._incoming.get(current, set()):
                        edge = self._edges.get(eid)
                        if edge:
                            result_edges.append(
                                {
                                    "edge_id": eid,
                                    "from": edge.source_node_id,
                                    "to": edge.target_node_id,
                                    "transformation": edge.transformation,
                                }
                            )
                            queue.append((edge.source_node_id, depth + 1))
            return {
                "success": True,
                "target_node": node_id,
                "upstream_nodes": result_nodes,
                "upstream_edges": result_edges,
                "total_reachable": len(visited) - 1,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    @trace_operation("lineage.trace_downstream")
    def trace_downstream(self, node_id: str, max_depth: int = 10) -> Dict[str, Any]:
        """向下追踪：找出该节点影响的所有下游节点"""
        try:
            visited = set()
            result_nodes = []
            queue = [(node_id, 0)]
            while queue:
                current, depth = queue.pop(0)
                if current in visited or depth > max_depth:
                    continue
                visited.add(current)
                with self._lock:
                    if current in self._nodes and depth > 0:
                        result_nodes.append(
                            {
                                "node_id": current,
                                "name": self._nodes[current].name,
                                "type": self._nodes[current].node_type.value,
                                "depth": depth,
                            }
                        )
                    for eid in self._outgoing.get(current, set()):
                        edge = self._edges.get(eid)
                        if edge:
                            queue.append((edge.target_node_id, depth + 1))
            return {
                "success": True,
                "source_node": node_id,
                "downstream_nodes": result_nodes,
                "total_affected": len(visited) - 1,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    @trace_operation("lineage.impact_analysis")
    def impact_analysis(self, node_id: str) -> Dict[str, Any]:
        """变更影响分析：评估某节点变更的下游影响"""
        try:
            downstream = self.trace_downstream(node_id, max_depth=20)
            if not downstream.get("success"):
                return downstream
            affected = downstream["downstream_nodes"]
            depths = [n["depth"] for n in affected]
            max_depth = max(depths) if depths else 0
            # 风险评估
            if max_depth >= 5:
                risk = "critical"
            elif max_depth >= 3:
                risk = "high"
            elif max_depth >= 2:
                risk = "medium"
            else:
                risk = "low"
            # 按类型分组
            by_type = defaultdict(list)
            for n in affected:
                by_type[n["type"]].append(n["name"])
            return {
                "success": True,
                "node_id": node_id,
                "risk_level": risk,
                "total_affected_nodes": len(affected),
                "max_downstream_depth": max_depth,
                "affected_by_type": dict(by_type),
                "affected_nodes": affected,
                "recommendation": f"变更影响{len(affected)}个下游节点，风险等级: {risk}。建议在非高峰期执行变更。",
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    @trace_operation("lineage.get_full_graph")
    def get_full_graph(self, include_edges: bool = True) -> Dict[str, Any]:
        """获取完整血缘图"""
        with self._lock:
            nodes = [
                {
                    "node_id": n.node_id,
                    "name": n.name,
                    "type": n.node_type.value,
                    "source": n.source_system,
                    "tags": n.tags,
                }
                for n in self._nodes.values()
            ]
            edges = (
                [
                    {
                        "edge_id": e.edge_id,
                        "source": e.source_node_id,
                        "target": e.target_node_id,
                        "transformation": e.transformation,
                    }
                    for e in self._edges.values()
                ]
                if include_edges
                else []
            )
        return {"success": True, "nodes": nodes, "edges": edges, "node_count": len(nodes), "edge_count": len(edges)}

    @trace_operation("lineage.health_check")
    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        with self._lock:
            orphan_nodes = [nid for nid in self._nodes if not self._outgoing.get(nid) and not self._incoming.get(nid)]
        return {
            "healthy": True,
            "status": "ok",
            "module_id": "data_lineage",
            "total_nodes": len(self._nodes),
            "total_edges": len(self._edges),
            "orphan_nodes": len(orphan_nodes),
            "change_history_size": len(self._change_history),
            "last_check": datetime.now().isoformat(),
        }

    def _record_change(self, change_type: LineageChangeType, entity_id: str):
        self._change_history.append(
            {"type": change_type.value, "entity_id": entity_id, "timestamp": datetime.now().isoformat()}
        )
        if len(self._change_history) > self._max_history:
            self._change_history = self._change_history[-self._max_history :]

    @trace_operation("lineage.get_statistics")
    def get_statistics(self) -> Dict[str, Any]:
        """获取血缘统计"""
        with self._lock:
            by_type = defaultdict(int)
            for n in self._nodes.values():
                by_type[n.node_type.value] += 1
            total_transformations = sum(1 for e in self._edges.values() if e.transformation)
        return {
            "success": True,
            "total_nodes": len(self._nodes),
            "total_edges": len(self._edges),
            "nodes_by_type": dict(by_type),
            "edges_with_transformation": total_transformations,
            "change_events": len(self._change_history),
            "graph_connectivity": round(len(self._edges) / max(len(self._nodes), 1), 2),
        }

    async def execute(self, action: str, params: dict = None) -> dict:
        """执行桥接"""
        _ = self.trace("execute")
        metrics_collector.counter("data_lineage_ops_total", labels={"action": action})
        self.audit("execute", f"action={action}")
        params = params or {}
        actions_map = {
            "add_node": lambda: self.add_node(
                params.get("name", ""),
                params.get("node_type", "source"),
                params.get("source_system", ""),
                params.get("metadata"),
                params.get("tags"),
            ),
            "add_edge": lambda: self.add_edge(
                params.get("source_node_id", ""),
                params.get("target_node_id", ""),
                params.get("transformation", ""),
                params.get("column_mapping"),
            ),
            "trace_upstream": lambda: self.trace_upstream(params.get("node_id", ""), params.get("max_depth", 10)),
            "trace_downstream": lambda: self.trace_downstream(params.get("node_id", ""), params.get("max_depth", 10)),
            "impact_analysis": lambda: self.impact_analysis(params.get("node_id", "")),
            "get_full_graph": lambda: self.get_full_graph(params.get("include_edges", True)),
            "get_statistics": lambda: self.get_statistics(),
            "health_check": lambda: self.health_check(),
        }
        handler = actions_map.get(action)
        if handler:
            return handler()
        return {"success": False, "error": f"Unknown action: {action}"}

    def analyze_impact(self, source_table: str, change_type: str = "schema") -> Dict[str, Any]:
        """变更影响分析：上游表变更后，自动计算影响范围和风险等级"""
        lineage = self._lineage if hasattr(self, "_lineage") else {}
        # 找到直接下游
        direct_downstream = []
        for edge in lineage.get("edges", []):
            if edge.get("source") == source_table:
                direct_downstream.append(edge.get("target"))
        # 递归查找所有间接下游
        all_affected = set(direct_downstream)
        queue = list(direct_downstream)
        depth_map = {t: 1 for t in direct_downstream}
        while queue:
            current = queue.pop(0)
            for edge in lineage.get("edges", []):
                if edge.get("source") == current and edge.get("target") not in all_affected:
                    all_affected.add(edge["target"])
                    queue.append(edge["target"])
                    depth_map[edge["target"]] = depth_map.get(current, 1) + 1
        # 按影响深度分级
        critical = [t for t, d in depth_map.items() if d <= 2]
        moderate = [t for t, d in depth_map.items() if 2 < d <= 4]
        low = [t for t, d in depth_map.items() if d > 4]
        # 生成风险报告
        risk_level = "critical" if len(critical) > 5 else "high" if len(critical) > 0 else "moderate"
        if change_type == "schema":
            risk_level = "critical" if len(all_affected) > 0 else "none"
        elif change_type == "data":
            risk_level = "high" if len(critical) > 3 else "moderate"
        return {
            "source": source_table,
            "change_type": change_type,
            "risk_level": risk_level,
            "total_affected": len(all_affected),
            "direct_downstream": direct_downstream,
            "by_severity": {"critical": critical, "moderate": moderate, "low": low},
            "max_depth": max(depth_map.values()) if depth_map else 0,
            "recommendation": self._impact_recommendation(risk_level, len(all_affected)),
        }

    def _impact_recommendation(self, risk_level: str, affected_count: int) -> str:
        if risk_level == "critical":
            return f"影响{affected_count}张表，建议召开变更评审会议，通知所有下游团队"
        elif risk_level == "high":
            return f"影响{affected_count}张表，建议在低峰期执行变更，准备回滚方案"
        else:
            return f"影响{affected_count}张表，常规变更流程即可"

    def check_lineage_completeness(self, schema_tables: List[str]) -> Dict[str, Any]:
        """血缘完整性检查：对比实际表与血缘图，发现未登记的数据依赖"""
        lineage = self._lineage if hasattr(self, "_lineage") else {}
        graph_tables = set()
        for edge in lineage.get("edges", []):
            graph_tables.add(edge.get("source", ""))
            graph_tables.add(edge.get("target", ""))
        schema_set = set(schema_tables)
        # 未登记的表
        unregistered = schema_set - graph_tables
        # 血缘图中不存在的幽灵表
        ghost_tables = graph_tables - schema_set
        # 计算覆盖率
        coverage = len(schema_set & graph_tables) / max(len(schema_set), 1)
        # 孤立表（在血缘图中但没有上下游关系）
        source_tables = set(e.get("source") for e in lineage.get("edges", []))
        target_tables = set(e.get("target") for e in lineage.get("edges", []))
        isolated = graph_tables - source_tables - target_tables
        return {
            "schema_tables": len(schema_set),
            "lineage_tables": len(graph_tables),
            "coverage": round(coverage, 4),
            "unregistered": sorted(unregistered),
            "ghost_tables": sorted(ghost_tables),
            "isolated_tables": sorted(isolated),
            "grade": "A" if coverage > 0.95 else "B" if coverage > 0.8 else "C" if coverage > 0.6 else "D",
        }

    def trace_column_lineage(self, table: str, column: str, direction: str = "downstream") -> Dict[str, Any]:
        """字段级血缘追踪：追踪某个字段的数据流转路径"""
        lineage = self._lineage if hasattr(self, "_lineage") else {}
        column_edges = lineage.get("column_edges", [])
        path = []
        visited = set()
        current = f"{table}.{column}"
        queue = [current]
        depth = 0
        while queue and depth < 10:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            if direction == "downstream":
                for ce in column_edges:
                    if ce.get("source_col") == current:
                        path.append(
                            {"from": current, "to": ce.get("target_col"), "transform": ce.get("transform", "direct")}
                        )
                        queue.append(ce["target_col"])
            else:
                for ce in column_edges:
                    if ce.get("target_col") == current:
                        path.append(
                            {"from": ce.get("source_col"), "to": current, "transform": ce.get("transform", "direct")}
                        )
                        queue.append(ce["source_col"])
            depth += 1
        return {"start": f"{table}.{column}", "direction": direction, "path_length": len(path), "path": path[:50]}

    def export_lineage_report(self, tables: List[str] = None, format: str = "dict") -> Dict[str, Any]:
        """导出血缘报告：汇总指定表的上下游依赖关系"""
        lineage = self._lineage if hasattr(self, "_lineage") else {}
        edges = lineage.get("edges", [])
        target_tables = set(tables) if tables else None
        upstream = {}
        downstream = {}
        for edge in edges:
            src = edge.get("source", "")
            tgt = edge.get("target", "")
            if target_tables and src not in target_tables and tgt not in target_tables:
                continue
            downstream.setdefault(src, []).append(tgt)
            upstream.setdefault(tgt, []).append(src)
        report_tables = target_tables or set(downstream.keys()) | set(upstream.keys())
        table_details = []
        for t in sorted(report_tables):
            table_details.append(
                {
                    "table": t,
                    "upstream_count": len(upstream.get(t, [])),
                    "downstream_count": len(downstream.get(t, [])),
                    "upstream": upstream.get(t, []),
                    "downstream": downstream.get(t, []),
                }
            )
        return {"total_tables": len(report_tables), "total_edges": len(edges), "tables": table_details}

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

    def shutdown(self) -> dict:
        """Graceful shutdown for data_lineage."""
        self.status = "stopped"
        self.logger.info("%s shutdown complete", self.__class__.__name__)
        return {"success": True, "module": self.__class__.__name__}

    def initialize(self) -> dict:
        """Initialize data_lineage."""
        self.status = "initialized"
        self._start_time = time.time()
        self.status = "active"
        self.logger.info("%s initialized", self.__class__.__name__)
        return {"success": True, "module": self.__class__.__name__}

module_class = DataLineageManager
