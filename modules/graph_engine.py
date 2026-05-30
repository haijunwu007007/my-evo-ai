"""
AUTO-EVO-AI V0.1 — 图引擎
Grade: A (生产级) | Category: 数据处理
职责：图数据存储、节点/边管理、路径查找、图遍历、关系查询
"""

__module_meta__ = {
    "id": "graph-engine",
    "name": "Graph Engine",
    "version": "V0.1",
    "group": "developer",
    "inputs": [
        {"name": "config", "type": "string", "required": True, "description": ""},
        {"name": "action", "type": "string", "required": True, "description": ""},
        {"name": "params", "type": "string", "required": True, "description": ""},
        {"name": "source", "type": "string", "required": True, "description": ""},
        {"name": "target", "type": "string", "required": True, "description": ""},
        {"name": "relation", "type": "string", "required": True, "description": ""},
    ],
    "outputs": [
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
    ],
    "triggers": [],
    "depends_on": [],
    "tags": ["engine", "graph"],
    "grade": "B",
    "description": "AUTO-EVO-AI V0.1 — 图引擎 Grade: A (生产级) | Category: 数据处理",
}

import os
import asyncio
import time
import logging
from typing import Any, Dict, List, Optional, Set
from enum import Enum
from dataclasses import dataclass, field
from collections import defaultdict, deque

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

logger = logging.getLogger("graph_engine")

@dataclass
class GraphNode:
    node_id: str
    label: str = ""
    properties: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

@dataclass
class GraphEdge:
    edge_id: str
    source: str
    target: str
    relation: str = ""
    weight: float = 1.0
    properties: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

@dataclass
class PathResult:
    nodes: List[str] = field(default_factory=list)
    edges: List[str] = field(default_factory=list)
    total_weight: float = 0.0

class GraphEngine(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    MODULE_ID = "graph_engine"
    MODULE_NAME = "图引擎"
    VERSION = "V0.1"
    MODULE_LEVEL = "A"

    def __init__(self, config: Optional[Dict[str, Any]] = None):

        super().__init__(config)
        self.module_level = self.MODULE_LEVEL
        self._audit = None
        self._metrics = metrics_collector
        self._nodes: Dict[str, GraphNode] = {}
        self._edges: Dict[str, GraphEdge] = {}
        self._adj: Dict[str, List[str]] = defaultdict(list)  # node_id -> [edge_ids]
        self._reverse_adj: Dict[str, List[str]] = defaultdict(list)
        self._counter: int = 0

    def initialize(self) -> None:
        try:
            self._nodes.clear()
            self._edges.clear()
            self._adj.clear()
            self._reverse_adj.clear()
            # 默认图数据
            node_data = [
                ("user_alice", "User", {"name": "Alice", "role": "admin"}),
                ("user_bob", "User", {"name": "Bob", "role": "member"}),
                ("user_charlie", "User", {"name": "Charlie", "role": "member"}),
                ("group_eng", "Group", {"name": "Engineering"}),
                ("project_bgos", "Project", {"name": "BGOS"}),
            ]
            for nid, label, props in node_data:
                self._nodes[nid] = GraphNode(node_id=nid, label=label, properties=props)
            edge_data = [
                ("user_alice", "group_eng", "belongs_to"),
                ("user_bob", "group_eng", "belongs_to"),
                ("group_eng", "project_bgos", "works_on"),
                ("user_alice", "user_bob", "manages"),
                ("user_bob", "user_charlie", "collaborates"),
            ]
            for src, tgt, rel in edge_data:
                self._add_edge(src, tgt, rel)
            if self._audit:
                self._audit.log("graph_engine_initialized", {"nodes": len(self._nodes), "edges": len(self._edges)})
            self.stats.success_count += 1
        except Exception as e:
            self.stats.error_count += 1
            raise

    async def execute(self, action: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        self.trace("execute", {"module": "graph_engine"})
        self.metrics_collector.counter("graph_engine.execute.calls", 1)
        self.audit("execute", {"module": "graph_engine"})
        params = params or {}
        start = time.time()
        ok = False
        err = None
        try:
            if action == "add_node":
                nid = params.get("node_id", "")
                label = params.get("label", "")
                if not nid:
                    return {"success": False, "error": "Missing: node_id"}
                self._nodes[nid] = GraphNode(node_id=nid, label=label, properties=params.get("properties", {}))
                ok = True
                return {"success": True, "result": {"node_id": nid}}
            elif action == "add_edge":
                src = params.get("source", "")
                tgt = params.get("target", "")
                rel = params.get("relation", "")
                if not src or not tgt:
                    return {"success": False, "error": "Missing: source, target"}
                e = self._add_edge(src, tgt, rel, params.get("weight", 1.0))
                ok = True
                return {"success": True, "result": {"edge_id": e.edge_id}}
            elif action == "get_node":
                nid = params.get("node_id", "")
                n = self._nodes.get(nid)
                if not n:
                    return {"success": False, "error": "Not found"}
                neighbors = self._get_neighbors(nid)
                return {
                    "success": True,
                    "result": {
                        "node_id": n.node_id,
                        "label": n.label,
                        "properties": n.properties,
                        "degree": len(neighbors),
                    },
                }
            elif action == "get_edge":
                eid = params.get("edge_id", "")
                e = self._edges.get(eid)
                if not e:
                    return {"success": False, "error": "Not found"}
                return {
                    "success": True,
                    "result": {
                        "edge_id": e.edge_id,
                        "source": e.source,
                        "target": e.target,
                        "relation": e.relation,
                        "weight": e.weight,
                    },
                }
            elif action == "get_neighbors":
                nid = params.get("node_id", "")
                if not nid:
                    return {"success": False, "error": "Missing: node_id"}
                return {"success": True, "result": self._get_neighbors(nid)}
            elif action == "shortest_path":
                src = params.get("source", "")
                tgt = params.get("target", "")
                if not src or not tgt:
                    return {"success": False, "error": "Missing: source, target"}
                path = self._shortest_path(src, tgt)
                return {"success": True, "result": {"path": path.nodes, "weight": round(path.total_weight, 3)}}
            elif action == "find_paths":
                src = params.get("source", "")
                tgt = params.get("target", "")
                max_depth = params.get("max_depth", 5)
                if not src or not tgt:
                    return {"success": False, "error": "Missing: source, target"}
                paths = self._find_all_paths(src, tgt, max_depth)
                return {
                    "success": True,
                    "result": [{"path": p.nodes, "weight": round(p.total_weight, 3)} for p in paths],
                }
            elif action == "query_nodes":
                label = params.get("label", "")
                props = params.get("properties", {})
                results = []
                for n in self._nodes.values():
                    if label and n.label != label:
                        continue
                    match = all(n.properties.get(k) == v for k, v in props.items())
                    if match:
                        results.append({"node_id": n.node_id, "label": n.label, "properties": n.properties})
                return {"success": True, "result": results}
            elif action == "query_edges":
                relation = params.get("relation", "")
                results = []
                for e in self._edges.values():
                    if relation and e.relation != relation:
                        continue
                    results.append(
                        {"edge_id": e.edge_id, "source": e.source, "target": e.target, "relation": e.relation}
                    )
                return {"success": True, "result": results}
            elif action == "get_stats":
                return {
                    "success": True,
                    "result": {
                        "nodes": len(self._nodes),
                        "edges": len(self._edges),
                        "labels": list(set(n.label for n in self._nodes.values())),
                        "relations": list(set(e.relation for e in self._edges.values())),
                    },
                }
            else:
                return {"success": False, "error": f"Unknown: {action}"}
        except Exception as e:
            err = str(e)
            return {"success": False, "error": err}
        finally:
            self.stats.record_request((time.time() - start) * 1000, ok, err)

    def health_check(self) -> Dict[str, Any]:
        return {
            "status": "healthy",
            "module_id": self.module_id,
            "module_level": self.module_level,
            "nodes": len(self._nodes),
            "edges": len(self._edges),
        }

    def shutdown(self) -> None:
        self._nodes.clear()
        self._edges.clear()
        self._adj.clear()
        self._reverse_adj.clear()
        super().shutdown()

    def _add_edge(self, source: str, target: str, relation: str = "", weight: float = 1.0) -> GraphEdge:
        self._counter += 1
        eid = f"edge_{self._counter}"
        e = GraphEdge(edge_id=eid, source=source, target=target, relation=relation, weight=weight)
        self._edges[eid] = e
        self._adj[source].append(eid)
        self._reverse_adj[target].append(eid)
        return e

    def _get_neighbors(self, node_id: str) -> List[Dict]:
        neighbors = []
        for eid in self._adj.get(node_id, []):
            e = self._edges.get(eid)
            if e:
                neighbors.append({"node_id": e.target, "relation": e.relation, "weight": e.weight})
        return neighbors

    def _shortest_path(self, source: str, target: str) -> PathResult:
        if source not in self._nodes or target not in self._nodes:
            return PathResult()
        visited = {source}
        queue = deque([(source, [])])
        while queue:
            current, path = queue.popleft()
            new_path = path + [current]
            if current == target:
                weight = 0
                for i in range(len(new_path) - 1):
                    for eid in self._adj.get(new_path[i], []):
                        e = self._edges.get(eid)
                        if e and e.target == new_path[i + 1]:
                            weight += e.weight
                            break
                return PathResult(nodes=new_path, total_weight=weight)
            for eid in self._adj.get(current, []):
                e = self._edges.get(eid)
                if e and e.target not in visited:
                    visited.add(e.target)
                    queue.append((e.target, new_path))
        return PathResult()

    def _find_all_paths(self, source: str, target: str, max_depth: int) -> List[PathResult]:
        if source not in self._nodes or target not in self._nodes:
            return []
        results = []

        def dfs(node: str, path: List[str], visited: Set[str], depth: int):
            if depth > max_depth:
                return
            if node == target:
                weight = 0
                for i in range(len(path) - 1):
                    for eid in self._adj.get(path[i], []):
                        e = self._edges.get(eid)
                        if e and e.target == path[i + 1]:
                            weight += e.weight
                            break
                results.append(PathResult(nodes=list(path), total_weight=weight))
                return
            for eid in self._adj.get(node, []):
                e = self._edges.get(eid)
                if e and e.target not in visited:
                    visited.add(e.target)
                    path.append(e.target)
                    dfs(e.target, path, visited, depth + 1)
                    path.pop()
                    visited.remove(e.target)

        dfs(source, [source], {source}, 0)
        return results

    def get_graph_statistics(self) -> Dict[str, Any]:
        """图统计信息。企业场景：知识图谱管理员查看图谱规模、密度、
        连通性等指标，评估数据质量。
        """
        total_nodes = len(self._nodes)
        total_edges = len(self._edges)
        # 计算度分布
        node_degrees = {}
        for nid in self._nodes:
            node_degrees[nid] = 0
        for edge in self._edges.values():
            node_degrees[edge.source] = node_degrees.get(edge.source, 0) + 1
            node_degrees[edge.target] = node_degrees.get(edge.target, 0) + 1
        if total_nodes > 0:
            avg_degree = round(sum(node_degrees.values()) / total_nodes, 2)
            max_degree = max(node_degrees.values()) if node_degrees else 0
        else:
            avg_degree = 0
            max_degree = 0
        # 孤立节点
        isolated = sum(1 for d in node_degrees.values() if d == 0)
        density = round(2 * total_edges / max(total_nodes * (total_nodes - 1), 1), 4)
        # 类型分布
        node_types = {}
        for nid, node in self._nodes.items():
            ntype = getattr(node, "node_type", "default")
            node_types[ntype] = node_types.get(ntype, 0) + 1
        return {
            "success": True,
            "total_nodes": total_nodes,
            "total_edges": total_edges,
            "avg_degree": avg_degree,
            "max_degree": max_degree,
            "isolated_nodes": isolated,
            "density": density,
            "node_types": node_types,
            "hub_nodes": sorted(node_degrees.items(), key=lambda x: -x[1])[:10],
        }

    def find_shortest_path(self, source: str, target: str) -> Dict[str, Any]:
        """最短路径（BFS）。企业场景：社交网络分析中查找两个用户的
        最短关系链路，推荐"你可能认识的人"。
        """
        if source not in self._nodes or target not in self._nodes:
            return {"success": False, "error": "节点不存在"}
        if source == target:
            return {"success": True, "path": [source], "length": 0}
        from collections import deque

        queue = deque([(source, [source])])
        visited = {source}
        while queue:
            node, path = queue.popleft()
            for eid in self._adj.get(node, []):
                edge = self._edges.get(eid)
                if not edge:
                    continue
                next_node = edge.target
                if next_node in visited:
                    continue
                visited.add(next_node)
                new_path = path + [next_node]
                if next_node == target:
                    return {"success": True, "path": new_path, "length": len(new_path) - 1}
                queue.append((next_node, new_path))
        return {"success": True, "path": [], "length": -1, "message": "无可达路径"}

    def get_node_neighbors(self, node_id: str, depth: int = 1) -> Dict[str, Any]:
        """获取节点邻居。企业场景：知识图谱探索时查看某实体的关联实体
        及其属性，辅助信息检索和关系发现。
        """
        if node_id not in self._nodes:
            return {"success": False, "error": f"节点 {node_id} 不存在"}
        neighbors = {"nodes": [], "edges": []}
        visited = {node_id}
        current_level = {node_id}
        for _ in range(depth):
            next_level = set()
            for nid in current_level:
                for eid in self._adj.get(nid, []):
                    edge = self._edges.get(eid)
                    if not edge:
                        continue
                    peer = edge.target if edge.source == nid else edge.source
                    if peer not in visited:
                        visited.add(peer)
                        next_level.add(peer)
                        node = self._nodes.get(peer)
                        neighbors["nodes"].append(
                            {
                                "node_id": peer,
                                "type": getattr(node, "node_type", "default") if node else "unknown",
                                "properties": getattr(node, "properties", {}) if node else {},
                            }
                        )
                    neighbors["edges"].append(
                        {
                            "edge_id": eid,
                            "source": edge.source,
                            "target": edge.target,
                            "type": getattr(edge, "edge_type", ""),
                        }
                    )
            current_level = next_level
        return {
            "success": True,
            "node_id": node_id,
            "depth": depth,
            "neighbors_count": len(neighbors["nodes"]),
            "edges_count": len(neighbors["edges"]),
            **neighbors,
        }

    def find_shortest_path(self, source_id: str, target_id: str) -> Dict[str, Any]:
        """最短路径。企业场景：社交网络中查找两人之间的最短关系链，
        或供应链中查找两个供应商之间的最短依赖路径。
        """
        nodes = getattr(self, "_nodes", {})
        edges = getattr(self, "_edges", {})
        if source_id not in nodes:
            return {"success": False, "error": f"起始节点 {source_id} 不存在"}
        if target_id not in nodes:
            return {"success": False, "error": f"目标节点 {target_id} 不存在"}
        # BFS最短路径
        from collections import deque

        queue = deque([(source_id, [source_id])])
        visited = {source_id}
        while queue:
            current, path = queue.popleft()
            if current == target_id:
                return {
                    "success": True,
                    "source": source_id,
                    "target": target_id,
                    "path_length": len(path) - 1,
                    "path": path,
                }
            for eid, edge in edges.items():
                if edge.source == current and edge.target not in visited:
                    visited.add(edge.target)
                    queue.append((edge.target, path + [edge.target]))
                elif edge.target == current and edge.source not in visited:
                    visited.add(edge.source)
                    queue.append((edge.source, path + [edge.source]))
        return {
            "success": True,
            "source": source_id,
            "target": target_id,
            "path_length": -1,
            "path": [],
            "message": "无可达路径",
        }

    def get_graph_statistics(self) -> Dict[str, Any]:
        """图统计。企业场景：知识图谱分析时获取节点数、边数、
        平均度数、连通分量数，评估图谱完整度。
        """
        nodes = getattr(self, "_nodes", {})
        edges = getattr(self, "_edges", {})
        # 度数统计
        degree_count = {}
        for node_id in nodes:
            degree_count[node_id] = 0
        for edge in edges.values():
            degree_count[edge.source] = degree_count.get(edge.source, 0) + 1
            degree_count[edge.target] = degree_count.get(edge.target, 0) + 1
        degrees = list(degree_count.values())
        avg_degree = sum(degrees) / max(len(degrees), 1)
        max_degree = max(degrees) if degrees else 0
        # 节点类型分布
        type_dist = {}
        for node in nodes.values():
            nt = getattr(node, "node_type", "default")
            type_dist[nt] = type_dist.get(nt, 0) + 1
        # 边类型分布
        edge_type_dist = {}
        for edge in edges.values():
            et = getattr(edge, "edge_type", "")
            edge_type_dist[et] = edge_type_dist.get(et, 0) + 1
        return {
            "success": True,
            "node_count": len(nodes),
            "edge_count": len(edges),
            "avg_degree": round(avg_degree, 2),
            "max_degree": max_degree,
            "node_type_distribution": type_dist,
            "edge_type_distribution": edge_type_dist,
        }

    def find_shortest_path(self, source: str, target: str, max_depth: int = 10) -> Dict[str, Any]:
        """BFS最短路径。企业场景：社交网络好友推荐、知识图谱关系查询、
        微服务调用链路追踪，查找两个节点间的最短关系路径。
        """
        nodes = getattr(self, "_nodes", {})
        edges = getattr(self, "_edges", [])
        if source not in nodes or target not in nodes:
            return {"success": False, "error": "源节点或目标节点不存在", "source": source, "target": target}
        if source == target:
            return {"success": True, "path": [source], "length": 0, "edges_traversed": []}
        # BFS
        from collections import deque

        visited = {source}
        queue = deque([(source, [source])])
        found_path = None
        found_edges = []
        # 邻接表
        adj = {}
        for e in edges:
            s = getattr(e, "source", "")
            t = getattr(e, "target", "")
            eid = getattr(e, "edge_id", "")
            adj.setdefault(s, []).append((t, eid))
            adj.setdefault(t, []).append((s, eid))  # 无向
        while queue and len(found_path or []) == 0:
            current, path = queue.popleft()
            if len(path) > max_depth + 1:
                break
            for neighbor, eid in adj.get(current, []):
                if neighbor == target:
                    found_path = path + [target]
                    found_edges = eid
                    break
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))
        if found_path:
            return {"success": True, "path": found_path, "length": len(found_path) - 1, "nodes_explored": len(visited)}
        return {
            "success": False,
            "path": None,
            "error": f"在深度{max_depth}内未找到路径",
            "nodes_explored": len(visited),
        }

module_class = GraphEngine
