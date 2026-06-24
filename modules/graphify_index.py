"""
AUTO-EVO-AI V0.1 — Graphify 代码知识图谱引擎
Grade: A (生产级) | Category: 开发者工具
职责：扫描代码目录 → AST分析 → 构建可查询的知识图谱
"""

__module_meta__ = {
    "id": "graphify-index",
    "name": "Graphify Index",
    "version": "V0.1",
    "group": "developer",
    "description": "代码AST分析引擎 — 扫描代码库生成可查询的知识图谱",
    "grade": "A",
}

import os
import ast
import json
import time
import sqlite3
import logging
import hashlib
from pathlib import Path
from typing import Any
from collections import defaultdict

logger = logging.getLogger("graphify_index")

class CodeEntity:
    """代码实体 — 函数、类、变量、导入等"""
    __slots__ = ('id', 'name', 'entity_type', 'file_path', 'line_start', 'line_end',
                 'docstring', 'signature', 'properties', 'children_ids')

    def __init__(self, name, entity_type, file_path, line_start=0, line_end=0):
        self.id = hashlib.md5(f"{file_path}:{name}:{entity_type}:{line_start}".encode()).hexdigest()[:12]
        self.name = name
        self.entity_type = entity_type
        self.file_path = file_path
        self.line_start = line_start
        self.line_end = line_end
        self.docstring = ""
        self.signature = ""
        self.properties = {}
        self.children_ids = []

class GraphifyIndex:
    """代码知识图谱索引引擎"""

    def __init__(self, db_path=None):
        self._entities = {}       # entity_id -> CodeEntity
        self._relations = []      # (source_id, target_id, relation_type, label)
        self._file_index = defaultdict(list)  # file_path -> [entity_ids]
        self._db_path = db_path or os.path.join(os.path.dirname(__file__), '..', 'data', 'graphify.db')
        self._ensure_db()

    def _ensure_db(self):
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
        conn = sqlite3.connect(self._db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS entities (
                id TEXT PRIMARY KEY, name TEXT, entity_type TEXT,
                file_path TEXT, line_start INTEGER, line_end INTEGER,
                docstring TEXT, signature TEXT, properties TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS relations (
                source_id TEXT, target_id TEXT, relation_type TEXT,
                label TEXT, FOREIGN KEY(source_id) REFERENCES entities(id),
                FOREIGN KEY(target_id) REFERENCES entities(id)
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(entity_type)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_entities_file ON entities(file_path)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_relations_src ON relations(source_id)")
        conn.commit()
        conn.close()

    def index_directory(self, directory: str, extensions: list = None) -> dict:
        """扫描目录，索引所有代码文件"""
        if extensions is None:
            extensions = ['.py', '.js', '.ts', '.java', '.go', '.rs', '.cpp', '.h']
        start = time.time()
        files_scanned = 0
        errors = 0

        for root, dirs, files in os.walk(directory):
            # 跳过隐藏目录和常见忽略目录
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ('node_modules', '__pycache__', 'venv', '.git', 'dist', 'build')]
            for fname in files:
                ext = os.path.splitext(fname)[1].lower()
                if ext not in extensions:
                    continue
                fpath = os.path.join(root, fname)
                try:
                    self._index_file(fpath)
                    files_scanned += 1
                except Exception as e:
                    errors += 1
                    logger.debug(f"索引失败 {fpath}: {e}")

        elapsed = time.time() - start
        self._persist()
        return {
            "success": True,
            "files_scanned": files_scanned,
            "entities": len(self._entities),
            "relations": len(self._relations),
            "errors": errors,
            "elapsed_seconds": round(elapsed, 2),
        }

    def _index_file(self, file_path: str):
        """索引单个文件"""
        ext = os.path.splitext(file_path)[1].lower()
        if ext == '.py':
            self._index_python(file_path)
        else:
            self._index_generic(file_path)

    def _index_python(self, file_path: str):
        """使用Python AST解析.py文件"""
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            source = f.read()
        try:
            tree = ast.parse(source, filename=file_path)
        except SyntaxError:
            return

        rel_path = os.path.relpath(file_path)
        file_entity = CodeEntity(os.path.basename(rel_path), 'file', rel_path)
        self._entities[file_entity.id] = file_entity
        self._file_index[rel_path].append(file_entity.id)

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                cls = CodeEntity(node.name, 'class', rel_path, node.lineno, (node.end_lineno or node.lineno))
                cls.docstring = ast.get_docstring(node) or ""
                cls.signature = f"class {node.name}"
                for base in node.bases:
                    base_name = self._get_name(base)
                    self._relations.append((cls.id, base_name, 'inherits', f"extends {base_name}"))
                self._entities[cls.id] = self._entities.get(cls.id, cls)
                self._file_index[rel_path].append(cls.id)
                file_entity.children_ids.append(cls.id)

                # 类下的方法
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        self._add_method(item, cls.id, rel_path)
                    elif isinstance(item, ast.Assign):
                        for target in item.targets:
                            if isinstance(target, ast.Name):
                                attr = CodeEntity(target.id, 'attribute', rel_path, item.lineno, (item.end_lineno or item.lineno))
                                self._entities[attr.id] = attr
                                self._relations.append((cls.id, attr.id, 'has_attr', target.id))

            elif isinstance(node, ast.FunctionDef):
                # 顶层函数
                fn = CodeEntity(node.name, 'function', rel_path, node.lineno, (node.end_lineno or node.lineno))
                fn.docstring = ast.get_docstring(node) or ""
                args = [a.arg for a in node.args.args]
                fn.signature = f"{node.name}({', '.join(args)})"
                fn.properties['args'] = args
                self._entities[fn.id] = fn
                self._file_index[rel_path].append(fn.id)
                file_entity.children_ids.append(fn.id)

                # 函数调用分析
                for child in ast.walk(node):
                    if isinstance(child, ast.Call):
                        called = self._get_name(child.func)
                        if called:
                            self._relations.append((fn.id, called, 'calls', f"calls {called}"))

        # 导入分析
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imp = CodeEntity(alias.name, 'import', rel_path, node.lineno, (node.end_lineno or node.lineno))
                    self._entities[imp.id] = imp
                    self._relations.append((file_entity.id, imp.id, 'imports', alias.name))
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    full = f"{module}.{alias.name}"
                    imp = CodeEntity(full, 'import', rel_path, node.lineno, (node.end_lineno or node.lineno))
                    self._entities[imp.id] = imp
                    self._relations.append((file_entity.id, imp.id, 'imports', full))

    def _add_method(self, node, parent_id, rel_path):
        """索引类中的方法"""
        fn = CodeEntity(node.name, 'method', rel_path, node.lineno, (node.end_lineno or node.lineno))
        fn.docstring = ast.get_docstring(node) or ""
        args = [a.arg for a in node.args.args]
        fn.signature = f"{node.name}({', '.join(args)})"
        fn.properties['args'] = args
        self._entities[fn.id] = fn
        self._file_index[rel_path].append(fn.id)
        self._relations.append((parent_id, fn.id, 'has_method', node.name))

        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                called = self._get_name(child.func)
                if called:
                    self._relations.append((fn.id, called, 'calls', f"calls {called}"))

    def _index_generic(self, file_path: str):
        """通用文件索引（非Python）"""
        rel_path = os.path.relpath(file_path)
        fname = os.path.basename(rel_path)
        file_entity = CodeEntity(fname, 'file', rel_path)
        self._entities[file_entity.id] = file_entity
        self._file_index[rel_path].append(file_entity.id)

    def _get_name(self, node):
        """从AST节点提取名称"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        elif isinstance(node, ast.Subscript):
            return f"{self._get_name(node.value)}[{self._get_name(node.slice) if hasattr(node,'slice') else ''}]"
        return None

    def _persist(self):
        """持久化到SQLite"""
        conn = sqlite3.connect(self._db_path)
        conn.execute("DELETE FROM entities")
        conn.execute("DELETE FROM relations")
        for eid, ent in self._entities.items():
            conn.execute(
                "INSERT OR REPLACE INTO entities VALUES (?,?,?,?,?,?,?,?,?)",
                (eid, ent.name, ent.entity_type, ent.file_path, ent.line_start, ent.line_end,
                 ent.docstring[:500] if ent.docstring else "",
                 ent.signature[:200] if ent.signature else "",
                 json.dumps(ent.properties, ensure_ascii=False)))
        for src, tgt, rtype, label in self._relations:
            conn.execute("INSERT INTO relations VALUES (?,?,?,?)", (src, tgt, rtype, label))
        conn.commit()
        conn.close()

    def query(self, qtype: str = "all", keyword: str = "", file_path: str = "", entity_type: str = "") -> dict:
        """查询知识图谱"""
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        results = {"entities": [], "relations": [], "stats": {}}

        if qtype == "stats" or qtype == "all":
            c.execute("SELECT entity_type, COUNT(*) as cnt FROM entities GROUP BY entity_type ORDER BY cnt DESC")
            results["stats"]["type_distribution"] = {r["entity_type"]: r["cnt"] for r in c.fetchall()}
            c.execute("SELECT COUNT(*) as c FROM entities")
            results["stats"]["total_entities"] = c.fetchone()["c"]
            c.execute("SELECT COUNT(*) as c FROM relations")
            results["stats"]["total_relations"] = c.fetchone()["c"]

        if qtype == "search" or keyword:
            like = f"%{keyword}%"
            c.execute("SELECT * FROM entities WHERE name LIKE ? OR docstring LIKE ? OR file_path LIKE ? LIMIT 50",
                      (like, like, like))
            results["entities"] = [dict(r) for r in c.fetchall()]

        if entity_type:
            c.execute("SELECT * FROM entities WHERE entity_type = ? LIMIT 100", (entity_type,))
            results["entities"] = [dict(r) for r in c.fetchall()]

        if file_path:
            like = f"%{file_path}%"
            c.execute("SELECT * FROM entities WHERE file_path LIKE ? LIMIT 100", (like,))
            results["entities"] = [dict(r) for r in c.fetchall()]

        if qtype == "relations" or qtype == "all":
            c.execute("""
                SELECT r.*, e1.name as src_name, e2.name as tgt_name
                FROM relations r
                LEFT JOIN entities e1 ON r.source_id = e1.id
                LEFT JOIN entities e2 ON r.target_id = e2.id
                LIMIT 200
            """)
            results["relations"] = [dict(r) for r in c.fetchall()]

        conn.close()
        results["success"] = True
        return results

    def get_call_graph(self, function_name: str = "", depth: int = 2) -> dict:
        """获取函数调用图"""
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        if function_name:
            c.execute("""
                SELECT DISTINCT r.source_id, r.target_id, r.relation_type, e.name as caller_name,
                       e2.name as callee_name
                FROM relations r
                JOIN entities e ON r.source_id = e.id
                JOIN entities e2 ON r.target_id = e2.id
                WHERE r.relation_type = 'calls' AND (e.name LIKE ? OR e2.name LIKE ?)
                LIMIT 100
            """, (f"%{function_name}%", f"%{function_name}%"))
        else:
            c.execute("""
                SELECT DISTINCT r.source_id, r.target_id, r.relation_type, e.name as caller_name,
                       e2.name as callee_name
                FROM relations r
                JOIN entities e ON r.source_id = e.id
                JOIN entities e2 ON r.target_id = e2.id
                WHERE r.relation_type = 'calls'
                LIMIT 200
            """)
        calls = [{"caller": r["caller_name"], "callee": r["callee_name"]} for r in c.fetchall()]
        conn.close()
        return {"success": True, "calls": calls, "count": len(calls)}

    def get_file_dependencies(self, file_path: str) -> dict:
        """获取文件的导入依赖"""
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        like = f"%{file_path}%"
        c = conn.cursor()
        c.execute("""
            SELECT e.name as import_name, e.file_path, r.label
            FROM relations r
            JOIN entities e ON r.target_id = e.id
            JOIN entities src ON r.source_id = src.id
            WHERE r.relation_type = 'imports' AND src.file_path LIKE ?
        """, (like,))
        imports = [dict(r) for r in c.fetchall()]
        conn.close()
        return {"success": True, "imports": imports, "count": len(imports)}

    async def execute(self, action: str = "status", params: dict = None) -> dict:
        if params is None:
            params = {}
        start = time.time()
        try:
            if action == "index":
                path = params.get("path", ".")
                return self.index_directory(path)
            elif action == "query":
                return self.query(
                    qtype=params.get("qtype", "all"),
                    keyword=params.get("keyword", ""),
                    file_path=params.get("file_path", ""),
                    entity_type=params.get("entity_type", ""))
            elif action == "call_graph":
                return self.get_call_graph(params.get("function", ""), int(params.get("depth", 2)))
            elif action == "dependencies":
                return self.get_file_dependencies(params.get("file_path", ""))
            elif action == "stats":
                return self.query(qtype="stats")
            elif action == "status":
                total = sum(1 for _ in self._entities) if hasattr(self, '_entities') else 0
                return {"success": True, "status": "ready", "entities_cached": total, "db_path": self._db_path}
            return {"success": False, "error": f"Unknown action: {action}"}
        except Exception as e:
            logger.error(f"Graphify error: {e}")
            return {"success": False, "error": str(e)[:200]}

module_class = GraphifyIndex
