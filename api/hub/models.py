"""开源中心 — 数据模型"""
from __future__ import annotations
import sqlite3, json, time
from pathlib import Path
from typing import Optional

DB_DIR = Path(__file__).resolve().parent.parent.parent / "core"
DB_PATH = DB_DIR / "hub.db"

def _get_conn():
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_db():
    """初始化数据库表结构"""
    conn = _get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            full_name TEXT,
            source TEXT DEFAULT 'github',
            repo_url TEXT,
            description TEXT DEFAULT '',
            category TEXT DEFAULT '',
            tags TEXT DEFAULT '[]',
            tech_stack TEXT DEFAULT '[]',
            stars INTEGER DEFAULT 0,
            license TEXT DEFAULT '',
            readme TEXT DEFAULT '',
            icon_url TEXT DEFAULT '',
            homepage TEXT DEFAULT '',
            status TEXT DEFAULT 'discovered',
            config TEXT DEFAULT '{}',
            health TEXT DEFAULT '{}',
            port INTEGER DEFAULT 0,
            container_id TEXT DEFAULT '',
            pid INTEGER DEFAULT 0,
            cpu REAL DEFAULT 0,
            memory REAL DEFAULT 0,
            auto_start INTEGER DEFAULT 0,
            version TEXT DEFAULT '1.0.0',
            fork_from TEXT DEFAULT '',
            fork_depth INTEGER DEFAULT 0,
            canvas_x REAL DEFAULT 100,
            canvas_y REAL DEFAULT 100,
            created_at REAL DEFAULT (strftime('%s','now')),
            updated_at REAL DEFAULT (strftime('%s','now'))
        );
        CREATE TABLE IF NOT EXISTS connections (
            id TEXT PRIMARY KEY,
            source_id TEXT NOT NULL,
            target_id TEXT NOT NULL,
            conn_type TEXT DEFAULT 'data_flow',
            config TEXT DEFAULT '{}',
            created_at REAL DEFAULT (strftime('%s','now'))
        );
        CREATE TABLE IF NOT EXISTS composes (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            nodes TEXT DEFAULT '[]',
            edges TEXT DEFAULT '[]',
            unified_port INTEGER DEFAULT 0,
            root_path TEXT DEFAULT '',
            created_at REAL DEFAULT (strftime('%s','now')),
            updated_at REAL DEFAULT (strftime('%s','now'))
        );
        CREATE TABLE IF NOT EXISTS forks (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            parent_id TEXT NOT NULL,
            depth INTEGER DEFAULT 1,
            base_commit TEXT DEFAULT '',
            current_commit TEXT DEFAULT '',
            modified_files TEXT DEFAULT '[]',
            diff_summary TEXT DEFAULT '',
            upstream_url TEXT DEFAULT '',
            last_sync_at REAL DEFAULT 0,
            published INTEGER DEFAULT 0,
            license TEXT DEFAULT 'MIT',
            created_at REAL DEFAULT (strftime('%s','now'))
        );
        CREATE TABLE IF NOT EXISTS templates (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            category TEXT DEFAULT '',
            tags TEXT DEFAULT '[]',
            nodes TEXT DEFAULT '[]',
            edges TEXT DEFAULT '[]',
            author TEXT DEFAULT '',
            downloads INTEGER DEFAULT 0,
            created_at REAL DEFAULT (strftime('%s','now'))
        );
    """)
    conn.commit()
    conn.close()

# ── 项目 CRUD ──

def add_project(proj: dict) -> str:
    conn = _get_conn()
    conn.execute("""INSERT OR REPLACE INTO projects 
        (id,name,full_name,source,repo_url,description,category,tags,tech_stack,stars,license,readme,icon_url,homepage,status,config)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
        proj["id"], proj["name"], proj.get("full_name",""), proj.get("source","github"),
        proj.get("repo_url",""), proj.get("description",""), proj.get("category",""),
        json.dumps(proj.get("tags",[])), json.dumps(proj.get("tech_stack",[])),
        proj.get("stars",0), proj.get("license",""), proj.get("readme",""),
        proj.get("icon_url",""), proj.get("homepage",""), proj.get("status","discovered"),
        json.dumps(proj.get("config",{}))
    ))
    conn.commit(); conn.close()
    return proj["id"]

def get_project(pid: str) -> dict|None:
    conn = _get_conn()
    r = conn.execute("SELECT * FROM projects WHERE id=?", (pid,)).fetchone()
    conn.close()
    if not r: return None
    return dict(r)

def list_projects(status: str="", category: str="", page: int=1, limit: int=20) -> dict:
    conn = _get_conn()
    where = []
    params = []
    if status: where.append("status=?"); params.append(status)
    if category: where.append("category=?"); params.append(category)
    w = ("WHERE "+" AND ".join(where)) if where else ""
    total = conn.execute(f"SELECT COUNT(*) FROM projects {w}", params).fetchone()[0]
    offset = (page-1)*limit
    rows = conn.execute(f"SELECT * FROM projects {w} ORDER BY stars DESC, created_at DESC LIMIT ? OFFSET ?", params+[limit,offset]).fetchall()
    conn.close()
    return {"projects": [dict(r) for r in rows], "total": total, "page": page, "limit": limit}

def update_project(pid: str, updates: dict):
    conn = _get_conn()
    sets = [f"{k}=?" for k in updates]
    vals = list(updates.values()) + [pid]
    conn.execute(f"UPDATE projects SET {','.join(sets)}, updated_at=strftime('%s','now') WHERE id=?", vals)
    conn.commit(); conn.close()

def delete_project(pid: str):
    conn = _get_conn()
    conn.execute("DELETE FROM projects WHERE id=?", (pid,))
    conn.execute("DELETE FROM connections WHERE source_id=? OR target_id=?", (pid,pid))
    conn.commit(); conn.close()

# ── 连接 CRUD ──

def add_connection(conn_data: dict) -> str:
    conn = _get_conn()
    conn.execute("INSERT INTO connections (id,source_id,target_id,conn_type,config) VALUES (?,?,?,?,?)",
        (conn_data["id"], conn_data["source_id"], conn_data["target_id"],
         conn_data.get("conn_type","data_flow"), json.dumps(conn_data.get("config",{}))))
    conn.commit(); conn.close()
    return conn_data["id"]

def list_connections(project_id: str="") -> list:
    conn = _get_conn()
    if project_id:
        rows = conn.execute("SELECT * FROM connections WHERE source_id=? OR target_id=?", (project_id,project_id)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM connections").fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ── 组合 CRUD ──

def add_compose(data: dict) -> str:
    conn = _get_conn()
    conn.execute("INSERT INTO composes (id,name,description,nodes,edges,unified_port,root_path) VALUES (?,?,?,?,?,?,?)",
        (data["id"], data["name"], data.get("description",""),
         json.dumps(data.get("nodes",[])), json.dumps(data.get("edges",[])),
         data.get("unified_port",0), data.get("root_path","")))
    conn.commit(); conn.close()
    return data["id"]

def list_composes() -> list:
    conn = _get_conn()
    rows = conn.execute("SELECT * FROM composes ORDER BY updated_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ── 二次开发 CRUD ──

def add_fork(data: dict) -> str:
    conn = _get_conn()
    conn.execute("INSERT INTO forks (id,name,parent_id,depth,base_commit,upstream_url) VALUES (?,?,?,?,?,?)",
        (data["id"], data["name"], data["parent_id"], data.get("depth",1),
         data.get("base_commit",""), data.get("upstream_url","")))
    conn.commit(); conn.close()
    return data["id"]

def list_forks(parent_id: str="") -> list:
    conn = _get_conn()
    if parent_id:
        rows = conn.execute("SELECT * FROM forks WHERE parent_id=? ORDER BY created_at DESC", (parent_id,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM forks ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ── 模板 CRUD ──

def add_template(data: dict) -> str:
    conn = _get_conn()
    conn.execute("INSERT INTO templates (id,name,description,category,tags,nodes,edges,author) VALUES (?,?,?,?,?,?,?,?)",
        (data["id"], data["name"], data.get("description",""), data.get("category",""),
         json.dumps(data.get("tags",[])), json.dumps(data.get("nodes",[])),
         json.dumps(data.get("edges",[])), data.get("author","")))
    conn.commit(); conn.close()
    return data["id"]

def list_templates(category: str="") -> list:
    conn = _get_conn()
    if category:
        rows = conn.execute("SELECT * FROM templates WHERE category=? ORDER BY downloads DESC", (category,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM templates ORDER BY downloads DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

# 初始化
init_db()
