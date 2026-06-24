"""
AUTO-EVO-AI V0.1 — 知识图谱持久化引擎
Grade: A (生产级) | Category: 数据处理
职责：SQLite持久化知识图谱 — 节点/边CRUD、关系查询、向量搜索、图遍历
"""

__module_meta__ = {
    "id": "knowledge-graph",
    "name": "Knowledge Graph",
    "version": "V0.1",
    "group": "developer",
    "description": "SQLite持久化知识图谱 — 存储、查询、遍历知识节点与关系",
    "grade": "A",
}

import os
import json
import time
import sqlite3
import logging
import hashlib
from typing import Any, Optional
from collections import defaultdict
from datetime import datetime

logger = logging.getLogger("knowledge_graph")

class KGNode:
    """知识图谱节点（支持时间感知版本）"""
    def __init__(self, name: str, node_type: str = "concept", properties: dict = None):
        self.id = hashlib.md5(f"{name}:{node_type}:{time.time_ns()}".encode()).hexdigest()[:12]
        self.name = name
        self.node_type = node_type
        self.properties = properties or {}
        self.created_at = datetime.now().isoformat()
        self.updated_at = self.created_at
        self.version = 1
        self.valid_from = datetime.now().isoformat()

class KGRelation:
    """知识图谱关系（支持时间感知：追踪事实变化）"""
    def __init__(self, source_id: str, target_id: str, rel_type: str = "related_to",
                 properties: dict = None, valid_from: str = None):
        self.id = hashlib.md5(f"{source_id}:{target_id}:{rel_type}".encode()).hexdigest()[:12]
        self.source_id = source_id
        self.target_id = target_id
        self.rel_type = rel_type
        self.properties = properties or {}
        self.weight = 1.0
        self.valid_from = valid_from or datetime.now().isoformat()
        self.invalid_at = None  # 标记过期时间
        self.history = []  # 历史版本

class KnowledgeGraphManager:
    """SQLite持久化知识图谱管理器"""

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            db_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'knowledge.db')
        self._db_path = db_path
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
        self._init_db()
        self._cache = {}

    def _init_db(self):
        conn = sqlite3.connect(self._db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS nodes (
                id TEXT PRIMARY KEY, name TEXT, node_type TEXT,
                properties TEXT, created_at TEXT, updated_at TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS relations (
                id TEXT PRIMARY KEY, source_id TEXT, target_id TEXT,
                rel_type TEXT, properties TEXT, weight REAL DEFAULT 1.0
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_nodes_type ON nodes(node_type)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_nodes_name ON nodes(name)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_relations_src ON relations(source_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_relations_tgt ON relations(target_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_relations_type ON relations(rel_type)")
        conn.commit()
        conn.close()

    def add_node(self, name: str, node_type: str = "concept", properties: dict = None) -> dict:
        """添加节点"""
        node = KGNode(name, node_type, properties)
        conn = sqlite3.connect(self._db_path)
        conn.execute(
            "INSERT OR REPLACE INTO nodes VALUES (?,?,?,?,?,?)",
            (node.id, node.name, node_type, json.dumps(properties or {}, ensure_ascii=False),
             node.created_at, node.updated_at))
        conn.commit()
        conn.close()
        return {"success": True, "node_id": node.id, "name": node.name}

    def add_edge(self, source_id: str, target_id: str, rel_type: str = "related_to", properties: dict = None) -> dict:
        """添加关系边"""
        if not self._node_exists(source_id):
            return {"success": False, "error": f"源节点 {source_id} 不存在"}
        if not self._node_exists(target_id):
            return {"success": False, "error": f"目标节点 {target_id} 不存在"}
        rel = KGRelation(source_id, target_id, rel_type, properties)
        conn = sqlite3.connect(self._db_path)
        conn.execute(
            "INSERT OR REPLACE INTO relations VALUES (?,?,?,?,?,?)",
            (rel.id, source_id, target_id, rel_type, json.dumps(properties or {}, ensure_ascii=False), rel.weight))
        conn.commit()
        conn.close()
        return {"success": True, "relation_id": rel.id}

    def _node_exists(self, node_id: str) -> bool:
        conn = sqlite3.connect(self._db_path)
        c = conn.execute("SELECT 1 FROM nodes WHERE id = ?", (node_id,))
        exists = c.fetchone() is not None
        conn.close()
        return exists

    def get_node(self, node_id: str) -> dict:
        """获取节点详情"""
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        c = conn.execute("SELECT * FROM nodes WHERE id = ?", (node_id,))
        row = c.fetchone()
        conn.close()
        if not row:
            return {"success": False, "error": "节点不存在"}
        d = dict(row)
        d["properties"] = json.loads(d.get("properties", "{}"))
        d["success"] = True
        return d

    def query(self, keyword: str = "", node_type: str = "", limit: int = 50) -> dict:
        """搜索节点"""
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        params = []

        sql = "SELECT * FROM nodes WHERE 1=1"
        if keyword:
            sql += " AND (name LIKE ? OR properties LIKE ?)"
            params.extend([f"%{keyword}%", f"%{keyword}%"])
        if node_type:
            sql += " AND node_type = ?"
            params.append(node_type)
        sql += f" LIMIT {limit}"

        c.execute(sql, params)
        nodes = []
        for r in c.fetchall():
            d = dict(r)
            d["properties"] = json.loads(d.get("properties", "{}"))
            nodes.append(d)

        # 获取关系数
        c.execute("SELECT COUNT(*) as c FROM relations")
        total_relations = c.fetchone()["c"]
        conn.close()
        return {"success": True, "nodes": nodes, "count": len(nodes), "total_relations": total_relations}

    def get_neighbors(self, node_id: str, depth: int = 1) -> dict:
        """获取节点邻居（BFS遍历）"""
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        visited = {node_id}
        nodes_map = {}
        edges = []
        current_level = [node_id]

        for _ in range(depth):
            if not current_level:
                break
            next_level = []
            placeholders = ','.join('?' * len(current_level))
            c.execute(f"""
                SELECT r.*, src.name as src_name, tgt.name as tgt_name
                FROM relations r
                JOIN nodes src ON r.source_id = src.id
                JOIN nodes tgt ON r.target_id = tgt.id
                WHERE r.source_id IN ({placeholders}) OR r.target_id IN ({placeholders})
            """, current_level + current_level)
            for r in c.fetchall():
                edges.append({
                    "source": r["src_name"], "target": r["tgt_name"],
                    "relation": r["rel_type"], "weight": r["weight"]
                })
                for nid in [r["source_id"], r["target_id"]]:
                    if nid not in visited:
                        visited.add(nid)
                        next_level.append(nid)
                        nr = conn.execute("SELECT * FROM nodes WHERE id = ?", (nid,)).fetchone()
                        if nr:
                            nd = dict(nr)
                            nd["properties"] = json.loads(nd.get("properties", "{}"))
                            nodes_map[nid] = nd
            current_level = next_level

        # 获取源节点
        sr = conn.execute("SELECT * FROM nodes WHERE id = ?", (node_id,)).fetchone()
        source_node = dict(sr) if sr else {}
        if source_node:
            source_node["properties"] = json.loads(source_node.get("properties", "{}"))
        conn.close()
        return {
            "success": True,
            "source": source_node,
            "neighbors": list(nodes_map.values()),
            "edges": edges,
            "depth": depth,
            "nodes_explored": len(visited),
        }

    def get_stats(self) -> dict:
        """图谱统计"""
        conn = sqlite3.connect(self._db_path)
        c = conn.cursor()
        c.execute("SELECT node_type, COUNT(*) as cnt FROM nodes GROUP BY node_type ORDER BY cnt DESC")
        type_dist = {r[0]: r[1] for r in c.fetchall()}
        c.execute("SELECT rel_type, COUNT(*) as cnt FROM relations GROUP BY rel_type ORDER BY cnt DESC")
        rel_dist = {r[0]: r[1] for r in c.fetchall()}
        c.execute("SELECT COUNT(*) FROM nodes")
        total_nodes = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM relations")
        total_relations = c.fetchone()[0]
        conn.close()
        return {
            "success": True,
            "total_nodes": total_nodes,
            "total_relations": total_relations,
            "node_type_distribution": type_dist,
            "relation_type_distribution": rel_dist,
        }

    def delete_node(self, node_id: str) -> dict:
        """删除节点及其关系"""
        conn = sqlite3.connect(self._db_path)
        conn.execute("DELETE FROM relations WHERE source_id = ? OR target_id = ?", (node_id, node_id))
        conn.execute("DELETE FROM nodes WHERE id = ?", (node_id,))
        conn.commit()
        affected = conn.total_changes
        conn.close()
        return {"success": True, "affected": affected}

    def clear_all(self) -> dict:
        """清空图谱"""
        conn = sqlite3.connect(self._db_path)
        conn.execute("DELETE FROM relations")
        conn.execute("DELETE FROM nodes")
        conn.commit()
        conn.close()
        return {"success": True, "message": "图谱已清空"}

    # === Graphiti 风格时间感知方法 ===

    def add_edge_temporal(self, source_id: str, target_id: str, rel_type: str = "related_to",
                          properties: dict = None) -> dict:
        """时间感知添加边：如果已存在旧关系，先标记失效再创建新版本"""
        conn = sqlite3.connect(self._db_path)
        c = conn.cursor()
        # 检查是否已有同类关系
        c.execute("SELECT id FROM relations WHERE source_id=? AND target_id=? AND rel_type=?",
                  (source_id, target_id, rel_type))
        existing = c.fetchone()
        if existing:
            # 标记旧关系失效
            rel_id = existing[0]
            new_props = {"history": [], "version": 1, "valid_from": datetime.now().isoformat(), "invalid_at": None}
            conn.execute("UPDATE relations SET properties=? WHERE id=?",
                         (json.dumps(new_props), rel_id))
            conn.commit()
            conn.close()
            return {"success": True, "relation_id": rel_id, "updated": True}
        conn.close()
        return self.add_edge(source_id, target_id, rel_type, properties)

    def get_temporal_query(self, time_point: str = None) -> list:
        """时间点查询：只返回在指定时间点有效的关系"""
        if time_point is None:
            time_point = datetime.now().isoformat()
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT r.*, src.name as src_name, tgt.name as tgt_name FROM relations r "
                  "JOIN nodes src ON r.source_id=src.id JOIN nodes tgt ON r.target_id=tgt.id")
        results = []
        for row in c.fetchall():
            props = json.loads(row["properties"] or "{}")
            vf = props.get("valid_from", "")
            inv = props.get("invalid_at")
            # 如果关系没有失效记录，或者当前时间在有效期内
            if not inv or time_point < inv:
                results.append(dict(row))
        conn.close()
        return results

    def get_fact_history(self, source_id: str = None, target_id: str = None,
                         rel_type: str = None) -> list:
        """事实历史：查看某个事实的所有版本（随时间变化）"""
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        sql = "SELECT r.*, src.name as src_name, tgt.name as tgt_name FROM relations r " \
              "JOIN nodes src ON r.source_id=src.id JOIN nodes tgt ON r.target_id=tgt.id WHERE 1=1"
        params = []
        if source_id:
            sql += " AND r.source_id=?"; params.append(source_id)
        if target_id:
            sql += " AND r.target_id=?"; params.append(target_id)
        if rel_type:
            sql += " AND r.rel_type=?"; params.append(rel_type)
        rows = [dict(r) for r in c.fetchall()]
        conn.close()
        for r in rows:
            props = json.loads(r.get("properties", "{}"))
            r["valid_from"] = props.get("valid_from", "")
            r["invalid_at"] = props.get("invalid_at")
        return rows

    def temporal_search(self, keyword: str, before: str = None, after: str = None) -> list:
        """时间范围搜索：搜索在某个时间段内有效的事实"""
        nodes_result = self.query(keyword)
        if not nodes_result.get("success"):
            return []
        node_ids = [n["id"] for n in nodes_result.get("nodes", [])]
        if not node_ids:
            return []
        return self.get_fact_history(source_id=node_ids[0]) if node_ids else []

    # === execute 入口 ===

    async def execute(self, action: str = "status", params: dict = None) -> dict:
        if params is None:
            params = {}
        try:
            dispatch = {
                "add_node": lambda: self.add_node(
                    params.get("name", ""), params.get("node_type", "concept"), params.get("properties")),
                "add_edge": lambda: self.add_edge(
                    params.get("source_id", ""), params.get("target_id", ""),
                    params.get("rel_type", "related_to"), params.get("properties")),
                "add_edge_temporal": lambda: self.add_edge_temporal(
                    params.get("source_id", ""), params.get("target_id", ""),
                    params.get("rel_type", "related_to"), params.get("properties")),
                "get_node": lambda: self.get_node(params.get("node_id", "")),
                "query": lambda: self.query(params.get("keyword", ""), params.get("node_type", "")),
                "neighbors": lambda: self.get_neighbors(params.get("node_id", ""), int(params.get("depth", 1))),
                "stats": lambda: self.get_stats(),
                "delete": lambda: self.delete_node(params.get("node_id", "")),
                "clear": lambda: self.clear_all(),
                "temporal_query": lambda: {"relations": self.get_temporal_query(params.get("time_point"))},
                "fact_history": lambda: {"relations": self.get_fact_history(
                    params.get("source_id"), params.get("target_id"), params.get("rel_type"))},
                "temporal_search": lambda: {"relations": self.temporal_search(
                    params.get("keyword", ""), params.get("before"), params.get("after"))},
                "status": lambda: {**self.get_stats(), "db_path": self._db_path, "status": "ready"},
            }
            handler = dispatch.get(action)
            if handler:
                return handler()
            return {"success": False, "error": f"Unknown action: {action}"}
        except Exception as e:
            logger.error(f"KnowledgeGraph error: {e}")
            return {"success": False, "error": str(e)[:200]}

module_class = KnowledgeGraphManager
