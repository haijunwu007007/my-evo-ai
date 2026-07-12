from __future__ import annotations
from modules._base.enterprise_module import EnterpriseModule
# -*- coding: utf-8 -*-
"""持久记忆树 — 持久化知识图谱"""
import os, json, sqlite3, time
from typing import Optional

class MemoryTree(EnterpriseModule):
    def __init__(self, db_path: str = ""):
        self._db = db_path or os.path.join(os.path.dirname(__file__), "..", "memory_tree.db")
        self._conn: Optional[sqlite3.Connection] = None
    
    def _get_db(self):
        if self._conn is None:
            self._conn = sqlite3.connect(self._db)
            self._conn.execute("""CREATE TABLE IF NOT EXISTS nodes(
                id TEXT PRIMARY KEY, parent_id TEXT, type TEXT, title TEXT,
                content TEXT, tags TEXT, created REAL, updated REAL
            )""")
            self._conn.execute("""CREATE TABLE IF NOT EXISTS edges(
                id INTEGER PRIMARY KEY AUTOINCREMENT, from_id TEXT, to_id TEXT, relation TEXT
            )""")
        return self._conn
    
    def add_node(self, node_id: str, title: str, content: str = "", node_type: str = "note", parent: str = "", tags: str = ""):
        db = self._get_db()
        now = time.time()
        db.execute("INSERT OR REPLACE INTO nodes VALUES(?,?,?,?,?,?,?,?)",
                   (node_id, parent or None, node_type, title, content, tags, now, now))
        if parent:
            db.execute("INSERT OR IGNORE INTO edges(from_id,to_id,relation) VALUES(?,?,?)", (node_id, parent, "child_of"))
        db.commit()
    
    def search(self, query: str) -> list:
        db = self._get_db()
        rows = db.execute(
            "SELECT id,title,content,tags,type,created FROM nodes WHERE title LIKE ? OR content LIKE ? OR tags LIKE ? LIMIT 20",
            (f"%{query}%",)*3
        ).fetchall()
        return [{"id":r[0],"title":r[1],"content":r[2][:100],"tags":r[3],"type":r[4],"created":r[5]} for r in rows]
    
    def get_tree(self, root: str = "") -> list:
        db = self._get_db()
        rows = db.execute("SELECT id,parent_id,title,type FROM nodes ORDER BY created DESC LIMIT 100").fetchall()
        return [{"id":r[0],"parent":r[1],"title":r[2],"type":r[3]} for r in rows]
    
    def close(self):
        if self._conn: self._conn.close()
